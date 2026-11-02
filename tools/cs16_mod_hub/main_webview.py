"""
tools/cs16_mod_hub/main_webview.py
Modern Desktop Executable Entry Point for Counter-Strike 1.6 Mod Hub.
Uses Microsoft Edge WebView2 (Chromium) for Hardware-Accelerated 60-144 FPS rendering.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
# Ensure repo root is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.cs16_mod_hub.core.api import ModHubAPI


def get_html_path() -> Path:
    """Returns absolute path to web/index.html."""
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates = [
            base_dir / "web" / "index.html",
            base_dir / "tools" / "cs16_mod_hub" / "web" / "index.html",
            Path(sys.executable).parent / "tools" / "cs16_mod_hub" / "web" / "index.html",
        ]
        for c in candidates:
            if c.is_file():
                return c
    return SCRIPT_DIR / "web" / "index.html"


def _patch_webview_interop():
    """
    Safeguards webview against FileNotFoundError: Cannot find win-arm64
    by monkeypatching webview.util.interop_dll_path with robust fallbacks.
    """
    try:
        import webview.util
        orig_interop = webview.util.interop_dll_path

        def safe_interop_dll_path(dll_name: str) -> str:
            try:
                return orig_interop(dll_name)
            except FileNotFoundError:
                meipass = getattr(sys, "_MEIPASS", None)
                candidates = []
                if meipass:
                    candidates.extend([
                        os.path.join(meipass, dll_name),
                        os.path.join(meipass, "runtimes", dll_name),
                        os.path.join(meipass, "runtimes", dll_name, "native"),
                        os.path.join(meipass, "webview", "lib", "runtimes", dll_name, "native"),
                        os.path.join(meipass, "webview", "lib", "runtimes", dll_name),
                        os.path.join(meipass, "lib", "runtimes", dll_name, "native"),
                        os.path.join(meipass, "lib", dll_name),
                    ])
                try:
                    import webview
                    pkg_dir = os.path.dirname(webview.__file__)
                    candidates.extend([
                        os.path.join(pkg_dir, "lib", "runtimes", dll_name, "native"),
                        os.path.join(pkg_dir, "lib", "runtimes", dll_name),
                        os.path.join(pkg_dir, "lib", dll_name),
                    ])
                except Exception:
                    pass

                for p in candidates:
                    if os.path.exists(p):
                        return p

                # If missing platform architecture folder (like win-arm64 on an x64 PC),
                # provide a dummy directory so edgechromium does not crash!
                if dll_name in ("win-arm64", "win-x64", "win-x86"):
                    if meipass:
                        fallback = os.path.join(meipass, dll_name)
                    else:
                        import tempfile
                        fallback = os.path.join(tempfile.gettempdir(), f"pywebview_{dll_name}")
                    os.makedirs(fallback, exist_ok=True)
                    return fallback

                raise

        webview.util.interop_dll_path = safe_interop_dll_path
    except Exception:
        pass


# Apply interop safeguard immediately so CLI scripts and main app are both protected
_patch_webview_interop()


def main():
    _patch_webview_interop()
    import webview

    html_path = get_html_path()
    if not html_path.is_file():
        if sys.stderr:
            print(f"Error: Could not locate index.html at {html_path}", file=sys.stderr)
        sys.exit(1)

    api = ModHubAPI()

    # Create Modern Desktop Application Window
    window = webview.create_window(
        title="COUNTER-STRIKE 1.6 MOD HUB",
        url=str(html_path.resolve()),
        js_api=api,
        width=1140,
        height=780,
        min_size=(960, 640),
        background_color="#0c0f15",
        text_select=False,
    )

    # Launch Edge Chromium WebView2 engine
    webview.start(debug=False)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()

    # Intercept any command-line invocation to prevent opening GUI windows
    if len(sys.argv) > 1:
        cli_args = sys.argv[1:]
        while cli_args and cli_args[0] in ("-u", "-B", "-O"):
            cli_args = cli_args[1:]

        if cli_args and cli_args[0] in ("--script", "-s"):
            cli_args = cli_args[1:]

        is_cli_script = cli_args and (cli_args[0] == "-c" or cli_args[0].endswith(".py"))
        is_cli_help = cli_args and cli_args[0] in ("-h", "--help", "-v", "--version")

        if is_cli_script or is_cli_help:
            # Reattach console for CLI feedback in terminal if frozen on Windows
            if sys.platform == "win32" and getattr(sys, "frozen", False):
                try:
                    import ctypes
                    ctypes.windll.kernel32.AttachConsole(-1)
                except Exception:
                    pass
                if sys.stdout is None:
                    try:
                        import io
                        sys.stdout = io.TextIOWrapper(open(1, "wb", closefd=False), encoding="utf-8", errors="replace")
                    except Exception:
                        try:
                            sys.stdout = open("CONOUT$", "w", encoding="utf-8")
                        except Exception:
                            pass
                if sys.stderr is None:
                    try:
                        import io
                        sys.stderr = io.TextIOWrapper(open(2, "wb", closefd=False), encoding="utf-8", errors="replace")
                    except Exception:
                        try:
                            sys.stderr = open("CONOUT$", "w", encoding="utf-8")
                        except Exception:
                            pass

            if is_cli_help:
                print("Usage: CS16_Mod_Manager.exe [-c <code> | <script.py> [args...]]")
                sys.exit(0)

            from tools.cs16_mod_hub.core.common import _run_script_in_process
            if cli_args[0] == "-c":
                code = cli_args[1] if len(cli_args) > 1 else ""
                res = _run_script_in_process(None, cli_args[1:], is_inline_c=True)
            else:
                target_script = Path(cli_args[0])
                if not target_script.is_file():
                    meipass = getattr(sys, "_MEIPASS", None)
                    if (PROJECT_ROOT / target_script).is_file():
                        target_script = PROJECT_ROOT / target_script
                    elif meipass and (Path(meipass) / target_script).is_file():
                        target_script = Path(meipass) / target_script
                res = _run_script_in_process(target_script, cli_args[1:], is_inline_c=False)
            sys.exit(res.returncode)

    main()
