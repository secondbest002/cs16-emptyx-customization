"""
pw_restore.py - Player (p_*.mdl) and World (w_*.mdl) model resolver,
backup detector, and atomic restoration engine for CS 1.6 Asset Studio Pro.
Integrated with EmptyX Customization config_manager.
GoldSrc StudioModel (IDST v10) compatible.
"""

import base64
import datetime
import io
import os
from pathlib import Path
import shutil
import struct
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image

from .config_manager import config

STUDIO_MAGIC = b"IDST"
STUDIO_VERSION = 10


BACKUP_FOLDER_NAMES = ["backup", "backups", ".backup", ".studio_backups"]


def get_model_backup_dir(
    model_path: Union[str, Path],
    folder_name: str = "backup",
    create: bool = True,
) -> Path:
    """Returns the dedicated backup folder for the model."""
    p = Path(model_path).resolve()
    b_dir = p.parent / folder_name
    if create:
        b_dir.mkdir(parents=True, exist_ok=True)
    return b_dir


def get_model_backup_path(
    model_path: Union[str, Path],
    ext: str = ".orig.mdl",
    folder_name: str = "backup",
) -> Path:
    """Returns the full path to a model backup inside the dedicated backup directory."""
    b_dir = get_model_backup_dir(model_path, folder_name=folder_name, create=True)
    return b_dir / f"{Path(model_path).stem}{ext}"


def find_model_backup(model_path: Union[str, Path]) -> Tuple[Optional[Path], Optional[str]]:
    """
    Checks for available backup files for a model.
    Checks dedicated backup subfolders ('backup/', 'backups/', '.backup/', '.studio_backups/')
    first, and falls back to the parent directory for backwards compatibility.
    Returns (backup_path, backup_type) where backup_type is '.orig.mdl' or '.bak'.
    """
    p = Path(model_path).resolve()
    stem = p.stem
    name = p.name

    # 1. Search in dedicated backup directories
    for b_name in BACKUP_FOLDER_NAMES:
        b_dir = p.parent / b_name
        if not b_dir.is_dir():
            continue

        # Check .orig.mdl variants
        cand_orig = b_dir / f"{stem}.orig.mdl"
        if cand_orig.is_file():
            return cand_orig, ".orig.mdl"

        # Check .bak variants
        for cand_bak in (
            b_dir / f"{stem}.mdl.bak",
            b_dir / f"{stem}.orig.bak",
            b_dir / f"{name}.bak",
            b_dir / f"{stem}.bak",
            b_dir / name,  # exact model name inside backup dir
        ):
            if cand_bak.is_file():
                return cand_bak, ".bak"

    # 2. Legacy fallback: check parent directory directly
    orig = p.with_suffix(".orig.mdl")
    if orig.is_file():
        return orig, ".orig.mdl"

    bak_full = Path(str(p) + ".bak")
    if bak_full.is_file():
        return bak_full, ".bak"

    bak_suffix = p.with_suffix(".bak")
    if bak_suffix.is_file():
        return bak_suffix, ".bak"

    cand_orig_bak = p.parent / f"{stem}.orig.bak"
    if cand_orig_bak.is_file():
        return cand_orig_bak, ".orig.bak"

    return None, None


def restore_single_model_file(model_path: Union[str, Path]) -> Tuple[bool, str, Optional[str]]:
    """
    Safely restores a single GoldSrc MDL file from its backup (.orig.mdl or .bak).
    Performs IDST v10 validation before replacing the file atomically.
    """
    p = Path(model_path).resolve()
    bak_path, bak_type = find_model_backup(p)
    if not bak_path:
        return False, f"No backup (.orig.mdl or .bak) found for '{p.name}'.", None

    try:
        with open(bak_path, "rb") as f:
            data = f.read()
    except Exception as e:
        return False, f"Failed to read backup '{bak_path.name}': {e}", bak_type

    if len(data) < 188:
        return False, f"Backup file '{bak_path.name}' is too small ({len(data)} bytes).", bak_type

    magic, ver = struct.unpack_from("<4sI", data, 0)
    if magic != STUDIO_MAGIC or ver != STUDIO_VERSION:
        return False, f"Corrupted backup '{bak_path.name}' (magic={magic}, ver={ver}, expected IDST v10).", bak_type

    p.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = p.with_suffix(".tmp")
    try:
        with open(tmp_path, "wb") as f:
            f.write(data)
        os.replace(tmp_path, p)
    except Exception as e:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        return False, f"Failed to replace '{p.name}' with backup: {e}", bak_type

    orig_path = get_model_backup_path(p, ext=".orig.mdl")
    if bak_type == ".bak" and not orig_path.exists():
        try:
            shutil.copy2(bak_path, orig_path)
        except OSError:
            pass

    return True, f"Successfully restored '{p.name}' from {bak_path.name}.", bak_type


def resolve_weapon_triplet(
    path_or_weapon: str,
    team: str = "ct",
    root_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, dict]:
    """
    Resolves viewmodel (v_*.mdl), player model (p_*.mdl), and world model (w_*.mdl)
    for a given weapon or path. Defaults root_dir to config.get_game_root().
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    candidate = Path(path_or_weapon)

    base = candidate.name.lower()
    if base.endswith(".bak"):
        base = base[:-4]
    if base.endswith(".orig.mdl"):
        base = base[:-9]
    elif base.endswith(".mdl"):
        base = base[:-4]

    for prefix in ("v_", "p_", "w_"):
        if base.startswith(prefix):
            base = base[len(prefix):]
            break

    weapon_key = base
    team = team.lower()
    other_team = "t" if team == "ct" else "ct"

    alias_keys = [weapon_key]
    if weapon_key == "elite":
        alias_keys.append("elites")
    elif weapon_key == "elites":
        alias_keys.append("elite")

    is_knife_variant = weapon_key.startswith("knife_")

    triplet = {}
    for role in ("v", "p", "w"):
        filename = f"{role}_{weapon_key}.mdl"
        role_label = (
            "Viewmodel (First-Person)"
            if role == "v"
            else ("Player Model (Third-Person)" if role == "p" else "World Model (Dropped)")
        )

        found_path: Optional[Path] = None

        if candidate.is_file():
            if candidate.name.lower() == filename:
                found_path = candidate.resolve()
            elif (candidate.parent / filename).is_file():
                found_path = (candidate.parent / filename).resolve()
            elif is_knife_variant and (candidate.parent / f"{role}_knife.mdl").is_file():
                found_path = (candidate.parent / f"{role}_knife.mdl").resolve()

        if not found_path and candidate.is_dir():
            for ak in alias_keys:
                f_cand = candidate / f"{role}_{ak}.mdl"
                if f_cand.is_file():
                    found_path = f_cand.resolve()
                    break

        if not found_path:
            for ak in alias_keys:
                names_to_try = [f"{role}_{ak}.mdl"]
                if is_knife_variant:
                    names_to_try.append(f"{role}_knife.mdl")

                for nm in names_to_try:
                    search_paths = [
                        root / "cstrike" / "models" / "custom_skins" / team / nm,
                        root / "cstrike" / "models" / "custom_skins" / other_team / nm,
                        root / "cstrike" / "models" / "csgo_skins" / team / nm,
                        root / "cstrike" / "models" / "csgo_skins" / other_team / nm,
                        root / "cstrike_hd" / "models" / nm,
                        root / "cstrike" / "models" / nm,
                    ]
                    for sp in search_paths:
                        if sp.is_file():
                            found_path = sp.resolve()
                            break
                    if found_path:
                        break
                if found_path:
                    break

        if not found_path:
            for search_root_dir in (root / "cstrike" / "models", root / "cstrike_hd" / "models"):
                if search_root_dir.is_dir():
                    for ak in alias_keys:
                        names_to_try = [f"{role}_{ak}.mdl"]
                        if is_knife_variant:
                            names_to_try.append(f"{role}_knife.mdl")
                        for nm in names_to_try:
                            for f in search_root_dir.rglob("*.mdl"):
                                parts_lower = [part.lower() for part in f.parts]
                                if any(b in parts_lower for b in BACKUP_FOLDER_NAMES):
                                    continue
                                if f.name.lower() == nm and not f.name.endswith(".orig.mdl") and not f.name.endswith(".bak"):
                                    found_path = f.resolve()
                                    break
                            if found_path:
                                break
                        if found_path:
                            break
                if found_path:
                    break

        backup_path, backup_type = (find_model_backup(found_path) if found_path else (None, None))

        triplet[role] = {
            "role": role,
            "role_label": role_label,
            "filename": filename,
            "path": str(found_path) if found_path else None,
            "exists": found_path is not None and found_path.is_file(),
            "has_backup": backup_path is not None,
            "backup_path": str(backup_path) if backup_path else None,
            "backup_type": backup_type,
        }

    return triplet


def restore_weapon_models(
    path_or_weapon: str,
    team: str = "ct",
    scope: str = "all",
    root_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Restores weapon models according to scope:
      - 'all' or 'v_p_w': restores v, p, and w models
      - 'pw' or 'pw_only': restores p and w models
      - 'v' or 'v_only': restores v model only
      - 'p' or 'p_only': restores p model only
      - 'w' or 'w_only': restores w model only
    Defaults root_dir to config.get_game_root().
    """
    scope_clean = str(scope).lower().strip()
    if scope_clean in ("all", "v_p_w", "everything"):
        target_roles = ["v", "p", "w"]
    elif scope_clean in ("pw", "pw_only", "p_w", "thirdperson"):
        target_roles = ["p", "w"]
    elif scope_clean in ("v", "v_only", "viewmodel"):
        target_roles = ["v"]
    elif scope_clean in ("p", "p_only", "player"):
        target_roles = ["p"]
    elif scope_clean in ("w", "w_only", "world"):
        target_roles = ["w"]
    else:
        raise ValueError(f"Unknown restore scope '{scope}'. Valid options: 'all', 'pw', 'v', 'p', 'w'.")

    triplet = resolve_weapon_triplet(path_or_weapon, team=team, root_dir=root_dir)

    results = {
        "weapon": path_or_weapon,
        "team": team,
        "scope": scope_clean,
        "target_roles": target_roles,
        "restored_count": 0,
        "failed_count": 0,
        "models": {},
        "success": False,
    }

    for role in target_roles:
        info = triplet.get(role, {})
        m_path_str = info.get("path")
        res_entry = {
            "role": role,
            "role_label": info.get("role_label", role),
            "filename": info.get("filename"),
            "path": m_path_str,
            "exists": info.get("exists", False),
            "restored": False,
            "backup_type": info.get("backup_type"),
            "message": "",
        }

        if not info.get("exists") or not m_path_str:
            res_entry["message"] = f"Model {info.get('filename')} does not exist on disk."
            results["failed_count"] += 1
        elif not info.get("has_backup"):
            res_entry["message"] = f"No backup (.orig.mdl or .bak) found for {Path(m_path_str).name}."
            results["failed_count"] += 1
        else:
            ok, msg, b_type = restore_single_model_file(m_path_str)
            res_entry["restored"] = ok
            res_entry["message"] = msg
            res_entry["backup_type"] = b_type
            if ok:
                results["restored_count"] += 1
            else:
                results["failed_count"] += 1

        results["models"][role] = res_entry

    results["success"] = results["restored_count"] > 0
    return results


def migrate_loose_backups(
    search_dirs: Optional[List[Union[str, Path]]] = None,
    target_folder_name: str = "backup",
    root_dir: Optional[Union[str, Path]] = None,
) -> List[Dict[str, str]]:
    """
    Finds loose backup files (.orig.mdl, .mdl.bak, .bak, .orig.bak, .original_palettes.dat)
    sitting directly in model directories and moves them neatly into their dedicated 'backup/' folder.
    Returns list of moved file records: [{'source': str, 'dest': str}].
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    if not search_dirs:
        search_dirs = [
            root / "cstrike" / "models" / "custom_skins" / "ct",
            root / "cstrike" / "models" / "custom_skins" / "t",
            root / "cstrike" / "models" / "csgo_skins" / "ct",
            root / "cstrike" / "models" / "csgo_skins" / "t",
            root / "cstrike" / "models" / "pw_models",
            root / "cstrike" / "models",
            root / "cstrike_hd" / "models",
        ]

    moved = []
    backup_extensions = (".orig.mdl", ".mdl.bak", ".bak", ".orig.bak", ".original_palettes.dat")

    for s_dir in search_dirs:
        dir_p = Path(s_dir).resolve()
        if not dir_p.is_dir():
            continue

        b_dir = dir_p / target_folder_name

        try:
            entries = list(dir_p.iterdir())
        except OSError:
            continue

        for f in entries:
            if not f.is_file():
                continue
            f_name_lower = f.name.lower()
            if any(f_name_lower.endswith(ext) for ext in backup_extensions):
                b_dir.mkdir(parents=True, exist_ok=True)
                dest = b_dir / f.name
                if not dest.exists():
                    try:
                        shutil.move(str(f), str(dest))
                        moved.append({"source": str(f), "dest": str(dest), "action": "moved"})
                    except OSError as e:
                        pass
                else:
                    # Destination already has this backup; remove the loose duplicate
                    try:
                        f.unlink()
                        moved.append({"source": str(f), "dest": str(dest), "action": "removed_loose_duplicate"})
                    except OSError:
                        pass

    return moved



def get_model_thumbnail(model_path: Union[str, Path], max_dim: int = 128) -> Optional[str]:
    """Generates a base64 PNG data URI thumbnail of the model's primary skin texture."""
    try:
        from .mdl_core import MdlModel
        p = Path(model_path).resolve()
        if not p.is_file():
            return None
        model = MdlModel(p)
        skins = model.get_skins()
        tex = max(skins, key=lambda t: t.width * t.height) if skins else (model.textures[0] if model.textures else None)
        if not tex:
            return None
        img = tex.to_rgba_image()
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
    except Exception:
        return None


def list_model_backups(model_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Returns complete metadata and thumbnails for all available restore points
    (golden original, intermediate .bak, undo snapshots) for a model.
    """
    p = Path(model_path).resolve()
    stem = p.stem
    name = p.name

    current_info = None
    if p.is_file():
        mtime = os.path.getmtime(p)
        dt = datetime.datetime.fromtimestamp(mtime)
        current_info = {
            "name": name,
            "path": str(p),
            "size": p.stat().st_size,
            "modified_at": dt.isoformat(),
            "formatted_date": dt.strftime("%b %d, %Y %H:%M"),
            "thumbnail": get_model_thumbnail(p, max_dim=128),
        }

    backups = []
    seen_paths = set()

    # Search in dedicated backup directories
    for b_name in BACKUP_FOLDER_NAMES:
        b_dir = p.parent / b_name
        if not b_dir.is_dir():
            continue

        try:
            candidates = list(b_dir.glob(f"{stem}*.mdl*")) + list(b_dir.glob(f"{name}*"))
        except OSError:
            continue

        for cand in sorted(candidates, key=lambda f: f.stat().st_mtime, reverse=True):
            cand_res = cand.resolve()
            if cand_res in seen_paths or not cand_res.is_file():
                continue
            seen_paths.add(cand_res)

            # Validate IDST header
            is_valid = False
            tex_count = 0
            try:
                with open(cand_res, "rb") as f:
                    hdr = f.read(188)
                    if len(hdr) >= 188:
                        magic, ver = struct.unpack_from("<4sI", hdr, 0)
                        if magic == STUDIO_MAGIC and ver == STUDIO_VERSION:
                            is_valid = True
                            tex_count, _ = struct.unpack_from("<II", hdr, 180)
            except Exception:
                pass

            if not is_valid:
                continue

            mtime = cand_res.stat().st_mtime
            dt = datetime.datetime.fromtimestamp(mtime)
            c_name = cand_res.name

            b_type = "orig" if ".orig" in c_name else "bak"
            label = "Golden Original (.orig.mdl)" if b_type == "orig" else f"Backup ({c_name})"

            backups.append({
                "id": c_name,
                "filename": c_name,
                "path": str(cand_res),
                "label": label,
                "type": b_type,
                "size": cand_res.stat().st_size,
                "modified_at": dt.isoformat(),
                "formatted_date": dt.strftime("%b %d, %Y %H:%M"),
                "texture_count": tex_count,
                "thumbnail": get_model_thumbnail(cand_res, max_dim=128),
                "is_dedicated": True,
            })

    # Search legacy parent directory backups
    for cand in (
        p.with_suffix(".orig.mdl"),
        Path(str(p) + ".bak"),
        p.with_suffix(".bak"),
        p.parent / f"{stem}.orig.bak",
    ):
        if cand.is_file() and cand.resolve() not in seen_paths:
            cand_res = cand.resolve()
            seen_paths.add(cand_res)
            try:
                with open(cand_res, "rb") as f:
                    hdr = f.read(188)
                    if len(hdr) >= 188:
                        magic, ver = struct.unpack_from("<4sI", hdr, 0)
                        if magic == STUDIO_MAGIC and ver == STUDIO_VERSION:
                            tex_count, _ = struct.unpack_from("<II", hdr, 180)
                            mtime = cand_res.stat().st_mtime
                            dt = datetime.datetime.fromtimestamp(mtime)
                            b_type = "orig" if ".orig" in cand_res.name else "bak"
                            backups.append({
                                "id": cand_res.name,
                                "filename": cand_res.name,
                                "path": str(cand_res),
                                "label": f"Loose Legacy ({cand_res.name})",
                                "type": b_type,
                                "size": cand_res.stat().st_size,
                                "modified_at": dt.isoformat(),
                                "formatted_date": dt.strftime("%b %d, %Y %H:%M"),
                                "texture_count": tex_count,
                                "thumbnail": get_model_thumbnail(cand_res, max_dim=128),
                                "is_dedicated": False,
                            })
            except Exception:
                pass

    return {
        "model_name": name,
        "model_path": str(p),
        "current": current_info,
        "backups": backups,
        "total_backups": len(backups),
    }


def restore_specific_backup(
    model_path: Union[str, Path],
    backup_target: Union[str, Path],
) -> Tuple[bool, str]:
    """
    Safely restores a model from a specific backup file or filename with atomic replacement.
    """
    p = Path(model_path).resolve()
    b_path = Path(backup_target)
    if not b_path.is_absolute():
        cand1 = get_model_backup_dir(p) / b_path.name
        cand2 = p.parent / b_path.name
        if cand1.is_file():
            b_path = cand1.resolve()
        elif cand2.is_file():
            b_path = cand2.resolve()
        else:
            return False, f"Backup file '{backup_target}' not found."
    else:
        b_path = b_path.resolve()

    if not b_path.is_file():
        return False, f"Backup file '{b_path}' does not exist."

    try:
        with open(b_path, "rb") as f:
            data = f.read()
    except Exception as e:
        return False, f"Failed to read backup '{b_path.name}': {e}"

    if len(data) < 188:
        return False, f"Backup '{b_path.name}' is too small ({len(data)} bytes)."

    magic, ver = struct.unpack_from("<4sI", data, 0)
    if magic != STUDIO_MAGIC or ver != STUDIO_VERSION:
        return False, f"Backup '{b_path.name}' is not a valid GoldSrc StudioModel IDST v10."

    tmp_path = p.with_suffix(".tmp")
    try:
        with open(tmp_path, "wb") as f:
            f.write(data)
        os.replace(tmp_path, p)
        return True, f"Successfully restored '{p.name}' from {b_path.name}."
    except Exception as e:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        return False, f"Failed to replace model with backup: {e}"
