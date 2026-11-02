"""
tools/cs16_mod_hub/gui/app.py
Main Application Window for Counter-Strike 1.6 Unified Mod Hub.
Built with CustomTkinter 6.0 and Dark Slate theme. Strictly zero emojis.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Optional
import customtkinter

from .theme import (
    COLOR_BG_MAIN,
    COLOR_BG_CARD,
    COLOR_BG_INPUT,
    COLOR_BG_CONSOLE,
    COLOR_BORDER,
    COLOR_ACCENT_PRIMARY,
    COLOR_ACCENT_HOVER,
    COLOR_ACCENT_SECONDARY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_SUCCESS,
    GLYPH_DIAMOND,
    GLYPH_DIAMOND_OUTLINE,
    GLYPH_SWAP,
    GLYPH_STAR,
    GLYPH_GEAR,
    GLYPH_RESET,
    font_title,
    font_subheader,
    font_body,
    font_body_bold,
    font_small,
    apply_global_theme,
)
from .tabs.model_studio_tab import ModelStudioTab
from .tabs.vibrance_tab import VibranceTab
from .tabs.sticker_fx_tab import StickerFxTab
from .tabs.amxx_tab import AmxxTab
from .tabs.safety_tab import SafetyTab
from ..core.common import get_project_root


class AppWindow(customtkinter.CTk):
    """
    Main application window hosting the 5 modular functional tabs and status header/footer.
    """

    TAB_MODEL_STUDIO = f"{GLYPH_SWAP} Skin & Model Studio"
    TAB_VIBRANCE = f"{GLYPH_DIAMOND} Color & Vibrance Tuner"
    TAB_STICKER = f"{GLYPH_STAR} Sticker FX Lab"
    TAB_AMXX = f"{GLYPH_GEAR} Plugin & Gameplay Manager"
    TAB_SAFETY = f"{GLYPH_RESET} Backup & Safety Center"

    def __init__(self, initial_tab: Optional[str] = None, debug: bool = False):
        super().__init__()

        self.debug_mode = debug
        self.game_root = get_project_root()

        # Apply global CustomTkinter Dark mode settings
        apply_global_theme()

        # Window Configuration
        self.title("COUNTER-STRIKE 1.6 MOD HUB")
        self.geometry("1100x750")
        self.minsize(960, 650)
        self.configure(fg_color=COLOR_BG_MAIN)

        # Build Header Bar
        self._build_header_bar()

        # Build Multi-Tab Container
        self._build_tabview()

        # Build Footer Status Bar
        self._build_status_bar()

        # Select initial tab if requested
        if initial_tab:
            self.select_tab(initial_tab)

    def _build_header_bar(self) -> None:
        """Top application branding header bar."""
        header = customtkinter.CTkFrame(
            self,
            fg_color=COLOR_BG_CARD,
            corner_radius=0,
            border_width=0,
            height=60,
        )
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # Left branding
        brand_frame = customtkinter.CTkFrame(header, fg_color="transparent")
        brand_frame.pack(side="left", padx=18, pady=8)

        lbl_title = customtkinter.CTkLabel(
            brand_frame,
            text=f"{GLYPH_DIAMOND} COUNTER-STRIKE 1.6 MOD HUB",
            font=font_title(),
            text_color=COLOR_ACCENT_PRIMARY,
            anchor="w",
        )
        lbl_title.pack(anchor="w")

        lbl_subtitle = customtkinter.CTkLabel(
            brand_frame,
            text="Tactical Weapon Customization, Model Shaders & Competitive Match Manager",
            font=font_small(),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        lbl_subtitle.pack(anchor="w")

        # Right status badge
        badge_frame = customtkinter.CTkFrame(header, fg_color="transparent")
        badge_frame.pack(side="right", padx=18, pady=12)

        lbl_engine_badge = customtkinter.CTkLabel(
            badge_frame,
            text="[ GoldSrc Engine IDST v10 ]",
            font=font_body_bold(),
            text_color=COLOR_ACCENT_SECONDARY,
        )
        lbl_engine_badge.pack(side="left", padx=(0, 10))

        lbl_status_badge = customtkinter.CTkLabel(
            badge_frame,
            text=f"{GLYPH_DIAMOND} ONLINE",
            font=font_body_bold(),
            text_color=COLOR_SUCCESS,
        )
        lbl_status_badge.pack(side="left")

    def _build_tabview(self) -> None:
        """Main CTkTabview hosting the 5 tabs."""
        self.tabview = customtkinter.CTkTabview(
            self,
            fg_color=COLOR_BG_MAIN,
            segmented_button_fg_color=COLOR_BG_CARD,
            segmented_button_selected_color=COLOR_ACCENT_PRIMARY,
            segmented_button_selected_hover_color=COLOR_ACCENT_HOVER,
            segmented_button_unselected_color=COLOR_BG_INPUT,
            segmented_button_unselected_hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=8,
        )
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(4, 6))

        # Add all 5 tabs
        self.tab_studio_container = self.tabview.add(self.TAB_MODEL_STUDIO)
        self.tab_vibrance_container = self.tabview.add(self.TAB_VIBRANCE)
        self.tab_sticker_container = self.tabview.add(self.TAB_STICKER)
        self.tab_amxx_container = self.tabview.add(self.TAB_AMXX)
        self.tab_safety_container = self.tabview.add(self.TAB_SAFETY)

        # Instantiate tab views
        self.tab_studio = ModelStudioTab(self.tab_studio_container)
        self.tab_studio.pack(fill="both", expand=True)

        self.tab_vibrance = VibranceTab(self.tab_vibrance_container)
        self.tab_vibrance.pack(fill="both", expand=True)

        self.tab_sticker = StickerFxTab(self.tab_sticker_container)
        self.tab_sticker.pack(fill="both", expand=True)

        self.tab_amxx = AmxxTab(self.tab_amxx_container)
        self.tab_amxx.pack(fill="both", expand=True)

        self.tab_safety = SafetyTab(self.tab_safety_container)
        self.tab_safety.pack(fill="both", expand=True)

    def _build_status_bar(self) -> None:
        """Bottom status bar with game root and environmental info."""
        self.status_bar = customtkinter.CTkFrame(
            self,
            fg_color=COLOR_BG_CONSOLE,
            height=26,
            corner_radius=0,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)

        lbl_root = customtkinter.CTkLabel(
            self.status_bar,
            text=f"Game Root: {self.game_root.as_posix()}",
            font=font_small(),
            text_color=COLOR_TEXT_MUTED,
            anchor="w",
        )
        lbl_root.pack(side="left", padx=12)

        lbl_ver = customtkinter.CTkLabel(
            self.status_bar,
            text="CS 1.6 Unified Mod Hub v1.0 | Pure CustomTkinter",
            font=font_small(),
            text_color=COLOR_TEXT_MUTED,
            anchor="e",
        )
        lbl_ver.pack(side="right", padx=12)

    def select_tab(self, tab_name_or_keyword: str) -> None:
        """
        Switches active tab by exact name, index, or keyword:
        Keywords: 'studio', 'skin', 'vibrance', 'color', 'sticker', 'amxx', 'plugin', 'safety', 'backup'.
        """
        k = tab_name_or_keyword.strip().lower()

        if "studio" in k or "skin" in k or "model" in k:
            self.tabview.set(self.TAB_MODEL_STUDIO)
        elif "vibrance" in k or "color" in k or "palette" in k:
            self.tabview.set(self.TAB_VIBRANCE)
        elif "sticker" in k or "fx" in k:
            self.tabview.set(self.TAB_STICKER)
        elif "amxx" in k or "plugin" in k or "gameplay" in k:
            self.tabview.set(self.TAB_AMXX)
        elif "safety" in k or "backup" in k or "restore" in k:
            self.tabview.set(self.TAB_SAFETY)
        else:
            # Try exact match
            for t in [
                self.TAB_MODEL_STUDIO,
                self.TAB_VIBRANCE,
                self.TAB_STICKER,
                self.TAB_AMXX,
                self.TAB_SAFETY,
            ]:
                if t.lower() == k:
                    self.tabview.set(t)
                    return
