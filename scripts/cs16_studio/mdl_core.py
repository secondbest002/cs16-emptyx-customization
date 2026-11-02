"""
mdl_core.py - Core binary parser, dynamic texture classifier,
immutable backup manager, and atomic injector for GoldSrc StudioModel (IDST v10).
Integrated with EmptyX Customization config_manager.
"""

import base64
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from .pw_restore import find_model_backup, restore_single_model_file, resolve_weapon_triplet, restore_weapon_models
from .config_manager import config
from PIL import Image

STUDIO_MAGIC = b"IDST"
STUDIO_VERSION = 10

# GoldSrc texture flags
STUDIO_NF_FLATSHADE = 0x0001
STUDIO_NF_CHROME = 0x0002
STUDIO_NF_FULLBRIGHT = 0x0004
STUDIO_NF_NOMIPS = 0x0008
STUDIO_NF_ALPHA = 0x0010
STUDIO_NF_ADDITIVE = 0x0020
STUDIO_NF_MASKED = 0x0040  # Index 255 is transparent

# Texture Roles
ROLE_SKIN = "skin"
ROLE_STICKER = "sticker"
ROLE_GLOVE = "glove"
ROLE_STATTRAK = "stattrak"
ROLE_OTHER = "other"
ROLE_SLEEVE = "sleeve"

GLOVE_KEYWORDS = ("sport", "glove", "hand", "finger")
SLEEVE_KEYWORDS = ("sleeve", "arm", "t_arm", "ct_arm")
STATTRAK_KEYWORDS = ("stattrak", "stat_")


def classify_texture(name: str, flags: int, width: int, height: int) -> Tuple[str, str]:
    """
    Dynamically classifies a texture's role based on name, flags, and dimensions.
    Returns (role, label).
    """
    lower = name.lower()
    base_no_ext = os.path.splitext(lower)[0]

    # Check Glove / Sleeve / Arm
    NON_GLOVE_PARTS = (
        "handguard",
        "hand_guard",
        "handle",
        "handlebar",
        "sidearm",
        "firearm",
        "charm",
        "weapon_charm",
        "armor",
        "armour",
        "armature",
        "alarm",
        "swarm",
        "disarm",
    )
    is_non_glove = any(k in lower for k in NON_GLOVE_PARTS) and not any(k in lower for k in ("glove", "sport"))
    # 1. Check Sleeve / Arm first (Strict separation from Gloves)
    if not is_non_glove:
        is_sleeve = (
            "sleeve" in lower
            or bool(re.search(r"(?:^|[\W_\d])(sleeve|t_arm|ct_arm|arms?)(?:$|[\W_\d])", lower))
            or lower.startswith("sleeve")
            or lower.startswith("arm_")
            or lower.endswith("_arm.bmp")
            or lower in ("arm.bmp", "sleeve.bmp", "t_arm.bmp", "ct_arm.bmp")
        )
        if is_sleeve and not any(k in lower for k in ("glove", "sport")):
            return ROLE_SLEEVE, "Sleeve / Arm"

    # 2. Check Glove / Hand
    if not is_non_glove and any(k in lower for k in GLOVE_KEYWORDS):
        return ROLE_GLOVE, "Gloves / Hand"

    # Check StatTrak
    if any(k in lower for k in STATTRAK_KEYWORDS) or lower.startswith("st_"):
        return ROLE_STATTRAK, "StatTrak Module"

    # Check Masked / Stickers
    # GoldSrc uses flags & STUDIO_NF_MASKED (0x40) for 1-bit transparency (stickers/decals)
    is_masked = bool(flags & STUDIO_NF_MASKED)

    if is_masked:
        if "scope" in lower:
            return ROLE_OTHER, "Scope Lens (Masked)"
        if "sticker" in lower or "decal" in lower:
            return ROLE_STICKER, "Sticker Slot"
        if base_no_ext.isdigit():
            return ROLE_STICKER, f"Sticker Slot {base_no_ext}"
        return ROLE_STICKER, "Sticker / Decal"

    # Not masked
    if "sticker" in lower or "decal" in lower:
        return ROLE_STICKER, "Sticker Slot"

    if "scope" in lower:
        return ROLE_OTHER, "Scope Lens"

    # Multi-part skin body or single skin body
    if base_no_ext.isdigit():
        return ROLE_SKIN, f"Body Part {base_no_ext}"

    return ROLE_SKIN, "Weapon Body Skin"


class MdlTexture:
    """Represents a single texture entry inside a GoldSrc MDL file."""

    def __init__(
        self,
        index: int,
        header_offset: int,
        name: str,
        flags: int,
        width: int,
        height: int,
        data_offset: int,
        raw_data: bytes,
    ):
        self.index = index
        self.header_offset = header_offset
        self.name = name
        self.flags = flags
        self.width = width
        self.height = height
        self.data_offset = data_offset
        self.raw_data = raw_data  # width * height + 768 bytes
        self.size = width * height + 768

        self.role, self.role_label = classify_texture(name, flags, width, height)

    @property
    def is_masked(self) -> bool:
        return bool(self.flags & STUDIO_NF_MASKED)

    @property
    def pixels(self) -> bytes:
        return self.raw_data[: self.width * self.height]

    @property
    def palette(self) -> bytes:
        return self.raw_data[self.width * self.height : self.width * self.height + 768]

    def to_rgba_image(self) -> Image.Image:
        """Decodes the 8-bit indexed texture + palette into a PIL RGBA Image."""
        p_img = Image.frombytes("P", (self.width, self.height), self.pixels)
        pal = list(self.palette)
        while len(pal) < 768:
            pal.extend([0, 0, 0])
        p_img.putpalette(pal[:768])
        rgba = p_img.convert("RGBA")

        # If texture is masked, index 255 is transparent
        if self.is_masked:
            pix_arr = np.frombuffer(self.pixels, dtype=np.uint8)
            rgba_arr = np.array(rgba)
            rgba_arr[pix_arr.reshape((self.height, self.width)) == 255, 3] = 0
            rgba = Image.fromarray(rgba_arr, mode="RGBA")

        return rgba

    def to_png_bytes(self) -> bytes:
        """Converts texture to PNG bytes."""
        img = self.to_rgba_image()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def to_base64_data_uri(self) -> str:
        """Converts texture to a base64 data URI for HTML preview."""
        png_data = self.to_png_bytes()
        encoded = base64.b64encode(png_data).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "name": self.name,
            "flags": self.flags,
            "flags_hex": f"0x{self.flags:04X}",
            "is_masked": self.is_masked,
            "width": self.width,
            "height": self.height,
            "size": self.size,
            "role": self.role,
            "role_label": self.role_label,
        }


class MdlModel:
    """GoldSrc StudioModel parser and manipulator."""

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath).resolve()
        if not self.filepath.is_file():
            raise FileNotFoundError(f"Model file not found: {self.filepath}")

        with open(self.filepath, "rb") as f:
            self.data = bytearray(f.read())

        self.textures: List[MdlTexture] = []
        self._parse()

    def _parse(self):
        if len(self.data) < 188:
            raise ValueError(f"File too small for GoldSrc MDL: {len(self.data)} bytes")

        magic, ver = struct.unpack_from("<4sI", self.data, 0)
        if magic != STUDIO_MAGIC or ver != STUDIO_VERSION:
            raise ValueError(
                f"Invalid GoldSrc StudioModel magic/ver: magic={magic}, ver={ver} (expected IDST v10)"
            )

        numtextures, textureindex = struct.unpack_from("<II", self.data, 180)
        self.textures = []

        for i in range(numtextures):
            offset = textureindex + i * 80
            if offset + 80 > len(self.data):
                break
            tname, flags, w, h, idx = struct.unpack_from("<64sIIII", self.data, offset)
            name_str = tname.split(b"\x00")[0].decode("latin1", errors="ignore")
            size = w * h + 768
            raw_data = bytes(self.data[idx : idx + size])

            tex = MdlTexture(
                index=i,
                header_offset=offset,
                name=name_str,
                flags=flags,
                width=w,
                height=h,
                data_offset=idx,
                raw_data=raw_data,
            )
            self.textures.append(tex)

    def get_texture_by_name(self, name: str) -> Optional[MdlTexture]:
        name_lower = name.lower()
        for t in self.textures:
            if t.name.lower() == name_lower:
                return t
        # Partial match
        for t in self.textures:
            if name_lower in t.name.lower():
                return t
        return None

    def get_texture_by_index(self, index: int) -> Optional[MdlTexture]:
        if 0 <= index < len(self.textures):
            return self.textures[index]
        return None

    def find_texture(
        self,
        identifier: Union[int, str],
        prefer_role: Optional[str] = None,
    ) -> Optional[MdlTexture]:
        if isinstance(identifier, int):
            return self.get_texture_by_index(identifier)

        ident_str = str(identifier).strip()
        ident_lower = ident_str.lower()

        # 1. Exact name match (e.g. "1.bmp", "sticker_1.bmp", "pist_223_vanila.bmp")
        for t in self.textures:
            if t.name.lower() == ident_lower:
                return t

        # 2. Match with .bmp extension (e.g. "1" -> "1.bmp", "sticker_1" -> "sticker_1.bmp")
        bmp_name = ident_lower if ident_lower.endswith(".bmp") else f"{ident_lower}.bmp"
        if prefer_role == ROLE_STICKER:
            for s in self.get_stickers():
                if s.name.lower() == bmp_name:
                    return s
        for t in self.textures:
            if t.name.lower() == bmp_name:
                return t

        # 3. Check sticker slot indexing if numeric
        stickers = self.get_stickers()
        if ident_str.isdigit():
            val = int(ident_str)
            # Check if any sticker name contains this digit (e.g. sticker_1.bmp, 1.bmp)
            for s in stickers:
                if f"_{val}." in s.name.lower() or s.name.lower().startswith(f"{val}."):
                    return s
            if prefer_role == ROLE_STICKER or (stickers and 1 <= val <= len(stickers)):
                if 1 <= val <= len(stickers):
                    return stickers[val - 1]

        # 4. Partial substring in texture name
        if prefer_role == ROLE_STICKER:
            for s in stickers:
                if ident_lower in s.name.lower():
                    return s
        for t in self.textures:
            if ident_lower in t.name.lower():
                return t

        # 5. Fallback: 0-based index if numeric
        if ident_str.isdigit():
            idx = int(ident_str)
            if 0 <= idx < len(self.textures):
                return self.textures[idx]

        return None

    def get_stickers(self) -> List[MdlTexture]:
        return [t for t in self.textures if t.role == ROLE_STICKER]

    def get_skins(self) -> List[MdlTexture]:
        return [t for t in self.textures if t.role == ROLE_SKIN]

    def get_gloves(self) -> List[MdlTexture]:
        return [t for t in self.textures if t.role == ROLE_GLOVE]

    def get_sleeves(self) -> List[MdlTexture]:
        return [t for t in self.textures if t.role == ROLE_SLEEVE]

    def inject_texture_payload(
        self,
        tex_ref: Union[int, str, MdlTexture],
        new_payload: bytes,
        new_flags: Optional[int] = None,
    ) -> bool:
        """
        Injects raw texture bytes (width * height + 768 palette) into the model buffer.
        """
        if isinstance(tex_ref, MdlTexture):
            target_tex = tex_ref
        else:
            target_tex = self.find_texture(tex_ref)

        if not target_tex:
            raise KeyError(f"Texture '{tex_ref}' not found in model.")

        if len(new_payload) != target_tex.size:
            raise ValueError(
                f"Payload size mismatch for '{target_tex.name}': "
                f"got {len(new_payload)} bytes, expected {target_tex.size} bytes "
                f"({target_tex.width}x{target_tex.height} + 768)."
            )

        # Inject payload
        off = target_tex.data_offset
        self.data[off : off + target_tex.size] = new_payload
        target_tex.raw_data = bytes(new_payload)

        # Update flags if requested
        if new_flags is not None:
            flag_off = target_tex.header_offset + 64
            struct.pack_into("<I", self.data, flag_off, new_flags)
            target_tex.flags = new_flags
            target_tex.role, target_tex.role_label = classify_texture(
                target_tex.name, new_flags, target_tex.width, target_tex.height
            )

        return True

    def set_texture_flags(
        self,
        tex_ref: Union[int, str, MdlTexture],
        new_flags: int,
    ) -> bool:
        """Updates texture flags directly in the StudioModel header."""
        target_tex = tex_ref if isinstance(tex_ref, MdlTexture) else self.find_texture(tex_ref)
        if not target_tex:
            return False
        flag_off = target_tex.header_offset + 64
        struct.pack_into("<I", self.data, flag_off, new_flags)
        target_tex.flags = new_flags
        target_tex.role, target_tex.role_label = classify_texture(
            target_tex.name, new_flags, target_tex.width, target_tex.height
        )
        return True

    def toggle_chrome_shimmer(
        self,
        tex_ref: Union[int, str, MdlTexture],
        enable: Optional[bool] = None,
    ) -> bool:
        """
        Toggles STUDIO_NF_CHROME (0x02) on a texture.
        Enables reflective metallic environment mapping in GoldSrc engine.
        """
        target_tex = tex_ref if isinstance(tex_ref, MdlTexture) else self.find_texture(tex_ref)
        if not target_tex:
            return False
        if enable is None:
            new_flags = target_tex.flags ^ STUDIO_NF_CHROME
        elif enable:
            new_flags = target_tex.flags | STUDIO_NF_CHROME
        else:
            new_flags = target_tex.flags & ~STUDIO_NF_CHROME
        return self.set_texture_flags(target_tex, new_flags)

    def reposition_slot(
        self,
        slot_identifier: Union[int, str],
        target_pos_three: Union[List[float], Tuple[float, float, float], np.ndarray],
        target_normal_three: Union[List[float], Tuple[float, float, float], np.ndarray],
        scale: float = 1.0,
        rotation: float = 0.0,
        bone_id: Optional[int] = None,
    ) -> dict:
        """
        Reposition an existing sticker slot in-place (Solusi B) delegating to slot_geometry.
        """
        from .slot_geometry import reposition_slot_quad
        res = reposition_slot_quad(
            self.filepath,
            slot_identifier=slot_identifier,
            target_pos_three=target_pos_three,
            target_normal_three=target_normal_three,
            scale=scale,
            rotation=rotation,
            bone_id=bone_id,
        )
        with open(self.filepath, "rb") as f:
            self.data = bytearray(f.read())
        self._parse()
        return res

    def inject_new_slot(
        self,
        slot_name: Optional[str] = None,
        target_pos_three: Optional[Union[List[float], Tuple[float, float, float], np.ndarray]] = None,
        target_normal_three: Optional[Union[List[float], Tuple[float, float, float], np.ndarray]] = None,
        scale: float = 1.0,
        rotation: float = 0.0,
        image_source: Optional[Union[str, Path, bytes, Image.Image]] = None,
        fx: str = "foil",
        bone_id: Optional[int] = None,
    ) -> dict:
        """
        Inject a new 3D sticker slot submesh and texture (Solusi A) delegating to slot_geometry.
        """
        from .slot_geometry import inject_new_slot_quad
        res = inject_new_slot_quad(
            self.filepath,
            slot_name=slot_name,
            target_pos_three=target_pos_three,
            target_normal_three=target_normal_three,
            scale=scale,
            rotation=rotation,
            image_source=image_source,
            fx=fx,
            bone_id=bone_id,
        )
        with open(self.filepath, "rb") as f:
            self.data = bytearray(f.read())
        self._parse()
        return res

    def validate_health(self) -> dict:
        """
        Validates model structural integrity against GoldSrc IDST v10 engine constraints.
        """
        from .slot_geometry import validate_model_health
        return validate_model_health(self.filepath)

    def get_backup_dir(self) -> Path:
        """Returns the model-specific snapshot backup directory."""
        b_dir = self.filepath.parent / ".studio_backups" / self.filepath.stem
        b_dir.mkdir(parents=True, exist_ok=True)
        return b_dir

    def create_immutable_backup_if_needed(self) -> Path:
        """
        Creates an immutable original backup (.orig.mdl) if it does not already exist.
        This file is NEVER overwritten once created.
        """
        orig_path = self.filepath.with_suffix(".orig.mdl")
        if not orig_path.exists():
            shutil.copy2(self.filepath, orig_path)
        return orig_path

    def save_slot_snapshot(self, texture: MdlTexture):
        """Saves a single texture snapshot before modifying it."""
        b_dir = self.get_backup_dir()
        bin_path = b_dir / f"{texture.name}.bin"
        if not bin_path.exists():
            with open(bin_path, "wb") as f:
                f.write(texture.raw_data)
        # Also save metadata (flags, dimensions)
        meta_path = b_dir / f"{texture.name}.json"
        if not meta_path.exists():
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({"flags": texture.flags, "width": texture.width, "height": texture.height}, f)
        # Also save PNG preview for inspection
        png_path = b_dir / f"{texture.name}.png"
        if not png_path.exists():
            with open(png_path, "wb") as f:
                f.write(texture.to_png_bytes())

    def save_atomic(self, dest_path: Optional[Union[str, Path]] = None, create_backup: bool = True) -> Path:
        """
        Safely writes the model data using an atomic swap (.tmp -> dest).
        Guarantees that corrupt writes or crashes cannot destroy the existing file.
        """
        out_path = Path(dest_path).resolve() if dest_path else self.filepath
        out_dir = out_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        # Validate internal structure
        if len(self.data) < 188:
            raise ValueError("Refusing to save corrupted MDL: data too short.")
        magic, ver = struct.unpack_from("<4sI", self.data, 0)
        if magic != STUDIO_MAGIC or ver != STUDIO_VERSION:
            raise ValueError(f"Corrupted StudioModel in memory (magic={magic}, ver={ver})")

        # Create immutable original backup if modifying in place
        if create_backup and out_path == self.filepath and out_path.exists():
            self.create_immutable_backup_if_needed()

        tmp_path = out_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "wb") as f:
                f.write(self.data)

            # Validate written file
            with open(tmp_path, "rb") as f:
                chk_magic, chk_ver = struct.unpack("<4sI", f.read(8))
                if chk_magic != STUDIO_MAGIC or chk_ver != STUDIO_VERSION:
                    raise IOError("Temp file verification failed!")

            # Atomic replace
            os.replace(tmp_path, out_path)
            self.filepath = out_path
            return out_path
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def restore_from_immutable_original(self) -> bool:
        """Restores the model from its immutable .orig.mdl backup (or fallback .bak)."""
        ok, msg, _ = restore_single_model_file(self.filepath)
        if ok:
            with open(self.filepath, "rb") as f:
                self.data = bytearray(f.read())
            self._parse()
            return True
        return False

    def revert_texture_from_backup(
        self,
        tex_ref: Union[int, str, MdlTexture],
        prefer_role: Optional[str] = None,
    ) -> bool:
        """
        Reverts a single texture back to its original state using .orig.mdl or slot snapshot.
        """
        if isinstance(tex_ref, MdlTexture):
            target_tex = tex_ref
        else:
            target_tex = self.find_texture(tex_ref, prefer_role=prefer_role)

        if not target_tex:
            return False

        orig_path = self.filepath.with_suffix(".orig.mdl")
        b_dir = self.get_backup_dir()

        # Helper to check if backup exists for a given texture
        def do_revert(tex: MdlTexture) -> bool:
            if orig_path.exists():
                orig_model = MdlModel(orig_path)
                orig_tex = orig_model.find_texture(tex.name)
                if orig_tex and orig_tex.size == tex.size:
                    self.inject_texture_payload(tex, orig_tex.raw_data, new_flags=orig_tex.flags)
                    self.save_atomic(create_backup=False)
                    return True

            bin_path = b_dir / f"{tex.name}.bin"
            meta_path = b_dir / f"{tex.name}.json"
            if bin_path.exists():
                with open(bin_path, "rb") as f:
                    saved_raw = f.read()
                if len(saved_raw) == tex.size:
                    saved_flags = None
                    if meta_path.exists():
                        try:
                            saved_flags = json.loads(meta_path.read_text(encoding="utf-8")).get("flags")
                        except Exception:
                            pass
                    self.inject_texture_payload(tex, saved_raw, new_flags=saved_flags)
                    self.save_atomic(create_backup=False)
                    return True
            return False

        # Try primary resolved texture
        if do_revert(target_tex):
            return True

        # If primary failed and input was digit, check sticker slots or body parts with backups
        if isinstance(tex_ref, str) and tex_ref.strip().isdigit():
            val = int(tex_ref.strip())
            for s in self.get_stickers():
                if (f"_{val}." in s.name.lower() or s.name.lower().startswith(f"{val}.")) and s != target_tex:
                    if do_revert(s):
                        return True

        return False


def resolve_model_path(
    path_or_weapon: str,
    team: str = "ct",
    root_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """
    Resolves weapon name or model path into an absolute file path.
    Prioritizes active custom_skins folders for the chosen team.
    Defaults root_dir to config.get_game_root().
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    candidate_path = Path(path_or_weapon)

    # 1. Direct path check
    if candidate_path.is_file():
        return candidate_path.resolve()
    if (root / candidate_path).is_file():
        return (root / candidate_path).resolve()

    # Normalize name to v_{weapon}.mdl
    base = candidate_path.name.lower()
    if base.endswith(".mdl"):
        base = base[:-4]
    if base.startswith("v_"):
        base = base[2:]
    weapon_key = base
    mdl_filename = f"v_{weapon_key}.mdl"

    team = team.lower()
    other_team = "t" if team == "ct" else "ct"

    search_paths = [
        root / "cstrike" / "models" / "custom_skins" / team / mdl_filename,
        root / "cstrike" / "models" / "custom_skins" / other_team / mdl_filename,
        root / "cstrike" / "models" / "csgo_skins" / team / mdl_filename,
        root / "cstrike" / "models" / "csgo_skins" / other_team / mdl_filename,
        root / "cstrike_hd" / "models" / mdl_filename,
        root / "cstrike" / "models" / mdl_filename,
    ]

    for p in search_paths:
        if p.is_file():
            return p.resolve()

    # Deep recursive search inside cstrike/models
    models_dir = root / "cstrike" / "models"
    if models_dir.is_dir():
        for f in models_dir.rglob("*.mdl"):
            if f.name.lower() == mdl_filename.lower():
                return f.resolve()

    raise FileNotFoundError(
        f"Could not find model for weapon '{path_or_weapon}' (team={team}) in {root}."
    )


def discover_available_models(root_dir: Optional[Union[str, Path]] = None) -> Dict[str, List[dict]]:
    """
    Discovers all viewmodels (v_*.mdl) grouped by team ('ct', 't', 'all').
    Defaults root_dir to config.get_game_root().
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    results = {"ct": [], "t": [], "all": []}
    seen_team_paths = set()
    seen_all_paths = set()

    def add_model(team_key: str, mdl_path: Path):
        p_str = str(mdl_path.resolve())
        pair_key = (team_key, p_str)
        if pair_key not in seen_team_paths:
            seen_team_paths.add(pair_key)
            name = mdl_path.stem
            weapon = name[2:] if name.startswith("v_") else name
            orig_exists = mdl_path.with_suffix(".orig.mdl").exists()

            item = {
                "name": name,
                "weapon": weapon,
                "path": p_str,
                "team": team_key,
                "size": mdl_path.stat().st_size,
                "has_orig_backup": orig_exists,
            }
            results[team_key].append(item)

        if p_str not in seen_all_paths:
            seen_all_paths.add(p_str)
            name = mdl_path.stem
            weapon = name[2:] if name.startswith("v_") else name
            orig_exists = mdl_path.with_suffix(".orig.mdl").exists()
            results["all"].append({
                "name": name,
                "weapon": weapon,
                "path": p_str,
                "team": team_key,
                "size": mdl_path.stat().st_size,
                "has_orig_backup": orig_exists,
            })

    for team in ("ct", "t"):
        team_dir = root / "cstrike" / "models" / "custom_skins" / team
        if team_dir.is_dir():
            for f in sorted(team_dir.glob("v_*.mdl")):
                if not f.name.endswith(".orig.mdl") and not f.name.endswith(".bak"):
                    if f.name.startswith("v_knife"):
                        add_model("ct", f)
                        add_model("t", f)
                    else:
                        add_model(team, f)

        # csgo_skins fallback
        csgo_team_dir = root / "cstrike" / "models" / "csgo_skins" / team
        if csgo_team_dir.is_dir():
            for f in sorted(csgo_team_dir.glob("v_*.mdl")):
                if not f.name.endswith(".orig.mdl") and not f.name.endswith(".bak"):
                    if f.name.startswith("v_knife"):
                        add_model("ct", f)
                        add_model("t", f)
                    else:
                        add_model(team, f)

    # General cstrike_hd / cstrike (accessible by both CT and T)
    for d in (root / "cstrike_hd" / "models", root / "cstrike" / "models"):
        if d.is_dir():
            for f in sorted(d.glob("v_*.mdl")):
                if not f.name.endswith(".orig.mdl") and not f.name.endswith(".bak"):
                    add_model("ct", f)
                    add_model("t", f)

    # Cross-reference skin_inventory.ini for explicitly assigned team models
    inv_path = root / "cstrike" / "addons" / "amxmodx" / "configs" / "skin_inventory.ini"
    if inv_path.is_file():
        try:
            with open(inv_path, "r", encoding="utf-8", errors="ignore") as f:
                cur_team = None
                for line in f:
                    s = line.strip()
                    if not s or s.startswith(";"):
                        continue
                    m = re.match(r"^\[(CT|T)_[A-Za-z0-9_]+\]$", s, re.IGNORECASE)
                    if m:
                        cur_team = m.group(1).lower()
                        continue
                    if cur_team:
                        tokens = re.findall(r'"([^"]*)"', s)
                        if len(tokens) >= 2:
                            v_rel = tokens[1]
                            v_file = root / "cstrike" / v_rel
                            if not v_file.is_file():
                                v_file = root / v_rel
                            if v_file.is_file() and v_file.name.startswith("v_") and not v_file.name.endswith(".bak") and not v_file.name.endswith(".orig.mdl"):
                                add_model(cur_team, v_file)
        except Exception:
            pass

    return results


def batch_inject_sticker(
    weapons: List[str],
    sticker_image: Union[str, Path, bytes],
    slot: Union[int, str] = 1,
    team: str = "ct",
    mode: str = "fit",
    scale: float = 1.0,
    fx: str = "matte",
    root_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, dict]:
    """
    Applies a sticker across multiple weapons in a single batch operation.
    Returns mapping of weapon -> result dict.
    Defaults root_dir to config.get_game_root().
    """
    from .image_pipeline import process_image_for_texture

    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    results = {}

    for w in weapons:
        w_clean = w.strip()
        if not w_clean:
            continue
        try:
            mdl_path = resolve_model_path(w_clean, team=team, root_dir=root)
            model = MdlModel(mdl_path)
            stickers = model.get_stickers()
            if not stickers:
                results[w_clean] = {
                    "success": False,
                    "weapon": w_clean,
                    "error": f"No dedicated sticker slots found in {mdl_path.name}",
                }
                continue

            target_tex = None
            slot_str = str(slot).strip()
            if slot_str.isdigit():
                slot_num = int(slot_str)
                for s in stickers:
                    if slot_str in s.name:
                        target_tex = s
                        break
                if not target_tex and 1 <= slot_num <= len(stickers):
                    target_tex = stickers[slot_num - 1]
            else:
                target_tex = model.find_texture(slot_str)

            if not target_tex:
                target_tex = stickers[0]

            new_flags = target_tex.flags
            if fx in ("chrome", "foil"):
                new_flags = STUDIO_NF_MASKED | STUDIO_NF_CHROME
            elif fx == "glow":
                new_flags = STUDIO_NF_MASKED | STUDIO_NF_ADDITIVE
            elif fx == "matte":
                new_flags = STUDIO_NF_MASKED

            model.save_slot_snapshot(target_tex)

            payload, _ = process_image_for_texture(
                sticker_image,
                target_tex.width,
                target_tex.height,
                is_masked=True,
                mode=mode,
                scale_multiplier=scale,
            )

            model.inject_texture_payload(target_tex, payload, new_flags=new_flags)
            saved_path = model.save_atomic(create_backup=True)

            results[w_clean] = {
                "success": True,
                "weapon": w_clean,
                "slot_name": target_tex.name,
                "model_name": mdl_path.name,
                "saved_path": str(saved_path),
            }
        except Exception as e:
            results[w_clean] = {
                "success": False,
                "weapon": w_clean,
                "error": str(e),
            }

    return results


def make_bone_matrix(pos, rot) -> np.ndarray:
    """Half-Life SDK AngleMatrix (rot: [0]=roll/X, [1]=pitch/Y, [2]=yaw/Z)."""
    sr = math.sin(rot[0]); cr = math.cos(rot[0])
    sp = math.sin(rot[1]); cp = math.cos(rot[1])
    sy = math.sin(rot[2]); cy = math.cos(rot[2])
    m = np.identity(4, dtype=np.float32)
    m[0, 0] = cp * cy
    m[0, 1] = sr * sp * cy + cr * -sy
    m[0, 2] = cr * sp * cy + -sr * -sy
    m[0, 3] = pos[0]

    m[1, 0] = cp * sy
    m[1, 1] = sr * sp * sy + cr * cy
    m[1, 2] = cr * sp * sy + -sr * cy
    m[1, 3] = pos[1]

    m[2, 0] = -sp
    m[2, 1] = sr * cp
    m[2, 2] = cr * cp
    m[2, 3] = pos[2]
    return m


def extract_model_3d(model_path: Union[str, Path]) -> dict:
    """
    Parses StudioModel geometry (IDST v10), transforms vertices with default bone matrices,
    and groups meshes by texture index for interactive Three.js WebGL rendering.
    """
    path = Path(model_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Model file not found: {path}")

    with open(path, "rb") as f:
        data = f.read()

    if len(data) < 188:
        raise ValueError(f"File too small for GoldSrc StudioModel: {len(data)} bytes")

    magic, ver = struct.unpack_from("<4sI", data, 0)
    if magic != STUDIO_MAGIC or ver != STUDIO_VERSION:
        raise ValueError(f"Invalid GoldSrc StudioModel header (magic={magic}, ver={ver})")

    # Textures
    numtextures, textureindex = struct.unpack_from("<II", data, 180)
    textures = []
    for i in range(numtextures):
        offset = textureindex + i * 80
        if offset + 80 > len(data):
            break
        tname, flags, w, h, idx = struct.unpack_from("<64sIIII", data, offset)
        name_str = tname.split(b"\x00")[0].decode("latin1", errors="ignore")
        is_masked = bool(flags & STUDIO_NF_MASKED)
        is_chrome = bool(flags & STUDIO_NF_CHROME)
        is_additive = bool(flags & STUDIO_NF_ADDITIVE)
        textures.append({
            "index": i,
            "name": name_str,
            "flags": flags,
            "is_masked": is_masked,
            "is_chrome": is_chrome,
            "is_additive": is_additive,
            "width": w,
            "height": h,
        })

    # Bones & Transformations
    numbones, boneindex = struct.unpack_from("<II", data, 140)
    bones = []
    for b in range(numbones):
        b_offset = boneindex + b * 112
        if b_offset + 112 > len(data):
            break
        name_bytes, parent, flags = struct.unpack_from("<32sii", data, b_offset)
        vals = struct.unpack_from("<6f", data, b_offset + 64)
        scales = struct.unpack_from("<6f", data, b_offset + 88)
        bones.append({
            "parent": parent,
            "pos": list(vals[:3]),
            "rot": list(vals[3:]),
            "scale": list(scales),
        })

    bind_pos = [list(b["pos"]) for b in bones]
    bind_rot = [list(b["rot"]) for b in bones]

    # Sequence 0 ('idle1' or initial holding pose) evaluation
    numseq = 0
    seqindex = 0
    numseqgroups = 0
    seqgroupindex = 0
    if len(data) >= 180:
        numseq, seqindex = struct.unpack_from("<II", data, 164)
        numseqgroups, seqgroupindex = struct.unpack_from("<II", data, 172)
        if numseq > 0 and 0 < seqindex < len(data) and numseqgroups > 0 and 0 < seqgroupindex < len(data):
            try:
                _, _, _, seqgroup_data_off = struct.unpack_from("<32s64sii", data, seqgroupindex)
                if seqindex + 176 <= len(data):
                    animindex = struct.unpack_from("<i", data, seqindex + 124)[0]
                    seqgroup = struct.unpack_from("<i", data, seqindex + 156)[0]
                    if seqgroup == 0 and animindex > 0:
                        anim_base = seqgroup_data_off + animindex
                        for b_idx in range(len(bones)):
                            bone_anim_off = anim_base + b_idx * 12
                            if bone_anim_off + 12 <= len(data):
                                anim_offsets = struct.unpack_from("<6H", data, bone_anim_off)
                                b_scales = bones[b_idx]["scale"]
                                for j in range(3):
                                    off_j = anim_offsets[j]
                                    if off_j != 0:
                                        ptr = bone_anim_off + off_j
                                        if ptr + 4 <= len(data):
                                            valid, _ = struct.unpack_from("<BB", data, ptr)
                                            if valid > 0:
                                                anim_val = struct.unpack_from("<h", data, ptr + 2)[0]
                                                bones[b_idx]["pos"][j] += anim_val * b_scales[j]
                                for j in range(3):
                                    off_j = anim_offsets[j + 3]
                                    if off_j != 0:
                                        ptr = bone_anim_off + off_j
                                        if ptr + 4 <= len(data):
                                            valid, _ = struct.unpack_from("<BB", data, ptr)
                                            if valid > 0:
                                                anim_val = struct.unpack_from("<h", data, ptr + 2)[0]
                                                bones[b_idx]["rot"][j] += anim_val * b_scales[j + 3]
            except Exception:
                pass

    world_matrices = []
    for b in bones:
        local_m = make_bone_matrix(b["pos"], b["rot"])
        if b["parent"] == -1 or b["parent"] < 0 or b["parent"] >= len(world_matrices):
            world_matrices.append(local_m)
        else:
            world_matrices.append(np.matmul(world_matrices[b["parent"]], local_m))

    # Read skinindex table (replaceable textures / skin families)
    numskinref, numskinfamilies, skinindex = struct.unpack_from("<III", data, 192)
    skin_table = []
    if numskinref > 0 and 0 < skinindex < len(data):
        total_entries = numskinref * max(1, numskinfamilies)
        if skinindex + total_entries * 2 <= len(data):
            skin_table = list(struct.unpack_from(f"<{total_entries}h", data, skinindex))

    # Mesh accumulation grouped by (texture skinref, bone_id) to prevent vertex tearing during inspect animations
    grouped_meshes = {}

    numbodyparts, bodypartindex = struct.unpack_from("<II", data, 204)
    for bp in range(numbodyparts):
        bp_offset = bodypartindex + bp * 76
        if bp_offset + 76 > len(data):
            break
        name_bytes, nummodels, base, modelindex = struct.unpack_from("<64siii", data, bp_offset)
        for m in range(nummodels):
            m_offset = modelindex + m * 112
            if m_offset + 112 > len(data):
                break
            (
                m_name, m_type, m_radius,
                nummesh, meshindex,
                numverts, vertinfoindex, vertindex,
                numnorms, norminfoindex, normindex,
                numgroups, groupindex
            ) = struct.unpack_from("<64sif10I", data, m_offset)

            # Unpack and transform model vertices into world space
            transformed_verts = []
            for v_i in range(numverts):
                v_off = vertindex + v_i * 12
                if v_off + 12 > len(data):
                    break
                vx, vy, vz = struct.unpack_from("<3f", data, v_off)
                bone_id = data[vertinfoindex + v_i] if (vertinfoindex + v_i) < len(data) else 0
                if bone_id < len(world_matrices):
                    v_vec = np.array([vx, vy, vz, 1.0], dtype=np.float32)
                    tw = np.matmul(world_matrices[bone_id], v_vec)
                    three_x = float(-tw[1])
                    three_y = float(tw[2])
                    three_z = float(-tw[0])
                else:
                    three_x, three_y, three_z = float(-vy), float(vz), float(-vx)
                transformed_verts.append((three_x, three_y, three_z, bone_id))

            for mesh_i in range(nummesh):
                mesh_offset = meshindex + mesh_i * 20
                if mesh_offset + 20 > len(data):
                    break
                numtris, triindex, skinref, _, _ = struct.unpack_from("<5i", data, mesh_offset)
                actual_tex_index = skinref
                if skin_table and 0 <= skinref < numskinref:
                    actual_tex_index = skin_table[skinref]
                if actual_tex_index < 0 or actual_tex_index >= numtextures:
                    continue

                tex_w = max(1, textures[actual_tex_index]["width"])
                tex_h = max(1, textures[actual_tex_index]["height"])

                pos = triindex
                while pos + 2 <= len(data):
                    strip_len = struct.unpack_from("<h", data, pos)[0]
                    pos += 2
                    if strip_len == 0:
                        break
                    count = abs(strip_len)
                    is_strip = strip_len > 0

                    strip_verts = []
                    for _ in range(count):
                        if pos + 8 > len(data):
                            break
                        v_idx, n_idx, s, t = struct.unpack_from("<4h", data, pos)
                        pos += 8
                        if v_idx < len(transformed_verts):
                            vx, vy, vz, v_bone = transformed_verts[v_idx]
                        else:
                            vx, vy, vz, v_bone = 0.0, 0.0, 0.0, 0
                        u = float(s) / float(tex_w)
                        v = 1.0 - (float(t) / float(tex_h))
                        strip_verts.append((vx, vy, vz, u, v, v_bone))

                    if len(strip_verts) < count:
                        break

                    # Triangulate
                    if is_strip:
                        for k in range(count - 2):
                            if k % 2 == 0:
                                tri = (strip_verts[k], strip_verts[k + 1], strip_verts[k + 2])
                            else:
                                tri = (strip_verts[k + 1], strip_verts[k], strip_verts[k + 2])
                            tri_bone = tri[0][5]
                            key = (actual_tex_index, tri_bone)
                            if key not in grouped_meshes:
                                grouped_meshes[key] = {"positions": [], "uvs": [], "bone_ids": []}
                            for sv in tri:
                                grouped_meshes[key]["positions"].extend([sv[0], sv[1], sv[2]])
                                grouped_meshes[key]["uvs"].extend([sv[3], sv[4]])
                                grouped_meshes[key]["bone_ids"].append(sv[5])
                    else:
                        for k in range(1, count - 1):
                            tri = (strip_verts[0], strip_verts[k], strip_verts[k + 1])
                            tri_bone = tri[0][5]
                            key = (actual_tex_index, tri_bone)
                            if key not in grouped_meshes:
                                grouped_meshes[key] = {"positions": [], "uvs": [], "bone_ids": []}
                            for sv in tri:
                                grouped_meshes[key]["positions"].extend([sv[0], sv[1], sv[2]])
                                grouped_meshes[key]["uvs"].extend([sv[3], sv[4]])
                                grouped_meshes[key]["bone_ids"].append(sv[5])

    mesh_list = []
    all_positions = []
    weapon_positions = []

    for (skinref, tri_bone), mesh_data in grouped_meshes.items():
        if not mesh_data["positions"]:
            continue
        tex = textures[skinref]
        role, role_label = classify_texture(tex["name"], tex["flags"], tex["width"], tex["height"])

        slot_identifier = None
        if role == ROLE_STICKER:
            base_name = os.path.splitext(tex["name"].lower())[0]
            if base_name.isdigit():
                slot_identifier = f"Slot {base_name}"
            elif "_" in base_name and base_name.split("_")[-1].isdigit():
                slot_identifier = f"Slot {base_name.split('_')[-1]}"
            else:
                slot_identifier = tex["name"]

        mesh_list.append({
            "texture_index": skinref,
            "texture_name": tex["name"],
            "role": role,
            "role_label": role_label,
            "slot_identifier": slot_identifier,
            "bone_id": tri_bone,
            "is_masked": tex["is_masked"],
            "is_chrome": tex["is_chrome"],
            "is_additive": tex["is_additive"],
            "positions": mesh_data["positions"],
            "uvs": mesh_data["uvs"],
            "vertex_count": len(mesh_data["positions"]) // 3,
        })
        all_positions.extend(mesh_data["positions"])
        if role not in (ROLE_GLOVE, ROLE_SLEEVE):
            weapon_positions.extend(mesh_data["positions"])

    def calc_bounds(positions):
        if not positions:
            return {
                "center": [0.0, 0.0, 0.0],
                "radius": 10.0,
                "size": [0.0, 0.0, 0.0],
                "min": [0.0, 0.0, 0.0],
                "max": [0.0, 0.0, 0.0],
            }
        xs = positions[0::3]
        ys = positions[1::3]
        zs = positions[2::3]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        min_z, max_z = min(zs), max(zs)
        center = [(min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0]
        size = [max_x - min_x, max_y - min_y, max_z - min_z]
        radius = math.sqrt(size[0] ** 2 + size[1] ** 2 + size[2] ** 2) / 2.0
        return {
            "center": center,
            "radius": radius,
            "size": size,
            "min": [min_x, min_y, min_z],
            "max": [max_x, max_y, max_z],
        }

    overall_bounds = calc_bounds(all_positions)
    weapon_bounds = calc_bounds(weapon_positions) if weapon_positions else overall_bounds

    return {
        "success": True,
        "mesh_count": len(mesh_list),
        "meshes": mesh_list,
        "bounds": overall_bounds,
        "weapon_bounds": weapon_bounds,
    }
