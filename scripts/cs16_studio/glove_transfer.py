"""
glove_transfer.py - 1-Click Glove & Sleeve Transfer Engine.
Integrated with EmptyX Customization config_manager.
Copies and synchronizes glove textures (sport_right.bmp, sport_left.bmp, sleeve.bmp, etc.)
from a source viewmodel (or preset) to target viewmodels with automatic dimension adaptation.
"""

import base64
from datetime import datetime
import io
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image, ImageOps

from .image_pipeline import quantize_goldsrc
from .mdl_core import (
    GLOVE_KEYWORDS,
    ROLE_GLOVE,
    MdlModel,
    MdlTexture,
    discover_available_models,
    resolve_model_path,
)
from .config_manager import config


def classify_glove_role(tname: str, guard_bare: bool = False) -> Optional[str]:
    lower = tname.lower()

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
    if any(k in lower for k in NON_GLOVE_PARTS):
        if not any(k in lower for k in ("sport", "glove")):
            return None

    is_hand = False
    if "sport" in lower or "glove" in lower or "finger" in lower:
        is_hand = True
    elif "hand" in lower:
        if re.search(r"(?:^|[\W_\d])hands?(?:$|[\W_\d])", lower):
            is_hand = True

    is_arm = False
    if "sleeve" in lower:
        is_arm = True
    elif "arm" in lower:
        if re.search(r"(?:^|[\W_\d])arms?(?:$|[\W_\d])", lower):
            is_arm = True

    if not is_hand and not is_arm:
        return None

    is_left = bool(
        re.search(r"(?:^|[\W_\d])(left|l)(?:$|[\W_\d])", lower)
        or "left" in lower
        or "_l." in lower
        or lower.startswith("l_")
        or lower.endswith("_l")
        or "_l_" in lower
        or "-l." in lower
        or "-l-" in lower
        or "left_" in lower
    )
    is_right = bool(
        re.search(r"(?:^|[\W_\d])(right|r)(?:$|[\W_\d])", lower)
        or "right" in lower
        or "_r." in lower
        or lower.startswith("r_")
        or lower.endswith("_r")
        or "_r_" in lower
        or "-r." in lower
        or "-r-" in lower
        or "right_" in lower
    )

    if is_hand:
        if is_left and is_right:
            return "general_glove"
        if is_left:
            return "left_glove"
        if is_right:
            return "right_glove"
        return "general_glove"

    if is_arm:
        if guard_bare and ("bare" in lower or "t_arm" in lower):
            return "bare_arm"
        return "sleeve"

    return None


def transfer_gloves(
    source_model: Union[str, Path, MdlModel],
    target_model: Union[str, Path, MdlModel],
    sync_sleeves: bool = True,
) -> Dict[str, Union[bool, str, List[str]]]:
    src_m = source_model if isinstance(source_model, MdlModel) else MdlModel(source_model)
    tgt_m = target_model if isinstance(target_model, MdlModel) else MdlModel(target_model)

    src_gloves = [t for t in src_m.textures if t.role == ROLE_GLOVE or classify_glove_role(t.name)]
    tgt_gloves = [t for t in tgt_m.textures if t.role == ROLE_GLOVE or classify_glove_role(t.name)]

    if not src_gloves:
        return {
            "success": False,
            "error": f"No glove textures found in source model '{src_m.filepath.name}'",
        }

    if not tgt_gloves:
        return {
            "success": False,
            "error": f"No glove textures found in target model '{tgt_m.filepath.name}'",
        }

    transferred = []
    src_by_name = {t.name.lower(): t for t in src_gloves}
    src_by_role = {}
    for t in src_gloves:
        role = classify_glove_role(t.name, guard_bare=False)
        if role and role not in src_by_role:
            src_by_role[role] = t

    guarded_bare_arms = []
    for tgt_t in tgt_gloves:
        tgt_role = classify_glove_role(tgt_t.name, guard_bare=True)
        if tgt_role == "bare_arm":
            guarded_bare_arms.append(tgt_t.name)
            continue

        if tgt_role == "sleeve" and not sync_sleeves:
            continue

        donor_t: Optional[MdlTexture] = None
        if tgt_t.name.lower() in src_by_name:
            donor_t = src_by_name[tgt_t.name.lower()]
        elif tgt_role in src_by_role:
            donor_t = src_by_role[tgt_role]

        if not donor_t:
            continue

        tgt_m.save_slot_snapshot(tgt_t)

        if donor_t.width == tgt_t.width and donor_t.height == tgt_t.height:
            payload = donor_t.raw_data
        else:
            donor_rgba = donor_t.to_rgba_image()
            resized = donor_rgba.resize((tgt_t.width, tgt_t.height), Image.Resampling.LANCZOS)
            pix_bytes, pal_bytes = quantize_goldsrc(resized, is_masked=tgt_t.is_masked, defringe=tgt_t.is_masked)
            payload = pix_bytes + pal_bytes

        tgt_m.inject_texture_payload(tgt_t, payload, new_flags=tgt_t.flags)
        transferred.append(f"{tgt_t.name} (from {donor_t.name})")

    if not transferred:
        if guarded_bare_arms:
            return {
                "success": False,
                "error": (
                    f"2D sleeve transfer was blocked for bare arm textures ({', '.join(guarded_bare_arms)}) "
                    f"to prevent the 'Manset Ketat' distortion bug. Please use 3D Sleeve Transplant instead."
                ),
                "guarded_bare_arms": guarded_bare_arms,
            }
        return {
            "success": False,
            "error": f"No compatible glove slots matched between '{src_m.filepath.name}' and '{tgt_m.filepath.name}'",
        }

    tgt_m.save_atomic(create_backup=True)

    result_payload: Dict[str, Any] = {
        "success": True,
        "source": src_m.filepath.name,
        "target": tgt_m.filepath.name,
        "transferred": transferred,
    }
    if guarded_bare_arms:
        result_payload["guarded_bare_arms"] = guarded_bare_arms
        result_payload["notice"] = "2D sleeve overwrite was prevented on bare arms to avoid Manset Ketat distortion."

    return result_payload


def batch_transfer_gloves(
    source_weapon: str,
    target_weapons: List[str],
    team: str = "ct",
    sync_sleeves: bool = True,
    root_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, dict]:
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    src_path = resolve_model_path(source_weapon, team=team, root_dir=root)
    src_model = MdlModel(src_path)

    if not target_weapons or "all" in [w.lower() for w in target_weapons]:
        available = discover_available_models(root)
        models_for_team = available.get(team, [])
        target_weapons = [m["weapon"] for m in models_for_team if m["weapon"].lower() != source_weapon.lower()]

    results = {}
    for tgt_w in target_weapons:
        if tgt_w.lower() == source_weapon.lower():
            continue
        try:
            tgt_path = resolve_model_path(tgt_w, team=team, root_dir=root)
            tgt_model = MdlModel(tgt_path)
            res = transfer_gloves(src_model, tgt_model, sync_sleeves=sync_sleeves)
            results[tgt_w] = res
        except Exception as e:
            results[tgt_w] = {"success": False, "error": str(e)}

    return results


def _load_image_input(img_input: Union[bytes, Image.Image, Path, str], root_dir: Optional[Union[str, Path]] = None) -> Image.Image:
    root = Path(root_dir).resolve() if root_dir else config.get_studio_root()
    if isinstance(img_input, Image.Image):
        return img_input.convert("RGBA")

    if isinstance(img_input, (str, Path)):
        s = str(img_input).strip()
        if not s:
            raise ValueError("Image input string is empty.")

        if s.startswith("data:image/") or ";base64," in s:
            try:
                _, b64 = s.split(",", 1) if "," in s else ("", s)
                raw = base64.b64decode(b64)
                return Image.open(io.BytesIO(raw)).convert("RGBA")
            except Exception as e:
                raise ValueError(f"Failed to decode base64 image data URI: {str(e)}")

        p = Path(s)
        if not p.is_file() and root:
            candidate = root / p
            if candidate.is_file():
                p = candidate

        if p.is_file():
            try:
                return Image.open(p).convert("RGBA")
            except Exception as e:
                raise ValueError(f"Failed to read image file '{p.name}': {str(e)}")

        try:
            raw = base64.b64decode(s, validate=True)
            return Image.open(io.BytesIO(raw)).convert("RGBA")
        except Exception:
            raise FileNotFoundError(f"Could not load image from input path or base64: {s[:60]}...")

    if isinstance(img_input, bytes):
        if not img_input:
            raise ValueError("Image bytes input is empty.")
        try:
            return Image.open(io.BytesIO(img_input)).convert("RGBA")
        except Exception as e:
            raise ValueError(f"Failed to load image from raw bytes: {str(e)}")

    raise TypeError(f"Unsupported image input type: {type(img_input)}")


def batch_inject_glove_images(
    left_image: Optional[Union[bytes, Image.Image, Path, str]] = None,
    right_image: Optional[Union[bytes, Image.Image, Path, str]] = None,
    team: str = "all",
    target_weapons: Optional[List[str]] = None,
    mirror_left_to_right: bool = False,
    root_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    if left_image is None and right_image is None:
        raise ValueError("At least one glove image (left or right) must be provided.")

    root = Path(root_dir).resolve() if root_dir else config.get_game_root()

    left_img: Optional[Image.Image] = None
    right_img: Optional[Image.Image] = None

    if left_image is not None:
        left_img = _load_image_input(left_image, root_dir=root)

    if mirror_left_to_right and left_img is not None:
        right_img = ImageOps.mirror(left_img)
    elif right_image is not None:
        right_img = _load_image_input(right_image, root_dir=root)

    available = discover_available_models(root)

    team_lower = team.lower().strip()
    if team_lower == "all":
        teams_to_scan = ["ct", "t"]
    elif team_lower in ("ct", "t"):
        teams_to_scan = [team_lower]
    else:
        teams_to_scan = ["ct", "t"]

    has_filter = (
        target_weapons is not None
        and len(target_weapons) > 0
        and "all" not in [w.lower() for w in target_weapons]
    )
    norm_targets = [w.lower().strip() for w in target_weapons] if has_filter else None

    target_models_map: Dict[Path, Dict[str, str]] = {}
    if not has_filter:
        for t_key in teams_to_scan:
            for m_info in available.get(t_key, []):
                p = Path(m_info["path"]).resolve()
                if p.is_file() and p not in target_models_map:
                    target_models_map[p] = {"weapon": m_info["weapon"], "team": t_key}
    else:
        for t_key in teams_to_scan:
            for tw in norm_targets:
                matched_model = None
                for m_info in available.get(t_key, []):
                    w_name = m_info["weapon"].lower()
                    m_name = m_info["name"].lower()
                    if w_name == tw or m_name == tw or m_name == f"v_{tw}":
                        p = Path(m_info["path"]).resolve()
                        if p.is_file() and p not in target_models_map:
                            matched_model = p
                            target_models_map[p] = {"weapon": m_info["weapon"], "team": t_key}
                            break
                if not matched_model:
                    try:
                        p = resolve_model_path(tw, team=t_key, root_dir=root)
                        other_team = "ct" if t_key == "t" else "t"
                        is_other_custom = f"custom_skins\\{other_team}" in str(p).lower() or f"custom_skins/{other_team}" in str(p).lower()
                        if not is_other_custom and p.is_file() and p not in target_models_map:
                            target_models_map[p] = {"weapon": tw, "team": t_key}
                    except Exception:
                        pass

    if not target_models_map:
        return {
            "success": False,
            "message": f"No target viewmodels found for team '{team}'.",
            "updated_models": [],
            "total_models": 0,
            "total_slots_updated": 0,
            "left_updated": 0,
            "right_updated": 0,
            "results": {},
        }

    results: Dict[str, Any] = {}
    updated_models: List[str] = []
    total_slots_updated = 0
    left_updated_count = 0
    right_updated_count = 0

    for mdl_path, info in target_models_map.items():
        weapon_name = info["weapon"]
        team_key = info["team"]
        try:
            model = MdlModel(mdl_path)
            weapon_slots = []

            for t in model.textures:
                role = classify_glove_role(t.name)
                tname_lower = t.name.lower()
                if "sport_left" in tname_lower or "glove_l" in tname_lower:
                    role = "left_glove"
                elif "sport_right" in tname_lower or "glove_r" in tname_lower:
                    role = "right_glove"

                source_img: Optional[Image.Image] = None
                slot_side = None

                if role == "left_glove" and left_img is not None:
                    source_img = left_img
                    slot_side = "left"
                elif role == "right_glove" and right_img is not None:
                    source_img = right_img
                    slot_side = "right"
                elif role == "general_glove":
                    source_img = left_img if left_img is not None else right_img
                    slot_side = "general"

                if source_img is None:
                    continue

                model.save_slot_snapshot(t)

                resized = source_img.resize((t.width, t.height), Image.Resampling.LANCZOS)
                pix_bytes, pal_bytes = quantize_goldsrc(resized, is_masked=t.is_masked, defringe=t.is_masked)
                payload = pix_bytes + pal_bytes

                model.inject_texture_payload(t, payload, new_flags=t.flags)
                weapon_slots.append(f"{t.name} ({t.width}x{t.height})")

                if slot_side == "left":
                    left_updated_count += 1
                elif slot_side == "right":
                    right_updated_count += 1
                else:
                    left_updated_count += 1

            if weapon_slots:
                saved_path = model.save_atomic(create_backup=True)
                item_res = {
                    "success": True,
                    "weapon": weapon_name,
                    "team": team_key,
                    "slots": weapon_slots,
                    "path": str(saved_path),
                }
                if weapon_name not in results:
                    results[weapon_name] = item_res
                else:
                    results[f"{team_key}_{weapon_name}"] = item_res

                if weapon_name not in updated_models:
                    updated_models.append(weapon_name)
                total_slots_updated += len(weapon_slots)
            else:
                fail_res = {
                    "success": False,
                    "weapon": weapon_name,
                    "team": team_key,
                    "error": f"No compatible glove slots found in '{mdl_path.name}'.",
                    "path": str(mdl_path),
                }
                if weapon_name not in results:
                    results[weapon_name] = fail_res
                else:
                    results[f"{team_key}_{weapon_name}"] = fail_res
        except Exception as e:
            err_res = {
                "success": False,
                "weapon": weapon_name,
                "team": team_key,
                "error": str(e),
                "path": str(mdl_path),
            }
            if weapon_name not in results:
                results[weapon_name] = err_res
            else:
                results[f"{team_key}_{weapon_name}"] = err_res

    success = len(updated_models) > 0
    return {
        "success": success,
        "message": (
            f"Successfully injected glove textures into {len(updated_models)} models "
            f"({total_slots_updated} slots updated)."
            if success
            else "No glove slots were updated."
        ),
        "updated_models": updated_models,
        "total_models": len(target_models_map),
        "total_slots_updated": total_slots_updated,
        "left_updated": left_updated_count,
        "right_updated": right_updated_count,
        "results": results,
    }


GLOVE_PRESETS_DIR_NAME = ".studio_glove_presets"


def get_glove_presets_dir(root_dir: Optional[Union[str, Path]] = None) -> Path:
    root = Path(root_dir).resolve() if root_dir else config.get_studio_root()
    p = root / GLOVE_PRESETS_DIR_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def _make_thumbnail_uri(img: Image.Image, size: int = 96) -> str:
    thumb = img.copy()
    thumb.thumbnail((size, size), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    thumb.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _image_to_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def list_glove_presets(root_dir: Optional[Union[str, Path]] = None) -> List[dict]:
    presets_dir = get_glove_presets_dir(root_dir)
    results = []
    json_files = sorted(presets_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in json_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            results.append({
                "name": data.get("name", f.stem),
                "created_at": data.get("created_at", ""),
                "has_left": bool(data.get("left_image")),
                "has_right": bool(data.get("right_image")),
                "left_thumb": data.get("left_thumb", ""),
                "right_thumb": data.get("right_thumb", ""),
                "filename": f.name,
            })
        except Exception:
            results.append({
                "name": f.stem,
                "created_at": "",
                "has_left": False,
                "has_right": False,
                "left_thumb": "",
                "right_thumb": "",
                "filename": f.name,
            })
    return results


def save_glove_preset(
    name: str,
    left_image: Optional[Union[bytes, Image.Image, Path, str]] = None,
    right_image: Optional[Union[bytes, Image.Image, Path, str]] = None,
    mirror_left_to_right: bool = False,
    root_dir: Optional[Union[str, Path]] = None,
) -> dict:
    preset_name = name.strip()
    if not preset_name:
        raise ValueError("Preset name is required.")
    if left_image is None and right_image is None:
        raise ValueError("At least one glove image must be provided.")

    root = Path(root_dir).resolve() if root_dir else config.get_studio_root()
    presets_dir = get_glove_presets_dir(root)

    left_img = _load_image_input(left_image, root_dir=root) if left_image is not None else None
    if mirror_left_to_right and left_img is not None:
        right_img = ImageOps.mirror(left_img)
    elif right_image is not None:
        right_img = _load_image_input(right_image, root_dir=root)
    else:
        right_img = None

    left_data_uri = _image_to_data_uri(left_img) if left_img else None
    right_data_uri = _image_to_data_uri(right_img) if right_img else None
    left_thumb_uri = _make_thumbnail_uri(left_img) if left_img else None
    right_thumb_uri = _make_thumbnail_uri(right_img) if right_img else None

    safe_name = re.sub(r"[^a-zA-Z0-9_\- ]", "", preset_name).strip().replace(" ", "_")
    if not safe_name:
        safe_name = "preset"
    out_file = presets_dir / f"{safe_name}.json"

    data = {
        "name": preset_name,
        "created_at": datetime.now().isoformat(),
        "left_image": left_data_uri,
        "right_image": right_data_uri,
        "left_thumb": left_thumb_uri,
        "right_thumb": right_thumb_uri,
    }

    with open(out_file, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2)

    return {
        "success": True,
        "message": f"Preset '{preset_name}' saved successfully.",
        "name": preset_name,
        "filename": out_file.name,
    }


def load_glove_preset(name: str, root_dir: Optional[Union[str, Path]] = None) -> dict:
    presets_dir = get_glove_presets_dir(root_dir)
    safe_name = re.sub(r"[^a-zA-Z0-9_\- ]", "", name).strip().replace(" ", "_")
    target_path = presets_dir / f"{safe_name}.json"
    if not target_path.is_file():
        for f in presets_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    d = json.load(fp)
                if d.get("name", "").lower() == name.lower():
                    return d
            except Exception:
                pass
        raise FileNotFoundError(f"Glove preset '{name}' not found.")

    with open(target_path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def delete_glove_preset(name: str, root_dir: Optional[Union[str, Path]] = None) -> bool:
    presets_dir = get_glove_presets_dir(root_dir)
    safe_name = re.sub(r"[^a-zA-Z0-9_\- ]", "", name).strip().replace(" ", "_")
    target_path = presets_dir / f"{safe_name}.json"
    if target_path.is_file():
        target_path.unlink()
        return True
    for f in presets_dir.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
            if d.get("name", "").lower() == name.lower():
                f.unlink()
                return True
        except Exception:
            pass
    return False


def apply_glove_preset(
    name: str,
    team: str = "all",
    target_weapons: Optional[List[str]] = None,
    root_dir: Optional[Union[str, Path]] = None,
) -> dict:
    preset = load_glove_preset(name, root_dir=root_dir)
    left_source = preset.get("left_image")
    right_source = preset.get("right_image")
    if not left_source and not right_source:
        raise ValueError(f"Preset '{name}' does not contain any glove texture data.")

    return batch_inject_glove_images(
        left_image=left_source,
        right_image=right_source,
        team=team,
        target_weapons=target_weapons,
        mirror_left_to_right=False,
        root_dir=root_dir,
    )
