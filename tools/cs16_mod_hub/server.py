"""
tools/cs16_mod_hub/server.py
Lightweight High-Speed Local Web Server & REST API Backend for CS 1.6 Mod Hub.
Zero external dependencies required (Pure Python Standard Library).
"""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import mimetypes
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time
from typing import Any, Dict, Optional
import urllib.parse
import webbrowser

# Ensure repo root is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.cs16_mod_hub.core.api import ModHubAPI

WEB_DIR = SCRIPT_DIR / "web"


def find_edge_path() -> Optional[str]:
    """Locates Microsoft Edge executable on Windows for borderless App Mode."""
    if sys.platform != "win32":
        return None

    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Microsoft\\Edge\\Application\\msedge.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "Microsoft\\Edge\\Application\\msedge.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft\\Edge\\Application\\msedge.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    which = shutil.which("msedge")
    if which and os.path.isfile(which):
        return which

    return None


class ModHubRequestHandler(BaseHTTPRequestHandler):
    """Handles static web assets and REST API endpoints."""

    api_instance: ModHubAPI = None  # Injected before server start

    def log_message(self, format: str, *args: Any):
        # Suppress noisy standard HTTP access logs, display only errors or API calls
        msg = format % args
        if " 40" in msg or " 50" in msg:
            sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

    def _send_json(self, data: Any, status: int = HTTPStatus.OK):
        try:
            payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        except Exception as e:
            payload = json.dumps({"error": str(e)}).encode("utf-8")
            status = HTTPStatus.INTERNAL_SERVER_ERROR

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self) -> Dict[str, Any]:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            return {}
        body_bytes = self.rfile.read(content_len)
        try:
            return json.loads(body_bytes.decode("utf-8"))
        except Exception:
            return {}

    def do_OPTIONS(self):
        """CORS preflight support."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # =========================================================================
    # GET REQUEST ROUTER
    # =========================================================================

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # REST API Endpoints
        if path == "/api/status":
            studio_stat = self.api_instance.check_asset_studio_status()
            self._send_json({
                "status": "online",
                "app": "Counter-Strike 1.6 Mod Hub",
                "version": "4.0.0",
                "game_root": str(PROJECT_ROOT),
                "asset_studio": studio_stat,
            })
            return

        if path == "/api/plugins":
            plugins = self.api_instance.get_plugins()
            self._send_json({"success": True, "plugins": plugins})
            return

        if path == "/api/cs2-engine":
            res = self.api_instance.get_cs2_engine_config()
            self._send_json(res)
            return

        if path == "/api/competitive":
            res = self.api_instance.get_competitive_config()
            self._send_json(res)
            return

        if path == "/api/bots":
            res = self.api_instance.get_bot_ecosystem()
            self._send_json(res)
            return

        if path == "/api/profiles":
            profiles = self.api_instance.get_profiles()
            active = self.api_instance.get_active_profile()
            self._send_json({"success": True, "profiles": profiles, "active": active})
            return

        if path == "/api/backups":
            dir_param = query.get("dir", [None])[0]
            backups = self.api_instance.get_backups(dir_path=dir_param)
            self._send_json({"success": True, "backups": backups})
            return

        if path == "/api/backups/telemetry":
            dir_param = query.get("dir", [None])[0]
            res = self.api_instance.get_backup_telemetry(dir_path=dir_param)
            self._send_json(res)
            return

        if path == "/api/backups/verify":
            dir_param = query.get("dir", [None])[0]
            verified = self.api_instance.verify_all_backups(dir_path=dir_param)
            self._send_json({"success": True, "backups": verified})
            return

        if path == "/api/studio-status":
            res = self.api_instance.check_asset_studio_status()
            self._send_json({"success": True, "studio": res})
            return

        if path == "/api/logs":
            logs = self.api_instance.get_logs()
            self._send_json({"success": True, "logs": logs})
            return

        # Static File Delivery from WEB_DIR
        rel_path = path.lstrip("/")
        if not rel_path or rel_path == "":
            rel_path = "index.html"

        file_path = (WEB_DIR / rel_path).resolve()
        # Security: Prevent directory traversal outside WEB_DIR
        try:
            file_path.relative_to(WEB_DIR.resolve())
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return

        if not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File Not Found")
            return

        # Determine MIME Type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            if file_path.suffix == ".js":
                mime_type = "application/javascript"
            elif file_path.suffix == ".css":
                mime_type = "text/css"
            elif file_path.suffix == ".html":
                mime_type = "text/html"
            else:
                mime_type = "application/octet-stream"

        try:
            content = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type or "javascript" in mime_type else mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Error reading file: {e}")

    # =========================================================================
    # POST REQUEST ROUTER
    # =========================================================================

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

        if path == "/api/plugins/toggle":
            plugin = body.get("plugin", "")
            active = bool(body.get("active", False))
            res = self.api_instance.toggle_plugin(plugin, active)
            self._send_json(res)
            return

        if path == "/api/cs2-engine/save":
            settings = body.get("settings", {})
            res = self.api_instance.save_cs2_engine_settings(settings)
            self._send_json(res)
            return

        if path == "/api/cs2-engine/cvar":
            cvar = body.get("cvar", "")
            val = body.get("value", "")
            res = self.api_instance.save_cs2_engine_cvar(cvar, val)
            self._send_json(res)
            return

        if path == "/api/competitive/save":
            settings = body.get("settings", {})
            res = self.api_instance.save_competitive_settings(settings)
            self._send_json(res)
            return

        if path == "/api/competitive/cvar":
            cvar = body.get("cvar", "")
            val = body.get("value", "")
            res = self.api_instance.save_competitive_cvar(cvar, val)
            self._send_json(res)
            return

        if path == "/api/competitive/preset":
            preset = body.get("preset", "")
            res = self.api_instance.apply_competitive_preset(preset)
            self._send_json(res)
            return

        if path == "/api/bots/preset":
            preset = body.get("preset", "")
            res = self.api_instance.apply_bot_preset(preset)
            self._send_json(res)
            return

        if path == "/api/bots/master":
            enable = bool(body.get("enable", True))
            res = self.api_instance.toggle_savage_ai(enable)
            self._send_json(res)
            return

        if path == "/api/bots/yapb/cvar":
            cvar = body.get("cvar", "")
            val = body.get("value", "")
            res = self.api_instance.save_yapb_cvar(cvar, val)
            self._send_json(res)
            return

        if path == "/api/bots/savage/cvar":
            cvar = body.get("cvar", "")
            val = body.get("value", "")
            res = self.api_instance.save_savage_cvar(cvar, val)
            self._send_json(res)
            return

        if path == "/api/bots/sanitize-cheats":
            res = self.api_instance.sanitize_bot_cheats()
            self._send_json(res)
            return

        if path == "/api/bots/save":
            yapb = body.get("yapb", None)
            savage = body.get("savage", None)
            res = self.api_instance.save_bot_settings(yapb_settings=yapb, savage_settings=savage)
            self._send_json(res)
            return

        if path == "/api/profiles/select":
            profile_id = body.get("profile", "")
            res = self.api_instance.set_profile(profile_id)
            self._send_json(res)
            return

        if path == "/api/backups/restore":
            backup_path = body.get("backup_path", "")
            res = self.api_instance.restore_backup(backup_path)
            self._send_json(res)
            return

        if path == "/api/open-folder":
            folder = body.get("folder", None)
            res = self.api_instance.open_in_explorer(folder)
            self._send_json(res)
            return

        if path == "/api/studio-launch":
            res = self.api_instance.launch_asset_studio()
            self._send_json(res)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "API Endpoint Not Found")


def run_server(port: int = 5170, auto_launch: bool = True, app_mode: bool = False):
    """Starts local HTTP server and opens application view."""
    ModHubRequestHandler.api_instance = ModHubAPI()
    server_address = ("127.0.0.1", port)

    try:
        httpd = HTTPServer(server_address, ModHubRequestHandler)
    except OSError as e:
        if e.errno in (10048, 98):  # Address already in use
            print(f"[!] Port {port} is already active. Checking if CS 1.6 Mod Hub is already running...")
            url = f"http://127.0.0.1:{port}/"
            if auto_launch:
                _open_app_window(url, app_mode=app_mode)
            return
        raise

    url = f"http://127.0.0.1:{port}/"
    print("=" * 70)
    print("      COUNTER-STRIKE 1.6 MOD HUB - MODERN WEB DASHBOARD")
    print("=" * 70)
    print(f"[*] Server listening on: {url}")
    print(f"[*] Workspace Root:     {PROJECT_ROOT}")
    print("[*] Press Ctrl+C in this console to stop the server.")
    print("=" * 70)

    if auto_launch:
        # Launch UI in system default browser after slight delay to ensure socket is ready
        threading.Thread(target=_open_app_window, args=(url, app_mode), daemon=True).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down CS 1.6 Mod Hub server...")
    finally:
        httpd.server_close()


def _open_app_window(url: str, app_mode: bool = False):
    time.sleep(0.3)
    if app_mode:
        edge = find_edge_path()
        if edge:
            try:
                # Chromium App Mode creates a frameless, native-app window
                subprocess.Popen([
                    edge,
                    f"--app={url}",
                    "--disable-features=TranslateUI",
                    "--window-size=1180,820",
                ])
                print("[*] Launched Mod Hub in Edge Chromium App Mode.")
                return
            except Exception:
                pass

    print(f"[*] Opening in system default web browser: {url}")
    webbrowser.open(url)


def main():
    parser = argparse.ArgumentParser(description="Counter-Strike 1.6 Mod Hub Server")
    parser.add_argument("--port", type=int, default=5170, help="Local HTTP port (default: 5170)")
    parser.add_argument("--no-launch", action="store_true", help="Do not open browser automatically")
    parser.add_argument("--app-mode", action="store_true", help="Launch in Edge Chromium App Mode instead of default browser")

    args = parser.parse_args()
    run_server(port=args.port, auto_launch=not args.no_launch, app_mode=args.app_mode)


if __name__ == "__main__":
    main()
