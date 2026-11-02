"""
tools/cs16_mod_hub/gui/components/log_console.py
Monospace streaming console log viewer with auto-scroll and thread-safe posting.
"""

from __future__ import annotations

from datetime import datetime
import threading
from typing import Optional
import customtkinter

from ..theme import (
    COLOR_BG_CARD,
    COLOR_BG_CONSOLE,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_CONSOLE,
    COLOR_ACCENT_PRIMARY,
    COLOR_ACCENT_HOVER,
    COLOR_SUCCESS,
    COLOR_ERROR,
    COLOR_WARN,
    GLYPH_RESET,
    GLYPH_DIAMOND,
    font_console,
    font_small,
    font_card_title,
)


class LogConsole(customtkinter.CTkFrame):
    """
    Thread-safe monospace log console viewer.
    Handles background thread stream callbacks via root.after().
    """

    def __init__(
        self,
        master,
        title: str = "Execution Console",
        height: int = 160,
        show_header: bool = True,
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

        self._show_header = show_header

        if self._show_header:
            header_bar = customtkinter.CTkFrame(self, fg_color="transparent", height=28)
            header_bar.pack(fill="x", padx=10, pady=(6, 4))

            self.title_lbl = customtkinter.CTkLabel(
                header_bar,
                text=f"{GLYPH_DIAMOND}  {title}",
                font=font_card_title(),
                text_color=COLOR_TEXT_PRIMARY,
                anchor="w",
            )
            self.title_lbl.pack(side="left", padx=2)

            self.status_lbl = customtkinter.CTkLabel(
                header_bar,
                text="[ Idle ]",
                font=font_small(),
                text_color=COLOR_TEXT_MUTED,
            )
            self.status_lbl.pack(side="right", padx=(4, 6))

            self.clear_btn = customtkinter.CTkButton(
                header_bar,
                text=f"{GLYPH_RESET} Clear",
                width=65,
                height=22,
                font=font_small(),
                fg_color=COLOR_BORDER,
                hover_color=COLOR_ACCENT_PRIMARY,
                text_color=COLOR_TEXT_PRIMARY,
                command=self.clear,
            )
            self.clear_btn.pack(side="right", padx=4)

        # Monospace Text Box
        self.textbox = customtkinter.CTkTextbox(
            self,
            font=font_console(),
            fg_color=COLOR_BG_CONSOLE,
            text_color=COLOR_TEXT_CONSOLE,
            corner_radius=6,
            border_width=1,
            border_color=COLOR_BORDER,
            height=height,
            wrap="word",
        )
        self.textbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def log(self, message: str, level: str = "info") -> None:
        """
        Thread-safe message logging. If called from a worker thread,
        schedules the append on the main GUI thread via after(0, ...).
        If called on the main thread, appends directly.
        """
        if threading.current_thread() is threading.main_thread():
            self._append_log_mainthread(message, level)
        else:
            self.after(0, self._append_log_mainthread, message, level)

    def _append_log_mainthread(self, message: str, level: str) -> None:
        """Internal main-thread append handler."""
        if not message:
            return

        now_str = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{now_str}] "

        # Clean trailing newline if any, then add standard newline
        clean_msg = message.rstrip("\r\n")
        formatted = f"{prefix}{clean_msg}\n"

        self.textbox.configure(state="normal")
        self.textbox.insert("end", formatted)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def set_status(self, status: str, is_busy: bool = False, level: str = "info") -> None:
        """Thread-safe status badge update."""
        if threading.current_thread() is threading.main_thread():
            self._set_status_mainthread(status, is_busy, level)
        else:
            self.after(0, self._set_status_mainthread, status, is_busy, level)

    def _set_status_mainthread(self, status: str, is_busy: bool, level: str) -> None:
        if not hasattr(self, "status_lbl"):
            return
        if level == "error":
            color = COLOR_ERROR
        elif level == "success":
            color = COLOR_SUCCESS
        elif is_busy:
            color = COLOR_ACCENT_PRIMARY
        else:
            color = COLOR_TEXT_MUTED

        self.status_lbl.configure(text=f"[ {status} ]", text_color=color)

    def clear(self) -> None:
        """Clears console text."""
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")

    def get_text(self) -> str:
        """Returns entire log content."""
        return self.textbox.get("1.0", "end-1c")
