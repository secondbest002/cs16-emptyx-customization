"""
fps_booster.py - CS 1.6 Potato FPS Boost Engine & Optimizer Suite.
Integrates with Decoupled Studio Bridge Architecture to tune GoldSrc engine cvars,
audio buffers, and YaPB bot think rates for low-end hardware.
"""

import argparse
import os
from pathlib import Path
import re
import sys
from typing import Dict, Any, Optional

try:
    from .config_manager import StudioConfig
except ImportError:
    from config_manager import StudioConfig


PRESETS = {
    "balanced": {
        "name": "Esports Balanced Boost",
        "description": "Recommended for potato laptops. Eliminates muzzleflash lightmap lag, particle spam, and bot CPU spikes while preserving custom weapon skins and visual clarity.",
        "cvars": {
            "fps_override": "1",
            "fps_max": "101",
            "gl_vsync": "0",
            "r_dynamic": "0",
            "r_lightmap": "0",
            "gl_monolights": "0",
            "max_shells": "0",
            "max_smokepuffs": "0",
            "fastsprites": "2",
            "cl_weather": "0",
            "cl_shadows": "0",
            "mp_decals": "25",
            "sp_decals": "50",
            "r_decals": "25",
            "cl_corpsestay": "5",
            "gl_texturemode": "GL_LINEAR_MIPMAP_NEAREST",
            "gl_dither": "0",
            "gl_fog": "0",
            "gl_keeptjunctions": "0",
            "gl_lightholes": "0",
            "gl_wateramp": "0",
            "gl_polyoffset": "0.1",
            "ati_npatch": "0",
            "r_detailtextures": "0",
            "hisound": "1",
            "snd_mixahead": "0.14",
            "room_off": "1",
            "rate": "100000",
            "cl_updaterate": "101",
            "cl_cmdrate": "101",
            "cl_cmdbackup": "2",
            "ex_interp": "0.01",
            "cl_dlmax": "1024",
            "cl_minmodels": "0",
            "hud_fastswitch": "1",
            "cl_showfps": "1",
        },
        "bot_think_fps": "24.0",
    },
    "extreme": {
        "name": "Potato Max Performance",
        "description": "Maximum FPS mode for extreme low-end hardware. Forces single models, zeros decals, zero corpses, and ultra-light bot thinking.",
        "cvars": {
            "fps_override": "1",
            "fps_max": "101",
            "gl_vsync": "0",
            "r_dynamic": "0",
            "r_lightmap": "0",
            "gl_monolights": "0",
            "max_shells": "0",
            "max_smokepuffs": "0",
            "fastsprites": "2",
            "cl_weather": "0",
            "cl_shadows": "0",
            "mp_decals": "0",
            "sp_decals": "0",
            "r_decals": "0",
            "cl_corpsestay": "1",
            "gl_texturemode": "GL_LINEAR_MIPMAP_NEAREST",
            "gl_dither": "0",
            "gl_fog": "0",
            "gl_keeptjunctions": "0",
            "gl_lightholes": "0",
            "gl_wateramp": "0",
            "gl_polyoffset": "0.1",
            "ati_npatch": "0",
            "r_detailtextures": "0",
            "hisound": "1",
            "snd_mixahead": "0.16",
            "room_off": "1",
            "rate": "100000",
            "cl_updaterate": "101",
            "cl_cmdrate": "101",
            "cl_cmdbackup": "2",
            "ex_interp": "0.01",
            "cl_dlmax": "1024",
            "cl_minmodels": "1",
            "hud_fastswitch": "1",
            "cl_showfps": "1",
        },
        "bot_think_fps": "20.0",
    },
    "stock": {
        "name": "Stock / Factory Reset",
        "description": "Restores original visual configuration (full dynamic lighting, default 120 shells & smoke puffs, 10-minute corpses).",
        "cvars": {
            "fps_override": "1",
            "fps_max": "100",
            "gl_vsync": "0",
            "r_dynamic": "1",
            "r_lightmap": "1",
            "gl_monolights": "0",
            "max_shells": "120",
            "max_smokepuffs": "120",
            "fastsprites": "0",
            "cl_weather": "1",
            "cl_shadows": "1",
            "mp_decals": "300",
            "sp_decals": "4096",
            "r_decals": "300",
            "cl_corpsestay": "600",
            "gl_texturemode": "GL_LINEAR_MIPMAP_LINEAR",
            "gl_dither": "1",
            "gl_fog": "1",
            "gl_keeptjunctions": "1",
            "gl_lightholes": "1",
            "gl_wateramp": "0",
            "gl_polyoffset": "4",
            "ati_npatch": "1.0",
            "r_detailtextures": "0",
            "hisound": "1",
            "snd_mixahead": "0.1",
            "room_off": "0",
            "rate": "100000",
            "cl_updaterate": "101",
            "cl_cmdrate": "101",
            "cl_cmdbackup": "2",
            "ex_interp": "0.1",
            "cl_dlmax": "1024",
            "cl_minmodels": "0",
            "hud_fastswitch": "1",
            "cl_showfps": "1",
        },
        "bot_think_fps": "30.0",
    },
}


class FPSBooster:
    def __init__(self):
        self.config_mgr = StudioConfig.get_instance()
        self.game_root = self.config_mgr.get_game_root()
        self.cstrike_dir = self.game_root / "cstrike"

    def get_fps_boost_cfg_path(self) -> Path:
        return self.cstrike_dir / "fps_boost.cfg"

    def get_userconfig_path(self) -> Path:
        return self.cstrike_dir / "userconfig.cfg"

    def get_yapb_cfg_path(self) -> Path:
        return self.cstrike_dir / "addons" / "yapb" / "conf" / "yapb.cfg"

    def generate_cfg_content(self, preset_key: str) -> str:
        preset = PRESETS.get(preset_key, PRESETS["balanced"])
        lines = [
            "// ==============================================================================",
            f"// CS 1.6 POTATO FPS BOOST - [{preset['name'].upper()}]",
            f"// {preset['description']}",
            "// Generated by CS 1.6 EmptyX Customization Studio",
            "// ==============================================================================",
            "",
            "echo \"================================================\"",
            f"echo \" Loading CS 1.6 {preset['name']}...\"",
            "echo \"================================================\"",
            "",
        ]

        for cvar, val in preset["cvars"].items():
            lines.append(f'{cvar} "{val}"')

        lines.extend([
            "",
            f"echo \">> CS 1.6 {preset['name']} Activated Successfully!\"",
            "",
        ])
        return "\n".join(lines)

    def apply_preset(self, preset_key: str) -> bool:
        if preset_key not in PRESETS:
            print(f"[ERROR] Unknown preset: {preset_key}")
            return False

        preset = PRESETS[preset_key]
        print(f"\n[*] Applying FPS Boost Preset: {preset['name']}...")

        # 1. Write fps_boost.cfg
        cfg_path = self.get_fps_boost_cfg_path()
        content = self.generate_cfg_content(preset_key)
        try:
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cfg_path, "w", encoding="ascii", errors="replace") as f:
                f.write(content)
            print(f"  [+] Wrote config: {cfg_path}")
        except Exception as e:
            print(f"  [!] Failed to write {cfg_path}: {e}")
            return False

        # 2. Ensure userconfig.cfg hooks fps_boost.cfg
        userconfig_path = self.get_userconfig_path()
        if userconfig_path.is_file():
            try:
                with open(userconfig_path, "r", encoding="utf-8", errors="replace") as f:
                    ucontent = f.read()
            except Exception:
                ucontent = ""
        else:
            ucontent = ""

        if "exec fps_boost.cfg" not in ucontent:
            hook_text = (
                "\n// ==============================================================================\n"
                "// CS 1.6 POTATO FPS BOOST ENGINE HOOK\n"
                "// ==============================================================================\n"
                "exec fps_boost.cfg\n"
                "fps_override \"1\"\n"
                "fps_max \"101\"\n"
                "gl_vsync \"0\"\n"
            )
            ucontent = ucontent.strip() + hook_text
            try:
                with open(userconfig_path, "w", encoding="ascii", errors="replace") as f:
                    f.write(ucontent)
                print(f"  [+] Hooked fps_boost.cfg into {userconfig_path}")
            except Exception as e:
                print(f"  [!] Failed updating userconfig.cfg: {e}")

        # 3. Update YaPB Bot Think FPS
        yapb_path = self.get_yapb_cfg_path()
        if yapb_path.is_file():
            try:
                with open(yapb_path, "r", encoding="utf-8", errors="replace") as f:
                    ycontent = f.read()
                new_fps = preset["bot_think_fps"]
                updated_ycontent = re.sub(
                    r'yb_think_fps\s+"[\d\.]+"',
                    f'yb_think_fps "{new_fps}"',
                    ycontent
                )
                with open(yapb_path, "w", encoding="utf-8") as f:
                    f.write(updated_ycontent)
                print(f"  [+] Configured YaPB bot think FPS to {new_fps} in {yapb_path.name}")
            except Exception as e:
                print(f"  [!] Could not adjust YaPB config: {e}")

        print(f"[SUCCESS] Preset '{preset['name']}' is now ACTIVE.")
        return True

    def get_status(self) -> Dict[str, Any]:
        cfg_path = self.get_fps_boost_cfg_path()
        active = cfg_path.is_file()
        current_preset = "Unknown"
        active_cvars = {}

        if active:
            try:
                with open(cfg_path, "r", encoding="ascii", errors="replace") as f:
                    for line in f:
                        m = re.match(r'^\s*([a-zA-Z0-9_]+)\s+"([^"]*)"', line)
                        if m:
                            active_cvars[m.group(1)] = m.group(2)
                if active_cvars.get("cl_minmodels") == "1":
                    current_preset = "Potato Max Performance (extreme)"
                elif active_cvars.get("r_dynamic") == "0":
                    current_preset = "Esports Balanced Boost (balanced)"
                else:
                    current_preset = "Stock / Custom"
            except Exception:
                pass

        yapb_path = self.get_yapb_cfg_path()
        bot_fps = "Default"
        if yapb_path.is_file():
            try:
                with open(yapb_path, "r", encoding="utf-8", errors="replace") as f:
                    m = re.search(r'yb_think_fps\s+"([^"]+)"', f.read())
                    if m:
                        bot_fps = m.group(1)
            except Exception:
                pass

        return {
            "active": active,
            "cfg_path": str(cfg_path),
            "preset_detected": current_preset,
            "bot_think_fps": bot_fps,
            "cvars": active_cvars,
        }


def main():
    parser = argparse.ArgumentParser(description="CS 1.6 Potato FPS Boost Optimizer")
    parser.add_argument(
        "--apply",
        choices=["balanced", "extreme", "stock"],
        help="Apply a performance preset (balanced, extreme, stock)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Display current FPS boost status and active cvars",
    )
    args = parser.parse_args()

    booster = FPSBooster()

    if args.status or (not args.apply):
        st = booster.get_status()
        print("=" * 60)
        print(" CS 1.6 POTATO FPS BOOST STATUS")
        print("=" * 60)
        print(f" Game Directory : {booster.game_root}")
        print(f" FPS Config     : {st['cfg_path']} ({'EXISTS' if st['active'] else 'NOT FOUND'})")
        print(f" Active Preset  : {st['preset_detected']}")
        print(f" YaPB Bot FPS   : {st['bot_think_fps']}")
        if st["cvars"]:
            print("\n Key Active CVars:")
            for k in ["fps_override", "fps_max", "r_dynamic", "max_shells", "max_smokepuffs", "cl_corpsestay", "gl_texturemode", "cl_minmodels"]:
                if k in st["cvars"]:
                    print(f"   - {k:<16}: {st['cvars'][k]}")
        print("=" * 60)

    if args.apply:
        booster.apply_preset(args.apply)


if __name__ == "__main__":
    main()
