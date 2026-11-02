"""
pov_manager.py - First-Person Viewmodel Camera (Modern CS POV) Controller for CS 1.6.
Integrated with EmptyX Customization config_manager.

Manages GoldSrc client viewmodel translation offsets, inertia sway, dynamic bobbing,
and inspect weapon bindings to replicate CS2/CS:GO first-person weapon perspective.
"""

from dataclasses import dataclass, asdict, fields, replace
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

from .config_manager import config

DEFAULT_ROOT = config.get_game_root()


@dataclass
class PovConfig:
    """Configuration parameters for modern GoldSrc first-person viewmodel POV."""

    offset_x: float = 2.5
    offset_y: float = 1.5
    offset_z: float = -1.5

    lag_scale: float = 1.5
    lag_speed: float = 8.0
    shift: int = 2
    shift_left_amt: float = 0.5
    shift_right_amt: float = 0.25
    retract: int = 1

    bobstyle: int = 2
    bobamt_lat: float = 0.4
    bobamt_vert: float = 0.25
    bob_lower_amt: float = 21.0
    bobcycle: float = 0.8

    camera_movement_interp: float = 0.1
    camera_movement_scale: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PovConfig":
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def clone(self) -> "PovConfig":
        return replace(self)


PRESETS: Dict[str, PovConfig] = {
    "cs2_classic": PovConfig(
        offset_x=2.5,
        offset_y=1.5,
        offset_z=-1.5,
        bobstyle=2,
        lag_scale=1.5,
        lag_speed=8.0,
        retract=1,
    ),
    "csgo_desktop": PovConfig(
        offset_x=1.0,
        offset_y=1.0,
        offset_z=-1.0,
        bobstyle=2,
        lag_scale=1.0,
        lag_speed=8.0,
        retract=1,
    ),
    "couch": PovConfig(
        offset_x=0.0,
        offset_y=2.0,
        offset_z=-2.0,
        bobstyle=2,
        lag_scale=1.2,
        lag_speed=7.0,
        retract=1,
    ),
    "quake_centered": PovConfig(
        offset_x=0.0,
        offset_y=1.8,
        offset_z=-1.0,
        bobstyle=0,
        lag_scale=0.0,
        lag_speed=0.0,
        retract=0,
        shift=0,
        shift_left_amt=0.0,
        shift_right_amt=0.0,
    ),
    "vanilla_16": PovConfig(
        offset_x=0.0,
        offset_y=0.0,
        offset_z=0.0,
        bobstyle=0,
        lag_scale=0.0,
        lag_speed=8.0,
        retract=0,
        shift=0,
        shift_left_amt=0.0,
        shift_right_amt=0.0,
    ),
}


def get_preset(name: str) -> Optional[PovConfig]:
    cfg = PRESETS.get(name.lower().strip())
    if cfg is not None:
        return cfg.clone()
    return None


WEAPON_CATEGORIES: Dict[str, str] = {
    "usp": "pistol",
    "glock18": "pistol",
    "glock": "pistol",
    "deagle": "pistol",
    "p228": "pistol",
    "fiveseven": "pistol",
    "elite": "elites",
    "ak47": "rifle",
    "m4a1": "rifle",
    "galil": "rifle",
    "famas": "rifle",
    "aug": "rifle",
    "sg552": "rifle",
    "awp": "sniper",
    "scout": "sniper",
    "g3sg1": "sniper",
    "sg550": "sniper",
    "mp5": "smg_heavy",
    "mp5navy": "smg_heavy",
    "p90": "smg_heavy",
    "ump45": "smg_heavy",
    "mac10": "smg_heavy",
    "tmp": "smg_heavy",
    "m3": "smg_heavy",
    "xm1014": "smg_heavy",
    "m249": "smg_heavy",
    "knife": "melee",
}

CATEGORY_PRESETS: Dict[str, PovConfig] = {
    "pistol": PovConfig(
        offset_x=1.0,
        offset_y=1.2,
        offset_z=-1.2,
        bobstyle=2,
        lag_scale=1.2,
        lag_speed=8.0,
        retract=1,
    ),
    "elites": PovConfig(
        offset_x=0.0,
        offset_y=1.4,
        offset_z=-1.3,
        bobstyle=2,
        lag_scale=1.2,
        lag_speed=8.0,
        retract=1,
    ),
    "rifle": PovConfig(
        offset_x=2.2,
        offset_y=1.4,
        offset_z=-1.4,
        bobstyle=2,
        lag_scale=1.5,
        lag_speed=8.0,
        retract=1,
    ),
    "sniper": PovConfig(
        offset_x=2.0,
        offset_y=1.3,
        offset_z=-1.3,
        bobstyle=2,
        lag_scale=1.3,
        lag_speed=8.0,
        retract=1,
    ),
    "smg_heavy": PovConfig(
        offset_x=1.8,
        offset_y=1.2,
        offset_z=-1.3,
        bobstyle=2,
        lag_scale=1.4,
        lag_speed=8.0,
        retract=1,
    ),
    "melee": PovConfig(
        offset_x=1.2,
        offset_y=1.0,
        offset_z=-1.1,
        bobstyle=2,
        lag_scale=1.0,
        lag_speed=8.0,
        retract=1,
    ),
}


def get_category_for_weapon(weapon: Optional[str]) -> str:
    if not weapon:
        return "rifle"
    stem = Path(weapon).stem.lower()
    if stem.startswith("v_"):
        stem = stem[2:]
    return WEAPON_CATEGORIES.get(stem, "rifle")


def get_category_preset(category: str) -> Optional[PovConfig]:
    cfg = CATEGORY_PRESETS.get(category.lower().strip())
    if cfg is not None:
        return cfg.clone()
    return None


def get_config_for_weapon(weapon: Optional[str], is_right_hand: bool = True) -> PovConfig:
    cat = get_category_for_weapon(weapon)
    cfg = get_category_preset(cat) or CATEGORY_PRESETS["rifle"].clone()
    if not is_right_hand:
        cfg.offset_x = -cfg.offset_x if cat != "elites" else 0.0
    return cfg


def validate_and_clamp(cfg: PovConfig, weapon: Optional[str] = None) -> Tuple[PovConfig, List[str]]:
    warnings: List[str] = []

    cfg.offset_x = max(-2.5, min(2.5, float(cfg.offset_x)))
    cfg.offset_y = max(-2.0, min(2.0, float(cfg.offset_y)))
    cfg.offset_z = max(-2.0, min(2.0, float(cfg.offset_z)))

    if weapon:
        clean_wep = Path(weapon).stem.lower()
        if clean_wep in ("elite", "v_elite", "elites"):
            cfg.offset_x = 0.0
            warnings.append("Dual Elites POV Override: offset_x automatically locked to 0.0 so both pistols remain centered.")

    if cfg.offset_y > 1.8:
        warnings.append("offset_y > 1.8 may expose hollow sleeve seams on certain weapon models.")
    if cfg.offset_z < -1.8:
        warnings.append("offset_z < -1.8 may clip wrist geometry on lower screen bounds.")

    return cfg, warnings


def export_cfg_string(cfg: PovConfig, weapon: Optional[str] = None) -> str:
    clamped, _ = validate_and_clamp(cfg.clone(), weapon=weapon)
    elite_note = ""
    if weapon and Path(weapon).stem.lower() in ("elite", "v_elite", "elites"):
        elite_note = " // Dual Elites Auto-Centered"

    lines = [
        "// ========================================================",
        "// CS 1.6 Modern POV Controller Configuration",
        "// Generated by CS16 Asset Studio Pro",
        "// ========================================================",
        "",
        "// --- 3D Viewmodel Offsets ---",
        f'viewmodel_offset_x "{clamped.offset_x:.2f}"{elite_note}',
        f'viewmodel_offset_y "{clamped.offset_y:.2f}"',
        f'viewmodel_offset_z "{clamped.offset_z:.2f}"',
        "",
        "// --- Weapon Inertia & Sway ---",
        f'viewmodel_lag_scale "{cfg.lag_scale:.2f}"',
        f'viewmodel_lag_speed "{cfg.lag_speed:.2f}"',
        f'viewmodel_shift "{int(cfg.shift)}"',
        f'viewmodel_shift_left_amt "{cfg.shift_left_amt:.2f}"',
        f'viewmodel_shift_right_amt "{cfg.shift_right_amt:.2f}"',
        f'viewmodel_retract "{int(cfg.retract)}"',
        "",
        "// --- CS:GO Bobbing Dynamics ---",
        f'cl_bobstyle "{int(cfg.bobstyle)}"',
        f'cl_bobamt_lat "{cfg.bobamt_lat:.2f}"',
        f'cl_bobamt_vert "{cfg.bobamt_vert:.2f}"',
        f'cl_bob_lower_amt "{cfg.bob_lower_amt:.1f}"',
        f'cl_bobcycle "{cfg.bobcycle:.2f}"',
        "",
        "// --- Inspect Weapon Binding ---",
        'bind "f" "lookatweapon"',
        "",
    ]
    return "\n".join(lines)


def _split_cfg_commands(line: str) -> List[str]:
    commands: List[str] = []
    current: List[str] = []
    in_quote = False
    quote_char = ""

    for char in line:
        if char in ('"', "'"):
            if not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char:
                in_quote = False
                quote_char = ""
            current.append(char)
        elif char == ";" and not in_quote:
            cmd = "".join(current).strip()
            if cmd:
                commands.append(cmd)
            current = []
        else:
            current.append(char)

    cmd = "".join(current).strip()
    if cmd:
        commands.append(cmd)
    return commands


def parse_cfg_string(content: str) -> PovConfig:
    params: Dict[str, Any] = {}

    cvar_map = {
        "viewmodel_offset_x": ("offset_x", float),
        "viewmodel_offset_y": ("offset_y", float),
        "viewmodel_offset_z": ("offset_z", float),
        "viewmodel_lag_scale": ("lag_scale", float),
        "viewmodel_lag_speed": ("lag_speed", float),
        "viewmodel_shift": ("shift", int),
        "viewmodel_shift_left_amt": ("shift_left_amt", float),
        "viewmodel_shift_right_amt": ("shift_right_amt", float),
        "viewmodel_retract": ("retract", int),
        "cl_bobstyle": ("bobstyle", int),
        "cl_bobamt_lat": ("bobamt_lat", float),
        "cl_bobamt_vert": ("bobamt_vert", float),
        "cl_bob_lower_amt": ("bob_lower_amt", float),
        "cl_bobcycle": ("bobcycle", float),
        "viewmodel_camera_movement_interp": ("camera_movement_interp", float),
        "viewmodel_camera_movement_scale": ("camera_movement_scale", float),
    }

    cvar_pattern = re.compile(r"^([a-zA-Z0-9_]+)(?:\s*=\s*|\s+)[\"']?([^\"'\r\n;]+)[\"']?")

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("//") or line.startswith("#"):
            continue
        if "//" in line:
            line = line.split("//", 1)[0].strip()

        for cmd in _split_cfg_commands(line):
            m = cvar_pattern.match(cmd)
            if m:
                cvar = m.group(1).lower()
                val = m.group(2).strip()
                if cvar in cvar_map:
                    field_name, converter = cvar_map[cvar]
                    try:
                        params[field_name] = converter(val)
                    except (ValueError, TypeError):
                        pass

    return PovConfig(**params)


def _resolve_cstrike_dir(cstrike_dir: Optional[Union[str, Path]] = None) -> Path:
    if cstrike_dir is None:
        p = config.get_game_root()
    else:
        p = Path(cstrike_dir).resolve()

    if p.name.lower() == "cstrike":
        return p
    if (p / "cstrike").is_dir():
        return p / "cstrike"
    return p


def _safe_atomic_replace(src: Path, dst: Path) -> None:
    was_readonly = False
    if dst.exists():
        mode = dst.stat().st_mode
        was_readonly = not bool(mode & stat.S_IWRITE)
        if was_readonly:
            try:
                os.chmod(dst, mode | stat.S_IWRITE)
            except OSError:
                pass
    try:
        src.replace(dst)
        if was_readonly and dst.exists():
            try:
                os.chmod(dst, dst.stat().st_mode & ~stat.S_IWRITE)
            except OSError:
                pass
    finally:
        if src.exists():
            try:
                src.unlink()
            except OSError:
                pass


def read_current_config(cstrike_dir: Optional[Union[str, Path]] = None) -> Optional[PovConfig]:
    target_dir = _resolve_cstrike_dir(cstrike_dir)
    cfg_path = target_dir / "modern_pov.cfg"
    if not cfg_path.is_file():
        return None

    try:
        content = cfg_path.read_text(encoding="utf-8-sig", errors="ignore")
        return parse_cfg_string(content)
    except Exception:
        return None


def apply_to_game(
    cstrike_dir: Optional[Union[str, Path]] = None,
    cfg: Optional[PovConfig] = None,
    weapon: Optional[str] = None,
) -> bool:
    if cfg is None:
        cfg = get_preset("cs2_classic") or PRESETS["cs2_classic"]
    try:
        target_dir = _resolve_cstrike_dir(cstrike_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        clamped_cfg, _ = validate_and_clamp(cfg.clone(), weapon=weapon)
        cfg_content = export_cfg_string(clamped_cfg, weapon=weapon)

        target_cfg = target_dir / "modern_pov.cfg"
        user_cfg = target_dir / "userconfig.cfg"

        # 1. Atomic write modern_pov.cfg
        tmp_pov = target_dir / f"modern_pov.tmp_{os.getpid()}"
        try:
            tmp_pov.write_text(cfg_content, encoding="utf-8")
            _safe_atomic_replace(tmp_pov, target_cfg)
        finally:
            if tmp_pov.exists():
                try:
                    tmp_pov.unlink()
                except OSError:
                    pass

        # 2. Check and atomically update userconfig.cfg
        hook_cmd = "exec modern_pov.cfg"
        hook_pattern = r'^\s*exec\s+["\']?modern_pov\.cfg["\']?'

        if user_cfg.exists():
            existing = user_cfg.read_text(encoding="utf-8-sig", errors="ignore")
            if not re.search(hook_pattern, existing, re.MULTILINE | re.IGNORECASE):
                sep = "\n" if existing.endswith("\n") else "\n\n"
                new_user_content = f"{existing}{sep}// Modern POV Engine Hook\n{hook_cmd}\n"
                tmp_user = target_dir / f"userconfig.tmp_{os.getpid()}"
                try:
                    tmp_user.write_text(new_user_content, encoding="utf-8")
                    _safe_atomic_replace(tmp_user, user_cfg)
                finally:
                    if tmp_user.exists():
                        try:
                            tmp_user.unlink()
                        except OSError:
                            pass
        else:
            new_user_content = f"// Modern POV Engine Hook\n{hook_cmd}\n"
            tmp_user = target_dir / f"userconfig.tmp_{os.getpid()}"
            try:
                tmp_user.write_text(new_user_content, encoding="utf-8")
                _safe_atomic_replace(tmp_user, user_cfg)
            finally:
                if tmp_user.exists():
                    try:
                        tmp_user.unlink()
                    except OSError:
                        pass

        return True
    except Exception as exc:
        print(f"[PovManager Error] Failed to apply POV configuration: {exc}", file=sys.stderr)
        return False


def reset_to_vanilla(cstrike_dir: Optional[Union[str, Path]] = None) -> bool:
    vanilla_cfg = get_preset("vanilla_16") or PRESETS["vanilla_16"]
    return apply_to_game(cstrike_dir, vanilla_cfg)
