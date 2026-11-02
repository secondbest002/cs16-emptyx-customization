"""
tools/cs16_mod_hub/core/bot_adapter.py
Unified adapter for YaPB Bot and Savage Esports AI configuration.
Provides seamless synchronization, multi-tier difficulty presets, and granular feature control.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .common import get_project_root
from .cfg_utils import (
    parse_cfg_cvars,
    get_cfg_cvar,
    set_cfg_cvar,
    set_cfg_cvars,
)

YAPB_RELEVANT_CVARS = [
    "yb_quota",
    "yb_quota_mode",
    "yb_quota_match",
    "yb_join_team",
    "yb_join_after_player",
    "yb_autovacate",
    "yb_autovacate_keep_slots",
    "yb_difficulty",
    "yb_difficulty_min",
    "yb_difficulty_max",
    "yb_difficulty_auto",
    "yb_shoots_thru_walls",
    "yb_jasonmode",
    "yb_radio_mode",
    "yb_chat",
    "yb_chat_percent",
    "yb_preferred_personality",
    "yb_spraypaints",
    "yb_botbuy",
    "yb_tkpunish",
    "yb_show_avatars",
    "yb_show_latency",
    "yb_name_prefix",
]

SAVAGE_RELEVANT_CVARS = [
    "bot_savage_enable",
    "bot_savage_roles",
    "bot_savage_holding",
    "bot_savage_calls",
    "bot_savage_dropguns",
    "bot_savage_bhop",
    "bot_savage_counterstrafe",
    "bot_savage_jiggle",
    "bot_savage_recoil",
    "bot_savage_triggerbot",
    "bot_savage_tradefrag",
    "bot_savage_antiflash",
    "bot_savage_hivemind",
    "bot_savage_wallbang",
    "bot_savage_doublepeek",
    "bot_savage_fakedefuse",
    "bot_savage_jumpscout",
    "bot_savage_reloadcover",
    "bot_savage_knife_midbrawl",
    "bot_savage_scavenge",
    "bot_savage_roledeliver",
    "bot_savage_chat_calls",
    "bot_savage_chat_cooldown",
]

PRESET_DEFINITIONS: Dict[str, Dict[str, Dict[str, str]]] = {
    "vanilla": {
        "savage": {
            "bot_savage_enable": "0",
        },
        "yapb": {
            "yb_difficulty": "1",
            "yb_difficulty_min": "1",
            "yb_difficulty_max": "2",
            "yb_shoots_thru_walls": "1",
        },
    },
    "tactical": {
        "savage": {
            "bot_savage_enable": "1",
            "bot_savage_roles": "1",
            "bot_savage_holding": "1",
            "bot_savage_calls": "1",
            "bot_savage_dropguns": "1",
            "bot_savage_bhop": "0",
            "bot_savage_counterstrafe": "1",
            "bot_savage_jiggle": "0",
            "bot_savage_recoil": "0",
            "bot_savage_triggerbot": "0",
            "bot_savage_tradefrag": "1",
            "bot_savage_antiflash": "0",
            "bot_savage_hivemind": "0",
            "bot_savage_wallbang": "0",
            "bot_savage_doublepeek": "0",
            "bot_savage_fakedefuse": "1",
            "bot_savage_jumpscout": "0",
            "bot_savage_reloadcover": "1",
            "bot_savage_knife_midbrawl": "1",
            "bot_savage_scavenge": "1",
            "bot_savage_roledeliver": "1",
            "bot_savage_chat_calls": "1",
        },
        "yapb": {
            "yb_difficulty": "2",
            "yb_difficulty_min": "2",
            "yb_difficulty_max": "3",
            "yb_shoots_thru_walls": "1",
        },
    },
    "competitive": {
        "savage": {
            "bot_savage_enable": "1",
            "bot_savage_roles": "1",
            "bot_savage_holding": "1",
            "bot_savage_calls": "1",
            "bot_savage_dropguns": "1",
            "bot_savage_bhop": "0",
            "bot_savage_counterstrafe": "1",
            "bot_savage_jiggle": "1",
            "bot_savage_recoil": "0",
            "bot_savage_triggerbot": "0",
            "bot_savage_tradefrag": "1",
            "bot_savage_antiflash": "1",
            "bot_savage_hivemind": "0",
            "bot_savage_wallbang": "1",
            "bot_savage_doublepeek": "1",
            "bot_savage_fakedefuse": "1",
            "bot_savage_jumpscout": "1",
            "bot_savage_reloadcover": "1",
            "bot_savage_knife_midbrawl": "1",
            "bot_savage_scavenge": "1",
            "bot_savage_roledeliver": "1",
            "bot_savage_chat_calls": "1",
        },
        "yapb": {
            "yb_difficulty": "3",
            "yb_difficulty_min": "3",
            "yb_difficulty_max": "3",
            "yb_shoots_thru_walls": "2",
        },
    },
    "demon": {
        "savage": {
            "bot_savage_enable": "1",
            "bot_savage_roles": "1",
            "bot_savage_holding": "1",
            "bot_savage_calls": "1",
            "bot_savage_dropguns": "1",
            "bot_savage_bhop": "1",
            "bot_savage_counterstrafe": "1",
            "bot_savage_jiggle": "1",
            "bot_savage_recoil": "1",
            "bot_savage_triggerbot": "1",
            "bot_savage_tradefrag": "1",
            "bot_savage_antiflash": "1",
            "bot_savage_hivemind": "1",
            "bot_savage_wallbang": "1",
            "bot_savage_doublepeek": "1",
            "bot_savage_fakedefuse": "1",
            "bot_savage_jumpscout": "1",
            "bot_savage_reloadcover": "1",
            "bot_savage_knife_midbrawl": "1",
            "bot_savage_scavenge": "1",
            "bot_savage_roledeliver": "1",
            "bot_savage_chat_calls": "1",
        },
        "yapb": {
            "yb_difficulty": "4",
            "yb_difficulty_min": "4",
            "yb_difficulty_max": "4",
            "yb_shoots_thru_walls": "3",
        },
    },
}


class BotAdapter:
    """Manages reading and writing YaPB & Savage Bot configurations."""

    def __init__(self, game_root: Optional[Path] = None):
        if game_root is None:
            self.game_root = get_project_root()
        else:
            self.game_root = Path(game_root).resolve()

        self.yapb_cfg = self.game_root / "cstrike" / "addons" / "yapb" / "conf" / "yapb.cfg"
        self.savage_cfg = self.game_root / "cstrike" / "addons" / "amxmodx" / "configs" / "bot_savage_roles.cfg"

    # -------------------------------------------------------------------------
    # YaPB Operations
    # -------------------------------------------------------------------------

    def get_yapb_settings(self) -> Dict[str, str]:
        """Reads all relevant YaPB configuration CVARs."""
        return parse_cfg_cvars(self.yapb_cfg, YAPB_RELEVANT_CVARS)

    def set_yapb_cvar(self, cvar: str, value: Any) -> bool:
        """Sets a single YaPB CVAR."""
        return set_cfg_cvar(self.yapb_cfg, cvar, value)

    def set_yapb_settings(self, settings: Dict[str, Any]) -> bool:
        """Batch updates YaPB CVARs atomically."""
        return set_cfg_cvars(self.yapb_cfg, settings)

    # -------------------------------------------------------------------------
    # Savage Bot Operations
    # -------------------------------------------------------------------------

    def get_savage_settings(self) -> Dict[str, str]:
        """Reads all relevant Savage Bot configuration CVARs."""
        return parse_cfg_cvars(self.savage_cfg, SAVAGE_RELEVANT_CVARS)

    def set_savage_cvar(self, cvar: str, value: Any) -> bool:
        """Sets a single Savage Bot CVAR."""
        return set_cfg_cvar(self.savage_cfg, cvar, value)

    def set_savage_settings(self, settings: Dict[str, Any]) -> bool:
        """Batch updates Savage Bot CVARs atomically."""
        return set_cfg_cvars(self.savage_cfg, settings)

    # -------------------------------------------------------------------------
    # Preset & Ecosystem Intelligence
    # -------------------------------------------------------------------------

    def detect_active_preset(
        self,
        savage_settings: Optional[Dict[str, str]] = None,
        yapb_settings: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Determines current active preset based on savage and yapb configuration values.
        Returns: 'vanilla' | 'tactical' | 'competitive' | 'demon' | 'custom'
        """
        if savage_settings is None:
            savage_settings = self.get_savage_settings()
        if yapb_settings is None:
            yapb_settings = self.get_yapb_settings()

        s_enable = savage_settings.get("bot_savage_enable", "1")
        if s_enable == "0":
            return "vanilla"

        tb = savage_settings.get("bot_savage_triggerbot", "0")
        recoil = savage_settings.get("bot_savage_recoil", "0")
        hive = savage_settings.get("bot_savage_hivemind", "0")
        bhop = savage_settings.get("bot_savage_bhop", "0")

        if tb == "1" and recoil == "1" and hive == "1":
            return "demon"

        if tb == "0" and recoil == "0" and hive == "0":
            antiflash = savage_settings.get("bot_savage_antiflash", "0")
            jiggle = savage_settings.get("bot_savage_jiggle", "0")
            wallbang = savage_settings.get("bot_savage_wallbang", "0")
            if antiflash == "1" and (jiggle == "1" or wallbang == "1"):
                return "competitive"
            elif antiflash == "0" and wallbang == "0" and jiggle == "0":
                return "tactical"

        return "custom"

    def get_bot_ecosystem(self) -> Dict[str, Any]:
        """Returns the full bot ecosystem state for Web UI rendering."""
        yapb_cvars = self.get_yapb_settings()
        savage_cvars = self.get_savage_settings()
        active_preset = self.detect_active_preset(savage_cvars, yapb_cvars)
        savage_enable = savage_cvars.get("bot_savage_enable", "1") == "1"

        return {
            "success": True,
            "savage_enable": savage_enable,
            "active_preset": active_preset,
            "yapb": yapb_cvars,
            "savage": savage_cvars,
        }

    def apply_difficulty_preset(self, preset_name: str) -> Dict[str, Any]:
        """
        Applies a multi-tier difficulty preset across both Savage Bot and YaPB configurations.
        """
        preset_name = preset_name.strip().lower()
        if preset_name not in PRESET_DEFINITIONS:
            return {"success": False, "error": f"Unknown preset: '{preset_name}'"}

        preset = PRESET_DEFINITIONS[preset_name]
        savage_changes = preset.get("savage", {})
        yapb_changes = preset.get("yapb", {})

        s_ok = True
        if savage_changes:
            s_ok = self.set_savage_settings(savage_changes)

        y_ok = True
        if yapb_changes:
            y_ok = self.set_yapb_settings(yapb_changes)

        return {
            "success": s_ok and y_ok,
            "preset": preset_name,
            "savage_updated": s_ok,
            "yapb_updated": y_ok,
        }

    def toggle_savage_ai(self, enable: bool) -> Dict[str, Any]:
        """
        Master switch: 1-click toggle to enable or disable Savage AI and restore native YaPB.
        """
        val = "1" if enable else "0"
        s_ok = self.set_savage_cvar("bot_savage_enable", val)
        if not enable:
            # Revert YaPB shoots_thru_walls and difficulty to balanced standard if desired
            self.set_yapb_cvar("yb_shoots_thru_walls", "1")
        return {"success": s_ok, "savage_enable": enable}

    def sanitize_cheats(self) -> Dict[str, Any]:
        """
        Atomically disables all 4 predator/cheat tier parameters in bot_savage_roles.cfg.
        Does not affect any other roles, movement, or YaPB settings.
        """
        cheats = {
            "bot_savage_triggerbot": "0",
            "bot_savage_recoil": "0",
            "bot_savage_wallbang": "0",
            "bot_savage_hivemind": "0",
        }
        s_ok = self.set_savage_settings(cheats)
        return {
            "success": s_ok,
            "sanitized": list(cheats.keys()),
            "active_preset": self.detect_active_preset(),
        }


# Global instance
_default_bot_adapter: Optional[BotAdapter] = None


def get_bot_adapter() -> BotAdapter:
    global _default_bot_adapter
    if _default_bot_adapter is None:
        _default_bot_adapter = BotAdapter()
    return _default_bot_adapter
