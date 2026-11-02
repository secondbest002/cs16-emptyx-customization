"""
tools/cs16_mod_hub/gui/tabs/amxx_tab.py
Tab 4: Plugin & Gameplay Manager.
Controls 7 AMX Mod X plugins in plugins.ini and competitive tournament CVARs in csgo_competitive.cfg.
"""

from __future__ import annotations

import os
from pathlib import Path
import threading
from tkinter import messagebox
from typing import Dict, Optional
import customtkinter

from ..theme import (
    COLOR_BG_CARD,
    COLOR_BG_INPUT,
    COLOR_BORDER,
    COLOR_ACCENT_PRIMARY,
    COLOR_ACCENT_HOVER,
    COLOR_ACCENT_SECONDARY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_SUCCESS,
    COLOR_ERROR,
    GLYPH_GEAR,
    GLYPH_CHECK,
    GLYPH_RESET,
    GLYPH_DIAMOND,
    font_body,
    font_body_bold,
    font_small,
    font_card_title,
)
from ..components.card_frame import CardFrame
from ..components.log_console import LogConsole
from ...core.amxx_adapter import (
    AmxxAdapter,
    MANAGED_PLUGINS,
    get_plugin_status,
    set_plugin_status,
    list_custom_plugins,
    get_competitive_settings,
    set_competitive_settings,
)


class AmxxTab(customtkinter.CTkFrame):
    """
    Plugin & Gameplay Manager Tab view.
    """

    PLUGIN_LABELS = {
        "cs2_modern_engine.amxx": "CS2 Unified Modern Engine (10 Core Mechanics)",
        "cs2_skin_inventory.amxx": "CS2 Skin Inventory & Loadout Wheel",
        "cs2_weapon_variants.amxx": "CS2 Weapon Variants & Meta Pricing",
        "csgo_competitive.amxx": "Competitive Match Mod (MR12/15, Timeouts)",
        "bot_savage_ai.amxx": "Bot Savage & Predator AI (Esports Tactics & Eco)",
        "team_weapon_skins.amxx": "Team Weapon Skins [Legacy Fallback]",
        "csgo_knife_sound_manager.amxx": "Knife Sound Engine [Legacy Fallback]",
        "csgo_m4_loadout.amxx": "M4 Loadout Switcher [Legacy Fallback]",
        "csgo_usps_silencer.amxx": "USP-S Silencer Lock [Legacy Fallback]",
        "csgo_ammo_refill.amxx": "Ammo & Round Refill [Legacy Fallback]",
    }

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._plugin_switches: Dict[str, customtkinter.CTkSwitch] = {}
        self._is_loading = True

        # Top section: Two Cards
        self.top_container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.top_container.pack(fill="x", padx=10, pady=(10, 6))

        # Left Card: Managed AMXX Plugins
        self.card_plugins = CardFrame(
            self.top_container,
            title="AMX Mod X Plugins",
            subtitle="Toggle plugins directly in cstrike/addons/amxmodx/configs/plugins.ini",
            glyph=GLYPH_GEAR,
        )
        self.card_plugins.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # Right Card: Competitive Tournament Match Tuner
        self.card_competitive = CardFrame(
            self.top_container,
            title="Competitive Rules & CVARs",
            subtitle="Configure MR12/MR15 match rules and gameplay options in csgo_competitive.cfg",
            glyph=GLYPH_DIAMOND,
        )
        self.card_competitive.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # Build cards
        self._build_plugins_ui(self.card_plugins.content_frame)
        self._build_competitive_ui(self.card_competitive.content_frame)

        # Bottom section: Real-time Log Console
        self.console = LogConsole(
            self,
            title="Plugin & Gameplay Output Console",
            height=160,
        )
        self.console.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        # Load initial configuration from files
        self.load_configurations()

    def _build_plugins_ui(self, parent: customtkinter.CTkFrame) -> None:
        """Builds 7 live toggle switches for AMXX plugins."""
        for plugin in MANAGED_PLUGINS:
            label_text = self.PLUGIN_LABELS.get(plugin, plugin)

            switch = customtkinter.CTkSwitch(
                parent,
                text=label_text,
                font=font_body(),
                progress_color=COLOR_ACCENT_PRIMARY,
                text_color=COLOR_TEXT_PRIMARY,
                command=lambda p=plugin: self._on_plugin_toggled(p),
            )
            switch.pack(anchor="w", pady=4)
            self._plugin_switches[plugin] = switch

        # Reload plugins button
        btn_reload = customtkinter.CTkButton(
            parent,
            text=f"{GLYPH_RESET} Reload Plugins from Disk",
            font=font_small(),
            fg_color=COLOR_BORDER,
            hover_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            height=28,
            command=self.load_configurations,
        )
        btn_reload.pack(anchor="w", pady=(10, 2))

    def _build_competitive_ui(self, parent: customtkinter.CTkFrame) -> None:
        """Builds competitive format segmented buttons and toggle switches."""
        # Row 1: Match Format (MR12 vs MR15)
        lbl_format = customtkinter.CTkLabel(
            parent,
            text="Match Format (Rounds):",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_format.pack(anchor="w", pady=(2, 2))

        self.seg_format = customtkinter.CTkSegmentedButton(
            parent,
            values=["MR12 (First to 13, Max 24)", "MR15 (First to 16, Max 30)"],
            font=font_body(),
            selected_color=COLOR_ACCENT_PRIMARY,
            selected_hover_color=COLOR_ACCENT_HOVER,
            unselected_color=COLOR_BG_INPUT,
            unselected_hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.seg_format.set("MR12 (First to 13, Max 24)")
        self.seg_format.pack(fill="x", pady=(0, 6))

        # Row 2: Overtime Money ($10,000 vs $16,000)
        lbl_ot = customtkinter.CTkLabel(
            parent,
            text="Overtime Starting Money:",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_ot.pack(anchor="w", pady=(2, 2))

        self.seg_ot_money = customtkinter.CTkSegmentedButton(
            parent,
            values=["$10,000 (Standard)", "$16,000 (Full Buy)"],
            font=font_body(),
            selected_color=COLOR_ACCENT_PRIMARY,
            selected_hover_color=COLOR_ACCENT_HOVER,
            unselected_color=COLOR_BG_INPUT,
            unselected_hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.seg_ot_money.set("$10,000 (Standard)")
        self.seg_ot_money.pack(fill="x", pady=(0, 6))

        # Row 3: Gameplay Switches
        self.switch_knife = customtkinter.CTkSwitch(
            parent,
            text="Knife Round Decider (amx_csgo_kniferound)",
            font=font_body(),
            progress_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.switch_knife.pack(anchor="w", pady=3)

        self.switch_warmup = customtkinter.CTkSwitch(
            parent,
            text="Warmup Deathmatch (amx_csgo_warmup)",
            font=font_body(),
            progress_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.switch_warmup.pack(anchor="w", pady=3)

        self.switch_hud = customtkinter.CTkSwitch(
            parent,
            text="CS:GO Tactical HUD Style (amx_csgo_hud_style)",
            font=font_body(),
            progress_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.switch_hud.pack(anchor="w", pady=3)

        switch_grid = customtkinter.CTkFrame(parent, fg_color="transparent")
        switch_grid.pack(fill="x", pady=2)

        self.switch_dmg = customtkinter.CTkSwitch(
            switch_grid,
            text="Damage Card (amx_csgo_dmg_card)",
            font=font_body(),
            progress_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.switch_dmg.pack(side="left", padx=(0, 10))

        self.switch_mvp = customtkinter.CTkSwitch(
            switch_grid,
            text="MVP Card (amx_csgo_mvp_card)",
            font=font_body(),
            progress_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.switch_mvp.pack(side="left")

        # Row 4: Save Config Action Button
        self.btn_save_cfg = customtkinter.CTkButton(
            parent,
            text=f"{GLYPH_CHECK} Save Competitive Config",
            font=font_body_bold(),
            fg_color=COLOR_ACCENT_PRIMARY,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#1a1e24",
            height=34,
            command=self._on_save_competitive_clicked,
        )
        self.btn_save_cfg.pack(fill="x", pady=(10, 2))

    def load_configurations(self) -> None:
        """Reads plugins.ini and csgo_competitive.cfg from disk and populates widgets."""
        self._is_loading = True
        try:
            # 1. Populate plugin switches
            plugin_dict = list_custom_plugins()
            for plugin, pinfo in plugin_dict.items():
                if plugin in self._plugin_switches:
                    if pinfo.enabled:
                        self._plugin_switches[plugin].select()
                    else:
                        self._plugin_switches[plugin].deselect()

            self.console.log("Loaded AMX Mod X plugins.ini status.")

            # 2. Populate competitive settings
            settings = get_competitive_settings()
            maxrounds = settings.get("amx_csgo_maxrounds", "12")
            if maxrounds in ("15", "30"):
                self.seg_format.set("MR15 (First to 16, Max 30)")
            else:
                self.seg_format.set("MR12 (First to 13, Max 24)")

            ot_money = settings.get("amx_csgo_ot_money", "10000")
            if ot_money == "16000":
                self.seg_ot_money.set("$16,000 (Full Buy)")
            else:
                self.seg_ot_money.set("$10,000 (Standard)")

            # Switches
            self._set_switch_state(self.switch_knife, settings.get("amx_csgo_kniferound", "1") == "1")
            self._set_switch_state(self.switch_warmup, settings.get("amx_csgo_warmup", "1") == "1")
            self._set_switch_state(self.switch_hud, settings.get("amx_csgo_hud_style", "1") == "1")
            self._set_switch_state(self.switch_dmg, settings.get("amx_csgo_dmg_card", "1") == "1")
            self._set_switch_state(self.switch_mvp, settings.get("amx_csgo_mvp_card", "1") == "1")

            self.console.log("Loaded csgo_competitive.cfg parameters.")
            self.console.set_status("Ready", is_busy=False)
        except Exception as e:
            self.console.log(f"Notice during load: {e}")
        finally:
            self._is_loading = False

    def _set_switch_state(self, switch: customtkinter.CTkSwitch, enabled: bool) -> None:
        if enabled:
            switch.select()
        else:
            switch.deselect()

    def _on_plugin_toggled(self, plugin_name: str) -> None:
        """Instant atomic update when a plugin toggle switch is flipped."""
        if self._is_loading:
            return

        switch = self._plugin_switches[plugin_name]
        is_enabled = bool(switch.get())
        state_str = "ENABLED" if is_enabled else "DISABLED"

        ok = set_plugin_status(plugin_name, is_enabled)
        if ok:
            self.console.log(f"AMXX: '{plugin_name}' set to {state_str} in plugins.ini.")
            self.console.set_status("Saved", level="success")
        else:
            self.console.log(f"ERROR: Failed to update '{plugin_name}' in plugins.ini.")
            self.console.set_status("Error", level="error")

    def _on_save_competitive_clicked(self) -> None:
        """Saves competitive configuration changes to csgo_competitive.cfg."""
        format_sel = self.seg_format.get()
        maxrounds = "15" if "MR15" in format_sel else "12"

        ot_sel = self.seg_ot_money.get()
        ot_money = "16000" if "16,000" in ot_sel else "10000"

        settings_to_save = {
            "amx_csgo_maxrounds": maxrounds,
            "amx_csgo_ot_money": ot_money,
            "amx_csgo_kniferound": "1" if self.switch_knife.get() else "0",
            "amx_csgo_warmup": "1" if self.switch_warmup.get() else "0",
            "amx_csgo_hud_style": "1" if self.switch_hud.get() else "0",
            "amx_csgo_dmg_card": "1" if self.switch_dmg.get() else "0",
            "amx_csgo_mvp_card": "1" if self.switch_mvp.get() else "0",
        }

        self.console.set_status("Saving...", is_busy=True)
        ok = set_competitive_settings(settings_to_save)
        if ok:
            self.console.log(f"Successfully saved competitive CVARs to csgo_competitive.cfg:")
            for k, v in settings_to_save.items():
                self.console.log(f"  {k} = {v}")
            self.console.set_status("Saved", level="success")
        else:
            self.console.log("ERROR: Failed to save settings to csgo_competitive.cfg.")
            self.console.set_status("Error", level="error")
