"""
tools/cs16_mod_hub/gui/theme.py
Design tokens, color palette, typography, and clean glyphs for CS 1.6 Mod Hub.
Adheres strictly to Requirement R3: Dark Slate aesthetic with zero emojis.
"""

from __future__ import annotations

import customtkinter

# -----------------------------------------------------------------------------
# Dark Slate Color Palette (CS:GO / CS2 Tactical UI standard)
# -----------------------------------------------------------------------------
COLOR_BG_MAIN = "#1a1e24"           # Deep dark slate main background
COLOR_BG_CARD = "#222831"           # Secondary dark slate container card background
COLOR_BG_INPUT = "#2b303a"          # Subtle light slate for entry boxes and dropdowns
COLOR_BG_CONSOLE = "#15181c"        # Terminal black-slate for monospace log consoles
COLOR_BORDER = "#393e46"            # Crisp boundary border for cards and dividers
COLOR_BORDER_LIGHT = "#4f5b66"      # Highlighted active border

COLOR_ACCENT_PRIMARY = "#e5a93c"    # CS Classic Gold / Amber
COLOR_ACCENT_HOVER = "#f5ba50"      # CS Gold hover highlight
COLOR_ACCENT_SECONDARY = "#00adb5"  # Tactical Cyan accent
COLOR_ACCENT_SECONDARY_HOVER = "#00c2cb"

COLOR_WARN = "#ff7043"              # Vibrant Tactical Orange
COLOR_WARN_HOVER = "#ff8a65"
COLOR_SUCCESS = "#4caf50"           # Tactical Green (clean status)
COLOR_ERROR = "#f44336"             # Alert Red (error / modified)

COLOR_TEXT_PRIMARY = "#eeeeee"      # Crisp bright text
COLOR_TEXT_MUTED = "#9aa0a6"        # Secondary muted gray text
COLOR_TEXT_CONSOLE = "#a9b7c6"      # Soft terminal green-gray console text

# -----------------------------------------------------------------------------
# Clean Monochrome Typographic Glyphs (Strictly NO Emojis)
# -----------------------------------------------------------------------------
GLYPH_DIAMOND = "◆"
GLYPH_DIAMOND_OUTLINE = "◈"
GLYPH_PLAY = "▸"
GLYPH_GEAR = "⚙"
GLYPH_STAR = "✦"
GLYPH_RESET = "⟲"
GLYPH_CHECK = "✓"
GLYPH_CROSS = "✕"
GLYPH_SWAP = "⇄"
GLYPH_PLUS = "[+]"
GLYPH_MINUS = "[-]"

# -----------------------------------------------------------------------------
# Font Configurations
# -----------------------------------------------------------------------------
FONT_FAMILY_MAIN = "Segoe UI"
FONT_FAMILY_MONO = "Consolas"


def font_title() -> customtkinter.CTkFont:
    """Header and window title font."""
    return customtkinter.CTkFont(family=FONT_FAMILY_MAIN, size=16, weight="bold")


def font_subheader() -> customtkinter.CTkFont:
    """Tab header and major section font."""
    return customtkinter.CTkFont(family=FONT_FAMILY_MAIN, size=13, weight="bold")


def font_card_title() -> customtkinter.CTkFont:
    """Card container title font."""
    return customtkinter.CTkFont(family=FONT_FAMILY_MAIN, size=12, weight="bold")


def font_body() -> customtkinter.CTkFont:
    """Standard body font for labels, options, and inputs."""
    return customtkinter.CTkFont(family=FONT_FAMILY_MAIN, size=11)


def font_body_bold() -> customtkinter.CTkFont:
    """Emphasized body font."""
    return customtkinter.CTkFont(family=FONT_FAMILY_MAIN, size=11, weight="bold")


def font_small() -> customtkinter.CTkFont:
    """Small footnote, badge, or secondary description font."""
    return customtkinter.CTkFont(family=FONT_FAMILY_MAIN, size=9)


def font_console() -> customtkinter.CTkFont:
    """Monospace log console font."""
    return customtkinter.CTkFont(family=FONT_FAMILY_MONO, size=10)


def font_console_small() -> customtkinter.CTkFont:
    """Compact monospace log font."""
    return customtkinter.CTkFont(family=FONT_FAMILY_MONO, size=9)


def apply_global_theme() -> None:
    """Initializes CustomTkinter global appearance mode and color theme."""
    customtkinter.set_appearance_mode("dark")
    customtkinter.set_default_color_theme("dark-blue")
