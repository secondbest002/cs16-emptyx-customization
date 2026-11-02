"""
tools/cs16_mod_hub/gui/tabs/model_studio_tab.py
Tab 1: Skin & Model Studio.
Integrates skin transfer, glove injection, and P/W model baking with real-time streaming logs.
"""

from __future__ import annotations

import os
from pathlib import Path
import threading
from tkinter import filedialog, messagebox
from typing import List, Optional
import customtkinter

from ..theme import (
    COLOR_BG_CARD,
    COLOR_BG_INPUT,
    COLOR_BORDER,
    COLOR_ACCENT_PRIMARY,
    COLOR_ACCENT_HOVER,
    COLOR_ACCENT_SECONDARY,
    COLOR_ACCENT_SECONDARY_HOVER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_SUCCESS,
    COLOR_ERROR,
    GLYPH_SWAP,
    GLYPH_PLAY,
    GLYPH_STAR,
    GLYPH_RESET,
    GLYPH_DIAMOND,
    GLYPH_DIAMOND_OUTLINE,
    font_body,
    font_body_bold,
    font_small,
    font_card_title,
)
from ..components.card_frame import CardFrame
from ..components.log_console import LogConsole
from ...core.model_adapter import (
    transfer_skin,
    inject_gloves,
    inject_pw,
    list_viewmodels,
    list_donor_models,
)
from ...core.common import get_project_root


class ModelStudioTab(customtkinter.CTkFrame):
    """
    Skin & Model Studio Tab view.
    Manages skin transfers, glove texture injection, and P/W compilation.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._is_busy = False

        # Top section: split into two Cards
        self.top_container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.top_container.pack(fill="x", padx=10, pady=(10, 6))

        # Left Card: Skin Transfer Studio
        self.card_transfer = CardFrame(
            self.top_container,
            title="Weapon Skin Transfer",
            subtitle="Transfer body weapon skin from donor collection while preserving animations & stickers",
            glyph=GLYPH_SWAP,
        )
        self.card_transfer.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # Right Card: Glove & P/W Injection
        self.card_inject = CardFrame(
            self.top_container,
            title="Glove & P/W Model Studio",
            subtitle="Inject hands/gloves from donor or composite decals into player & world models",
            glyph=GLYPH_PLAY,
        )
        self.card_inject.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # --- Build Skin Transfer UI ---
        self._build_transfer_ui(self.card_transfer.content_frame)

        # --- Build Glove & P/W UI ---
        self._build_inject_ui(self.card_inject.content_frame)

        # Bottom section: Real-time Log Console
        self.console = LogConsole(
            self,
            title="Model Studio Output Console",
            height=200,
        )
        self.console.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        # Initial data population
        self.refresh_model_lists()

    def _build_transfer_ui(self, parent: customtkinter.CTkFrame) -> None:
        """Constructs target and donor selection controls for skin transfer."""
        # Row 1: Target Viewmodel
        lbl_target = customtkinter.CTkLabel(
            parent,
            text="Target Active Viewmodel:",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_target.pack(anchor="w", pady=(2, 2))

        self.cb_target = customtkinter.CTkComboBox(
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
            values=["Scanning models..."],
            state="readonly",
        )
        self.cb_target.pack(fill="x", pady=(0, 8))

        # Row 2: Donor Skin Model
        lbl_donor = customtkinter.CTkLabel(
            parent,
            text="Donor Skin Source Model:",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_donor.pack(anchor="w", pady=(2, 2))

        donor_row = customtkinter.CTkFrame(parent, fg_color="transparent")
        donor_row.pack(fill="x", pady=(0, 8))

        self.cb_donor = customtkinter.CTkComboBox(
            donor_row,
            font=font_body(),
            dropdown_font=font_body(),
            fg_color=COLOR_BG_INPUT,
            border_color=COLOR_BORDER,
            button_color=COLOR_ACCENT_PRIMARY,
            button_hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_text_color=COLOR_TEXT_PRIMARY,
            dropdown_fg_color=COLOR_BG_CARD,
            values=["Scanning donor models..."],
        )
        self.cb_donor.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_browse_donor = customtkinter.CTkButton(
            donor_row,
            text="Browse...",
            width=70,
            font=font_small(),
            fg_color=COLOR_BORDER,
            hover_color=COLOR_ACCENT_PRIMARY,
            command=self._on_browse_donor,
        )
        btn_browse_donor.pack(side="right")

        # Row 3: P/W Sync Switch
        self.switch_pw_sync = customtkinter.CTkSwitch(
            parent,
            text="Synchronize P/W models (copy clean skin to p_*.mdl & w_*.mdl)",
            font=font_body(),
            progress_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.switch_pw_sync.pack(anchor="w", pady=(4, 12))

        # Row 4: Action Button & Refresh
        action_row = customtkinter.CTkFrame(parent, fg_color="transparent")
        action_row.pack(fill="x", pady=(6, 2))

        self.btn_transfer = customtkinter.CTkButton(
            action_row,
            text=f"{GLYPH_SWAP} Transfer Skin",
            font=font_body_bold(),
            fg_color=COLOR_ACCENT_PRIMARY,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#1a1e24",
            height=34,
            command=self._on_transfer_skin_clicked,
        )
        self.btn_transfer.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_refresh = customtkinter.CTkButton(
            action_row,
            text=f"{GLYPH_RESET} Refresh",
            font=font_small(),
            width=76,
            height=34,
            fg_color=COLOR_BORDER,
            hover_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            command=self.refresh_model_lists,
        )
        btn_refresh.pack(side="right")

    def _build_inject_ui(self, parent: customtkinter.CTkFrame) -> None:
        """Constructs glove injector and P/W baker controls."""
        # Row 1: Target Model for Gloves
        lbl_target_glove = customtkinter.CTkLabel(
            parent,
            text="Target Model (Gloves):",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_target_glove.pack(anchor="w", pady=(2, 2))

        self.cb_glove_target = customtkinter.CTkComboBox(
            parent,
            font=font_body(),
            dropdown_font=font_body(),
            fg_color=COLOR_BG_INPUT,
            border_color=COLOR_BORDER,
            button_color=COLOR_ACCENT_SECONDARY,
            button_hover_color=COLOR_ACCENT_SECONDARY_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_text_color=COLOR_TEXT_PRIMARY,
            dropdown_fg_color=COLOR_BG_CARD,
            values=["Scanning models..."],
            state="readonly",
        )
        self.cb_glove_target.pack(fill="x", pady=(0, 8))

        # Row 2: Source Glove Donor
        lbl_source_glove = customtkinter.CTkLabel(
            parent,
            text="Source Glove Model:",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_source_glove.pack(anchor="w", pady=(2, 2))

        glove_source_row = customtkinter.CTkFrame(parent, fg_color="transparent")
        glove_source_row.pack(fill="x", pady=(0, 8))

        self.cb_glove_source = customtkinter.CTkComboBox(
            glove_source_row,
            font=font_body(),
            dropdown_font=font_body(),
            fg_color=COLOR_BG_INPUT,
            border_color=COLOR_BORDER,
            button_color=COLOR_ACCENT_SECONDARY,
            button_hover_color=COLOR_ACCENT_SECONDARY_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_text_color=COLOR_TEXT_PRIMARY,
            dropdown_fg_color=COLOR_BG_CARD,
            values=["awp", "v_awp.mdl", "ak47", "m4a1"],
        )
        self.cb_glove_source.pack(side="left", fill="x", expand=True, padx=(0, 6))

        btn_browse_glove = customtkinter.CTkButton(
            glove_source_row,
            text="Browse...",
            width=70,
            font=font_small(),
            fg_color=COLOR_BORDER,
            hover_color=COLOR_ACCENT_SECONDARY,
            command=self._on_browse_glove,
        )
        btn_browse_glove.pack(side="right")

        # Row 3: Action Buttons
        btn_row = customtkinter.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 2))

        self.btn_inject_gloves = customtkinter.CTkButton(
            btn_row,
            text=f"{GLYPH_PLAY} Inject Gloves",
            font=font_body_bold(),
            fg_color=COLOR_ACCENT_SECONDARY,
            hover_color=COLOR_ACCENT_SECONDARY_HOVER,
            text_color="#1a1e24",
            height=34,
            command=self._on_inject_gloves_clicked,
        )
        self.btn_inject_gloves.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self.btn_bake_pw = customtkinter.CTkButton(
            btn_row,
            text=f"{GLYPH_STAR} Bake P/W",
            font=font_body_bold(),
            fg_color=COLOR_ACCENT_PRIMARY,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#1a1e24",
            height=34,
            command=self._on_bake_pw_clicked,
        )
        self.btn_bake_pw.pack(side="right", fill="both", expand=True, padx=(4, 0))

    def refresh_model_lists(self) -> None:
        """Scans filesystem and updates viewmodel and donor dropdown values."""
        viewmodels = list_viewmodels()
        if not viewmodels:
            viewmodels = ["v_ak47.mdl", "v_m4a1.mdl", "v_awp.mdl", "v_deagle.mdl"]

        self.cb_target.configure(values=viewmodels)
        self.cb_glove_target.configure(values=viewmodels)
        if viewmodels:
            self.cb_target.set(viewmodels[0])
            self.cb_glove_target.set(viewmodels[0])

        donors = list_donor_models()
        if not donors:
            donors = [f"cstrike/models/{m}" for m in viewmodels]

        self.cb_donor.configure(values=donors)
        if donors:
            self.cb_donor.set(donors[0])

        # Also populate glove sources
        glove_sources = ["awp", "v_awp.mdl"] + donors[:15]
        self.cb_glove_source.configure(values=glove_sources)
        self.cb_glove_source.set("awp")

        self.console.log(
            f"Model Studio refreshed: Found {len(viewmodels)} active viewmodels, {len(donors)} donor skins."
        )

    def _on_browse_donor(self) -> None:
        root = get_project_root()
        path = filedialog.askopenfilename(
            initialdir=str(root / "cstrike" / "models"),
            title="Select Donor Model (.mdl)",
            filetypes=[("GoldSrc Studio Models", "*.mdl"), ("All Files", "*.*")],
        )
        if path:
            try:
                rel = Path(path).relative_to(root).as_posix()
            except ValueError:
                rel = path
            self.cb_donor.set(rel)

    def _on_browse_glove(self) -> None:
        root = get_project_root()
        path = filedialog.askopenfilename(
            initialdir=str(root / "cstrike" / "models"),
            title="Select Glove Source Model (.mdl)",
            filetypes=[("GoldSrc Studio Models", "*.mdl"), ("All Files", "*.*")],
        )
        if path:
            try:
                rel = Path(path).relative_to(root).as_posix()
            except ValueError:
                rel = path
            self.cb_glove_source.set(rel)

    def _set_busy(self, busy: bool, operation_name: str = "") -> None:
        self._is_busy = busy
        state = "disabled" if busy else "normal"
        self.btn_transfer.configure(state=state)
        self.btn_inject_gloves.configure(state=state)
        self.btn_bake_pw.configure(state=state)

        if busy:
            self.console.set_status(f"Running {operation_name}...", is_busy=True)
        else:
            self.console.set_status("Ready", is_busy=False)

    def _on_transfer_skin_clicked(self) -> None:
        if self._is_busy:
            return

        target = self.cb_target.get().strip()
        source = self.cb_donor.get().strip()
        sync_pw = bool(self.switch_pw_sync.get())

        if not target or not source:
            messagebox.showwarning("Input Required", "Please select both a target and a donor model.")
            return

        self._set_busy(True, "Skin Transfer")
        self.console.log(f"Starting skin transfer: Source='{source}' -> Target='{target}' (P/W Sync={sync_pw})")

        def worker():
            try:
                res = transfer_skin(
                    source=source,
                    target=target,
                    sync_pw=sync_pw,
                    log_callback=lambda line: self.console.log(line),
                )
                if res.success:
                    self.console.log(f"SUCCESS: {res.message}")
                    self.console.set_status("Success", level="success")
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

    def _on_inject_gloves_clicked(self) -> None:
        if self._is_busy:
            return

        target = self.cb_glove_target.get().strip()
        source = self.cb_glove_source.get().strip()

        if not target or not source:
            messagebox.showwarning("Input Required", "Please select target and glove source models.")
            return

        self._set_busy(True, "Glove Injection")
        self.console.log(f"Starting glove injection: Donor='{source}' -> Target='{target}'")

        def worker():
            try:
                res = inject_gloves(
                    target=target,
                    source=source,
                    log_callback=lambda line: self.console.log(line),
                )
                if res.success:
                    self.console.log(f"SUCCESS: {res.message}")
                    self.console.set_status("Success", level="success")
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

    def _on_bake_pw_clicked(self) -> None:
        if self._is_busy:
            return

        target = self.cb_target.get().strip()
        if not target:
            messagebox.showwarning("Input Required", "Please select a target viewmodel for P/W baking.")
            return

        # Derive weapon name from v_model (e.g. v_ak47.mdl -> ak47)
        stem = Path(target).stem
        weapon_name = stem[2:] if stem.startswith("v_") else stem

        self._set_busy(True, "P/W Sync")
        self.console.log(f"Starting P/W skin sync and injection for weapon '{weapon_name}'...")

        def worker():
            try:
                res = inject_pw(
                    weapon=weapon_name,
                    v_model=target,
                    log_callback=lambda line: self.console.log(line),
                )
                if res.success:
                    self.console.log(f"SUCCESS: {res.message}")
                    self.console.set_status("Success", level="success")
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
