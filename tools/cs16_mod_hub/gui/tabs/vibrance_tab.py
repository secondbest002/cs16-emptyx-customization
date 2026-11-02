"""
tools/cs16_mod_hub/gui/tabs/vibrance_tab.py
Tab 2: Color & Vibrance Tuner.
Provides real-time slider-driven HSV color adjustments, preset buttons, factory palette reset,
and live side-by-side texture thumbnail preview via TexturePreviewCache.
"""

from __future__ import annotations

import os
from pathlib import Path
import threading
from tkinter import messagebox
from typing import Optional
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
from ..components.preview_canvas import PreviewCanvas
from ...core.model_adapter import list_viewmodels
from ...core.vibrance_adapter import (
    apply_vibrance,
    reset_vibrance,
    get_preset_values,
    PRESET_VALUES,
)
from ...core.palette_preview import TexturePreviewCache, resolve_model_path


class VibranceTab(customtkinter.CTkFrame):
    """
    Color & Vibrance Tuner Tab view.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._is_busy = False
        self._cache = TexturePreviewCache()

        # Main horizontal split: Left (Controls), Right (Live Preview & Console)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # =====================================================================
        # LEFT COLUMN: Tuning Controls
        # =====================================================================
        self.col_left = customtkinter.CTkFrame(self, fg_color="transparent")
        self.col_left.grid(row=0, column=0, sticky="nsew", padx=(10, 6), pady=10)

        # Card 1: Weapon & Scope Selector
        self.card_scope = CardFrame(
            self.col_left,
            title="Model & Texture Target",
            subtitle="Select the viewmodel and target texture group to adjust",
            glyph=GLYPH_DIAMOND,
        )
        self.card_scope.pack(fill="x", pady=(0, 8))
        self._build_scope_ui(self.card_scope.content_frame)

        # Card 2: Preset Buttons & Sliders
        self.card_sliders = CardFrame(
            self.col_left,
            title="Color Presets & Sliders",
            subtitle="Fine-tune saturation, contrast, and brightness with live preview feedback",
            glyph=GLYPH_DIAMOND_OUTLINE,
        )
        self.card_sliders.pack(fill="x", pady=(0, 8))
        self._build_sliders_ui(self.card_sliders.content_frame)

        # Card 3: Action Buttons
        self.card_actions = CardFrame(
            self.col_left,
            title="Apply & Reset Operations",
            glyph=GLYPH_CHECK,
        )
        self.card_actions.pack(fill="x", pady=(0, 4))
        self._build_actions_ui(self.card_actions.content_frame)

        # =====================================================================
        # RIGHT COLUMN: Live Preview Canvas & Console
        # =====================================================================
        self.col_right = customtkinter.CTkFrame(self, fg_color="transparent")
        self.col_right.grid(row=0, column=1, sticky="nsew", padx=(6, 10), pady=10)

        # Top Right: Side-by-Side Preview Canvas
        self.preview_canvas = PreviewCanvas(
            self.col_right,
            thumb_size=(190, 190),
            title="Live Texture Preview",
        )
        self.preview_canvas.pack(fill="both", expand=True, pady=(0, 8))

        # Bottom Right: Output Console
        self.console = LogConsole(
            self.col_right,
            title="Vibrance Output Console",
            height=140,
        )
        self.console.pack(fill="x")

        # Initial populate
        self.refresh_models()

    def _build_scope_ui(self, parent: customtkinter.CTkFrame) -> None:
        """Builds weapon dropdown and target group segmented button."""
        # Row 1: Model dropdown
        lbl_model = customtkinter.CTkLabel(
            parent,
            text="Active Viewmodel:",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_model.pack(anchor="w", pady=(2, 2))

        self.cb_weapon = customtkinter.CTkComboBox(
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
            command=self._on_weapon_selected,
        )
        self.cb_weapon.pack(fill="x", pady=(0, 6))

        # Row 2: Target group segmented button: [ Weapon ] [ Gloves ] [ All ]
        lbl_target_grp = customtkinter.CTkLabel(
            parent,
            text="Target Texture Scope:",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_target_grp.pack(anchor="w", pady=(2, 2))

        self.seg_target = customtkinter.CTkSegmentedButton(
            parent,
            values=["Weapon", "Gloves", "All"],
            font=font_body(),
            selected_color=COLOR_ACCENT_PRIMARY,
            selected_hover_color=COLOR_ACCENT_HOVER,
            unselected_color=COLOR_BG_INPUT,
            unselected_hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
            command=self._on_target_scope_changed,
        )
        self.seg_target.set("Weapon")
        self.seg_target.pack(fill="x", pady=(0, 4))

    def _build_sliders_ui(self, parent: customtkinter.CTkFrame) -> None:
        """Builds preset selector buttons and precision sliders."""
        # Presets row
        lbl_presets = customtkinter.CTkLabel(
            parent,
            text="Quick Presets:",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
        )
        lbl_presets.pack(anchor="w", pady=(2, 2))

        preset_row = customtkinter.CTkFrame(parent, fg_color="transparent")
        preset_row.pack(fill="x", pady=(0, 10))

        presets = [("Vivid", "vivid"), ("Punchy", "punchy"), ("Soft", "soft"), ("Grayscale", "grayscale")]
        for label, name in presets:
            btn = customtkinter.CTkButton(
                preset_row,
                text=label,
                font=font_small(),
                height=26,
                fg_color=COLOR_BG_INPUT,
                hover_color=COLOR_ACCENT_PRIMARY,
                text_color=COLOR_TEXT_PRIMARY,
                command=lambda p=name: self._apply_preset(p),
            )
            btn.pack(side="left", fill="x", expand=True, padx=2)

        # Slider 1: Saturation (0.0 to 2.5)
        self.sat_val = 1.0
        header_sat = customtkinter.CTkFrame(parent, fg_color="transparent")
        header_sat.pack(fill="x", pady=(2, 0))
        lbl_sat = customtkinter.CTkLabel(header_sat, text="Saturation:", font=font_body(), text_color=COLOR_TEXT_PRIMARY)
        lbl_sat.pack(side="left")
        self.lbl_sat_val = customtkinter.CTkLabel(header_sat, text="1.00x", font=font_body_bold(), text_color=COLOR_ACCENT_PRIMARY)
        self.lbl_sat_val.pack(side="right")

        self.slider_sat = customtkinter.CTkSlider(
            parent,
            from_=0.0,
            to=2.5,
            number_of_steps=50,
            button_color=COLOR_ACCENT_PRIMARY,
            button_hover_color=COLOR_ACCENT_HOVER,
            progress_color=COLOR_ACCENT_PRIMARY,
            command=self._on_slider_moved,
        )
        self.slider_sat.set(1.0)
        self.slider_sat.pack(fill="x", pady=(0, 6))

        # Slider 2: Contrast (0.5 to 2.0)
        self.contrast_val = 1.0
        header_cont = customtkinter.CTkFrame(parent, fg_color="transparent")
        header_cont.pack(fill="x", pady=(2, 0))
        lbl_cont = customtkinter.CTkLabel(header_cont, text="Contrast:", font=font_body(), text_color=COLOR_TEXT_PRIMARY)
        lbl_cont.pack(side="left")
        self.lbl_cont_val = customtkinter.CTkLabel(header_cont, text="1.00x", font=font_body_bold(), text_color=COLOR_ACCENT_PRIMARY)
        self.lbl_cont_val.pack(side="right")

        self.slider_cont = customtkinter.CTkSlider(
            parent,
            from_=0.5,
            to=2.0,
            number_of_steps=30,
            button_color=COLOR_ACCENT_PRIMARY,
            button_hover_color=COLOR_ACCENT_HOVER,
            progress_color=COLOR_ACCENT_PRIMARY,
            command=self._on_slider_moved,
        )
        self.slider_cont.set(1.0)
        self.slider_cont.pack(fill="x", pady=(0, 6))

        # Slider 3: Brightness (0.5 to 1.5)
        self.bright_val = 1.0
        header_bright = customtkinter.CTkFrame(parent, fg_color="transparent")
        header_bright.pack(fill="x", pady=(2, 0))
        lbl_bright = customtkinter.CTkLabel(header_bright, text="Brightness:", font=font_body(), text_color=COLOR_TEXT_PRIMARY)
        lbl_bright.pack(side="left")
        self.lbl_bright_val = customtkinter.CTkLabel(header_bright, text="1.00x", font=font_body_bold(), text_color=COLOR_ACCENT_PRIMARY)
        self.lbl_bright_val.pack(side="right")

        self.slider_bright = customtkinter.CTkSlider(
            parent,
            from_=0.5,
            to=1.5,
            number_of_steps=20,
            button_color=COLOR_ACCENT_PRIMARY,
            button_hover_color=COLOR_ACCENT_HOVER,
            progress_color=COLOR_ACCENT_PRIMARY,
            command=self._on_slider_moved,
        )
        self.slider_bright.set(1.0)
        self.slider_bright.pack(fill="x", pady=(0, 4))

    def _build_actions_ui(self, parent: customtkinter.CTkFrame) -> None:
        """Builds Apply and Factory Reset action buttons."""
        action_row = customtkinter.CTkFrame(parent, fg_color="transparent")
        action_row.pack(fill="x", pady=(4, 2))

        self.btn_apply = customtkinter.CTkButton(
            action_row,
            text=f"{GLYPH_CHECK} Apply Vibrance",
            font=font_body_bold(),
            fg_color=COLOR_ACCENT_PRIMARY,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#1a1e24",
            height=34,
            command=self._on_apply_clicked,
        )
        self.btn_apply.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self.btn_reset = customtkinter.CTkButton(
            action_row,
            text=f"{GLYPH_RESET} Factory Reset",
            font=font_body_bold(),
            fg_color=COLOR_BORDER,
            hover_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            height=34,
            command=self._on_reset_clicked,
        )
        self.btn_reset.pack(side="right", fill="both", expand=True, padx=(4, 0))

    def refresh_models(self) -> None:
        """Scans for active viewmodels and reloads the preview."""
        viewmodels = list_viewmodels()
        if not viewmodels:
            viewmodels = ["v_ak47.mdl", "v_m4a1.mdl", "v_awp.mdl"]

        self.cb_weapon.configure(values=viewmodels)
        if viewmodels:
            self.cb_weapon.set(viewmodels[0])
            self._load_texture_preview(viewmodels[0])

    def _on_weapon_selected(self, weapon_name: str) -> None:
        self._load_texture_preview(weapon_name)

    def _on_target_scope_changed(self, scope: str) -> None:
        cur_weapon = self.cb_weapon.get()
        if cur_weapon:
            self._load_texture_preview(cur_weapon)

    def _load_texture_preview(self, weapon_name: str) -> None:
        """Loads base texture into in-memory preview cache and updates preview canvas."""
        scope = self.seg_target.get().lower()
        prefer_weapon = (scope != "gloves")

        try:
            orig_img, info_str = self._cache.load(
                weapon_name,
                thumb_size=(190, 190),
                prefer_weapon=prefer_weapon,
            )
            self.preview_canvas.set_original_image(orig_img, info_str)
            self._update_adjusted_preview()
            self.console.log(f"Loaded preview for '{weapon_name}': {info_str}")
        except Exception as e:
            self.preview_canvas.clear()
            self.console.log(f"Notice: Preview unavailable for '{weapon_name}': {e}")

    def _apply_preset(self, preset_name: str) -> None:
        """Sets sliders to preset multipliers and updates preview."""
        vals = get_preset_values(preset_name)
        self.slider_sat.set(vals["sat"])
        self.slider_cont.set(vals["contrast"])
        self.slider_bright.set(vals["brightness"])

        self._on_slider_moved(None)
        self.console.log(
            f"Preset '{preset_name.title()}' loaded: Sat={vals['sat']:.2f}, Contrast={vals['contrast']:.2f}, Brightness={vals['brightness']:.2f}"
        )

    def _on_slider_moved(self, _val) -> None:
        """Real-time slider drag handler (<2ms execution)."""
        sat = round(float(self.slider_sat.get()), 2)
        cont = round(float(self.slider_cont.get()), 2)
        bright = round(float(self.slider_bright.get()), 2)

        self.lbl_sat_val.configure(text=f"{sat:.2f}x")
        self.lbl_cont_val.configure(text=f"{cont:.2f}x")
        self.lbl_bright_val.configure(text=f"{bright:.2f}x")

        self._update_adjusted_preview()

    def _update_adjusted_preview(self) -> None:
        """Calculates adjusted thumbnail in memory and pushes to PreviewCanvas."""
        sat = float(self.slider_sat.get())
        cont = float(self.slider_cont.get())
        bright = float(self.slider_bright.get())

        adj_img = self._cache.compute_adjusted_thumbnail(sat, cont, bright)
        self.preview_canvas.update_adjusted_image(adj_img)

    def _set_busy(self, busy: bool, operation: str = "") -> None:
        self._is_busy = busy
        state = "disabled" if busy else "normal"
        self.btn_apply.configure(state=state)
        self.btn_reset.configure(state=state)

        if busy:
            self.console.set_status(f"Running {operation}...", is_busy=True)
        else:
            self.console.set_status("Ready", is_busy=False)

    def _on_apply_clicked(self) -> None:
        if self._is_busy:
            return

        weapon = self.cb_weapon.get().strip()
        target_scope = self.seg_target.get().lower()
        sat = round(float(self.slider_sat.get()), 2)
        cont = round(float(self.slider_cont.get()), 2)
        bright = round(float(self.slider_bright.get()), 2)

        if not weapon:
            messagebox.showwarning("Input Required", "Please select a weapon model.")
            return

        self._set_busy(True, "Vibrance Adjustment")
        self.console.log(
            f"Applying vibrance to '{weapon}' (target={target_scope}, sat={sat}, contrast={cont}, bright={bright})..."
        )

        def worker():
            try:
                res = apply_vibrance(
                    weapon=weapon,
                    target=target_scope,
                    sat=sat,
                    contrast=cont,
                    brightness=bright,
                    log_callback=lambda line: self.console.log(line),
                )
                if res.success:
                    self.console.log(f"SUCCESS: {res.message}")
                    self.console.set_status("Success", level="success")
                    # Reload preview to reflect newly saved textures
                    self.after(0, self._load_texture_preview, weapon)
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

    def _on_reset_clicked(self) -> None:
        if self._is_busy:
            return

        weapon = self.cb_weapon.get().strip()
        target_scope = self.seg_target.get().lower()

        if not weapon:
            messagebox.showwarning("Input Required", "Please select a weapon model.")
            return

        self._set_busy(True, "Factory Palette Reset")
        self.console.log(f"Resetting '{weapon}' (scope={target_scope}) back to factory original palette...")

        def worker():
            try:
                res = reset_vibrance(
                    weapon=weapon,
                    target=target_scope,
                    log_callback=lambda line: self.console.log(line),
                )
                if res.success:
                    self.console.log(f"SUCCESS: {res.message}")
                    self.console.set_status("Success", level="success")
                    # Reset sliders to default 1.0
                    self.after(0, self._reset_slider_values)
                    self.after(0, self._load_texture_preview, weapon)
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

    def _reset_slider_values(self) -> None:
        self.slider_sat.set(1.0)
        self.slider_cont.set(1.0)
        self.slider_bright.set(1.0)
        self._on_slider_moved(None)
