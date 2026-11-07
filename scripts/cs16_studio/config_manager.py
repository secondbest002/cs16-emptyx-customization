"""
config_manager.py - Centralized configuration and decoupled path resolver for CS 1.6 Customization Suite.
Provides a resilient bridge between the external Studio workspace and the target CS 1.6 installation.
"""

import json
import os
from pathlib import Path
import subprocess
from typing import Dict, Optional, Union

STUDIO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = STUDIO_ROOT / "config.json"


class StudioConfig:
    """Manages workspace paths, remote game binding, and sandbox staging."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "StudioConfig":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.studio_root = STUDIO_ROOT
        self.config_data: Dict[str, Union[str, bool, int]] = {}
        self.load()

    def load(self) -> None:
        """Loads config.json or initializes default values."""
        if CONFIG_FILE.is_file():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config_data = json.load(f)
            except Exception:
                self.config_data = {}
        else:
            self.config_data = {
                "game_directory": r"D:\Games\Counter-Strike\Counter-Strike 1.6 Original",
                "active_team": "ct",
                "workspace_version": "2.1.0",
                "staging_dir": "./my_mods/staging",
                "exports_dir": "./my_mods/exports",
                "auto_backup": True,
                "max_workspace_mb": 80,
            }
            self.save()

    def save(self) -> bool:
        """Persists current configuration to config.json."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2)
            return True
        except Exception:
            return False

    def get_game_root(self, override: Optional[Union[str, Path]] = None) -> Path:
        """
        Resolves the target CS 1.6 game root directory.
        Priority:
        1. Explicit override argument
        2. Environment variable CS16_GAME_DIR
        3. config.json 'game_directory'
        4. Studio root fallback (legacy in-place)
        """
        if override:
            p = Path(override).resolve()
            if (p / "cstrike").is_dir():
                return p
            return p

        env_path = os.getenv("CS16_GAME_DIR")
        if env_path:
            p = Path(env_path).resolve()
            if (p / "cstrike").is_dir():
                return p

        cfg_path = self.config_data.get("game_directory")
        if cfg_path:
            p = Path(str(cfg_path)).resolve()
            if (p / "cstrike").is_dir():
                return p

        # 4. Sibling directory check (e.g. D:\Counter-Strike 1.6\Counter-Strike 1.6 Original)
        sibling = self.studio_root.parent / "Counter-Strike 1.6 Original"
        if (sibling / "cstrike").is_dir():
            return sibling

        # Fallback to studio root
        return self.studio_root

    def set_game_root(self, new_path: Union[str, Path]) -> bool:
        """Updates game directory path and saves to config.json."""
        p = Path(new_path).resolve()
        self.config_data["game_directory"] = str(p)
        return self.save()

    def get_studio_root(self) -> Path:
        """Returns the studio / customization workspace root."""
        return self.studio_root

    def get_staging_dir(self) -> Path:
        """Returns the local staging directory for mod projects."""
        rel = str(self.config_data.get("staging_dir", "./my_mods/staging"))
        p = (self.studio_root / rel).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_exports_dir(self) -> Path:
        """Returns the exported modpack directory."""
        rel = str(self.config_data.get("exports_dir", "./my_mods/exports"))
        p = (self.studio_root / rel).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def is_game_valid(self, game_root: Optional[Path] = None) -> bool:
        """Checks if the target game root has a valid cstrike folder."""
        root = game_root or self.get_game_root()
        return (root / "cstrike").is_dir() and (root / "cstrike" / "models").is_dir()

    def is_hl_running(self) -> bool:
        """Checks if hl.exe is currently running on Windows to prevent file locking."""
        try:
            out = subprocess.check_output(
                ["tasklist", "/fi", "imagename eq hl.exe"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            return "hl.exe" in out.lower()
        except Exception:
            return False


config = StudioConfig()
