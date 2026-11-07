"""
server.py - Lightweight local HTTP server and REST API for CS 1.6 Asset Studio.
Zero external server dependencies (uses standard library http.server).
"""

import base64
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Optional, Union
import urllib.parse
from PIL import Image

from ..config_manager import StudioConfig
from ..asset_library import (
    delete_custom_skin,
    delete_custom_sticker,
    edit_custom_skin,
    edit_custom_sticker,
    get_library_skins,
    get_library_stickers,
    restore_default_stickers,
    save_custom_skin,
    save_custom_sticker,
)
from ..baker import (
    bake_sticker_onto_texture,
    bake_multi_stickers_onto_texture,
    composite_multi_stickers,
    transform_sticker_layer,
)
from ..color_adjuster import adjust_and_quantize, adjust_color_grading
from ..glove_transfer import (
    apply_glove_preset,
    batch_inject_glove_images,
    batch_transfer_gloves,
    delete_glove_preset,
    list_glove_presets,
    save_glove_preset,
    transfer_gloves,
)
from ..image_pipeline import (
    load_image,
    process_image_for_texture,
    process_slot_sticker_with_transform,
)
from ..mdl_core import (
    STUDIO_NF_ADDITIVE,
    STUDIO_NF_CHROME,
    MdlModel,
    batch_inject_sticker,
    discover_available_models,
    extract_model_3d,
    resolve_model_path,
)
from ..profile_manager import (
    delete_profile,
    list_profiles,
    load_profile,
    save_profile,
)
from ..stattrak_customizer import customize_stattrak_texture
from ..wear_simulator import get_wear_condition_name, simulate_and_quantize
from ..pw_restore import (
    get_model_thumbnail,
    list_model_backups,
    restore_specific_backup,
    migrate_loose_backups,
)
from ..modpack_exporter import export_modpack
from ..slot_geometry import (
    inject_new_slot_quad,
    reposition_slot_quad,
    restore_geometry_snapshot,
    validate_model_health,
)
from ..amxx_manager import (
    ACTIVE_LOADOUT_REL,
    SKIN_INVENTORY_REL,
    find_weapon_audio,
    get_amxx_catalog,
    parse_active_loadout,
    set_active_loadout,
    sync_pw_models,
    get_triplet_status,
    resolve_triplet_models,
)
from ..chrome_injector import (
    MAXSTUDIOBODYPARTS,
    generate_chrome_preview_uri,
    inject_chrome_overlay,
    inspect_chrome_status,
    remove_chrome_overlay,
)
from ..pov_manager import (
    PovConfig,
    PRESETS as POV_PRESETS,
    apply_to_game as apply_pov_to_game,
    get_preset as get_pov_preset,
    read_current_config as read_current_pov_config,
    reset_to_vanilla as reset_pov_to_vanilla,
    validate_and_clamp as validate_and_clamp_pov,
)
from ..inventory_manager import (
    save_to_inventory,
    list_inventory,
    equip_inventory_skin,
    sync_gloves_to_inventory,
    delete_inventory_skin,
    toggle_amxx_registration,
)
from ..sleeve_injector import (
    SLEEVE_PRESETS,
    calculate_scale_ratio,
    detect_arm_type,
    transplant_3d_sleeves,
)

STATIC_DIR = Path(__file__).parent / "static"

_GAME_STATUS_CACHE = {"running": False, "ts": 0.0}


def is_hl_game_running() -> bool:
    """Checks whether Counter-Strike 1.6 engine (hl.exe) is currently active."""
    now = time.time()
    if now - _GAME_STATUS_CACHE["ts"] < 2.5:
        return _GAME_STATUS_CACHE["running"]
    try:
        flags = 0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        res = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq hl.exe"],
            capture_output=True,
            text=True,
            timeout=1.5,
            creationflags=flags,
        )
        is_running = "hl.exe" in (res.stdout or "").lower()
    except Exception:
        is_running = False
    _GAME_STATUS_CACHE["running"] = is_running
    _GAME_STATUS_CACHE["ts"] = now
    return is_running



def _safe_float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


def _safe_int(val, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_bool(val, default: bool = False) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    s = str(val).lower().strip()
    return s in ("true", "1", "yes", "on")


class StudioApiHandler(SimpleHTTPRequestHandler):
    """Handles REST API calls and serves modern static UI."""

    def __init__(self, *args, workspace_root: Optional[Path] = None, **kwargs):
        self.config = StudioConfig.get_instance()
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else self.config.get_game_root()
        self.studio_root = self.config.get_studio_root()
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def translate_path(self, path: str) -> str:
        local_path = super().translate_path(path)
        if os.path.exists(local_path):
            return local_path
        # Fallback to game root static files
        game_static = self.config.get_game_root() / "scripts" / "cs16_studio" / "web" / "static"
        clean_rel = urllib.parse.unquote(urllib.parse.urlsplit(path).path).lstrip("/")
        if not clean_rel or clean_rel.endswith("/"):
            clean_rel += "index.html"
        fallback_file = game_static / clean_rel
        if fallback_file.exists():
            return str(fallback_file)
        return local_path

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            return {}
        raw = self.rfile.read(content_len)
        return json.loads(raw.decode("utf-8"))

    def _extract_image_bytes(self, req_data: dict, base64_key: str = "image_base64", path_key: str = "image_path") -> bytes:
        img_path = req_data.get(path_key)
        if img_path:
            p = Path(img_path)
            if not p.is_absolute():
                p = self.workspace_root / p
            if not p.is_file():
                # Also try studio_root
                alt_p = self.studio_root / img_path
                if alt_p.is_file():
                    p = alt_p
                else:
                    raise FileNotFoundError(f"Image file not found: {p}")
            return p.read_bytes()
        img_data_uri = req_data.get(base64_key, "")
        if "," in img_data_uri:
            img_data_uri = img_data_uri.split(",", 1)[1]
        if not img_data_uri:
            raise ValueError("No image data or path provided.")
        return base64.b64decode(img_data_uri)

    def _resolve_layer_image_bytes(self, layer: dict) -> bytes:
        img_src = layer.get("image_base64") or layer.get("image") or layer.get("previewUri") or layer.get("preview")
        if img_src and str(img_src).startswith("data:"):
            if "," in img_src:
                img_src = img_src.split(",", 1)[1]
            return base64.b64decode(img_src)
        elif img_src and len(str(img_src)) > 500:
            try:
                return base64.b64decode(img_src)
            except Exception:
                pass

        path_str = layer.get("image_path") or layer.get("path")
        if path_str:
            p = Path(path_str)
            if not p.is_absolute():
                p = self.workspace_root / p
            if not p.is_file():
                alt = self.studio_root / path_str
                if alt.is_file():
                    p = alt
                else:
                    raise FileNotFoundError(f"Sticker layer image not found: {path_str}")
            return p.read_bytes()

        if isinstance(img_src, str) and len(img_src) < 500:
            p = Path(img_src)
            if not p.is_absolute():
                p = self.workspace_root / p
            if p.is_file():
                return p.read_bytes()
            alt = self.studio_root / img_src
            if alt.is_file():
                return alt.read_bytes()

        raise ValueError("Layer does not contain a valid image or path.")

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/config":
            self._send_json({
                "success": True,
                "game_directory": str(self.config.get_game_root()),
                "studio_directory": str(self.config.get_studio_root()),
                "is_game_valid": self.config.is_game_dir_valid(),
                "is_hl_running": self.config.is_hl_running(),
                "profiles_dir": str(self.config.get_profiles_dir()),
                "staging_dir": str(self.config.get_staging_dir()),
            })
            return

        elif path == "/api/inventory":
            weapon_f = query.get("weapon", [None])[0]
            team_f = query.get("team", [None])[0]
            try:
                items = list_inventory(weapon=weapon_f, team=team_f, root_dir=self.workspace_root)
                self._send_json({"success": True, "count": len(items), "items": items})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path in ("/api/models", "/api/weapons"):
            try:
                models = discover_available_models(self.workspace_root)
                self._send_json({"success": True, "models": models})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/engine/status":
            is_running = is_hl_game_running()
            self._send_json({
                "success": True,
                "is_game_running": is_running,
                "process_name": "hl.exe" if is_running else None,
                "port": 27015 if is_running else None,
                "mode": "ACTIVE IN-GAME" if is_running else "STANDALONE DCC",
                "goldsrc_version": "IDST v10",
            })
            return

        elif path == "/api/model/backups":
            team = query.get("team", ["ct"])[0]
            weapon = query.get("weapon", ["usp"])[0]
            custom_path = query.get("path", [None])[0]
            triplet_type = query.get("type", ["v"])[0].lower()

            try:
                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                elif triplet_type in ("p", "w"):
                    triplets = resolve_triplet_models(weapon, team=team, root_dir=self.workspace_root)
                    target_mdl = triplets.get(triplet_type)
                    if target_mdl and target_mdl.is_file():
                        mdl_path = target_mdl
                    else:
                        mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                result = list_model_backups(mdl_path)
                result["team"] = team
                result["weapon"] = weapon
                result["triplet_type"] = triplet_type
                result["success"] = True
                self._send_json(result)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/model":
            team = query.get("team", ["ct"])[0]
            weapon = query.get("weapon", ["usp"])[0]
            custom_path = query.get("path", [None])[0]
            triplet_type = query.get("type", ["v"])[0].lower()

            try:
                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                elif triplet_type in ("p", "w"):
                    triplets = resolve_triplet_models(weapon, team=team, root_dir=self.workspace_root)
                    target_mdl = triplets.get(triplet_type)
                    if target_mdl and target_mdl.is_file():
                        mdl_path = target_mdl
                    else:
                        mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                model = MdlModel(mdl_path)
                orig_exists = find_model_backup(mdl_path)[0] is not None

                textures_data = []
                for t in model.textures:
                    tex_dict = t.to_dict()
                    # Add base64 PNG preview
                    tex_dict["preview"] = t.to_base64_data_uri()
                    # Check if snapshot backup exists
                    snap_path = model.get_backup_dir() / f"{t.name}.bin"
                    tex_dict["has_snapshot"] = snap_path.exists()
                    textures_data.append(tex_dict)

                self._send_json(
                    {
                        "success": True,
                        "model_name": mdl_path.name,
                        "model_path": str(mdl_path),
                        "team": team,
                        "weapon": weapon,
                        "triplet_type": triplet_type,
                        "has_orig_backup": orig_exists,
                        "textures": textures_data,
                    }
                )
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=404)
            return

        elif path == "/api/library/stickers":
            try:
                stickers = get_library_stickers(self.studio_root)
                self._send_json({"success": True, "stickers": stickers})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/library/skins":
            try:
                skins = get_library_skins(self.studio_root)
                self._send_json({"success": True, "skins": skins})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/profiles":
            try:
                profiles = list_profiles(self.studio_root)
                self._send_json({"success": True, "profiles": profiles})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/gloves/presets":
            try:
                presets = list_glove_presets(self.studio_root)
                self._send_json({"success": True, "presets": presets})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/chrome/status":
            team = query.get("team", ["ct"])[0]
            weapon = query.get("weapon", ["usp"])[0]
            custom_path = query.get("path", [None])[0]
            triplet_type = query.get("type", ["v"])[0].lower()
            try:
                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)
                status = inspect_chrome_status(mdl_path)
                health = validate_model_health(mdl_path)
                self._send_json({
                    "success": True,
                    "chrome_status": status,
                    "has_chrome": status.get("has_chrome", False),
                    "detected_submodels": status.get("detected_submodels", []),
                    "target_skin_bodyparts": status.get("target_skin_bodyparts", []),
                    "active_preset": status.get("preset"),
                    "preset": status.get("preset"),
                    "num_bodyparts": status.get("num_bodyparts", 0),
                    "max_bodyparts": status.get("max_bodyparts_limit", MAXSTUDIOBODYPARTS),
                    "max_bodyparts_limit": status.get("max_bodyparts_limit", MAXSTUDIOBODYPARTS),
                    "can_inject": status.get("can_inject", True),
                    "num_textures": status.get("num_textures", 0),
                    "health": health,
                    "model_name": mdl_path.name,
                })
            except FileNotFoundError as e:
                self._send_json({"success": False, "error": str(e)}, status=404)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/chrome/preview_texture":
            preset = query.get("preset", ["silver"])[0]
            intensity = query.get("intensity", [None])[0]
            tightness = query.get("tightness", [None])[0]
            tint = query.get("tint", query.get("hue_tint", [None]))[0]
            try:
                data_uri = generate_chrome_preview_uri(
                    preset=preset,
                    intensity=float(intensity) if intensity is not None else None,
                    tightness=float(tightness) if tightness is not None else None,
                    tint=float(tint) if tint is not None else None,
                )
                self._send_json({
                    "success": True,
                    "preview": data_uri,
                    "preview_uri": data_uri,
                    "data_uri": data_uri,
                    "preset": preset,
                })
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=400)
            return

        elif path == "/api/model_3d":
            team = query.get("team", ["ct"])[0]
            weapon = query.get("weapon", ["usp"])[0]
            custom_path = query.get("path", [None])[0]
            triplet_type = query.get("type", ["v"])[0].lower()

            try:
                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                elif triplet_type in ("p", "w"):
                    triplets = resolve_triplet_models(weapon, team=team, root_dir=self.workspace_root)
                    target = triplets.get(triplet_type)
                    if not target or not target.is_file():
                        self._send_json({
                            "success": False,
                            "error": f"Model for '{triplet_type}_{weapon}.mdl' not found. Please sync viewmodel first."
                        }, status=404)
                        return
                    mdl_path = target
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                model_3d = extract_model_3d(mdl_path)
                self._send_json({"success": True, "model_name": mdl_path.name, "triplet_type": triplet_type, **model_3d})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/triplets/status":
            team = query.get("team", ["ct"])[0]
            weapon = query.get("weapon", ["usp"])[0]
            try:
                status_data = get_triplet_status(weapon=weapon, team=team, root_dir=self.workspace_root)
                self._send_json(status_data)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/export_modpack":
            team = query.get("team", ["all"])[0]
            weapons = query.get("weapon", None)
            include_only_modified = query.get("modified_only", ["false"])[0].lower() in ("1", "true", "yes")
            include_amxx = query.get("include_amxx", ["false"])[0].lower() in ("1", "true", "yes")
            include_pw = query.get("include_pw", ["false"])[0].lower() in ("1", "true", "yes")
            include_sounds = query.get("include_sounds", ["false"])[0].lower() in ("1", "true", "yes")
            try:
                zip_bytes, manifest = export_modpack(
                    root_dir=self.workspace_root,
                    team=team,
                    weapons=weapons,
                    include_only_modified=include_only_modified,
                    include_amxx_configs=include_amxx,
                    include_pw_models=include_pw,
                    include_sounds=include_sounds,
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", 'attachment; filename="cs16_custom_modpack.zip"')
                self.send_header("Content-Length", str(len(zip_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(zip_bytes)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/amxx/catalog":
            try:
                catalog = get_amxx_catalog(self.workspace_root)
                self._send_json(catalog)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/amxx/loadout":
            try:
                loadout_file = self.workspace_root / ACTIVE_LOADOUT_REL
                loadout = parse_active_loadout(loadout_file)
                self._send_json({"success": True, "loadout": loadout})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/amxx/sound":
            snd_path = query.get("path", [None])[0]
            weapon = query.get("weapon", [None])[0]
            lookup = snd_path or weapon
            if not lookup:
                self._send_json({"success": False, "error": "No sound path or weapon specified."}, status=400)
                return

            try:
                wav_file = find_weapon_audio(self.workspace_root, lookup)
                if not wav_file or not wav_file.is_file():
                    self._send_json({"success": False, "error": f"Audio file not found for '{lookup}'."}, status=404)
                    return

                wav_bytes = wav_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(len(wav_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(wav_bytes)
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/model/health":
            team = query.get("team", ["ct"])[0]
            weapon = query.get("weapon", ["usp"])[0]
            custom_path = query.get("path", [None])[0]
            triplet_type = query.get("type", ["v"])[0].lower()

            try:
                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                health = validate_model_health(mdl_path)
                self._send_json({"success": True, **health})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/pov/current":
            try:
                weapon = query.get("weapon", [None])[0]
                custom_cstrike = query.get("cstrike_dir", [None])[0]
                cstrike_dir = Path(custom_cstrike) if custom_cstrike else self.workspace_root / "cstrike"
                cfg = read_current_pov_config(cstrike_dir)
                if cfg is None:
                    cfg = get_pov_preset("cs2_classic") or PovConfig()
                clamped_cfg, warnings = validate_and_clamp_pov(cfg.clone(), weapon=weapon)
                self._send_json({"success": True, "config": clamped_cfg.to_dict(), "warnings": warnings})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/pov/presets":
            try:
                presets_dict = {k: v.to_dict() for k, v in POV_PRESETS.items()}
                self._send_json({"success": True, "presets": presets_dict})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        elif path == "/api/sleeve/inspect":
            team = query.get("team", ["ct"])[0]
            weapon = query.get("weapon", ["usp"])[0]
            custom_path = query.get("path", [None])[0]
            triplet_type = query.get("type", ["v"])[0].lower()
            donor_preset = query.get("donor_preset", ["sas_navy"])[0]
            custom_donor_path = query.get("donor_path", [None])[0]

            try:
                if custom_path:
                    tgt_path = Path(custom_path).resolve()
                else:
                    tgt_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                target_info = detect_arm_type(tgt_path)

                donor_p = None
                if custom_donor_path:
                    donor_p = Path(custom_donor_path).resolve()
                elif donor_preset in SLEEVE_PRESETS and SLEEVE_PRESETS[donor_preset]["default_donor"]:
                    donor_p = self.workspace_root / SLEEVE_PRESETS[donor_preset]["default_donor"]

                donor_info = None
                scale_ratio = 1.0
                ratio_desc = "Default 1.0x"
                if donor_p and donor_p.is_file():
                    donor_info = detect_arm_type(donor_p)
                    scale_ratio, ratio_desc = calculate_scale_ratio(tgt_path, donor_p)

                self._send_json({
                    "success": True,
                    "target": target_info,
                    "donor": donor_info,
                    "scale_ratio": scale_ratio,
                    "scale_description": ratio_desc,
                    "presets": SLEEVE_PRESETS,
                })
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        # Default static file serving
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            req_data = self._read_json_body()

            if path == "/api/config":
                new_game_dir = req_data.get("game_directory")
                if not new_game_dir:
                    self._send_json({"success": False, "error": "game_directory is required."}, status=400)
                    return
                success = self.config.set_game_root(new_game_dir)
                self.workspace_root = self.config.get_game_root()
                self._send_json({
                    "success": success,
                    "game_directory": str(self.config.get_game_root()),
                    "is_game_valid": self.config.is_game_dir_valid(),
                    "is_hl_running": self.config.is_hl_running(),
                })
                return

            elif path == "/api/preview":
                # Generate live before-and-after preview without writing to disk
                img_bytes = self._extract_image_bytes(req_data)

                w = int(req_data["width"])
                h = int(req_data["height"])
                is_masked = bool(req_data.get("is_masked", False))
                mode = req_data.get("mode", "auto")
                scale = float(req_data.get("scale", 1.0))

                _, preview_rgba = process_image_for_texture(
                    img_bytes, w, h, is_masked=is_masked, mode=mode, scale_multiplier=scale
                )

                buf = io.BytesIO()
                preview_rgba.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode("ascii")

                self._send_json(
                    {
                        "success": True,
                        "preview": f"data:image/png;base64,{encoded}",
                        "layers_count": len(resolved_layers) if req_data.get("layers") else 1,
                    }
                )
                return

            elif path in ("/api/bake_layers_preview", "/api/bake_preview"):
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                tex_idx = req_data.get("texture_index")

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                model = MdlModel(mdl_path)
                if tex_idx is not None:
                    target_tex = model.get_texture_by_index(int(tex_idx))
                else:
                    skins = model.get_skins()
                    target_tex = max(skins, key=lambda t: t.width * t.height) if skins else None

                if not target_tex:
                    self._send_json({"success": False, "error": "No weapon skin texture found."}, status=404)
                    return

                base_rgba = target_tex.to_rgba_image()

                if req_data.get("layers"):
                    raw_layers = req_data.get("layers", [])
                    resolved_layers = []
                    for idx, layer in enumerate(raw_layers):
                        if not layer.get("visible", True):
                            continue
                        try:
                            img_bytes = self._resolve_layer_image_bytes(layer)
                        except Exception:
                            continue
                        resolved_layers.append({
                            "image": img_bytes,
                            "x": layer.get("x"),
                            "y": layer.get("y"),
                            "scale": _safe_float(layer.get("scale"), 1.0),
                            "rotation": _safe_float(layer.get("rotation"), 0.0),
                            "scrape": _safe_float(layer.get("scrape"), 0.0),
                            "opacity": _safe_float(layer.get("opacity"), 1.0),
                            "chrome_effect": layer.get("chrome_effect"),
                            "visible": True,
                            "z_index": _safe_int(layer.get("z_index"), idx),
                        })

                    composite_rgba = composite_multi_stickers(base_rgba, resolved_layers, weapon_key=weapon)
                else:
                    preset = req_data.get("preset", "center")
                    coords = req_data.get("coords")
                    scale = _safe_float(req_data.get("scale"), 1.0)
                    rotation = _safe_float(req_data.get("rotation"), 0.0)
                    scrape = _safe_float(req_data.get("scrape"), 0.0)
                    pre_emphasis = _safe_bool(req_data.get("pre_emphasis"), True)
                    chrome_effect = req_data.get("chrome_effect") or req_data.get("fx")
                    if chrome_effect and str(chrome_effect).lower() in ("matte", "none", ""):
                        chrome_effect = None

                    sticker_bytes = self._extract_image_bytes(req_data)
                    custom_tuple = (int(coords[0]), int(coords[1])) if coords and len(coords) == 2 else None

                    _, composite_rgba = bake_sticker_onto_texture(
                        base_rgba,
                        sticker_bytes,
                        weapon_key=weapon,
                        preset=preset,
                        custom_coords=custom_tuple,
                        scale_multiplier=scale,
                        rotation_deg=rotation,
                        scrape=scrape,
                        pre_emphasis=pre_emphasis,
                        chrome_effect=chrome_effect,
                    )

                buf = io.BytesIO()
                composite_rgba.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode("ascii")

                self._send_json(
                    {
                        "success": True,
                        "preview": f"data:image/png;base64,{encoded}",
                        "layers_count": len(resolved_layers) if req_data.get("layers") else 1,
                    }
                )
                return

            elif path == "/api/inject":
                # Injects uploaded image into specific texture slot
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                tex_idx = req_data.get("texture_index")
                tex_name = req_data.get("texture_name")
                mode = req_data.get("mode", "auto")
                scale = float(req_data.get("scale", 1.0))

                img_bytes = self._extract_image_bytes(req_data)

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                model = MdlModel(mdl_path)
                target_tex = None
                if tex_idx is not None:
                    target_tex = model.get_texture_by_index(int(tex_idx))
                elif tex_name:
                    target_tex = model.get_texture_by_name(tex_name)

                if not target_tex:
                    self._send_json({"success": False, "error": "Texture slot not found."}, status=404)
                    return

                # Save backup snapshot
                model.save_slot_snapshot(target_tex)

                # Process image
                payload, preview_rgba = process_image_for_texture(
                    img_bytes,
                    target_tex.width,
                    target_tex.height,
                    is_masked=target_tex.is_masked,
                    mode=mode,
                    scale_multiplier=scale,
                )

                # Inject and save atomically
                model.inject_texture_payload(target_tex, payload)
                saved_path = model.save_atomic(create_backup=True)

                buf = io.BytesIO()
                preview_rgba.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode("ascii")

                self._send_json(
                    {
                        "success": True,
                        "message": f"Successfully injected into {target_tex.name} ({target_tex.width}x{target_tex.height}).",
                        "saved_path": str(saved_path),
                        "preview": f"data:image/png;base64,{encoded}",
                    }
                )
                return

            elif path in ("/api/bake_layers_commit", "/api/bake"):
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                tex_idx = req_data.get("texture_index")

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                model = MdlModel(mdl_path)
                if tex_idx is not None:
                    target_tex = model.get_texture_by_index(int(tex_idx))
                else:
                    skins = model.get_skins()
                    target_tex = max(skins, key=lambda t: t.width * t.height) if skins else None

                if not target_tex:
                    self._send_json({"success": False, "error": "No weapon skin texture found to bake onto."}, status=404)
                    return

                model.save_slot_snapshot(target_tex)
                base_rgba = target_tex.to_rgba_image()

                if req_data.get("layers"):
                    raw_layers = req_data.get("layers", [])
                    dither_mode = req_data.get("dither", "floyd_steinberg")
                    sync_pw = _safe_bool(req_data.get("sync_pw"), False)

                    resolved_layers = []
                    for idx, layer in enumerate(raw_layers):
                        if not layer.get("visible", True):
                            continue
                        try:
                            img_bytes = self._resolve_layer_image_bytes(layer)
                        except Exception:
                            continue
                        resolved_layers.append({
                            "image": img_bytes,
                            "x": layer.get("x"),
                            "y": layer.get("y"),
                            "scale": _safe_float(layer.get("scale"), 1.0),
                            "rotation": _safe_float(layer.get("rotation"), 0.0),
                            "scrape": _safe_float(layer.get("scrape"), 0.0),
                            "opacity": _safe_float(layer.get("opacity"), 1.0),
                            "chrome_effect": layer.get("chrome_effect"),
                            "visible": True,
                            "z_index": _safe_int(layer.get("z_index"), idx),
                        })

                    payload, composite_rgba = bake_multi_stickers_onto_texture(
                        base_rgba,
                        resolved_layers,
                        weapon_key=weapon,
                        dither=dither_mode,
                    )

                    model.inject_texture_payload(target_tex, payload)
                    saved_path = model.save_atomic(create_backup=True)

                    sync_res = None
                    if sync_pw:
                        try:
                            sync_res = sync_pw_models(
                                root_dir=self.workspace_root,
                                weapon=weapon,
                                team=team,
                                auto_backup=True,
                                v_model_path=str(mdl_path),
                                include_stickers=True,
                            )
                        except Exception as e:
                            sync_res = {"success": False, "error": str(e)}

                    buf = io.BytesIO()
                    composite_rgba.save(buf, format="PNG")
                    encoded = base64.b64encode(buf.getvalue()).decode("ascii")

                    self._send_json(
                        {
                            "success": True,
                            "message": f"Successfully baked {len(resolved_layers)} sticker layer(s) onto '{target_tex.name}'.",
                            "saved_path": str(saved_path),
                            "preview": f"data:image/png;base64,{encoded}",
                            "layers_count": len(resolved_layers),
                            "sync_pw": sync_res,
                        }
                    )
                    return
                else:
                    preset = req_data.get("preset", "center")
                    coords = req_data.get("coords")
                    scale = _safe_float(req_data.get("scale"), 1.0)
                    rotation = _safe_float(req_data.get("rotation"), 0.0)
                    scrape = _safe_float(req_data.get("scrape"), 0.0)
                    fx = req_data.get("fx")
                    pre_emphasis = _safe_bool(req_data.get("pre_emphasis"), True)
                    chrome_effect = req_data.get("chrome_effect") or req_data.get("fx")
                    if chrome_effect and str(chrome_effect).lower() in ("matte", "none", ""):
                        chrome_effect = None

                    sticker_bytes = self._extract_image_bytes(req_data)
                    custom_tuple = (int(coords[0]), int(coords[1])) if coords and len(coords) == 2 else None

                    payload, composite_rgba = bake_sticker_onto_texture(
                        base_rgba,
                        sticker_bytes,
                        weapon_key=weapon,
                        preset=preset,
                        custom_coords=custom_tuple,
                        scale_multiplier=scale,
                        rotation_deg=rotation,
                        scrape=scrape,
                        pre_emphasis=pre_emphasis,
                        chrome_effect=chrome_effect,
                    )

                    new_flags = None
                    if fx:
                        fx_clean = str(fx).lower().strip()
                        if fx_clean in ("chrome", "foil"):
                            new_flags = target_tex.flags | STUDIO_NF_CHROME
                        elif fx_clean == "glow":
                            new_flags = target_tex.flags | STUDIO_NF_ADDITIVE
                        elif fx_clean == "matte":
                            new_flags = target_tex.flags & ~(STUDIO_NF_CHROME | STUDIO_NF_ADDITIVE)

                    model.inject_texture_payload(target_tex, payload, new_flags=new_flags)
                    saved_path = model.save_atomic(create_backup=True)

                    buf = io.BytesIO()
                    composite_rgba.save(buf, format="PNG")
                    encoded = base64.b64encode(buf.getvalue()).decode("ascii")

                    self._send_json(
                        {
                            "success": True,
                            "message": f"Successfully baked sticker onto '{target_tex.name}' at '{preset}'.",
                            "saved_path": str(saved_path),
                            "preview": f"data:image/png;base64,{encoded}",
                        }
                    )
                    return

            elif path == "/api/revert":
                # Reverts single slot
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                tex_idx = req_data.get("texture_index")
                tex_name = req_data.get("texture_name")

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                model = MdlModel(mdl_path)
                target = tex_idx if tex_idx is not None else tex_name
                success = model.revert_texture_from_backup(target)

                if success:
                    reloaded = MdlModel(mdl_path)
                    t = reloaded.find_texture(target)
                    new_preview = t.to_base64_data_uri() if t else ""
                    self._send_json(
                        {
                            "success": True,
                            "message": f"Reverted slot successfully.",
                            "preview": new_preview,
                        }
                    )
                else:
                    self._send_json(
                        {"success": False, "error": "No backup found for this slot."}, status=400
                    )
                return

            elif path in ("/api/tools/clean_backups", "/api/tools/migrate_backups"):
                try:
                    moved = migrate_loose_backups(root_dir=self.workspace_root)
                    self._send_json({"success": True, "moved_count": len(moved), "moved": moved})
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=500)
                return

            elif path == "/api/model/restore_backup":
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                backup_target = req_data.get("backup_target")

                if not backup_target:
                    self._send_json({"success": False, "error": "Missing 'backup_target' parameter."}, status=400)
                    return

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                try:
                    success, msg = restore_specific_backup(mdl_path, backup_target=backup_target)
                    if success:
                        self._send_json({"success": True, "message": msg, "restored_from": str(backup_target)})
                    else:
                        self._send_json({"success": False, "error": msg}, status=400)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=500)
                return
                try:
                    moved = migrate_loose_backups(root_dir=self.workspace_root)
                    self._send_json({"success": True, "moved_count": len(moved), "moved": moved})
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=500)
                return

            elif path == "/api/restore":
                # Full restore from .orig.mdl
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                model = MdlModel(mdl_path)
                success = model.restore_from_immutable_original()

                if success:
                    self._send_json(
                        {
                            "success": True,
                            "message": f"Model '{mdl_path.name}' completely restored to original state.",
                        }
                    )
                else:
                    self._send_json(
                        {
                            "success": False,
                            "error": f"No original backup (.orig.mdl) found for {mdl_path.name}.",
                        },
                        status=400,
                    )
                return

            elif path == "/api/batch_inject":
                # Batch inject sticker into multiple weapons at once
                weapons = req_data.get("weapons", [])
                team = req_data.get("team", "ct")
                slot = req_data.get("slot", 1)
                img_data_uri = req_data.get("image_base64", "")
                img_path = req_data.get("image_path")
                mode = req_data.get("mode", "fit")
                scale = float(req_data.get("scale", 1.0))
                fx = req_data.get("fx", "matte")

                sticker_source = None
                if img_data_uri:
                    if "," in img_data_uri:
                        img_data_uri = img_data_uri.split(",", 1)[1]
                    sticker_source = base64.b64decode(img_data_uri)
                elif img_path:
                    p = Path(img_path)
                    if not p.is_absolute():
                        p = self.workspace_root / p
                    sticker_source = p

                if not sticker_source:
                    self._send_json({"success": False, "error": "No sticker image provided."}, status=400)
                    return

                results = batch_inject_sticker(
                    weapons=weapons,
                    sticker_image=sticker_source,
                    slot=slot,
                    team=team,
                    mode=mode,
                    scale=scale,
                    fx=fx,
                    root_dir=self.workspace_root,
                )
                self._send_json({"success": True, "results": results})
                return

            elif path == "/api/profiles/save":
                name = req_data.get("name", "").strip()
                if not name:
                    self._send_json({"success": False, "error": "Profile name is required."}, status=400)
                    return
                weapons = req_data.get("weapons")
                team = req_data.get("team", "ct")
                description = req_data.get("description", "")
                res = save_profile(name, weapons=weapons, team=team, description=description, root_dir=self.studio_root)
                self._send_json(res)
                return

            elif path == "/api/profiles/load":
                name = req_data.get("name", "").strip()
                if not name:
                    self._send_json({"success": False, "error": "Profile name is required."}, status=400)
                    return
                res = load_profile(name, root_dir=self.studio_root)
                self._send_json(res)
                return

            elif path == "/api/profiles/delete":
                name = req_data.get("name", "").strip()
                if not name:
                    self._send_json({"success": False, "error": "Profile name is required."}, status=400)
                    return
                deleted = delete_profile(name, root_dir=self.studio_root)
                if not deleted:
                    self._send_json({"success": False, "error": f"Profile '{name}' not found."}, status=404)
                    return
                self._send_json({"success": True, "message": f"Profile '{name}' deleted successfully."})
                return

            elif path == "/api/library/stickers/upload":
                try:
                    name = req_data.get("name", "custom_sticker")
                    category = req_data.get("category", "Custom / User")
                    auto_alpha = _safe_bool(req_data.get("auto_alpha", False))
                    img_bytes = self._extract_image_bytes(req_data)
                    res = save_custom_sticker(
                        name=name,
                        image_bytes=img_bytes,
                        category=category,
                        auto_alpha=auto_alpha,
                        workspace_root=self.studio_root,
                    )
                    self._send_json(res)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                return

            elif path == "/api/library/stickers/edit":
                try:
                    filename = (req_data.get("filename") or "").strip()
                    if not filename:
                        self._send_json({"success": False, "error": "Filename is required."}, status=400)
                        return
                    new_name = req_data.get("name") or req_data.get("new_name")
                    new_category = req_data.get("category") or req_data.get("new_category")
                    res = edit_custom_sticker(
                        filename=filename,
                        new_name=new_name,
                        new_category=new_category,
                        workspace_root=self.studio_root,
                    )
                    self._send_json(res)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                return

            elif path == "/api/library/stickers/delete":
                try:
                    filename = (req_data.get("filename") or "").strip()
                    if not filename:
                        self._send_json({"success": False, "error": "Filename is required."}, status=400)
                        return
                    res = delete_custom_sticker(
                        filename=filename,
                        workspace_root=self.studio_root,
                        allow_builtin=True,
                    )
                    self._send_json(res)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                return

            elif path == "/api/library/skins/upload":
                try:
                    name = req_data.get("name", "custom_skin")
                    weapon = req_data.get("weapon")
                    weapon_category = req_data.get("weapon_category")
                    skin_name = req_data.get("skin_name")
                    category = req_data.get("category", "Custom Weapon Skins")
                    img_bytes = self._extract_image_bytes(req_data)
                    res = save_custom_skin(
                        name=name,
                        image_bytes=img_bytes,
                        category=category,
                        weapon=weapon,
                        weapon_category=weapon_category,
                        skin_name=skin_name,
                        workspace_root=self.studio_root,
                    )
                    self._send_json(res)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                return

            elif path == "/api/library/skins/edit":
                try:
                    filename = (req_data.get("filename") or "").strip()
                    if not filename:
                        self._send_json({"success": False, "error": "Filename is required."}, status=400)
                        return
                    new_name = req_data.get("name") or req_data.get("new_name") or req_data.get("skin_name")
                    new_weapon = req_data.get("weapon") or req_data.get("new_weapon")
                    new_weapon_category = req_data.get("weapon_category") or req_data.get("new_weapon_category")
                    res = edit_custom_skin(
                        filename=filename,
                        new_name=new_name,
                        new_weapon=new_weapon,
                        new_weapon_category=new_weapon_category,
                        workspace_root=self.studio_root,
                    )
                    self._send_json(res)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                return

            elif path == "/api/library/skins/delete":
                try:
                    filename = (req_data.get("filename") or "").strip()
                    if not filename:
                        self._send_json({"success": False, "error": "Filename is required."}, status=400)
                        return
                    res = delete_custom_skin(
                        filename=filename,
                        workspace_root=self.studio_root,
                    )
                    self._send_json(res)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                return

            elif path == "/api/library/stickers/restore_defaults":
                try:
                    res = restore_default_stickers(workspace_root=self.studio_root)
                    self._send_json(res)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                return

            elif path == "/api/color_preview":
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                tex_idx = req_data.get("texture_index")
                tex_name = req_data.get("texture_name")

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                model = MdlModel(mdl_path)
                target_tex = model.find_texture(tex_idx if tex_idx is not None else tex_name)
                if not target_tex:
                    self._send_json({"success": False, "error": "Target texture not found."}, status=404)
                    return

                color_params = {
                    "brightness": float(req_data.get("brightness", 0)),
                    "contrast": float(req_data.get("contrast", 0)),
                    "saturation": float(req_data.get("saturation", 0)),
                    "vibrance": float(req_data.get("vibrance", 0)),
                    "clarity": float(req_data.get("clarity", 0)),
                    "shadows": float(req_data.get("shadows", 0)),
                    "highlights": float(req_data.get("highlights", 0)),
                    "temperature": float(req_data.get("temperature", 0)),
                    "tint": float(req_data.get("tint", 0)),
                    "hue": float(req_data.get("hue", 0)),
                    "sharpen": float(req_data.get("sharpen", 0)),
                    "wear": float(req_data.get("wear", 0)),
                    "hsl_adjustments": req_data.get("hsl_adjustments"),
                }

                adjusted_img = adjust_color_grading(target_tex.to_rgba_image(), **color_params)
                buf = io.BytesIO()
                adjusted_img.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode("ascii")
                self._send_json({"success": True, "preview": f"data:image/png;base64,{encoded}"})
                return

            elif path == "/api/color_apply":
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                tex_idx = req_data.get("texture_index")
                tex_name = req_data.get("texture_name")

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                model = MdlModel(mdl_path)
                target_tex = model.find_texture(tex_idx if tex_idx is not None else tex_name)
                if not target_tex:
                    self._send_json({"success": False, "error": "Target texture not found."}, status=404)
                    return

                color_params = {
                    "brightness": float(req_data.get("brightness", 0)),
                    "contrast": float(req_data.get("contrast", 0)),
                    "saturation": float(req_data.get("saturation", 0)),
                    "vibrance": float(req_data.get("vibrance", 0)),
                    "clarity": float(req_data.get("clarity", 0)),
                    "shadows": float(req_data.get("shadows", 0)),
                    "highlights": float(req_data.get("highlights", 0)),
                    "temperature": float(req_data.get("temperature", 0)),
                    "tint": float(req_data.get("tint", 0)),
                    "hue": float(req_data.get("hue", 0)),
                    "sharpen": float(req_data.get("sharpen", 0)),
                    "wear": float(req_data.get("wear", 0)),
                    "hsl_adjustments": req_data.get("hsl_adjustments"),
                }

                model.save_slot_snapshot(target_tex)
                is_tex_masked = bool(target_tex.is_masked or target_tex.role == "sticker")
                dither_choice = str(req_data.get("dither", "floyd_steinberg"))
                payload, preview_rgba = adjust_and_quantize(
                    target_tex.to_rgba_image(),
                    is_masked=is_tex_masked,
                    dither=dither_choice,
                    **color_params,
                )
                model.inject_texture_payload(target_tex, payload)
                saved_path = model.save_atomic(create_backup=True)

                buf = io.BytesIO()
                preview_rgba.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode("ascii")
                self._send_json({
                    "success": True,
                    "message": f"Successfully applied color grading to '{target_tex.name}'.",
                    "saved_path": str(saved_path),
                    "preview": f"data:image/png;base64,{encoded}",
                })
                return

            elif path == "/api/slot_tune_preview":
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                tex_idx = req_data.get("texture_index")
                scale = _safe_float(req_data.get("scale"), 1.0)
                offset_x = _safe_int(req_data.get("offset_x"), 0)
                offset_y = _safe_int(req_data.get("offset_y"), 0)
                rotation = _safe_float(req_data.get("rotation"), 0.0)
                fit_mode = req_data.get("mode", req_data.get("fit_mode", "fit"))
                scrape = _safe_float(req_data.get("scrape"), 0.0)

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                model = MdlModel(mdl_path)
                target_tex = model.get_texture_by_index(int(tex_idx)) if tex_idx is not None else None
                if not target_tex:
                    self._send_json({"success": False, "error": "Target slot not found."}, status=404)
                    return

                try:
                    img_bytes = self._extract_image_bytes(req_data)
                except Exception:
                    img_bytes = target_tex.to_png_bytes()

                _, preview_rgba = process_slot_sticker_with_transform(
                    img_bytes,
                    target_w=target_tex.width,
                    target_h=target_tex.height,
                    scale=scale,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    rotation=rotation,
                    fit_mode=fit_mode,
                    scrape=scrape,
                )
                buf = io.BytesIO()
                preview_rgba.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode("ascii")
                self._send_json({"success": True, "preview": f"data:image/png;base64,{encoded}"})
                return

            elif path == "/api/slot_tune_apply":
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                tex_idx = req_data.get("texture_index")
                scale = _safe_float(req_data.get("scale"), 1.0)
                offset_x = _safe_int(req_data.get("offset_x"), 0)
                offset_y = _safe_int(req_data.get("offset_y"), 0)
                rotation = _safe_float(req_data.get("rotation"), 0.0)
                fit_mode = req_data.get("mode", req_data.get("fit_mode", "fit"))
                scrape = _safe_float(req_data.get("scrape"), 0.0)

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                model = MdlModel(mdl_path)
                target_tex = model.get_texture_by_index(int(tex_idx)) if tex_idx is not None else None
                if not target_tex:
                    self._send_json({"success": False, "error": "Target slot not found."}, status=404)
                    return

                try:
                    img_bytes = self._extract_image_bytes(req_data)
                except Exception:
                    img_bytes = target_tex.to_png_bytes()

                model.save_slot_snapshot(target_tex)
                payload, preview_rgba = process_slot_sticker_with_transform(
                    img_bytes,
                    target_w=target_tex.width,
                    target_h=target_tex.height,
                    scale=scale,
                    offset_x=offset_x,
                    offset_y=offset_y,
                    rotation=rotation,
                    fit_mode=fit_mode,
                    scrape=scrape,
                )
                model.inject_texture_payload(target_tex, payload)
                saved_path = model.save_atomic(create_backup=True)

                buf = io.BytesIO()
                preview_rgba.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode("ascii")
                self._send_json({
                    "success": True,
                    "message": f"Successfully tuned and injected into '{target_tex.name}' ({target_tex.width}x{target_tex.height}).",
                    "saved_path": str(saved_path),
                    "preview": f"data:image/png;base64,{encoded}",
                })
                return

            elif path == "/api/stattrak_apply":
                try:
                    weapon = req_data.get("weapon", "usp")
                    team = req_data.get("team", "ct")
                    custom_path = req_data.get("path")
                    color_name = req_data.get("color", "orange")
                    custom_number = req_data.get("number")
                    tex_idx = req_data.get("texture_index")
                    tex_name = req_data.get("texture_name")

                    if custom_path:
                        mdl_path = Path(custom_path).resolve()
                    else:
                        mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                    model = MdlModel(mdl_path)
                    target_tex = None

                    # 1. Texture specified by index
                    if tex_idx is not None and str(tex_idx).strip() != "":
                        try:
                            target_tex = model.get_texture_by_index(int(tex_idx))
                        except (ValueError, TypeError):
                            target_tex = None
                        if not target_tex:
                            self._send_json({"success": False, "error": f"Specified texture_index '{tex_idx}' not found in {mdl_path.name}."}, status=404)
                            return

                    # 2. Texture specified by name
                    elif tex_name and str(tex_name).strip() != "":
                        target_tex = model.find_texture(str(tex_name))
                        if not target_tex:
                            self._send_json({"success": False, "error": f"Specified texture_name '{tex_name}' not found in {mdl_path.name}."}, status=404)
                            return

                    # 3. Auto-detect: Prioritize textures containing 'digit' in name (e.g. stattrak_digit.bmp, stat_digit.bmp)
                    if not target_tex:
                        digit_textures = [t for t in model.textures if "digit" in t.name.lower()]
                        if digit_textures:
                            target_tex = digit_textures[0]

                    # 4. Fallback: exact "stat_digit.bmp"
                    if not target_tex:
                        target_tex = model.find_texture("stat_digit.bmp")

                    # 5. Fallback: role == 'stattrak' or 'stat' in name
                    if not target_tex:
                        for t in model.textures:
                            if getattr(t, "role", "") == "stattrak" or "stat" in t.name.lower():
                                target_tex = t
                                break

                    if not target_tex:
                        self._send_json({"success": False, "error": f"No StatTrak digit texture found in {mdl_path.name}."}, status=404)
                        return

                    model.save_slot_snapshot(target_tex)
                    payload, preview_rgba = customize_stattrak_texture(
                        target_tex.to_rgba_image(),
                        color_name=color_name,
                        custom_number=custom_number,
                    )
                    model.inject_texture_payload(target_tex, payload)
                    saved_path = model.save_atomic(create_backup=True)

                    buf = io.BytesIO()
                    preview_rgba.save(buf, format="PNG")
                    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
                    self._send_json({
                        "success": True,
                        "message": f"StatTrak LED updated to {color_name.upper()} with count '{custom_number or 'default'}'.",
                        "saved_path": str(saved_path),
                        "preview": f"data:image/png;base64,{encoded}",
                        "texture_name": target_tex.name,
                        "texture_index": target_tex.index,
                    })
                except FileNotFoundError as e:
                    self._send_json({"success": False, "error": str(e)}, status=404)
                except ValueError as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                except Exception as e:
                    self._send_json({"success": False, "error": f"Failed to apply StatTrak: {str(e)}"}, status=400)
                return

            elif path == "/api/stattrak_reset":
                try:
                    weapon = req_data.get("weapon", "usp")
                    team = req_data.get("team", "ct")
                    custom_path = req_data.get("path")
                    tex_idx = req_data.get("texture_index")
                    tex_name = req_data.get("texture_name")

                    if custom_path:
                        mdl_path = Path(custom_path).resolve()
                    else:
                        mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                    orig_bak_tuple = find_model_backup(mdl_path)
                    orig_path = orig_bak_tuple[0] if orig_bak_tuple else None
                    if not orig_path or not orig_path.exists():
                        self._send_json({"success": False, "error": f"No original backup (.orig.mdl) found for {mdl_path.name}."}, status=404)
                        return

                    orig_model = MdlModel(orig_path)
                    model = MdlModel(mdl_path)

                    target_tex = None
                    if tex_idx is not None and str(tex_idx).strip() != "":
                        try:
                            target_tex = model.get_texture_by_index(int(tex_idx))
                        except (ValueError, TypeError):
                            target_tex = None

                    if not target_tex and tex_name:
                        target_tex = model.find_texture(str(tex_name))

                    if not target_tex:
                        for t in model.textures:
                            if "digit" in t.name.lower() or getattr(t, "role", "") == "stattrak":
                                target_tex = t
                                break

                    if not target_tex:
                        self._send_json({"success": False, "error": f"StatTrak texture not found in {mdl_path.name}."}, status=404)
                        return

                    orig_tex = orig_model.find_texture(target_tex.name)
                    if not orig_tex:
                        orig_tex = orig_model.get_texture_by_index(target_tex.index)

                    if not orig_tex:
                        self._send_json({"success": False, "error": f"Original texture '{target_tex.name}' not found in backup."}, status=404)
                        return

                    model.inject_texture_payload(target_tex, orig_tex.raw_data)
                    saved_path = model.save_atomic(create_backup=True)

                    buf = io.BytesIO()
                    orig_tex.to_rgba_image().save(buf, format="PNG")
                    encoded = base64.b64encode(buf.getvalue()).decode("ascii")

                    self._send_json({
                        "success": True,
                        "message": f"StatTrak LED reset to original texture '{target_tex.name}'.",
                        "saved_path": str(saved_path),
                        "preview": f"data:image/png;base64,{encoded}",
                        "texture_name": target_tex.name,
                        "texture_index": target_tex.index,
                    })
                except Exception as e:
                    self._send_json({"success": False, "error": f"Failed to reset StatTrak: {str(e)}"}, status=400)
                return

            elif path == "/api/wear_apply":
                try:
                    weapon = req_data.get("weapon", "usp")
                    team = req_data.get("team", "ct")
                    custom_path = req_data.get("path")
                    tex_idx = req_data.get("texture_index")
                    wear_float = float(req_data.get("wear_float", 0.35))
                    seed = int(req_data.get("seed", 1337))

                    if custom_path:
                        mdl_path = Path(custom_path).resolve()
                    else:
                        mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                    model = MdlModel(mdl_path)
                    if tex_idx is not None:
                        target_tex = model.get_texture_by_index(int(tex_idx))
                    else:
                        skins = model.get_skins()
                        target_tex = max(skins, key=lambda t: t.width * t.height) if skins else None

                    if not target_tex:
                        self._send_json({"success": False, "error": "Target skin texture not found."}, status=404)
                        return

                    tier_name = get_wear_condition_name(wear_float)
                    model.save_slot_snapshot(target_tex)
                    payload, worn_img = simulate_and_quantize(
                        target_tex.to_rgba_image(),
                        wear_float=wear_float,
                        seed=seed,
                        is_masked=target_tex.is_masked,
                    )
                    model.inject_texture_payload(target_tex, payload)
                    saved_path = model.save_atomic(create_backup=True)

                    buf = io.BytesIO()
                    worn_img.save(buf, format="PNG")
                    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
                    self._send_json({
                        "success": True,
                        "message": f"Applied wear float {wear_float:.3f} ({tier_name}) to '{target_tex.name}'.",
                        "tier_name": tier_name,
                        "saved_path": str(saved_path),
                        "preview": f"data:image/png;base64,{encoded}",
                    })
                except FileNotFoundError as e:
                    self._send_json({"success": False, "error": str(e)}, status=404)
                except ValueError as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                except Exception as e:
                    self._send_json({"success": False, "error": f"Failed to apply wear: {str(e)}"}, status=400)
                return

            elif path == "/api/glove_transfer":
                src_weapon = req_data.get("source_weapon", "usp")
                tgt_weapons = req_data.get("target_weapons", ["all"])
                team = req_data.get("team", "ct")
                sync_sleeves = bool(req_data.get("sync_sleeves", True))

                results = batch_transfer_gloves(
                    source_weapon=src_weapon,
                    target_weapons=tgt_weapons,
                    team=team,
                    sync_sleeves=sync_sleeves,
                    root_dir=self.workspace_root,
                )
                self._send_json({"success": True, "results": results})
                return

            elif path == "/api/gloves/batch_inject_images":
                try:
                    left_b64 = req_data.get("left_image_base64")
                    right_b64 = req_data.get("right_image_base64")
                    left_path = req_data.get("left_image_path")
                    right_path = req_data.get("right_image_path")
                    mirror_left = _safe_bool(req_data.get("mirror_left", False))
                    team = req_data.get("team", "all")
                    weapons = req_data.get("weapons")

                    left_source = left_b64 or left_path
                    right_source = right_b64 or right_path

                    if not left_source and not right_source:
                        self._send_json(
                            {"success": False, "error": "Please provide at least one glove image (left or right)."},
                            status=400,
                        )
                        return

                    res = batch_inject_glove_images(
                        left_image=left_source,
                        right_image=right_source,
                        team=team,
                        target_weapons=weapons,
                        mirror_left_to_right=mirror_left,
                        root_dir=self.workspace_root,
                    )
                    self._send_json(res)
                except (ValueError, FileNotFoundError) as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                except Exception as e:
                    self._send_json({"success": False, "error": f"Failed to process glove images: {str(e)}"}, status=400)
                return

            elif path == "/api/gloves/presets/save":
                try:
                    name = req_data.get("name", "").strip()
                    if not name:
                        self._send_json({"success": False, "error": "Preset name is required."}, status=400)
                        return
                    left_b64 = req_data.get("left_image_base64")
                    right_b64 = req_data.get("right_image_base64")
                    left_path = req_data.get("left_image_path")
                    right_path = req_data.get("right_image_path")
                    mirror_left = _safe_bool(req_data.get("mirror_left", False))

                    left_source = left_b64 or left_path
                    right_source = right_b64 or right_path

                    res = save_glove_preset(
                        name=name,
                        left_image=left_source,
                        right_image=right_source,
                        mirror_left_to_right=mirror_left,
                        root_dir=self.studio_root,
                    )
                    self._send_json(res)
                except (ValueError, FileNotFoundError) as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                except Exception as e:
                    self._send_json({"success": False, "error": f"Failed to save preset: {str(e)}"}, status=400)
                return

            elif path == "/api/gloves/presets/apply":
                try:
                    name = req_data.get("name", "").strip()
                    if not name:
                        self._send_json({"success": False, "error": "Preset name is required."}, status=400)
                        return
                    team = req_data.get("team", "all")
                    weapons = req_data.get("weapons")

                    res = apply_glove_preset(
                        name=name,
                        team=team,
                        target_weapons=weapons,
                        root_dir=self.workspace_root,
                    )
                    self._send_json(res)
                except FileNotFoundError as e:
                    self._send_json({"success": False, "error": str(e)}, status=404)
                except ValueError as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                except Exception as e:
                    self._send_json({"success": False, "error": f"Failed to apply preset: {str(e)}"}, status=400)
                return

            elif path == "/api/gloves/presets/delete":
                name = req_data.get("name", "").strip()
                if not name:
                    self._send_json({"success": False, "error": "Preset name is required."}, status=400)
                    return
                deleted = delete_glove_preset(name, root_dir=self.studio_root)
                if not deleted:
                    self._send_json({"success": False, "error": f"Preset '{name}' not found."}, status=404)
                    return
                self._send_json({"success": True, "message": f"Preset '{name}' deleted successfully."})
                return

            elif path == "/api/toggle_chrome":
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                tex_idx = req_data.get("texture_index")
                enable = req_data.get("enable")

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                model = MdlModel(mdl_path)
                target_tex = model.get_texture_by_index(int(tex_idx)) if tex_idx is not None else None
                if not target_tex:
                    self._send_json({"success": False, "error": "Target texture not found."}, status=404)
                    return

                model.save_slot_snapshot(target_tex)
                model.toggle_chrome_shimmer(target_tex, enable=enable)
                saved_path = model.save_atomic(create_backup=True)

                is_chrome = bool(target_tex.flags & STUDIO_NF_CHROME)
                self._send_json({
                    "success": True,
                    "texture_name": target_tex.name,
                    "flags": target_tex.flags,
                    "is_chrome": is_chrome,
                    "message": f"Chrome shimmer {'enabled' if is_chrome else 'disabled'} for '{target_tex.name}'.",
                })
                return

            elif path == "/api/chrome/preview_texture":
                preset = req_data.get("preset", "silver")
                intensity = req_data.get("intensity")
                tightness = req_data.get("tightness")
                tint = req_data.get("tint", req_data.get("hue_tint"))
                try:
                    data_uri = generate_chrome_preview_uri(
                        preset=preset,
                        intensity=float(intensity) if intensity is not None else None,
                        tightness=float(tightness) if tightness is not None else None,
                        tint=float(tint) if tint is not None else None,
                    )
                    self._send_json({
                        "success": True,
                        "preview": data_uri,
                        "preview_uri": data_uri,
                        "data_uri": data_uri,
                        "preset": preset,
                    })
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=400)
                return

            elif path == "/api/chrome/inject":
                team = req_data.get("team", "ct")
                weapon = req_data.get("weapon", "usp")
                preset = req_data.get("preset", "silver")
                intensity = req_data.get("intensity")
                tightness = req_data.get("tightness")
                tint = req_data.get("tint", req_data.get("hue_tint"))
                target_parts = req_data.get("target_parts")
                sync_pw = _safe_bool(req_data.get("sync_pw"), False)
                custom_path = req_data.get("path")

                try:
                    if custom_path:
                        mdl_path = Path(custom_path).resolve()
                    else:
                        mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                    res = inject_chrome_overlay(
                        model_path=mdl_path,
                        preset=preset,
                        force=True,
                        intensity=float(intensity) if intensity is not None else None,
                        tightness=float(tightness) if tightness is not None else None,
                        tint=float(tint) if tint is not None else None,
                        target_parts=target_parts,
                    )

                    if sync_pw:
                        try:
                            pw_res = sync_pw_models(
                                root_dir=self.workspace_root,
                                weapon=weapon,
                                team=team,
                                auto_backup=True,
                                v_model_path=str(mdl_path),
                            )
                            res["sync_pw_result"] = pw_res
                        except Exception as pw_err:
                            res["sync_pw_error"] = str(pw_err)

                    self._send_json(res)
                except FileNotFoundError as fe:
                    self._send_json({"success": False, "error": str(fe)}, status=404)
                except ValueError as ve:
                    self._send_json({"success": False, "error": str(ve)}, status=400)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=500)
                return

            elif path == "/api/chrome/remove":
                team = req_data.get("team", "ct")
                weapon = req_data.get("weapon", "usp")
                custom_path = req_data.get("path")
                sync_pw = _safe_bool(req_data.get("sync_pw"), False)

                try:
                    if custom_path:
                        mdl_path = Path(custom_path).resolve()
                    else:
                        mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                    res = remove_chrome_overlay(mdl_path)

                    if sync_pw:
                        try:
                            pw_res = sync_pw_models(
                                root_dir=self.workspace_root,
                                weapon=weapon,
                                team=team,
                                auto_backup=True,
                                v_model_path=str(mdl_path),
                            )
                            res["sync_pw_result"] = pw_res
                        except Exception as pw_err:
                            res["sync_pw_error"] = str(pw_err)

                    self._send_json(res)
                except FileNotFoundError as fe:
                    self._send_json({"success": False, "error": str(fe)}, status=404)
                except ValueError as ve:
                    self._send_json({"success": False, "error": str(ve)}, status=400)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=500)
                return

            elif path == "/api/export_modpack":
                team = req_data.get("team", "all")
                weapons = req_data.get("weapons")
                include_only_modified = bool(req_data.get("include_only_modified", False))
                include_amxx = bool(req_data.get("include_amxx_configs", False))
                include_pw = bool(req_data.get("include_pw_models", False))
                include_sounds = bool(req_data.get("include_sounds", False))
                pack_name = req_data.get("pack_name", "CS16_Custom_ModPack")

                zip_bytes, manifest = export_modpack(
                    root_dir=self.workspace_root,
                    team=team,
                    weapons=weapons,
                    include_only_modified=include_only_modified,
                    pack_name=pack_name,
                    include_amxx_configs=include_amxx,
                    include_pw_models=include_pw,
                    include_sounds=include_sounds,
                )

                encoded = base64.b64encode(zip_bytes).decode("ascii")
                self._send_json({
                    "success": True,
                    "message": f"Successfully exported {manifest['model_count']} weapon models into modpack zip.",
                    "filename": f"{pack_name}.zip",
                    "zip_base64": f"data:application/zip;base64,{encoded}",
                    "model_count": manifest["model_count"],
                    "manifest": manifest,
                })
                return

            elif path == "/api/amxx/loadout/equip":
                team = req_data.get("team", "ct")
                weapon = req_data.get("weapon", "usp")
                model_path = req_data.get("model_path")
                slot = req_data.get("slot")

                loadout_file = self.workspace_root / ACTIVE_LOADOUT_REL
                try:
                    result = set_active_loadout(
                        loadout_path=loadout_file,
                        team=team,
                        weapon=weapon,
                        model_path=model_path,
                        slot=slot,
                        root_dir=self.workspace_root,
                    )
                    self._send_json(result)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=500)
                return

            elif path == "/api/amxx/sync_pw":
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                auto_backup = _safe_bool(req_data.get("auto_backup"), True)
                include_stickers = _safe_bool(req_data.get("include_stickers"), False)
                sync_p = _safe_bool(req_data.get("sync_p"), True)
                sync_w = _safe_bool(req_data.get("sync_w"), True)
                v_model = req_data.get("v_model")
                p_model = req_data.get("p_model")
                w_model = req_data.get("w_model")

                try:
                    result = sync_pw_models(
                        root_dir=self.workspace_root,
                        weapon=weapon,
                        team=team,
                        auto_backup=auto_backup,
                        v_model_path=v_model,
                        p_model_path=p_model,
                        w_model_path=w_model,
                        include_stickers=include_stickers,
                        sync_p=sync_p,
                        sync_w=sync_w,
                    )
                    self._send_json(result)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=500)
                return

            elif path == "/api/slot/reposition":
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                slot = req_data.get("slot", "1")
                pos = req_data.get("pos")
                normal = req_data.get("normal")
                scale = _safe_float(req_data.get("scale"), 1.0)
                rotation = _safe_float(req_data.get("rotation"), 0.0)
                bone_id = req_data.get("bone_id")

                if pos is None or normal is None:
                    self._send_json({"success": False, "error": "pos and normal coordinates are required."}, status=400)
                    return

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                res = reposition_slot_quad(
                    mdl_path,
                    slot_identifier=slot,
                    target_pos_three=pos,
                    target_normal_three=normal,
                    scale=scale,
                    rotation=rotation,
                    bone_id=bone_id,
                )
                model_3d = extract_model_3d(mdl_path)
                self._send_json({
                    "success": True,
                    "message": f"Slot '{res.get('slot_name', slot)}' repositioned successfully.",
                    "slot_name": res.get("slot_name", slot),
                    "snapshot_id": res.get("snapshot_id"),
                    "model_3d": model_3d,
                })
                return

            elif path == "/api/slot/inject":
                self._send_json({
                    "success": False,
                    "error": "Dynamic slot injection is disabled to prevent GoldSrc engine heap corruption. Use safe in-place slot repositioning instead.",
                }, status=400)
                return

            elif path == "/api/slot/undo":
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                snapshot_id = req_data.get("snapshot_id")

                if custom_path:
                    mdl_path = Path(custom_path).resolve()
                else:
                    mdl_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                success = restore_geometry_snapshot(mdl_path, snapshot_id=snapshot_id)
                if not success:
                    self._send_json({"success": False, "error": "No geometry snapshot available to undo."}, status=400)
                    return

                model_3d = extract_model_3d(mdl_path)
                self._send_json({
                    "success": True,
                    "message": f"Geometry undone for '{mdl_path.name}'.",
                    "model_3d": model_3d,
                })
                return

            elif path == "/api/pov/apply":
                cfg_data = req_data.get("config", {})
                weapon = req_data.get("weapon")
                custom_cstrike = req_data.get("cstrike_dir")
                cstrike_dir = Path(custom_cstrike) if custom_cstrike else self.workspace_root / "cstrike"

                cfg = PovConfig(**{k: v for k, v in cfg_data.items() if hasattr(PovConfig, k)})
                clamped_cfg, warnings = validate_and_clamp_pov(cfg, weapon=weapon)
                ok = apply_pov_to_game(cstrike_dir, clamped_cfg, weapon=weapon)
                if ok:
                    self._send_json({
                        "success": True,
                        "message": "First-Person POV configuration applied successfully to game.",
                        "config": clamped_cfg.to_dict(),
                        "warnings": warnings,
                    })
                else:
                    self._send_json({"success": False, "error": "Failed to apply POV configuration to modern_pov.cfg."}, status=500)
                return

            elif path == "/api/pov/reset":
                custom_cstrike = req_data.get("cstrike_dir")
                cstrike_dir = Path(custom_cstrike) if custom_cstrike else self.workspace_root / "cstrike"
                ok = reset_pov_to_vanilla(cstrike_dir)
                if ok:
                    self._send_json({
                        "success": True,
                        "message": "First-Person POV reset to vanilla default.",
                    })
                else:
                    self._send_json({"success": False, "error": "Failed to reset POV to vanilla."}, status=500)
                return

            elif path == "/api/sleeve/inject":
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                donor_preset = req_data.get("donor_preset", "sas_navy")
                custom_donor_path = req_data.get("donor_path")
                scale_override = req_data.get("scale_override")
                auto_backup = _safe_bool(req_data.get("auto_backup"), True)

                scale_ratio = _safe_float(scale_override, 0.0) if scale_override is not None else None
                if scale_ratio == 0.0:
                    scale_ratio = None

                if custom_path:
                    tgt_path = Path(custom_path).resolve()
                else:
                    tgt_path = resolve_model_path(weapon, team=team, root_dir=self.workspace_root)

                donor_p = None
                if custom_donor_path:
                    donor_p = Path(custom_donor_path).resolve()

                result = transplant_3d_sleeves(
                    target_model_path=tgt_path,
                    donor_path=donor_p,
                    donor_preset=donor_preset,
                    scale_ratio=scale_ratio,
                    create_backup=auto_backup,
                    workspace_root=self.workspace_root,
                )

                if result.get("success"):
                    try:
                        result["model_3d"] = extract_model_3d(tgt_path)
                    except Exception:
                        pass
                    self._send_json(result)
                else:
                    self._send_json(result, status=400)
                return

            elif path == "/api/inventory/save":
                name = req_data.get("name", "Custom Skin")
                weapon = req_data.get("weapon", "usp")
                team = req_data.get("team", "ct")
                custom_path = req_data.get("path")
                sync_pw = _safe_bool(req_data.get("sync_pw"), True)
                register_amxx = _safe_bool(req_data.get("register_amxx"), False)
                equip_now = _safe_bool(req_data.get("equip_now"), False)
                thumb_b64 = req_data.get("thumb_b64") or req_data.get("thumbnail")
                knife_variant = req_data.get("knife_variant")

                res = save_to_inventory(
                    name=name,
                    weapon=weapon,
                    team=team,
                    source_mdl_path=custom_path,
                    sync_pw=sync_pw,
                    register_amxx=register_amxx,
                    equip_now=equip_now,
                    thumb_b64=thumb_b64,
                    knife_variant=knife_variant,
                    root_dir=self.workspace_root,
                )
                self._send_json(res)
                return

            elif path == "/api/inventory/equip":
                item_id = req_data.get("id") or req_data.get("item_id")
                team = req_data.get("team", "ct")
                sync_active_glove = _safe_bool(req_data.get("sync_active_glove"), True)
                if not item_id:
                    self._send_json({"success": False, "error": "item_id is required."}, status=400)
                    return
                res = equip_inventory_skin(
                    item_id_or_path=item_id,
                    team=team,
                    sync_active_glove=sync_active_glove,
                    root_dir=self.workspace_root,
                )
                self._send_json(res)
                return

            elif path == "/api/inventory/sync_gloves":
                preset_name = req_data.get("preset_name")
                donor_weapon = req_data.get("donor_weapon")
                team = req_data.get("team", "ct")
                target_items = req_data.get("target_items")
                res = sync_gloves_to_inventory(
                    glove_preset_name=preset_name,
                    donor_weapon_or_path=donor_weapon,
                    team=team,
                    target_item_ids=target_items,
                    root_dir=self.workspace_root,
                )
                self._send_json(res)
                return

            elif path == "/api/inventory/delete":
                item_id = req_data.get("id") or req_data.get("item_id")
                if not item_id:
                    self._send_json({"success": False, "error": "item_id is required."}, status=400)
                    return
                res = delete_inventory_skin(item_id, root_dir=self.workspace_root)
                self._send_json(res)
                return

            elif path == "/api/inventory/toggle_amxx":
                item_id = req_data.get("id") or req_data.get("item_id")
                enable = _safe_bool(req_data.get("enable"), True)
                if not item_id:
                    self._send_json({"success": False, "error": "item_id is required."}, status=400)
                    return
                res = toggle_amxx_registration(item_id, enable=enable, root_dir=self.workspace_root)
                self._send_json(res)
                return

            self._send_json({"success": False, "error": "Endpoint not found"}, status=404)

        except Exception as e:
            self._send_json({"success": False, "error": str(e)}, status=500)


def ensure_static_assets():
    """Ensure static web assets are populated in studio_root, mirroring from game_root if needed."""
    config = StudioConfig.get_instance()
    game_static = config.get_game_root() / "scripts" / "cs16_studio" / "web" / "static"
    if not game_static.is_dir():
        return
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    try:
        for item in game_static.rglob("*"):
            if item.is_file():
                rel = item.relative_to(game_static)
                dest = STATIC_DIR / rel
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
    except Exception:
        pass


def create_server(host: str = "127.0.0.1", port: int = 5160, workspace_root: Optional[Path] = None):
    ensure_static_assets()
    config = StudioConfig.get_instance()
    root = Path(workspace_root).resolve() if workspace_root else config.get_game_root()

    def handler(*args, **kwargs):
        return StudioApiHandler(*args, workspace_root=root, **kwargs)

    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def run_studio_server(host: str = "127.0.0.1", port: int = 5160, workspace_root: Optional[Path] = None):
    server = create_server(host=host, port=port, workspace_root=workspace_root)
    print(f"CS 1.6 Asset Studio running at http://{host}:{port}/")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping CS 1.6 Asset Studio server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_studio_server()
