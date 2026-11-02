"""
tools/cs16_mod_hub/core/vibrance_adapter.py
Backend adapter for CS 1.6 model color vibrance, saturation, and contrast.
Wraps .agents/skills/cs16-color-vibrance/scripts/adjust_vibrance.py via common subprocess runner.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

from .common import AdapterResult, get_project_root, run_script_streaming

SCRIPT_REL_PATH = ".agents/skills/cs16-color-vibrance/scripts/adjust_vibrance.py"

VALID_TARGETS = ("weapon", "gloves", "all")
VALID_PRESETS = ("vivid", "punchy", "soft", "grayscale")

PRESET_VALUES: dict[str, dict[str, float]] = {
    "vivid": {"sat": 1.35, "contrast": 1.15, "brightness": 1.0},
    "punchy": {"sat": 1.55, "contrast": 1.25, "brightness": 1.0},
    "soft": {"sat": 0.85, "contrast": 0.95, "brightness": 1.0},
    "grayscale": {"sat": 0.0, "contrast": 1.0, "brightness": 1.0},
}


def get_preset_values(preset: str) -> dict[str, float]:
    """Returns the saturation, contrast, and brightness multipliers for a named preset."""
    preset_lower = preset.lower()
    if preset_lower not in PRESET_VALUES:
        raise ValueError(f"Unknown preset '{preset}'. Valid presets: {list(PRESET_VALUES.keys())}")
    return PRESET_VALUES[preset_lower].copy()


def list_presets() -> list[str]:
    """Returns a list of supported color preset names."""
    return list(VALID_PRESETS)


def list_target_groups() -> list[str]:
    """Returns a list of supported target texture groups."""
    return list(VALID_TARGETS)


from .profiles import get_active_profile_path


def has_palette_backup(weapon: str, dir_path: Optional[str] = None) -> bool:
    """Checks whether factory original palette cache (.original_palettes.dat) exists."""
    root = get_project_root()
    base_name = os.path.basename(weapon)
    if not any(base_name.startswith(p) for p in ["v_", "p_", "w_"]):
        base_name = f"v_{base_name}"
    if not base_name.endswith(".mdl"):
        base_name = f"{base_name}.mdl"

    effective_dir = dir_path or get_active_profile_path()
    target_p = Path(effective_dir)
    target_dir = target_p if target_p.is_absolute() else (root / target_p)

    candidate_dirs = [
        target_dir,
        root / "cstrike" / "models" / "custom_skins" / "ct",
        root / "cstrike" / "models" / "custom_skins" / "t",
        root / "cstrike_hd" / "models",
        root / "cstrike" / "models",
    ]
    for d in candidate_dirs:
        dat_file = d / f"{base_name}.original_palettes.dat"
        if dat_file.is_file():
            return True
    return False


def apply_vibrance(
    weapon: str,
    target: str = "weapon",
    preset: Optional[str] = None,
    sat: Optional[float] = None,
    contrast: Optional[float] = None,
    brightness: Optional[float] = None,
    reset: bool = False,
    dir_path: Optional[str] = None,
    no_backup: bool = False,
    log_callback: Optional[Callable[[str], None]] = None,
) -> AdapterResult:
    """
    Applies vibrance, saturation, contrast, or preset adjustment to a weapon model.
    """
    if target not in VALID_TARGETS:
        return AdapterResult(
            success=False,
            message=f"Invalid target group '{target}'. Must be one of {VALID_TARGETS}.",
            returncode=-1,
        )

    if preset and preset.lower() not in VALID_PRESETS:
        return AdapterResult(
            success=False,
            message=f"Invalid preset '{preset}'. Must be one of {VALID_PRESETS}.",
            returncode=-1,
        )

    effective_dir = dir_path or get_active_profile_path()
    args = ["-w", str(weapon), "-t", str(target), "-d", str(effective_dir)]

    if reset:
        args.append("--reset")
    else:
        if preset:
            args.extend(["-p", preset.lower()])
        if sat is not None:
            args.extend(["--sat", str(sat)])
        if contrast is not None:
            args.extend(["--contrast", str(contrast)])
        if brightness is not None:
            args.extend(["--brightness", str(brightness)])

    if no_backup:
        args.append("--no-backup")

    return run_script_streaming(SCRIPT_REL_PATH, args, log_callback=log_callback)


def reset_vibrance(
    weapon: str,
    target: str = "weapon",
    dir_path: Optional[str] = None,
    no_backup: bool = False,
    log_callback: Optional[Callable[[str], None]] = None,
) -> AdapterResult:
    """
    Resets the targeted model texture palettes back to the factory original state.
    """
    return apply_vibrance(
        weapon=weapon,
        target=target,
        reset=True,
        dir_path=dir_path,
        no_backup=no_backup,
        log_callback=log_callback,
    )
