"""
tools/cs16_mod_hub/gui/components/card_frame.py
Dark Slate container card frame (#222831) with optional header and border.
"""

from __future__ import annotations

from typing import Optional
import customtkinter

from ..theme import (
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_ACCENT_PRIMARY,
    font_card_title,
    font_small,
)


class CardFrame(customtkinter.CTkFrame):
    """
    Styled container frame styled in Dark Slate (#222831) with an optional
    card header bar, title, subtitle, and an inner container for child widgets.
    """

    def __init__(
        self,
        master,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        glyph: Optional[str] = None,
        corner_radius: int = 8,
        border_width: int = 1,
        border_color: str = COLOR_BORDER,
        fg_color: str = COLOR_BG_CARD,
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=corner_radius,
            border_width=border_width,
            border_color=border_color,
            fg_color=fg_color,
            **kwargs,
        )

        self._title = title
        self._subtitle = subtitle
        self._glyph = glyph

        # Build card header if title is supplied
        if self._title:
            self.header_frame = customtkinter.CTkFrame(
                self,
                fg_color="transparent",
                corner_radius=0,
            )
            self.header_frame.pack(fill="x", padx=14, pady=(10, 4))

            title_text = f"{self._glyph}  {self._title}" if self._glyph else self._title
            self.title_label = customtkinter.CTkLabel(
                self.header_frame,
                text=title_text,
                font=font_card_title(),
                text_color=COLOR_TEXT_PRIMARY,
                anchor="w",
            )
            self.title_label.pack(side="left", fill="x", expand=True)

            if self._subtitle:
                self.subtitle_label = customtkinter.CTkLabel(
                    self,
                    text=self._subtitle,
                    font=font_small(),
                    text_color=COLOR_TEXT_MUTED,
                    anchor="w",
                )
                self.subtitle_label.pack(fill="x", padx=14, pady=(0, 6))

            # Subtle separator line
            self.separator = customtkinter.CTkFrame(
                self,
                height=1,
                fg_color=border_color,
                corner_radius=0,
            )
            self.separator.pack(fill="x", padx=10, pady=(2, 8))

        # Main content area
        self.content_frame = customtkinter.CTkFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self.content_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

    def set_title(self, title: str, glyph: Optional[str] = None) -> None:
        """Dynamically update card title."""
        self._title = title
        if glyph:
            self._glyph = glyph
        title_text = f"{self._glyph}  {self._title}" if self._glyph else self._title
        if hasattr(self, "title_label"):
            self.title_label.configure(text=title_text)
