"""
tools/cs16_mod_hub/gui/tabs/safety_tab.py
Tab 5: Backup & Safety Center.
Provides non-destructive model restoration, backup verification, and live log console.
"""

from __future__ import annotations

import os
from pathlib import Path
import threading
from tkinter import messagebox
from typing import Dict, List, Optional
import customtkinter

from ..theme import (
    COLOR_BG_CARD,
    COLOR_BG_INPUT,
    COLOR_BG_CONSOLE,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    COLOR_ACCENT_PRIMARY,
    COLOR_ACCENT_HOVER,
    COLOR_ACCENT_SECONDARY,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_SUCCESS,
    COLOR_WARN,
    COLOR_ERROR,
    GLYPH_RESET,
    GLYPH_CHECK,
    GLYPH_DIAMOND,
    GLYPH_DIAMOND_OUTLINE,
    font_body,
    font_body_bold,
    font_small,
    font_card_title,
    font_console_small,
)
from ..components.card_frame import CardFrame
from ..components.log_console import LogConsole
from ...core.model_adapter import (
    list_backups,
    restore_model_backup,
    restore_all_backups,
)


class SafetyTab(customtkinter.CTkFrame):
    """
    Backup & Safety Center Tab view.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._is_busy = False
        self._backups: List[dict] = []
        self._selected_index: Optional[int] = None
        self._row_frames: List[customtkinter.CTkFrame] = []

        # Card 1: Backup Files Table
        self.card_table = CardFrame(
            self,
            title="Model Safety Backups (.bak)",
            subtitle="Verified GoldSrc IDST backups generated before any model skin or glove operation",
            glyph=GLYPH_RESET,
        )
        self.card_table.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        self._build_table_ui(self.card_table.content_frame)

        # Bottom section: Real-time Log Console
        self.console = LogConsole(
            self,
            title="Safety Center Output Console",
            height=160,
        )
        self.console.pack(fill="both", expand=False, padx=10, pady=(4, 10))

        # Initial populate
        self.refresh_backups()

    def _build_table_ui(self, parent: customtkinter.CTkFrame) -> None:
        """Constructs backup list table header, scrollable list, and action buttons."""
        # Top toolbar: summary count & refresh button
        toolbar = customtkinter.CTkFrame(parent, fg_color="transparent", height=30)
        toolbar.pack(fill="x", pady=(0, 6))

        self.lbl_summary = customtkinter.CTkLabel(
            toolbar,
            text="Scanning backups...",
            font=font_body_bold(),
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        self.lbl_summary.pack(side="left")

        btn_refresh = customtkinter.CTkButton(
            toolbar,
            text=f"{GLYPH_RESET} Refresh List",
            width=90,
            height=26,
            font=font_small(),
            fg_color=COLOR_BORDER,
            hover_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            command=self.refresh_backups,
        )
        btn_refresh.pack(side="right")

        # Table Column Header
        tbl_header = customtkinter.CTkFrame(
            parent,
            fg_color=COLOR_BG_INPUT,
            height=26,
            corner_radius=4,
        )
        tbl_header.pack(fill="x", pady=(0, 2))

        col_model = customtkinter.CTkLabel(tbl_header, text="Model Name", font=font_small(), text_color=COLOR_TEXT_MUTED, width=170, anchor="w")
        col_model.pack(side="left", padx=(10, 4))

        col_status = customtkinter.CTkLabel(tbl_header, text="Status", font=font_small(), text_color=COLOR_TEXT_MUTED, width=100, anchor="center")
        col_status.pack(side="left", padx=4)

        col_size = customtkinter.CTkLabel(tbl_header, text="Backup / Active Size", font=font_small(), text_color=COLOR_TEXT_MUTED, width=180, anchor="w")
        col_size.pack(side="left", padx=4)

        col_date = customtkinter.CTkLabel(tbl_header, text="Backup Timestamp", font=font_small(), text_color=COLOR_TEXT_MUTED, anchor="w")
        col_date.pack(side="left", fill="x", expand=True, padx=4)

        # Scrollable container for rows
        self.scroll_list = customtkinter.CTkScrollableFrame(
            parent,
            fg_color=COLOR_BG_CONSOLE,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=6,
            height=160,
        )
        self.scroll_list.pack(fill="both", expand=True, pady=(0, 8))

        # Bottom Action Bar
        action_bar = customtkinter.CTkFrame(parent, fg_color="transparent")
        action_bar.pack(fill="x", pady=(2, 0))

        self.btn_restore_selected = customtkinter.CTkButton(
            action_bar,
            text=f"{GLYPH_RESET} Restore Selected Model",
            font=font_body_bold(),
            fg_color=COLOR_BORDER,
            hover_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            height=34,
            command=self._on_restore_selected_clicked,
        )
        self.btn_restore_selected.pack(side="left", padx=(0, 6))

        self.btn_restore_all = customtkinter.CTkButton(
            action_bar,
            text=f"{GLYPH_RESET} Restore All Models",
            font=font_body_bold(),
            fg_color=COLOR_ACCENT_PRIMARY,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#1a1e24",
            height=34,
            command=self._on_restore_all_clicked,
        )
        self.btn_restore_all.pack(side="left")

    def refresh_backups(self) -> None:
        """Scans filesystem for .bak files and updates table."""
        # Clear existing row frames
        for f in self._row_frames:
            f.destroy()
        self._row_frames.clear()
        self._selected_index = None

        self._backups = list_backups()
        n_total = len(self._backups)
        n_modified = sum(1 for b in self._backups if b["is_modified"])

        self.lbl_summary.configure(
            text=f"Total Backups: {n_total}  |  Modified Models: {n_modified}"
        )

        if not self._backups:
            empty_lbl = customtkinter.CTkLabel(
                self.scroll_list,
                text="No .bak backup files found in model directories.",
                font=font_small(),
                text_color=COLOR_TEXT_MUTED,
            )
            empty_lbl.pack(pady=20)
            self._row_frames.append(empty_lbl)
            self.console.log("Safety Center: No backups found.")
            return

        for idx, item in enumerate(self._backups):
            row = customtkinter.CTkFrame(
                self.scroll_list,
                fg_color=COLOR_BG_CARD if idx % 2 == 0 else COLOR_BG_INPUT,
                corner_radius=4,
                height=30,
            )
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            # Bind row click for selection
            row.bind("<Button-1>", lambda event, i=idx: self._select_row(i))

            # Model name
            lbl_name = customtkinter.CTkLabel(
                row,
                text=item["model_name"],
                font=font_body_bold(),
                text_color=COLOR_TEXT_PRIMARY,
                width=170,
                anchor="w",
            )
            lbl_name.pack(side="left", padx=(10, 4))
            lbl_name.bind("<Button-1>", lambda event, i=idx: self._select_row(i))

            # Status badge
            if item["is_modified"]:
                status_text = "[ Modified ]"
                status_color = COLOR_WARN
            else:
                status_text = "[ Clean ]"
                status_color = COLOR_SUCCESS

            lbl_st = customtkinter.CTkLabel(
                row,
                text=status_text,
                font=font_body_bold(),
                text_color=status_color,
                width=100,
                anchor="center",
            )
            lbl_st.pack(side="left", padx=4)
            lbl_st.bind("<Button-1>", lambda event, i=idx: self._select_row(i))

            # Sizes
            bak_kb = item["backup_size"] // 1024
            tgt_kb = (item["target_size"] // 1024) if item["target_size"] is not None else 0
            size_str = f"{bak_kb} KB / {tgt_kb} KB"
            lbl_sz = customtkinter.CTkLabel(
                row,
                text=size_str,
                font=font_console_small(),
                text_color=COLOR_TEXT_MUTED,
                width=180,
                anchor="w",
            )
            lbl_sz.pack(side="left", padx=4)
            lbl_sz.bind("<Button-1>", lambda event, i=idx: self._select_row(i))

            # Date
            lbl_dt = customtkinter.CTkLabel(
                row,
                text=item["backup_mtime"],
                font=font_small(),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
            )
            lbl_dt.pack(side="left", fill="x", expand=True, padx=4)
            lbl_dt.bind("<Button-1>", lambda event, i=idx: self._select_row(i))

            self._row_frames.append(row)

        self.console.log(f"Safety Center scanned: {n_total} backup(s) listed.")

    def _select_row(self, index: int) -> None:
        """Selects a row visually."""
        self._selected_index = index
        for idx, row in enumerate(self._row_frames):
            if not isinstance(row, customtkinter.CTkFrame):
                continue
            if idx == index:
                row.configure(border_width=1, border_color=COLOR_ACCENT_PRIMARY)
            else:
                row.configure(border_width=0)

    def _set_busy(self, busy: bool) -> None:
        self._is_busy = busy
        state = "disabled" if busy else "normal"
        self.btn_restore_selected.configure(state=state)
        self.btn_restore_all.configure(state=state)
        if busy:
            self.console.set_status("Restoring models...", is_busy=True)
        else:
            self.console.set_status("Ready", is_busy=False)

    def _on_restore_selected_clicked(self) -> None:
        if self._is_busy:
            return

        if self._selected_index is None or self._selected_index >= len(self._backups):
            messagebox.showinfo("Select Backup", "Please select a model backup from the list first.")
            return

        item = self._backups[self._selected_index]
        model_name = item["model_name"]

        confirmed = messagebox.askyesno(
            "Confirm Restore",
            f"Are you sure you want to restore '{model_name}' from its backup?\n\nThis will safely overwrite the active model with the pristine .bak version.",
        )
        if not confirmed:
            return

        self._set_busy(True)
        self.console.log(f"Restoring backup for '{model_name}'...")

        def worker():
            try:
                res = restore_model_backup(item["backup_path"])
                if res.success:
                    self.console.log(f"SUCCESS: {res.message}")
                    self.console.set_status("Success", level="success")
                    self.after(0, self.refresh_backups)
                else:
                    self.console.log(f"ERROR: {res.message}")
                    self.console.set_status("Error", level="error")
            except Exception as e:
                self.console.log(f"EXCEPTION: {e}")
                self.console.set_status("Error", level="error")
            finally:
                self.after(0, self._set_busy, False)

        threading.Thread(target=worker, daemon=True).start()

    def _on_restore_all_clicked(self) -> None:
        if self._is_busy:
            return

        if not self._backups:
            messagebox.showinfo("No Backups", "No model backups are currently available to restore.")
            return

        confirmed = messagebox.askyesno(
            "Confirm Batch Restore",
            f"Are you sure you want to restore ALL {len(self._backups)} models from backup?\n\nAll active models with backups will be reverted to pristine state.",
        )
        if not confirmed:
            return

        self._set_busy(True)
        self.console.log(f"Batch restoring {len(self._backups)} backup(s)...")

        def worker():
            try:
                res = restore_all_backups()
                if res.success:
                    self.console.log(f"SUCCESS: {res.message}")
                    self.console.set_status("Success", level="success")
                    self.after(0, self.refresh_backups)
                else:
                    self.console.log(f"ERROR: {res.message}")
                    self.console.set_status("Error", level="error")
            except Exception as e:
                self.console.log(f"EXCEPTION: {e}")
                self.console.set_status("Error", level="error")
            finally:
                self.after(0, self._set_busy, False)

        threading.Thread(target=worker, daemon=True).start()
