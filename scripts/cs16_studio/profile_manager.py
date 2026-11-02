"""
profile_manager.py - Loadout Profile & Preset Manager for CS 1.6 Asset Studio.
Integrated with EmptyX Customization config_manager.
Allows users to save, restore, export, and import complete weapon loadout configurations
(snapshots of textures across weapons) in .studio_profiles/.
"""

import base64
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
from typing import Dict, List, Optional, Union

from .mdl_core import MdlModel, discover_available_models, resolve_model_path
from .config_manager import config

PROFILES_DIR_NAME = ".studio_profiles"


def get_profiles_dir(root_dir: Optional[Union[str, Path]] = None) -> Path:
    """Returns and ensures the .studio_profiles directory exists in the studio workspace."""
    root = Path(root_dir).resolve() if root_dir else config.get_studio_root()
    p = root / PROFILES_DIR_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_profiles(root_dir: Optional[Union[str, Path]] = None) -> List[dict]:
    """Returns a list of all saved profiles."""
    profiles_dir = get_profiles_dir(root_dir)
    results = []

    for f in sorted(profiles_dir.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            results.append({
                "name": data.get("name", f.stem),
                "created_at": data.get("created_at", ""),
                "description": data.get("description", ""),
                "weapons": list(data.get("weapons", {}).keys()),
                "weapon_count": len(data.get("weapons", {})),
                "filename": f.name,
            })
        except Exception:
            results.append({
                "name": f.stem,
                "created_at": "",
                "description": "Corrupted or invalid profile",
                "weapons": [],
                "weapon_count": 0,
                "filename": f.name,
            })

    return results


def save_profile(
    name: str,
    weapons: Optional[List[str]] = None,
    team: str = "ct",
    description: str = "",
    root_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Saves current weapon texture states into a named profile.
    If weapons is None or empty, saves for all discovered weapons for this team.
    """
    game_root = config.get_game_root(root_dir)
    profiles_dir = get_profiles_dir(root_dir)

    clean_name = "".join(c for c in name if c.isalnum() or c in ("-", "_", " ")).strip()
    if not clean_name:
        raise ValueError("Invalid profile name.")

    profile_path = profiles_dir / f"{clean_name}.json"

    if not weapons:
        disc = discover_available_models(game_root)
        team_models = disc.get(team.lower(), [])
        if team_models:
            target_weapons = list({m["weapon"] for m in team_models})
        else:
            target_weapons = ["usp", "ak47", "m4a1", "awp", "deagle"]
    else:
        target_weapons = weapons

    weapons_data = {}
    for w in target_weapons:
        try:
            mdl_path = resolve_model_path(w, team=team, root_dir=game_root)
            model = MdlModel(mdl_path)
            tex_list = []
            for t in model.textures:
                tex_list.append({
                    "name": t.name,
                    "index": t.index,
                    "flags": t.flags,
                    "width": t.width,
                    "height": t.height,
                    "data_b64": base64.b64encode(t.raw_data).decode("ascii"),
                })
            weapons_data[w.lower()] = {
                "weapon": w.lower(),
                "team": team.lower(),
                "model_name": mdl_path.name,
                "textures": tex_list,
            }
        except Exception:
            continue

    profile_payload = {
        "name": clean_name,
        "created_at": datetime.now().isoformat(),
        "description": description or f"Snapshot of {len(weapons_data)} weapons ({team.upper()})",
        "team": team.lower(),
        "weapons": weapons_data,
    }

    with open(profile_path, "w", encoding="utf-8") as fp:
        json.dump(profile_payload, fp, indent=2)

    return {
        "success": True,
        "name": clean_name,
        "saved_path": str(profile_path),
        "weapons_count": len(weapons_data),
        "weapons": list(weapons_data.keys()),
    }


def load_profile(name: str, root_dir: Optional[Union[str, Path]] = None) -> dict:
    """Loads and restores weapon textures from a saved profile."""
    game_root = config.get_game_root(root_dir)
    profiles_dir = get_profiles_dir(root_dir)

    clean = name[:-5] if name.lower().endswith(".json") else name
    profile_path = profiles_dir / f"{clean}.json"
    if not profile_path.is_file():
        candidates = list(profiles_dir.glob(f"{clean}*.json"))
        if candidates:
            profile_path = candidates[0]
        else:
            raise FileNotFoundError(f"Profile '{name}' not found in {profiles_dir}.")

    with open(profile_path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    weapons_data = data.get("weapons", {})
    restored_weapons = []
    failed_weapons = []

    for w_key, w_val in weapons_data.items():
        team = w_val.get("team", "ct")
        try:
            mdl_path = resolve_model_path(w_key, team=team, root_dir=game_root)
            model = MdlModel(mdl_path)

            for t_saved in w_val.get("textures", []):
                t_name = t_saved["name"]
                target_tex = model.find_texture(t_name)
                if target_tex:
                    model.save_slot_snapshot(target_tex)
                    payload = base64.b64decode(t_saved["data_b64"])
                    flags = t_saved.get("flags")
                    model.inject_texture_payload(target_tex, payload, new_flags=flags)

            model.save_atomic(create_backup=True)
            restored_weapons.append(w_key)
        except Exception as e:
            failed_weapons.append({"weapon": w_key, "error": str(e)})

    return {
        "success": True,
        "name": data.get("name", name),
        "restored_count": len(restored_weapons),
        "restored_weapons": restored_weapons,
        "failed_weapons": failed_weapons,
    }


def delete_profile(name: str, root_dir: Optional[Union[str, Path]] = None) -> bool:
    """Deletes a saved profile."""
    profiles_dir = get_profiles_dir(root_dir)
    clean = name[:-5] if name.lower().endswith(".json") else name
    profile_path = profiles_dir / f"{clean}.json"
    if profile_path.is_file():
        profile_path.unlink()
        return True
    return False


def export_profile(name: str, export_path: Union[str, Path], root_dir: Optional[Union[str, Path]] = None) -> Path:
    """Exports a profile JSON file to an external path."""
    profiles_dir = get_profiles_dir(root_dir)
    clean = name[:-5] if name.lower().endswith(".json") else name
    profile_path = profiles_dir / f"{clean}.json"
    if not profile_path.is_file():
        raise FileNotFoundError(f"Profile '{name}' not found.")
    dest = Path(export_path).resolve()
    if dest.is_dir():
        dest = dest / f"{clean}.json"
    shutil.copy2(profile_path, dest)
    return dest


def import_profile(import_path: Union[str, Path], root_dir: Optional[Union[str, Path]] = None) -> dict:
    """Imports an external profile JSON file into the .studio_profiles store."""
    src = Path(import_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"File '{src}' not found.")

    with open(src, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    name = data.get("name", src.stem)
    clean_name = "".join(c for c in name if c.isalnum() or c in ("-", "_", " ")).strip()
    dest = get_profiles_dir(root_dir) / f"{clean_name}.json"
    shutil.copy2(src, dest)

    return {
        "success": True,
        "name": clean_name,
        "imported_path": str(dest),
        "weapon_count": len(data.get("weapons", {})),
    }
