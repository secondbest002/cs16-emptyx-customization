"""
tools/cs16_mod_hub/gui/components/preview_canvas.py
Side-by-side live texture preview display using CustomTkinter CTkImage and Pillow.
"""

from __future__ import annotations

from typing import Optional, Tuple
import customtkinter
from PIL import Image

from ..theme import (
    COLOR_BG_CARD,
    COLOR_BG_CONSOLE,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_ACCENT_PRIMARY,
    COLOR_ACCENT_SECONDARY,
    font_body_bold,
    font_small,
    font_card_title,
    GLYPH_DIAMOND,
    GLYPH_DIAMOND_OUTLINE,
)


class PreviewCanvas(customtkinter.CTkFrame):
    """
    Component for rendering side-by-side "Original" vs "Adjusted" GoldSrc 8-bit textures
    using CTkImage for high-DPI crisp rendering.
    """

    def __init__(
        self,
        master,
        thumb_size: Tuple[int, int] = (220, 220),
        title: str = "Live Texture Preview",
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_BORDER,
            fg_color=COLOR_BG_CARD,
            **kwargs,
        )

        self.thumb_size = thumb_size
        self._ctk_img_orig: Optional[customtkinter.CTkImage] = None
        self._ctk_img_adj: Optional[customtkinter.CTkImage] = None

        # Header with title and texture metadata label
        header_bar = customtkinter.CTkFrame(self, fg_color="transparent", height=28)
        header_bar.pack(fill="x", padx=12, pady=(10, 6))

        self.title_lbl = customtkinter.CTkLabel(
            header_bar,
            text=f"{GLYPH_DIAMOND}  {title}",
            font=font_card_title(),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        self.title_lbl.pack(side="left")

        self.meta_lbl = customtkinter.CTkLabel(
            header_bar,
            text="[ No Texture Loaded ]",
            font=font_small(),
            text_color=COLOR_TEXT_MUTED,
            anchor="e",
        )
        self.meta_lbl.pack(side="right")

        # Container for side-by-side previews
        preview_container = customtkinter.CTkFrame(self, fg_color="transparent")
        preview_container.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # --- Left Column: Original ---
        col_left = customtkinter.CTkFrame(preview_container, fg_color="transparent")
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        lbl_orig_title = customtkinter.CTkLabel(
            col_left,
            text=f"{GLYPH_DIAMOND_OUTLINE} Original Texture",
            font=font_body_bold(),
            text_color=COLOR_TEXT_MUTED,
        )
        lbl_orig_title.pack(anchor="w", pady=(0, 4))

        self.frame_orig_img = customtkinter.CTkFrame(
            col_left,
            width=thumb_size[0],
            height=thumb_size[1],
            fg_color=COLOR_BG_CONSOLE,
            corner_radius=6,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.frame_orig_img.pack(fill="both", expand=True)
        self.frame_orig_img.pack_propagate(False)

        self.orig_display_lbl = customtkinter.CTkLabel(
            self.frame_orig_img,
            text="No Model Selected",
            font=font_small(),
            text_color=COLOR_TEXT_MUTED,
        )
        self.orig_display_lbl.pack(expand=True)

        # --- Right Column: Adjusted ---
        col_right = customtkinter.CTkFrame(preview_container, fg_color="transparent")
        col_right.pack(side="right", fill="both", expand=True, padx=(6, 0))

        lbl_adj_title = customtkinter.CTkLabel(
            col_right,
            text=f"{GLYPH_DIAMOND} Live Adjusted",
            font=font_body_bold(),
            text_color=COLOR_ACCENT_PRIMARY,
        )
        lbl_adj_title.pack(anchor="w", pady=(0, 4))

        self.frame_adj_img = customtkinter.CTkFrame(
            col_right,
            width=thumb_size[0],
            height=thumb_size[1],
            fg_color=COLOR_BG_CONSOLE,
            corner_radius=6,
            border_width=1,
            border_color=COLOR_BORDER,
        )
        self.frame_adj_img.pack(fill="both", expand=True)
        self.frame_adj_img.pack_propagate(False)

        self.adj_display_lbl = customtkinter.CTkLabel(
            self.frame_adj_img,
            text="No Model Selected",
            font=font_small(),
            text_color=COLOR_TEXT_MUTED,
        )
        self.adj_display_lbl.pack(expand=True)

    def set_original_image(self, pil_img: Image.Image, info_text: str = "") -> None:
        """Sets and caches the base original texture thumbnail."""
        self._ctk_img_orig = customtkinter.CTkImage(
            light_image=pil_img,
            dark_image=pil_img,
            size=self.thumb_size,
        )
        self.orig_display_lbl.configure(image=self._ctk_img_orig, text="")
        if info_text:
            self.meta_lbl.configure(text=f"[ {info_text} ]")

    def update_adjusted_image(self, pil_img: Image.Image) -> None:
        """Updates the right-hand live adjusted preview without disk I/O."""
        self._ctk_img_adj = customtkinter.CTkImage(
            light_image=pil_img,
            dark_image=pil_img,
            size=self.thumb_size,
        )
        self.adj_display_lbl.configure(image=self._ctk_img_adj, text="")

    def clear(self) -> None:
        """Resets canvas to empty placeholder state."""
        self._ctk_img_orig = None
        self._ctk_img_adj = None
        self.orig_display_lbl.configure(image=None, text="No Model Selected")
        self.adj_display_lbl.configure(image=None, text="No Model Selected")
        self.meta_lbl.configure(text="[ No Texture Loaded ]")
