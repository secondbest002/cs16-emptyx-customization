"""
tools/cs16_mod_hub/core/sticker_adapter.py
Backend adapter for CS 1.6 model sticker visual FX flags and visibility.
Wraps .agents/skills/cs16-sticker-fx/scripts/toggle_sticker_fx.py via common subprocess runner.
Also provides fast in-memory sticker slot scanning directly from GoldSrc MDL headers.
"""

from __future__ import annotations

import os
from pathlib import Path
import struct
from typing import Callable, List, Optional

from .common import AdapterResult, get_project_root, run_script_streaming

SCRIPT_REL_PATH = ".agents/skills/cs16-sticker-fx/scripts/toggle_sticker_fx.py"

VALID_MODES = ("foil", "chrome", "matte", "glow", "hide", "restore")

MODE_DESCRIPTIONS: dict[str, str] = {
    "foil": "Foil / Chrome reflective metallic gleam (flags: 0x42)",
    "chrome": "Chrome reflective metallic gleam (flags: 0x42)",
    "matte": "Classic flat matte decal finish (flags: 0x40)",
    "glow": "Additive glow effect for dark environments (flags: 0x60)",
    "hide": "Completely hide sticker from weapon model",
    "restore": "Restore previously hidden sticker texture",
}


def list_supported_modes() -> list[str]:
    """Returns a list of supported sticker effect modes."""
    return list(VALID_MODES)


def get_mode_description(mode: str) -> str:
    """Returns human-readable description of sticker effect mode."""
    return MODE_DESCRIPTIONS.get(mode.lower(), "Custom rendering mode")


def set_sticker_fx(
    weapon: str,
    mode: str,
    sticker_id: str = "all",
    dir_path: str = "cstrike/models",
    no_backup: bool = False,
    log_callback: Optional[Callable[[str], None]] = None,
) -> AdapterResult:
    """
    Sets visual effect flags (Foil, Matte, Glow, Hide, Restore) on weapon stickers.
    """
    mode_lower = mode.lower()
    if mode_lower not in VALID_MODES:
        return AdapterResult(
            success=False,
            message=f"Invalid sticker mode '{mode}'. Must be one of {VALID_MODES}.",
            returncode=-1,
        )

    args = ["-w", str(weapon), "-m", mode_lower]
    if dir_path:
        args.extend(["-d", str(dir_path)])
    if sticker_id and str(sticker_id).lower() != "all":
        args.extend(["--sticker-id", str(sticker_id)])
    if no_backup:
        args.append("--no-backup")

    return run_script_streaming(SCRIPT_REL_PATH, args, log_callback=log_callback)


# Alias for intuitive API naming
apply_sticker_fx = set_sticker_fx


from .profiles import get_active_profile_path


def scan_model_stickers(mdl_path: str, dir_path: Optional[str] = None) -> List[dict]:
    """
    Scans a GoldSrc StudioModel (.mdl) and returns metadata for all sticker/decal texture slots.
    Returns empty list if no stickers are found.
    Raises FileNotFoundError if model file cannot be located.
    """
    root = get_project_root()
    resolved_path: Optional[Path] = None

    norm = Path(mdl_path)
    if norm.is_file():
        resolved_path = norm.resolve()
    else:
        # Search candidate locations
        base = norm.name
        if not any(base.startswith(p) for p in ["v_", "p_", "w_"]):
            base = f"v_{base}"
        if not base.endswith(".mdl"):
            base = f"{base}.mdl"

        active_dir = dir_path or get_active_profile_path()
        target_p = Path(active_dir)
        target_dir = target_p if target_p.is_absolute() else (root / target_p)

        search_dirs = [
            target_dir,
            root / "cstrike" / "models" / "custom_skins" / "ct",
            root / "cstrike" / "models" / "custom_skins" / "t",
            root / "cstrike_hd" / "models",
            root / "cstrike" / "models",
            root / "cstrike" / "models" / "csgo_skins" / "ct",
            root / "cstrike" / "models" / "csgo_skins" / "t",
        ]
        for d in search_dirs:
            candidate = d / base
            if candidate.is_file():
                resolved_path = candidate.resolve()
                break

    if not resolved_path or not resolved_path.is_file():
        raise FileNotFoundError(f"Model file '{mdl_path}' not found in any skin folder.")

    with open(resolved_path, "rb") as f:
        data = f.read()

    if len(data) < 188:
        raise ValueError(f"File too small to be a valid GoldSrc MDL: {resolved_path}")

    magic, ver = struct.unpack_from("<4sI", data, 0)
    if magic != b"IDST" or ver != 10:
        # Try fallback to cstrike_hd/models
        fallback_path = root / "cstrike_hd" / "models" / resolved_path.name
        if fallback_path.is_file() and fallback_path.resolve() != resolved_path:
            with open(fallback_path, "rb") as fb:
                data_fb = fb.read()
            if len(data_fb) >= 188:
                m_fb, v_fb = struct.unpack_from("<4sI", data_fb, 0)
                if m_fb == b"IDST" and v_fb == 10:
                    data = data_fb
                    resolved_path = fallback_path.resolve()
                    magic, ver = m_fb, v_fb

        if magic != b"IDST" or ver != 10:
            raise ValueError(f"Invalid GoldSrc MDL header in '{resolved_path.name}' (magic={magic!r}, ver={ver})")

    numtextures, textureindex = struct.unpack_from("<II", data, 180)
    stickers: List[dict] = []

    backup_dir = resolved_path.parent / ".sticker_backups"
    base_file_key = resolved_path.name

    for i in range(numtextures):
        offset = textureindex + i * 80
        tname, flags, w, h, idx = struct.unpack_from("<64sIIII", data, offset)
        tname_str = tname.split(b"\x00")[0].decode("latin1", errors="ignore")

        lower_name = tname_str.lower()
        if "sticker" in lower_name or "decal" in lower_name:
            pixel_start = idx
            pixel_end = idx + (w * h)
            pixel_slice = data[pixel_start:pixel_end] if pixel_end <= len(data) else b""

            # Check if all pixels are 0xFF (hidden transparent cutout)
            is_hidden = bool(pixel_slice and all(b == 255 for b in pixel_slice[: min(len(pixel_slice), 1024)]))

            # Check if raw backup exists
            raw_backup_path = backup_dir / f"{base_file_key}_{tname_str}.raw"
            has_raw_backup = raw_backup_path.is_file()

            # Human-readable mode string
            if flags == 0x42:
                mode_name = "Foil / Chrome (0x42)"
            elif flags == 0x40:
                mode_name = "Matte Decal (0x40)"
            elif flags == 0x60:
                mode_name = "Additive Glow (0x60)"
            else:
                mode_name = f"Custom (0x{flags:02X})"

            stickers.append({
                "index": i,
                "name": tname_str,
                "width": w,
                "height": h,
                "flags": flags,
                "mode_name": mode_name,
                "is_hidden": is_hidden,
                "has_raw_backup": has_raw_backup,
                "offset": offset,
                "pixel_offset": idx,
            })

    return stickers
