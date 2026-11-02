"""
tools/cs16_mod_hub/main.py
CLI and GUI entry point for Counter-Strike 1.6 Unified Mod Hub.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import traceback


def parse_args(argv=None) -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Counter-Strike 1.6 Unified Desktop Mod Hub"
    )
    parser.add_argument(
        "--tab",
        type=str,
        default=None,
        help="Initial tab to select ('studio', 'vibrance', 'sticker', 'amxx', 'safety')",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debugging output",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Keep standard output attached to console",
    )
    parser.add_argument(
        "--headless-test",
        action="store_true",
        help="Initialize GUI, construct widgets, run one event loop pass, and exit cleanly",
    )
    return parser.parse_args(argv)


def main() -> int:
    """Application main entry point."""
    args = parse_args()

    # Ensure repository root is on sys.path
    repo_root = Path(__file__).resolve().parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    try:
        from tools.cs16_mod_hub.gui.app import AppWindow

        app = AppWindow(initial_tab=args.tab, debug=args.debug)

        # Headless automated testing mode (for CI / test runners)
        if args.headless_test or os.environ.get("CI") == "1":
            app.update_idletasks()
            app.update()
            app.destroy()
            if args.debug or args.console:
                print("Headless verification: AppWindow initialized and destroyed successfully.")
            return 0

        # Standard interactive desktop GUI mainloop
        app.mainloop()
        return 0

    except Exception as exc:
        traceback.print_exc()
        try:
            import tkinter.messagebox as mb

            mb.showerror(
                "CS 1.6 Mod Hub - Critical Startup Error",
                f"An unhandled exception occurred during application startup:\n\n{exc}\n\nCheck terminal console for full traceback.",
            )
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
