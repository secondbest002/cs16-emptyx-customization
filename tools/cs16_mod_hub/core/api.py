"""
tools/cs16_mod_hub/core/api.py
High-Performance Python-to-JavaScript Bridge for Modern Webview Desktop GUI.
Exposes clean asynchronous methods to the Web UI at 60-144 FPS.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional

from .common import get_project_root
from .profiles import (
    get_available_profiles,
    get_active_profile_path,
    set_active_profile_path,
)
from .model_adapter import (
    list_viewmodels,
    list_donor_models,
    transfer_skin,
    inject_gloves,
    inject_pw,
    list_backups,
    restore_model_backup,
    verify_all_backups,
    get_backup_telemetry,
)
from .vibrance_adapter import (
    apply_vibrance,
    reset_vibrance,
    get_preset_values,
    has_palette_backup,
)
from .sticker_adapter import (
    scan_model_stickers,
    apply_sticker_fx,
    get_mode_description,
)
from .palette_preview import TexturePreviewCache
from .amxx_adapter import (
    list_all_plugins,
    set_plugin_status,
    get_competitive_settings,
    set_cvar,
    set_competitive_settings,
    get_cs2_engine_settings,
    set_cs2_engine_cvar,
    set_cs2_engine_settings,
)


def _is_same_model(m1: Optional[str], m2: Optional[str]) -> bool:
    """Robustly checks if two model paths or weapon names refer to the same model."""
    if not m1 or not m2:
        return False
    b1 = Path(m1).name.lower()
    b2 = Path(m2).name.lower()
    if not b1.endswith(".mdl"):
        b1 = f"{b1}.mdl"
    if not b2.endswith(".mdl"):
        b2 = f"{b2}.mdl"
    if not b1.startswith("v_"):
        b1 = f"v_{b1}"
    if not b2.startswith("v_"):
        b2 = f"v_{b2}"
    return b1 == b2


class ModHubAPI:
    """
    Exposed to window.pywebview.api in JavaScript.
    All calls from JS execute on this API.
    """

    def __init__(self):
        self._cache = TexturePreviewCache()
        self._log_history: List[str] = []

    def _log(self, msg: str):
        self._log_history.append(msg)
        if len(self._log_history) > 500:
            self._log_history.pop(0)

    # =========================================================================
    # LAUNCH STANDALONE SKIN SUITE
    # =========================================================================

    def launch_skin_suite(self) -> Dict[str, Any]:
        """Launches the centralized CS2 Private Skin & Loadout Suite."""
        root = get_project_root()
        exe_path = root / "CS2_Loadout_Manager.exe"
        py_script = root / "tools" / "cs2_gui" / "main.py"

        try:
            if exe_path.is_file():
                subprocess.Popen([str(exe_path)], cwd=str(root))
                self._log("[Suite] Launched CS2_Loadout_Manager.exe")
                return {"success": True, "message": "Launched CS2 Private Skin & Loadout Suite"}
            elif py_script.is_file():
                subprocess.Popen([sys.executable, str(py_script)], cwd=str(root))
                self._log("[Suite] Launched tools/cs2_gui/main.py via Python")
                return {"success": True, "message": "Launched CS2 Skin Suite (Python Source Mode)"}
            else:
                return {"success": False, "error": "Could not locate CS2_Loadout_Manager.exe or tools/cs2_gui/main.py"}
        except Exception as e:
            self._log(f"[Suite Error] Failed to launch skin suite: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # PROFILES & DIRECTORIES
    # =========================================================================

    def get_profiles(self) -> List[Dict[str, Any]]:
        """Returns available skin directories/profiles (CT, T, HD, etc.)."""
        return get_available_profiles()

    def get_active_profile(self) -> Dict[str, Any]:
        """Returns current active profile information."""
        active_path = get_active_profile_path()
        root = get_project_root()
        try:
            rel = Path(active_path).relative_to(root)
        except ValueError:
            rel = Path(active_path)
        return {
            "path": active_path,
            "rel_path": str(rel).replace("\\", "/"),
            "name": Path(active_path).name,
        }

    def set_profile(self, profile_id_or_path: str) -> Dict[str, Any]:
        """Sets active profile directory."""
        try:
            resolved = set_active_profile_path(profile_id_or_path)
            self._log(f"[Profile] Switched active skin folder to: {resolved}")
            return {"success": True, "path": resolved}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # VIEWMODELS & DONORS
    # =========================================================================

    def get_viewmodels(self, dir_path: Optional[str] = None) -> List[str]:
        """Returns list of viewmodels in target directory."""
        return list_viewmodels(dir_path=dir_path)

    def get_donor_models(self) -> List[str]:
        """Returns donor collection models."""
        return list_donor_models()

    # =========================================================================
    # LIVE TEXTURE PREVIEW (60-144 FPS)
    # =========================================================================

    def load_weapon_texture(
        self,
        weapon: str,
        dir_path: Optional[str] = None,
        sat: float = 1.0,
        contrast: float = 1.0,
        brightness: float = 1.0,
        target: str = "weapon",
    ) -> Dict[str, Any]:
        """
        Loads weapon texture into cache and returns Data URLs.
        Applies target group scope (weapon vs gloves vs all) and current slider multipliers.
        """
        try:
            effective_dir = dir_path or get_active_profile_path()
            prefer_weapon = (target != "gloves")
            self._cache.load(
                weapon,
                thumb_size=(256, 256),
                prefer_weapon=prefer_weapon,
                target=target,
                dir_path=effective_dir,
            )
            urls = self._cache.get_preview_data_urls(sat=sat, contrast=contrast, brightness=brightness)
            has_backup = has_palette_backup(weapon, dir_path=effective_dir)
            self._log(f"[Preview] Loaded texture for '{weapon}' ({target}): {urls['info']}")
            return {
                "success": True,
                "weapon": weapon,
                "original": urls["original"],
                "adjusted": urls["adjusted"],
                "info": urls["info"],
                "has_backup": has_backup,
            }
        except Exception as e:
            self._log(f"[Preview Error] Could not load '{weapon}': {e}")
            return {"success": False, "weapon": weapon, "error": str(e)}

    def update_preview_sliders(
        self,
        sat: float = 1.0,
        contrast: float = 1.0,
        brightness: float = 1.0,
        weapon: Optional[str] = None,
        target: str = "weapon",
        dir_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fast in-memory recalculation for slider drags (< 1ms).
        Returns adjusted image Data URL.
        """
        try:
            effective_dir = dir_path or get_active_profile_path()
            if weapon and not _is_same_model(self._cache.mdl_path, weapon):
                self._cache.load(
                    weapon,
                    thumb_size=(256, 256),
                    prefer_weapon=(target != "gloves"),
                    target=target,
                    dir_path=effective_dir,
                )
            urls = self._cache.get_preview_data_urls(sat=sat, contrast=contrast, brightness=brightness)
            return {"success": True, "adjusted": urls["adjusted"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # VIBRANCE & COLOR TUNING
    # =========================================================================

    def apply_vibrance(
        self,
        weapon: str,
        target: str = "weapon",
        preset: Optional[str] = None,
        sat: Optional[float] = None,
        contrast: Optional[float] = None,
        brightness: Optional[float] = None,
        dir_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Applies vibrance/HSV adjustments to weapon model."""
        effective_dir = dir_path or get_active_profile_path()
        res = apply_vibrance(
            weapon=weapon,
            target=target,
            preset=preset,
            sat=sat,
            contrast=contrast,
            brightness=brightness,
            dir_path=effective_dir,
            log_callback=self._log,
        )
        # Reload cache to show new original texture ONLY if cache active model still matches
        try:
            if _is_same_model(self._cache.mdl_path, weapon):
                prefer_weapon = (target != "gloves")
                self._cache.load(
                    weapon,
                    thumb_size=(256, 256),
                    prefer_weapon=prefer_weapon,
                    target=target,
                    dir_path=effective_dir,
                )
        except Exception:
            pass

        return {
            "success": res.success,
            "message": res.message,
            "output": res.output,
            "returncode": res.returncode,
        }

    def reset_vibrance(
        self,
        weapon: str,
        target: str = "weapon",
        dir_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resets weapon palette to factory state."""
        effective_dir = dir_path or get_active_profile_path()
        res = reset_vibrance(
            weapon=weapon,
            target=target,
            dir_path=effective_dir,
            log_callback=self._log,
        )
        try:
            if _is_same_model(self._cache.mdl_path, weapon):
                prefer_weapon = (target != "gloves")
                self._cache.load(
                    weapon,
                    thumb_size=(256, 256),
                    prefer_weapon=prefer_weapon,
                    target=target,
                    dir_path=effective_dir,
                )
        except Exception:
            pass
        return {
            "success": res.success,
            "message": res.message,
            "output": res.output,
            "returncode": res.returncode,
        }

    # =========================================================================
    # STICKER FX LAB
    # =========================================================================

    def scan_stickers(self, weapon: str, dir_path: Optional[str] = None) -> Dict[str, Any]:
        """Scans weapon model for sticker/decal slots."""
        effective_dir = dir_path or get_active_profile_path()
        try:
            slots = scan_model_stickers(weapon, dir_path=effective_dir)
            self._log(f"[Stickers] Scanned '{weapon}': found {len(slots)} sticker slot(s).")
            return {"success": True, "slots": slots}
        except Exception as e:
            self._log(f"[Sticker Error] Could not scan '{weapon}': {e}")
            return {"success": False, "error": str(e), "slots": []}

    def apply_sticker_fx(
        self,
        weapon: str,
        mode: str,
        slot_id: str = "all",
        dir_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Applies sticker FX flag (foil, matte, glow, hide, restore)."""
        effective_dir = dir_path or get_active_profile_path()
        res = apply_sticker_fx(
            weapon=weapon,
            mode=mode,
            sticker_id=slot_id,
            dir_path=effective_dir,
            log_callback=self._log,
        )
        try:
            if _is_same_model(self._cache.mdl_path, weapon):
                self._cache.load(
                    weapon,
                    thumb_size=(256, 256),
                    prefer_weapon=True,
                    dir_path=effective_dir,
                )
        except Exception:
            pass
        return {
            "success": res.success,
            "message": res.message,
            "output": res.output,
            "returncode": res.returncode,
        }

    # =========================================================================
    # SKIN TRANSFER & GLOVE INJECTOR
    # =========================================================================

    def transfer_skin(
        self,
        source: str,
        target: str,
        sync_pw: bool = False,
        dir_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Transfers body skin from donor to target model."""
        effective_dir = dir_path or get_active_profile_path()
        res = transfer_skin(
            source=source,
            target=target,
            sync_pw=sync_pw,
            dir_path=effective_dir,
            log_callback=self._log,
        )
        return {
            "success": res.success,
            "message": res.message,
            "output": res.output,
            "returncode": res.returncode,
        }

    def inject_gloves(
        self,
        target: str,
        source: str = "awp",
        dir_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Transfers glove/hand textures from source to target."""
        effective_dir = dir_path or get_active_profile_path()
        res = inject_gloves(
            target=target,
            source=source,
            dir_path=effective_dir,
            log_callback=self._log,
        )
        return {
            "success": res.success,
            "message": res.message,
            "output": res.output,
            "returncode": res.returncode,
        }

    # =========================================================================
    # AMX MOD X PLUGINS & COMPETITIVE CONFIG
    # =========================================================================

    def get_plugins(self) -> List[Dict[str, Any]]:
        """Returns list of all AMXX plugins and active status with metadata."""
        plugins = list_all_plugins()
        return [
            {
                "name": p.name,
                "is_active": p.enabled,
                "category": getattr(p, "category", "Custom"),
                "comment": getattr(p, "description", "") or getattr(p, "comment", ""),
                "display_title": getattr(p, "display_title", p.name),
                "line_number": getattr(p, "line_number", 0),
            }
            for p in plugins
        ]

    def toggle_plugin(self, plugin_name: str, active: bool) -> Dict[str, Any]:
        """Toggles an AMXX plugin on or off."""
        success = set_plugin_status(plugin_name, enabled=active)
        self._log(f"[AMXX] Set '{plugin_name}' -> {'ACTIVE' if active else 'DISABLED'}")
        return {"success": success}

    # =========================================================================
    # CS2 MODERN MECHANICS ENGINE
    # =========================================================================

    def get_cs2_engine_config(self) -> Dict[str, Any]:
        """Reads all settings from cs2_modern_engine.cfg."""
        settings = get_cs2_engine_settings()
        return {"success": True, "cvars": settings}

    def save_cs2_engine_cvar(self, cvar: str, value: Any) -> Dict[str, Any]:
        """Saves a single CVAR in cs2_modern_engine.cfg."""
        success = set_cs2_engine_cvar(cvar, value)
        self._log(f"[CS2 Engine] Saved {cvar} = {value}")
        return {"success": success}

    def save_cs2_engine_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Batch saves multiple CVARs in cs2_modern_engine.cfg."""
        success = set_cs2_engine_settings(settings)
        self._log(f"[CS2 Engine] Saved {len(settings)} CVARs")
        return {"success": success}

    # =========================================================================
    # BOTS & AI ECOSYSTEM (YaPB + Savage Bot)
    # =========================================================================

    def get_bot_ecosystem(self) -> Dict[str, Any]:
        """Returns full bot state: active preset, YaPB server cvars, Savage Bot cvars."""
        from .bot_adapter import get_bot_adapter
        adapter = get_bot_adapter()
        state = adapter.get_bot_ecosystem()
        return state

    def apply_bot_preset(self, preset_name: str) -> Dict[str, Any]:
        """Applies difficulty preset: 'vanilla' | 'tactical' | 'competitive' | 'demon'."""
        from .bot_adapter import get_bot_adapter
        adapter = get_bot_adapter()
        res = adapter.apply_difficulty_preset(preset_name)
        self._log(f"[Bot AI] Applied difficulty preset: '{preset_name}' (Result: {res.get('success')})")
        return res

    def toggle_savage_ai(self, enable: bool) -> Dict[str, Any]:
        """Master toggle: switch between Savage AI and pure Native YaPB."""
        from .bot_adapter import get_bot_adapter
        adapter = get_bot_adapter()
        res = adapter.toggle_savage_ai(enable)
        self._log(f"[Bot AI] Savage AI master switch set to: {'ENABLED' if enable else 'DISABLED (Pure YaPB)'}")
        return res

    def save_bot_settings(
        self,
        yapb_settings: Optional[Dict[str, Any]] = None,
        savage_settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Saves custom YaPB and Savage Bot settings."""
        from .bot_adapter import get_bot_adapter
        adapter = get_bot_adapter()
        y_ok = True
        s_ok = True
        if yapb_settings:
            y_ok = adapter.set_yapb_settings(yapb_settings)
        if savage_settings:
            s_ok = adapter.set_savage_settings(savage_settings)
        self._log(f"[Bot AI] Saved bot settings (YaPB: {y_ok}, Savage: {s_ok})")
        return {"success": y_ok and s_ok, "yapb_ok": y_ok, "savage_ok": s_ok}

    def save_yapb_cvar(self, cvar: str, value: Any) -> Dict[str, Any]:
        """Updates a single YaPB CVAR atomically."""
        from .bot_adapter import get_bot_adapter
        adapter = get_bot_adapter()
        ok = adapter.set_yapb_cvar(cvar, value)
        self._log(f"[YaPB] Saved {cvar} = {value}")
        return {"success": ok, "cvar": cvar, "value": value}

    def save_savage_cvar(self, cvar: str, value: Any) -> Dict[str, Any]:
        """Updates a single Savage Bot CVAR atomically."""
        from .bot_adapter import get_bot_adapter
        adapter = get_bot_adapter()
        ok = adapter.set_savage_cvar(cvar, value)
        self._log(f"[Savage AI] Saved {cvar} = {value}")
        return {"success": ok, "cvar": cvar, "value": value}

    def sanitize_bot_cheats(self) -> Dict[str, Any]:
        """Atomically disables all predator cheat CVARs."""
        from .bot_adapter import get_bot_adapter
        adapter = get_bot_adapter()
        res = adapter.sanitize_cheats()
        self._log("[Savage AI] Sanitized cheat CVARs: triggerbot, recoil, wallbang, hivemind set to 0")
        return res

    # =========================================================================
    # COMPETITIVE MATCH CONFIGURATION
    # =========================================================================

    def get_competitive_config(self) -> Dict[str, Any]:
        """Reads competitive CVAR settings."""
        cvars = get_competitive_settings()
        return {"success": True, "cvars": cvars}

    def save_competitive_cvar(self, cvar: str, value: str) -> Dict[str, Any]:
        """Updates a competitive CVAR."""
        success = set_cvar(cvar, value)
        self._log(f"[Comp] Saved {cvar} = {value}")
        return {"success": success}

    def save_competitive_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Batch updates competitive CVARs."""
        success = set_competitive_settings(settings)
        self._log(f"[Comp] Saved {len(settings)} competitive settings")
        return {"success": success}

    def apply_competitive_preset(self, preset_name: str) -> Dict[str, Any]:
        """Applies a competitive tournament rules preset atomically."""
        key = preset_name.strip().lower()
        presets: Dict[str, Dict[str, str]] = {
            "valve_major": {
                "amx_csgo_mode": "1",
                "amx_csgo_maxrounds": "12",
                "csgo_comp_max_rounds": "24",
                "mp_roundtime": "1.92",
                "mp_c4timer": "40",
                "amx_csgo_c4_timer": "40",
                "mp_freezetime": "20",
                "mp_buytime": "20",
                "amx_csgo_timeouts": "1",
                "amx_csgo_timeout_duration": "30",
                "amx_csgo_ot_money": "10000",
                "amx_csgo_kniferound": "1",
                "amx_csgo_bot_autoready": "1",
                "amx_csgo_lossbonus": "1",
                "amx_csgo_dmg_card": "1",
                "amx_csgo_mvp_card": "1",
            },
            "esl_pro": {
                "amx_csgo_mode": "1",
                "amx_csgo_maxrounds": "15",
                "csgo_comp_max_rounds": "30",
                "mp_roundtime": "1.92",
                "mp_c4timer": "40",
                "amx_csgo_c4_timer": "40",
                "mp_freezetime": "20",
                "mp_buytime": "15",
                "amx_csgo_timeouts": "1",
                "amx_csgo_timeout_duration": "60",
                "amx_csgo_ot_money": "16000",
                "amx_csgo_kniferound": "1",
                "amx_csgo_bot_autoready": "1",
                "amx_csgo_lossbonus": "1",
                "amx_csgo_dmg_card": "1",
                "amx_csgo_mvp_card": "1",
            },
            "cpl_wcg": {
                "amx_csgo_mode": "0",
                "amx_csgo_maxrounds": "15",
                "csgo_comp_max_rounds": "30",
                "mp_roundtime": "1.75",
                "mp_c4timer": "35",
                "amx_csgo_c4_timer": "35",
                "mp_freezetime": "10",
                "mp_buytime": "15",
                "amx_csgo_timeouts": "0",
                "amx_csgo_timeout_duration": "60",
                "amx_csgo_kniferound": "0",
                "amx_csgo_bot_autoready": "0",
                "amx_csgo_lossbonus": "0",
                "amx_csgo_dmg_card": "0",
                "amx_csgo_mvp_card": "0",
            },
        }
        if key not in presets:
            return {"success": False, "error": f"Unknown preset: '{preset_name}'"}
        settings = presets[key]
        success = set_competitive_settings(settings)
        self._log(f"[Comp] Applied tournament preset: {key.upper()}")
        return {"success": success, "preset": key, "cvars": settings}

    # =========================================================================
    # ASSET STUDIO BRIDGE & LAUNCHER
    # =========================================================================

    def check_asset_studio_status(self) -> Dict[str, Any]:
        """Checks if CS 1.6 Asset Studio is running on port 5160."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.3)
        is_running = False
        try:
            res = sock.connect_ex(("127.0.0.1", 5160))
            is_running = (res == 0)
        except Exception:
            pass
        finally:
            sock.close()
        return {
            "online": is_running,
            "url": "http://127.0.0.1:5160/",
            "port": 5160,
        }

    def launch_asset_studio(self) -> Dict[str, Any]:
        """Launches CS 1.6 Asset Studio (Port 5160)."""
        root = get_project_root()
        bat_script = root / "CS16_Asset_Studio.bat"
        py_script = root / "scripts" / "cs16_studio.py"
        try:
            if bat_script.is_file():
                subprocess.Popen(["cmd.exe", "/c", "start", "", str(bat_script)], cwd=str(root))
                self._log("[Asset Studio] Launched CS16_Asset_Studio.bat")
                return {"success": True, "message": "Launched CS 1.6 Asset Studio (Port 5160)"}
            elif py_script.is_file():
                subprocess.Popen([sys.executable, str(py_script), "--ui", "--port", "5160"], cwd=str(root))
                self._log("[Asset Studio] Launched scripts/cs16_studio.py")
                return {"success": True, "message": "Launched CS 1.6 Asset Studio (Python Mode)"}
            return {"success": False, "error": "Could not find CS16_Asset_Studio.bat or scripts/cs16_studio.py"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # BACKUPS & SYSTEM
    # =========================================================================

    def get_backups(self, dir_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns list of .bak backup files in target directory."""
        effective_dir = dir_path or get_active_profile_path()
        backups = list_backups(search_dirs=[effective_dir])
        return [
            {
                "backup_path": b["backup_path"],
                "target_path": b["target_path"],
                "model_name": b["model_name"],
                "size_bytes": b["backup_size"],
                "modified_str": b["backup_mtime"],
            }
            for b in backups
        ]

    def get_backup_telemetry(self, dir_path: Optional[str] = None) -> Dict[str, Any]:
        """Returns telemetry metrics for safety backup vault."""
        effective_dir = dir_path or get_active_profile_path()
        return get_backup_telemetry(search_dirs=[effective_dir])

    def verify_all_backups(self, dir_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Verifies binary IDST header and calculates SHA-256 hash for all backups."""
        effective_dir = dir_path or get_active_profile_path()
        return verify_all_backups(search_dirs=[effective_dir])

    def restore_backup(self, backup_path: str) -> Dict[str, Any]:
        """Restores a .bak file."""
        res = restore_model_backup(backup_path)
        self._log(f"[Restore] {res.message}")
        return {
            "success": res.success,
            "message": res.message,
        }

    def open_in_explorer(self, folder_path: Optional[str] = None):
        """Opens directory in Windows File Explorer."""
        target = folder_path or get_active_profile_path()
        try:
            os.startfile(target)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_logs(self) -> List[str]:
        """Returns recent log messages."""
        return list(self._log_history)
