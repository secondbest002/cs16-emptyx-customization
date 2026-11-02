"""
tools/cs16_mod_hub/core/amxx_adapter.py
Safely query, toggle, and configure AMX Mod X plugins, CS2 Modern Engine modules,
and competitive match CVARs.
Preserves line order, section comments, inline comments, and exact line endings.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional

from .common import get_project_root
from .cfg_utils import (
    parse_cfg_cvars,
    get_cfg_cvar,
    set_cfg_cvar,
    set_cfg_cvars,
    atomic_write_file,
    detect_line_ending,
)

# Core Modern Plugins & Legacy Fallbacks
MODERN_CORE_PLUGINS = [
    "cs2_modern_engine.amxx",
    "cs2_skin_inventory.amxx",
    "cs2_weapon_variants.amxx",
    "csgo_competitive.amxx",
    "bot_savage_ai.amxx",
]

LEGACY_MANAGED_PLUGINS = [
    "team_weapon_skins.amxx",
    "csgo_knife_sound_manager.amxx",
    "csgo_m4_loadout.amxx",
    "csgo_usps_silencer.amxx",
    "csgo_ammo_refill.amxx",
]

MANAGED_PLUGINS = MODERN_CORE_PLUGINS + LEGACY_MANAGED_PLUGINS

PLUGIN_METADATA = {
    "cs2_modern_engine.amxx": {
        "title": "CS2 Unified Modern Engine",
        "category": "Core Gameplay",
        "desc": "Centralized 10 modern mechanics: Kill chimes, HS dink, 3-way utility, E-pickup, switchhands, auto ammo, USPS lock, smart ping.",
    },
    "cs2_skin_inventory.amxx": {
        "title": "CS2 Skin Inventory & Loadout Wheel",
        "category": "Visuals & Economy",
        "desc": "Persistent nvault skin loadout manager, CT/T loadout wheels, M4A4/M4A1-S variant loadout slots.",
    },
    "cs2_weapon_variants.amxx": {
        "title": "CS2 Modern Weapon Variants",
        "category": "Weapons & Balancing",
        "desc": "Authentic CS2/CS:GO weapon pricing, reserve ammo balance, and authentic clip capacities.",
    },
    "csgo_competitive.amxx": {
        "title": "CS:GO/CS2 Competitive Match Engine",
        "category": "Match & Rules",
        "desc": "MR12/15 regulation rounds, Overtime rules, Warmup, Knife Round, Tactical Timeouts, and HUD Damage Cards.",
    },
    "bot_savage_ai.amxx": {
        "title": "Savage Esports Bot AI",
        "category": "AI & Companion",
        "desc": "5-Role competitive meta, holding angles, weapon drops, counter-strafe, and tactical radio calls.",
    },
}

CS2_ENGINE_CVARS = [
    "amx_cs2_engine",
    "amx_cs2_kill_chimes",
    "amx_cs2_headshot_dink",
    "amx_cs2_c4_warning",
    "amx_cs2_hud_cards",
    "amx_cs2_kill_reward",
    "amx_cs2_kill_reward_notify",
    "amx_cs2_throw_strength",
    "amx_cs2_smoke_bullets",
    "amx_cs2_smoke_disperse",
    "amx_cs2_drop_nades",
    "amx_cs2_buy_refund",
    "amx_cs2_refund_on_r",
    "amx_cs2_epickup",
    "amx_cs2_epickup_radius",
    "amx_cs2_epickup_sound",
    "amx_switchhands_enable",
    "amx_switchhands_redraw",
    "amx_switchhands_sound",
    "amx_switchhands_delay",
    "amx_switchhands_cooldown",
    "amx_csgo_ammo",
    "amx_csgo_ammo_on_buy",
    "amx_csgo_ammo_round_start",
    "amx_csgo_ammo_instant_clip",
    "amx_csgo_ammo_block_cmds",
    "amx_usps_lock",
    "amx_usps_ct_only",
    "amx_usps_block_secondary",
    "amx_usps_auto_silence",
    "amx_cs2_knife_sounds",
    "amx_cs2_ping",
    "amx_cs2_ping_cooldown",
    "amx_cs2_ping_duration",
    "amx_cs2_ping_bot_ai",
    "amx_cs2_ping_dlight",
    "amx_cs2_ping_hud",
    "amx_cs2_silentreload",
]

RE_PLUGIN_LINE = re.compile(
    r"^(?P<indent>\s*)(?P<comment>;*)\s*(?P<plugin>[a-zA-Z0-9_\-\/\\\.]+\.amxx)(?P<rest>.*?)(?P<eol>\r?\n)?$",
    re.IGNORECASE,
)


@dataclass
class PluginInfo:
    name: str
    enabled: bool
    description: str
    line_number: int
    category: str = "Custom"
    display_title: str = ""

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


@dataclass
class CompetitiveSetting:
    cvar: str
    value: str
    description: str = ""
    category: str = "Competitive"

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


class AmxxAdapter:
    """High-level interface for querying and modifying AMX Mod X plugins and configs."""

    def __init__(self, game_root: Optional[Path] = None):
        if game_root is None:
            self.game_root = get_project_root()
        else:
            self.game_root = Path(game_root).resolve()

        self.plugins_ini = self.game_root / "cstrike" / "addons" / "amxmodx" / "configs" / "plugins.ini"
        self.competitive_cfg = self.game_root / "cstrike" / "addons" / "amxmodx" / "configs" / "csgo_competitive.cfg"
        self.cs2_engine_cfg = self.game_root / "cstrike" / "addons" / "amxmodx" / "configs" / "cs2_modern_engine.cfg"

    # -------------------------------------------------------------------------
    # plugins.ini Operations
    # -------------------------------------------------------------------------

    def _normalize_plugin_name(self, name: str) -> str:
        s = name.strip().lower()
        if not s.endswith(".amxx"):
            s += ".amxx"
        return Path(s).name

    def get_plugin_status(self, plugin_name: str) -> Optional[bool]:
        """Returns True if plugin is enabled, False if commented with ;, or None if not found."""
        if not self.plugins_ini.is_file():
            return None

        target = self._normalize_plugin_name(plugin_name)
        text = self.plugins_ini.read_bytes().decode("utf-8", errors="replace")
        for line in text.splitlines():
            m = RE_PLUGIN_LINE.match(line)
            if m and Path(m.group("plugin")).name.lower() == target:
                return len(m.group("comment")) == 0
        return None

    def set_plugin_status(self, plugin_name: str, enabled: bool, append_if_missing: bool = True) -> bool:
        """Enables or disables plugin in plugins.ini, preserving comments, spacing, and order."""
        if not self.plugins_ini.is_file():
            return False

        target = self._normalize_plugin_name(plugin_name)
        text = self.plugins_ini.read_bytes().decode("utf-8", errors="replace")
        eol = detect_line_ending(text)
        lines = text.splitlines(keepends=True)

        found = False
        changed = False
        new_lines: List[str] = []

        for line in lines:
            m = RE_PLUGIN_LINE.match(line)
            if m and Path(m.group("plugin")).name.lower() == target:
                found = True
                indent = m.group("indent")
                plugin_token = m.group("plugin")
                rest = m.group("rest")
                line_eol = m.group("eol") or eol
                is_currently_enabled = len(m.group("comment")) == 0

                if enabled and not is_currently_enabled:
                    new_lines.append(f"{indent}{plugin_token}{rest}{line_eol}")
                    changed = True
                elif not enabled and is_currently_enabled:
                    new_lines.append(f"{indent};{plugin_token}{rest}{line_eol}")
                    changed = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        if not found:
            if enabled and append_if_missing:
                if new_lines and not new_lines[-1].endswith(("\n", "\r")):
                    new_lines[-1] += eol
                new_lines.append(f"{target}{eol}")
                changed = True
            else:
                return False

        if changed:
            atomic_write_file(self.plugins_ini, "".join(new_lines))
        return True

    def list_custom_plugins(self) -> Dict[str, PluginInfo]:
        """Scans plugins.ini and returns status dictionary for managed plugins."""
        result: Dict[str, PluginInfo] = {}
        if not self.plugins_ini.is_file():
            return result

        text = self.plugins_ini.read_bytes().decode("utf-8", errors="replace")
        lines = text.splitlines(keepends=True)

        for p in MANAGED_PLUGINS:
            meta = PLUGIN_METADATA.get(p, {})
            result[p] = PluginInfo(
                name=p,
                enabled=False,
                description=meta.get("desc", ""),
                line_number=-1,
                category=meta.get("category", "Custom"),
                display_title=meta.get("title", p),
            )

        for idx, line in enumerate(lines, start=1):
            m = RE_PLUGIN_LINE.match(line)
            if m:
                p_name = Path(m.group("plugin")).name.lower()
                for target_p in MANAGED_PLUGINS:
                    if target_p.lower() == p_name:
                        desc = m.group("rest").strip()
                        if desc.startswith(";"):
                            desc = desc.lstrip(";").strip()
                        meta = PLUGIN_METADATA.get(target_p, {})
                        result[target_p] = PluginInfo(
                            name=target_p,
                            enabled=(len(m.group("comment")) == 0),
                            description=desc or meta.get("desc", ""),
                            line_number=idx,
                            category=meta.get("category", "Custom"),
                            display_title=meta.get("title", target_p),
                        )
        return result

    def list_all_plugins(self) -> List[PluginInfo]:
        """Returns all plugins listed in plugins.ini."""
        plugins: List[PluginInfo] = []
        if not self.plugins_ini.is_file():
            return plugins

        text = self.plugins_ini.read_bytes().decode("utf-8", errors="replace")
        for idx, line in enumerate(text.splitlines(keepends=True), start=1):
            m = RE_PLUGIN_LINE.match(line)
            if m:
                p_filename = Path(m.group("plugin")).name
                desc = m.group("rest").strip()
                if desc.startswith(";"):
                    desc = desc.lstrip(";").strip()
                meta = PLUGIN_METADATA.get(p_filename.lower(), {})
                plugins.append(
                    PluginInfo(
                        name=p_filename,
                        enabled=(len(m.group("comment")) == 0),
                        description=desc or meta.get("desc", ""),
                        line_number=idx,
                        category=meta.get("category", "Custom"),
                        display_title=meta.get("title", p_filename),
                    )
                )
        return plugins

    # -------------------------------------------------------------------------
    # cs2_modern_engine.cfg Operations
    # -------------------------------------------------------------------------

    def get_cs2_engine_settings(self) -> Dict[str, str]:
        """Reads all configuration CVARs from cs2_modern_engine.cfg."""
        return parse_cfg_cvars(self.cs2_engine_cfg, CS2_ENGINE_CVARS)

    def set_cs2_engine_cvar(self, cvar_name: str, value: Any) -> bool:
        """Sets a single CVAR in cs2_modern_engine.cfg."""
        return set_cfg_cvar(self.cs2_engine_cfg, cvar_name, value)

    def set_cs2_engine_settings(self, settings: Dict[str, Any]) -> bool:
        """Batch updates CVARs in cs2_modern_engine.cfg atomically."""
        return set_cfg_cvars(self.cs2_engine_cfg, settings)

    # -------------------------------------------------------------------------
    # csgo_competitive.cfg Operations
    # -------------------------------------------------------------------------

    def get_cvar(self, cvar_name: str) -> Optional[str]:
        """Reads CVAR value from csgo_competitive.cfg."""
        return get_cfg_cvar(self.competitive_cfg, cvar_name)

    def set_cvar(self, cvar_name: str, value: Any, append_if_missing: bool = True) -> bool:
        """Updates CVAR value in csgo_competitive.cfg."""
        return set_cfg_cvar(self.competitive_cfg, cvar_name, value, append_if_missing=append_if_missing)

    def get_competitive_settings(self) -> Dict[str, str]:
        """Returns structured dictionary of primary competitive settings."""
        keys = [
            "amx_csgo_mode",
            "amx_csgo_maxrounds",
            "amx_csgo_kniferound",
            "amx_csgo_warmup",
            "amx_csgo_timeouts",
            "amx_csgo_timeout_duration",
            "amx_csgo_ot_money",
            "amx_csgo_bot_autoready",
            "amx_csgo_lossbonus",
            "amx_csgo_hud_style",
            "amx_csgo_mvp_card",
            "amx_csgo_c4_timer",
            "amx_csgo_screenfade",
            "amx_csgo_dmg_card",
            "mp_roundtime",
            "mp_c4timer",
            "mp_freezetime",
            "mp_buytime",
            "mp_startmoney",
            "csgo_comp_max_rounds",
            "csgo_comp_overtime",
            "csgo_comp_warmup_time",
        ]
        return parse_cfg_cvars(self.competitive_cfg, keys)

    def set_competitive_settings(self, settings: Dict[str, Any]) -> bool:
        """Batch updates competitive settings in csgo_competitive.cfg atomically."""
        return set_cfg_cvars(self.competitive_cfg, settings)


# Module-level convenience functions
_default_adapter: Optional[AmxxAdapter] = None


def _get_adapter() -> AmxxAdapter:
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = AmxxAdapter()
    return _default_adapter


def get_plugin_status(plugin_name: str) -> Optional[bool]:
    return _get_adapter().get_plugin_status(plugin_name)


def set_plugin_status(plugin_name: str, enabled: bool) -> bool:
    return _get_adapter().set_plugin_status(plugin_name, enabled)


def list_custom_plugins() -> Dict[str, PluginInfo]:
    return _get_adapter().list_custom_plugins()


def list_all_plugins() -> List[PluginInfo]:
    return _get_adapter().list_all_plugins()


def get_cvar(cvar_name: str) -> Optional[str]:
    return _get_adapter().get_cvar(cvar_name)


def set_cvar(cvar_name: str, value: Any) -> bool:
    return _get_adapter().set_cvar(cvar_name, value)


def get_competitive_settings() -> Dict[str, str]:
    return _get_adapter().get_competitive_settings()


def set_competitive_settings(settings: Dict[str, Any]) -> bool:
    return _get_adapter().set_competitive_settings(settings)


def get_cs2_engine_settings() -> Dict[str, str]:
    return _get_adapter().get_cs2_engine_settings()


def set_cs2_engine_cvar(cvar_name: str, value: Any) -> bool:
    return _get_adapter().set_cs2_engine_cvar(cvar_name, value)


def set_cs2_engine_settings(settings: Dict[str, Any]) -> bool:
    return _get_adapter().set_cs2_engine_settings(settings)
