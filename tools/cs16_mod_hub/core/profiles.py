"""
tools/cs16_mod_hub/core/profiles.py
Dynamic Target Directory and Team Skin Profile Manager.
Allows switching seamlessly between CT skins, T skins, HD models, vanilla models,
or any custom directory without hardcoding paths.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from .common import get_project_root


# Known directory presets in Counter-Strike 1.6
PRESET_PROFILES: List[Dict[str, str]] = [
    {
        "id": "ct_custom",
        "name": "CT Team Custom Skins",
        "rel_path": "cstrike/models/custom_skins/ct",
        "desc": "Team-specific skins used by CT (via team_weapon_skins.amxx)",
    },
    {
        "id": "t_custom",
        "name": "T Team Custom Skins",
        "rel_path": "cstrike/models/custom_skins/t",
        "desc": "Team-specific skins used by Terrorists (via team_weapon_skins.amxx)",
    },
    {
        "id": "hd_models",
        "name": "HD Viewmodels",
        "rel_path": "cstrike_hd/models",
        "desc": "Primary high-definition weapon viewmodels",
    },
    {
        "id": "vanilla_models",
        "name": "Default Game Models",
        "rel_path": "cstrike/models",
        "desc": "Standard Counter-Strike 1.6 models directory",
    },
    {
        "id": "csgo_ct",
        "name": "CS:GO Pack (CT)",
        "rel_path": "cstrike/models/csgo_skins/ct",
        "desc": "Alternative CS:GO skin pack for CT",
    },
    {
        "id": "csgo_t",
        "name": "CS:GO Pack (T)",
        "rel_path": "cstrike/models/csgo_skins/t",
        "desc": "Alternative CS:GO skin pack for T",
    },
]

# Global state for currently active profile
_ACTIVE_PROFILE_PATH: Optional[str] = None


def get_available_profiles() -> List[Dict[str, str]]:
    """
    Returns list of preset profiles that actually exist on disk,
    plus an indicator of whether each profile is active.
    """
    root = get_project_root()
    active = get_active_profile_path()
    results = []

    for p in PRESET_PROFILES:
        full_path = root / p["rel_path"]
        exists = full_path.is_dir()
        model_count = 0
        if exists:
            model_count = len([
                f for f in full_path.iterdir()
                if f.is_file() and f.name.lower().startswith("v_") and f.name.lower().endswith(".mdl") and not f.name.endswith(".bak")
            ])

        results.append({
            "id": p["id"],
            "name": p["name"],
            "rel_path": p["rel_path"],
            "full_path": str(full_path.resolve()),
            "desc": p["desc"],
            "exists": exists,
            "model_count": model_count,
            "is_active": (str(full_path.resolve()) == active),
        })

    return results


def get_active_profile_path() -> str:
    """
    Returns the resolved absolute path of the currently active profile directory.
    Defaults to cstrike/models/custom_skins/ct if it exists, otherwise cstrike_hd/models, then cstrike/models.
    """
    global _ACTIVE_PROFILE_PATH
    root = get_project_root()

    if _ACTIVE_PROFILE_PATH:
        p = Path(_ACTIVE_PROFILE_PATH)
        if p.is_dir():
            return str(p.resolve())

    # Auto-detect best default profile
    candidates = [
        root / "cstrike" / "models" / "custom_skins" / "ct",
        root / "cstrike_hd" / "models",
        root / "cstrike" / "models",
    ]
    for c in candidates:
        if c.is_dir():
            _ACTIVE_PROFILE_PATH = str(c.resolve())
            return _ACTIVE_PROFILE_PATH

    _ACTIVE_PROFILE_PATH = str((root / "cstrike" / "models").resolve())
    return _ACTIVE_PROFILE_PATH


def set_active_profile_path(path_or_id: str) -> str:
    """
    Sets the active profile either by profile ID (e.g. 'ct_custom', 'hd_models')
    or by relative/absolute directory path.
    """
    global _ACTIVE_PROFILE_PATH
    root = get_project_root()

    # Check if ID was given
    for p in PRESET_PROFILES:
        if p["id"] == path_or_id:
            resolved = (root / p["rel_path"]).resolve()
            _ACTIVE_PROFILE_PATH = str(resolved)
            return _ACTIVE_PROFILE_PATH

    # Treat as directory path
    norm = Path(path_or_id)
    if not norm.is_absolute():
        norm = (root / norm).resolve()

    if not norm.is_dir():
        raise FileNotFoundError(f"Target directory '{path_or_id}' does not exist on disk.")

    _ACTIVE_PROFILE_PATH = str(norm)
    return _ACTIVE_PROFILE_PATH
