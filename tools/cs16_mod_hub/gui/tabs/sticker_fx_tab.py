"""
tools/cs16_mod_hub/gui/tabs/sticker_fx_tab.py
Tab 3: Sticker FX Lab.
Customizes sticker visual effects: Chrome/Foil metallic gleam (0x42), flat Matte (0x40),
Additive Glow (0x60), and non-destructive sticker hiding and restoration.
"""

from __future__ import annotations

import os
from pathlib import Path
import threading
from tkinter import messagebox
from typing import List, Optional
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
    GLYPH_CHECK,
    GLYPH_DIAMOND,
    GLYPH_DIAMOND_OUTLINE,
    GLYPH_RESET,
    font_body,
    font_body_bold,
    font_small,
    font_card_title,
)
from ..components.card_frame import CardFrame
from ..components.log_console import LogConsole
from ...core.model_adapter import list_viewmodels
from ...core.sticker_adapter import (
    set_sticker_fx,
    scan_model_stickers,
    get_mode_description,
    list_supported_modes,
)


class StickerFxTab(customtkinter.CTkFrame):
    """
    Sticker FX Lab Tab view.
    """

    MODE_MAP = {
        "Foil / Chrome (0x42)": "foil",
        "Matte Decal (0x40)": "matte",
        "Additive Glow (0x60)": "glow",
        "Hide Sticker": "hide",
        "Restore Sticker": "restore",
    }

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._is_busy = False
        self._sticker_slots: List[dict] = []

        # Top section: Two Cards
        self.top_container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.top_container.pack(fill="x", padx=10, pady=(10, 6))

        # Left Card: Target Model & Sticker Slot
        self.card_slot = CardFrame(
            self.top_container,
            title="Model & Sticker Slot",
            subtitle="Select the viewmodel and target sticker/decal slot",
            glyph=GLYPH_DIAMOND,
        )
        self.card_slot.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # Right Card: Visual Effect Mode
        self.card_mode = CardFrame(
            self.top_container,
            title="Visual Rendering Effect",
            subtitle="Select the GoldSrc engine rendering flag or visibility state",
            glyph=GLYPH_DIAMOND_OUTLINE,
        )
        self.card_mode.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # Build UI in cards
        self._build_slot_ui(self.card_slot.content_frame)
        self._build_mode_ui(self.card_mode.content_frame)

        # Bottom section: Real-time Log Console
        self.console = LogConsole(
            self,
            title="Sticker FX Output Console",
            height=200,
        )
        self.console.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        # Initial populate
        self.refresh_models()

    def _build_slot_ui(self, parent: customtkinter.CTkFrame) -> None:
        """Constructs weapon dropdown, scan button, and sticker slot selector."""
        # Row 1: Active Weapon Model
        lbl_weapon = customtkinter.CTkLabel(
            parent,
            text="Active Weapon Model:",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_weapon.pack(anchor="w", pady=(2, 2))

        weapon_row = customtkinter.CTkFrame(parent, fg_color="transparent")
        weapon_row.pack(fill="x", pady=(0, 8))

        self.cb_weapon = customtkinter.CTkComboBox(
            weapon_row,
            font=font_body(),
            dropdown_font=font_body(),
            fg_color=COLOR_BG_INPUT,
            border_color=COLOR_BORDER,
            button_color=COLOR_ACCENT_PRIMARY,
            button_hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_text_color=COLOR_TEXT_PRIMARY,
            dropdown_fg_color=COLOR_BG_CARD,
            values=["Scanning models..."],
            state="readonly",
            command=self._on_weapon_changed,
        )
        self.cb_weapon.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_rescan = customtkinter.CTkButton(
            weapon_row,
            text=f"{GLYPH_RESET} Rescan",
            width=76,
            font=font_small(),
            fg_color=COLOR_BORDER,
            hover_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            command=self._scan_stickers_for_active_weapon,
        )
        btn_rescan.pack(side="right")

        # Row 2: Sticker Slot Selector
        lbl_slot = customtkinter.CTkLabel(
            parent,
            text="Target Sticker Slot:",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_slot.pack(anchor="w", pady=(2, 2))

        self.cb_slot = customtkinter.CTkComboBox(
            parent,
            font=font_body(),
            dropdown_font=font_body(),
            fg_color=COLOR_BG_INPUT,
            border_color=COLOR_BORDER,
            button_color=COLOR_ACCENT_PRIMARY,
            button_hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_text_color=COLOR_TEXT_PRIMARY,
            dropdown_fg_color=COLOR_BG_CARD,
            values=["All Stickers"],
            state="readonly",
        )
        self.cb_slot.pack(fill="x", pady=(0, 8))

        # Slot Info Summary Label
        self.lbl_slot_summary = customtkinter.CTkLabel(
            parent,
            text="Found 0 sticker slots in selected model.",
            font=font_small(),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        self.lbl_slot_summary.pack(fill="x", pady=(2, 2))

    def _build_mode_ui(self, parent: customtkinter.CTkFrame) -> None:
        """Constructs effect mode selection and description display."""
        lbl_mode = customtkinter.CTkLabel(
            parent,
            text="Rendering Mode / Flag:",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_mode.pack(anchor="w", pady=(2, 2))

        self.seg_mode = customtkinter.CTkSegmentedButton(
            parent,
            values=list(self.MODE_MAP.keys()),
            font=font_small(),
            selected_color=COLOR_ACCENT_PRIMARY,
            selected_hover_color=COLOR_ACCENT_HOVER,
            unselected_color=COLOR_BG_INPUT,
            unselected_hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
            command=self._on_mode_changed,
        )
        self.seg_mode.set("Foil / Chrome (0x42)")
        self.seg_mode.pack(fill="x", pady=(0, 8))

        # Mode Description Box
        self.card_desc = customtkinter.CTkFrame(
            parent,
            fg_color=COLOR_BG_INPUT,
            corner_radius=6,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.card_desc.pack(fill="x", pady=(0, 10))

        self.lbl_desc_title = customtkinter.CTkLabel(
            self.card_desc,
            text="GoldSrc Engine Rendering Behavior:",
            font=font_small(),
            text_color=COLOR_ACCENT_PRIMARY,
            anchor="w",
        )
        self.lbl_desc_title.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_desc_text = customtkinter.CTkLabel(
            self.card_desc,
            text=get_mode_description("foil"),
            font=font_body(),
            text_color=COLOR_TEXT_PRIMARY,
            wraplength=400,
            justify="left",
            anchor="w",
        )
        self.lbl_desc_text.pack(fill="x", padx=10, pady=(0, 8))

        # Action Button: Apply Sticker FX
        self.btn_apply = customtkinter.CTkButton(
            parent,
            text=f"{GLYPH_CHECK} Apply Sticker FX",
            font=font_body_bold(),
            fg_color=COLOR_ACCENT_PRIMARY,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#1a1e24",
            height=34,
            command=self._on_apply_clicked,
        )
        self.btn_apply.pack(fill="x", pady=(2, 2))

    def refresh_models(self) -> None:
        """Refreshes weapon dropdown and initiates sticker scan."""
        viewmodels = list_viewmodels()
        if not viewmodels:
            viewmodels = ["v_ak47.mdl", "v_m4a1.mdl", "v_awp.mdl"]

        self.cb_weapon.configure(values=viewmodels)
        if viewmodels:
            self.cb_weapon.set(viewmodels[0])
            self._scan_stickers_for_active_weapon()

    def _on_weapon_changed(self, _weapon: str) -> None:
        self._scan_stickers_for_active_weapon()

    def _scan_stickers_for_active_weapon(self) -> None:
        """Scans current weapon model for sticker textures."""
        weapon = self.cb_weapon.get().strip()
        if not weapon:
            return

        try:
            self._sticker_slots = scan_model_stickers(weapon)
            options = ["All Stickers"]
            for slot in self._sticker_slots:
                name = slot["name"]
                mode = slot["mode_name"]
                hidden_flag = " [HIDDEN]" if slot["is_hidden"] else ""
                options.append(f"Slot {slot['index']}: {name} ({mode}){hidden_flag}")

            self.cb_slot.configure(values=options)
            self.cb_slot.set("All Stickers")

            n_slots = len(self._sticker_slots)
            self.lbl_slot_summary.configure(
                text=f"Model '{weapon}': {n_slots} sticker/decal slot(s) identified."
            )
            self.console.log(f"Scanned '{weapon}': found {n_slots} sticker slot(s).")
            for s in self._sticker_slots:
                self.console.log(
                    f"  Slot {s['index']}: '{s['name']}' ({s['width']}x{s['height']}) - Mode: {s['mode_name']}"
                )
        except Exception as e:
            self._sticker_slots = []
            self.cb_slot.configure(values=["All Stickers"])
            self.cb_slot.set("All Stickers")
            self.lbl_slot_summary.configure(text=f"Scan note: {e}")
            self.console.log(f"Notice: Could not scan stickers for '{weapon}': {e}")

    def _on_mode_changed(self, mode_label: str) -> None:
        mode_key = self.MODE_MAP.get(mode_label, "foil")
        desc = get_mode_description(mode_key)
        self.lbl_desc_text.configure(text=desc)

    def _set_busy(self, busy: bool) -> None:
        self._is_busy = busy
        self.btn_apply.configure(state="disabled" if busy else "normal")
        if busy:
            self.console.set_status("Applying Sticker FX...", is_busy=True)
        else:
            self.console.set_status("Ready", is_busy=False)

    def _on_apply_clicked(self) -> None:
        if self._is_busy:
            return

        weapon = self.cb_weapon.get().strip()
        mode_label = self.seg_mode.get()
        mode_key = self.MODE_MAP.get(mode_label, "foil")
        slot_label = self.cb_slot.get().strip()

        if not weapon:
            messagebox.showwarning("Input Required", "Please select a weapon model.")
            return

        # Determine sticker_id argument: 'all' or specific slot index/name
        if slot_label == "All Stickers" or not slot_label:
            sticker_id = "all"
        else:
            # Parse slot index from prefix "Slot <N>: ..."
            if slot_label.startswith("Slot "):
                idx_part = slot_label.split(":")[0].replace("Slot ", "").strip()
                sticker_id = idx_part
            else:
                sticker_id = slot_label

        self._set_busy(True)
        self.console.log(f"Applying sticker FX: Weapon='{weapon}', Mode='{mode_key}', Slot='{sticker_id}'...")

        def worker():
            try:
                res = set_sticker_fx(
                    weapon=weapon,
                    mode=mode_key,
                    sticker_id=sticker_id,
                    log_callback=lambda line: self.console.log(line),
                )
                if res.success:
                    self.console.log(f"SUCCESS: {res.message}")
                    self.console.set_status("Success", level="success")
                    # Rescan slots to show updated mode names
                    self.after(0, self._scan_stickers_for_active_weapon)
                else:
                    self.console.log(f"ERROR: {res.message}")
                    if res.stderr:
                        self.console.log(res.stderr)
                    self.console.set_status("Error", level="error")
            except Exception as e:
                self.console.log(f"EXCEPTION: {e}")
                self.console.set_status("Error", level="error")
            finally:
                self.after(0, self._set_busy, False)

        threading.Thread(target=worker, daemon=True).start()
