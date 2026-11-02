"""
modpack_exporter.py - Bundles customized CS 1.6 weapon models into a clean, ready-to-use modpack ZIP.
Integrated with EmptyX Customization config_manager.
"""

from datetime import datetime
import io
import json
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple, Union
import zipfile

from .mdl_core import discover_available_models
from .config_manager import config


def export_modpack(
    root_dir: Optional[Union[str, Path]] = None,
    team: str = "all",
    weapons: Optional[Union[str, List[str]]] = None,
    include_only_modified: bool = False,
    pack_name: str = "CS16_Custom_ModPack",
    include_amxx_configs: bool = False,
    include_pw_models: bool = False,
    include_sounds: bool = False,
) -> Tuple[bytes, dict]:
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    discovered = discover_available_models(root)

    pack_name = re.sub(r'[^\w\-.]', '_', pack_name.strip()) or "CS16_Custom_ModPack"

    teams_to_scan = ["ct", "t"] if team == "all" else [team]
    selected_models: List[dict] = []
    seen_paths = set()

    if weapons:
        raw_list = [weapons] if isinstance(weapons, str) else list(weapons)
        weapons_filter = set()
        for w in raw_list:
            clean = str(w).lower().strip()
            if clean.startswith("v_"):
                clean = clean[2:]
            if clean.endswith(".mdl"):
                clean = clean[:-4]
            weapons_filter.add(clean)
    else:
        weapons_filter = None

    for t in teams_to_scan:
        for m in discovered.get(t, []):
            m_path = Path(m["path"]).resolve()
            if m_path in seen_paths:
                continue

            if weapons_filter and m["weapon"].lower() not in weapons_filter:
                continue

            if include_only_modified and not m.get("has_orig_backup", False):
                continue

            seen_paths.add(m_path)
            selected_models.append(m)

    buf = io.BytesIO()
    manifest_models = []

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for m in selected_models:
            src_file = Path(m["path"])
            if not src_file.is_file():
                continue

            try:
                rel = src_file.relative_to(root)
                arcname = str(rel).replace("\\", "/")
            except ValueError:
                arcname = f"cstrike/models/custom_skins/{m['team']}/{src_file.name}"

            zf.write(src_file, arcname=arcname)
            manifest_models.append({
                "weapon": m["weapon"],
                "team": m["team"],
                "model_name": src_file.name,
                "archive_path": arcname,
                "size_bytes": src_file.stat().st_size,
                "has_orig_backup": m.get("has_orig_backup", False),
            })

        if include_amxx_configs:
            amxx_configs = [
                root / "cstrike" / "addons" / "amxmodx" / "configs" / "skin_inventory.ini",
                root / "cstrike" / "addons" / "amxmodx" / "configs" / "active_loadout.ini",
            ]
            for cfg_f in amxx_configs:
                if cfg_f.is_file():
                    rel_cfg = f"cstrike/addons/amxmodx/configs/{cfg_f.name}"
                    zf.write(cfg_f, arcname=rel_cfg)

        if include_pw_models:
            pw_dir = root / "cstrike" / "models" / "pw_models"
            if pw_dir.is_dir():
                for mdl in sorted(pw_dir.glob("*.mdl")):
                    if not mdl.name.endswith(".bak") and not mdl.name.endswith(".orig.mdl"):
                        rel_pw = f"cstrike/models/pw_models/{mdl.name}"
                        zf.write(mdl, arcname=rel_pw)

        if include_sounds:
            snd_dir = root / "cstrike" / "sound" / "weapons" / "csgo"
            if snd_dir.is_dir():
                for wav in sorted(snd_dir.rglob("*.wav")):
                    try:
                        rel_snd = str(wav.relative_to(root)).replace("\\", "/")
                    except ValueError:
                        rel_snd = f"cstrike/sound/weapons/csgo/{wav.name}"
                    zf.write(wav, arcname=rel_snd)

        manifest = {
            "pack_name": pack_name,
            "created_at": datetime.now().isoformat(),
            "target_game": "Counter-Strike 1.6 (GoldSrc IDST v10)",
            "model_count": len(manifest_models),
            "team_filter": team,
            "include_amxx_configs": include_amxx_configs,
            "include_pw_models": include_pw_models,
            "include_sounds": include_sounds,
            "models": manifest_models,
        }
        zf.writestr("modpack_manifest.json", json.dumps(manifest, indent=2))

        readme_text = f"""========================================================================
CS 1.6 Asset Studio - Custom Weapon Mod Pack
Pack Name: {pack_name}
Created: {manifest['created_at']}
Total Models: {len(manifest_models)}
========================================================================

INSTALLATION INSTRUCTIONS:
1. Extract the contents of this ZIP archive directly into your Counter-Strike 1.6
   game installation directory (the folder containing hl.exe and the 'cstrike' folder).
2. If prompted, overwrite existing model files.
3. Launch Counter-Strike 1.6 and enjoy your customized weapon skins, stickers,
   and StatTrak LED counters!

========================================================================
MODELS INCLUDED:
"""
        for item in manifest_models:
            readme_text += f"- [{item['team'].upper()}] {item['weapon'].upper()} -> {item['archive_path']}\n"

        readme_text += "\nGenerated with CS 1.6 Asset Studio Pro.\n"
        zf.writestr("README_MODPACK.txt", readme_text)

    zip_bytes = buf.getvalue()
    return zip_bytes, manifest
