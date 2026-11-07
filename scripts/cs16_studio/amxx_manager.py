"""
amxx_manager.py - Core integration module between CS:GO AMXX weapon system and Asset Studio Pro.
Integrated with EmptyX Customization config_manager.
Handles:
1. Parsing skin catalog from cstrike/addons/amxmodx/configs/skin_inventory.ini
2. Reading and updating in-game active loadout in active_loadout.ini
3. Synchronizing Viewmodel (v_*.mdl) textures & decals into Player (p_*.mdl) and World (w_*.mdl) models
4. Serving CS:GO audio effects
"""

import os
from pathlib import Path
import re
import shutil
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image

from .image_pipeline import quantize_goldsrc
from .mdl_core import MdlModel, resolve_model_path, ROLE_SKIN, ROLE_GLOVE
from .pw_restore import find_model_backup, get_model_backup_path
from .pw_restore import find_model_backup, get_model_backup_path
from .config_manager import config

SKIN_INVENTORY_REL = Path("cstrike") / "addons" / "amxmodx" / "configs" / "skin_inventory.ini"
ACTIVE_LOADOUT_REL = Path("cstrike") / "addons" / "amxmodx" / "configs" / "active_loadout.ini"
PW_MODELS_DIR_REL = Path("cstrike") / "models" / "pw_models"
SOUNDS_DIR_REL = Path("cstrike") / "sound"

# Canonical AMXX slot keys
SLOT_SECTION_TO_LOADOUT = {
    "KNIVES": "KNIFE",
    "KNIFE": "KNIFE",
}

# Mapping from weapon identifier or variant to AMXX slot key
WEAPON_TO_SLOT = {
    # Knives
    "knife": "KNIFE",
    "knife_m9": "KNIFE",
    "knife_karambit": "KNIFE",
    "knife_butterfly": "KNIFE",
    "knife_huntsman": "KNIFE",
    "knife_bayonet": "KNIFE",
    # Rifles
    "m4a1": "M4A1",
    "m4a4": "M4A1",
    "ak47": "AK47",
    "awp": "AWP",
    "scout": "SCOUT",
    "galil": "GALIL",
    "famas": "FAMAS",
    "sg552": "SG552",
    "aug": "AUG",
    "g3sg1": "G3SG1",
    "sg550": "SG550",
    # SMGs
    "mp5": "MP5NAVY",
    "mp7": "MP5NAVY",
    "p90": "P90",
    "bizon": "P90",
    "ump45": "UMP45",
    "mac10": "MAC10",
    "cz75_mac10": "MAC10",
    "tmp": "TMP",
    "cz75_tmp": "TMP",
    "cz75": "TMP",  # Default CT CZ75 replaces TMP slot
    # Heavy
    "xm1014": "XM1014",
    "mag7": "XM1014",
    "m3": "M3",
    "sawedoff": "M3",
    "m249": "M249",
    "negev": "M249",
    # Pistols
    "usp": "USP",
    "glock18": "GLOCK18",
    "deagle": "DEAGLE",
    "p228": "P228",
    "tec9": "P228",
    "elite": "ELITE",
    "elites": "ELITE",
    "fiveseven": "FIVESEVEN",
}


def _clean_weapon_key(weapon: str) -> str:
    w = str(weapon).strip().lower()
    if w.endswith(".mdl"):
        w = w[:-4]
    if w.startswith("v_") or w.startswith("p_") or w.startswith("w_"):
        w = w[2:]
    return w


def parse_skin_inventory(inventory_path: Union[str, Path]) -> dict:
    """
    Parses skin_inventory.ini into structured catalog by team and slot.
    Format:
    [CT_M4A1]
    "M4A4 (Custom)" "models/custom_skins/ct/v_m4a4.mdl" "models/pw_models/p_m4a4.mdl" "models/pw_models/w_m4a4.mdl" "weapons/csgo/m4a4/m4a4-1.wav"
    """
    p = Path(inventory_path)
    if not p.is_file():
        return {"ct": {}, "t": {}, "raw_sections": {}}

    result = {"ct": {}, "t": {}, "raw_sections": {}}
    current_section = None
    current_team = None
    current_slot = None

    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line_str = line.strip()
            if not line_str or line_str.startswith(";"):
                continue

            sec_match = re.match(r"^\[([A-Za-z0-9_]+)\]$", line_str)
            if sec_match:
                current_section = sec_match.group(1).upper()
                if current_section.startswith("CT_"):
                    current_team = "ct"
                    sec_slot = current_section[3:]
                elif current_section.startswith("T_"):
                    current_team = "t"
                    sec_slot = current_section[2:]
                else:
                    current_team = None
                    sec_slot = current_section

                canonical_slot = SLOT_SECTION_TO_LOADOUT.get(sec_slot, sec_slot)
                current_slot = canonical_slot

                if current_team:
                    if current_slot not in result[current_team]:
                        result[current_team][current_slot] = []
                if current_section not in result["raw_sections"]:
                    result["raw_sections"][current_section] = []
                continue

            tokens = re.findall(r'"([^"]*)"', line_str)
            if len(tokens) >= 2:
                display_name = tokens[0]
                v_model = tokens[1]
                p_model = tokens[2] if len(tokens) > 2 else ""
                w_model = tokens[3] if len(tokens) > 3 else ""
                sounds = tokens[4:] if len(tokens) > 4 else []

                v_filename = Path(v_model).name
                w_key = _clean_weapon_key(v_filename)

                entry = {
                    "display_name": display_name,
                    "v_model": v_model,
                    "p_model": p_model,
                    "w_model": w_model,
                    "sounds": sounds,
                    "weapon_key": w_key,
                    "section": current_section,
                }

                if current_team and current_slot:
                    result[current_team][current_slot].append(entry)
                if current_section:
                    result["raw_sections"][current_section].append(entry)

    return result


def parse_active_loadout(loadout_path: Union[str, Path]) -> dict:
    """
    Parses active_loadout.ini into dictionary of active slots per team.
    Format:
    [CT_ACTIVE]
    KNIFE = "models/custom_skins/ct/v_knife.mdl"
    M4A1  = "models/custom_skins/ct/v_m4a4.mdl"
    """
    p = Path(loadout_path)
    if not p.is_file():
        return {"ct": {}, "t": {}}

    loadout = {"ct": {}, "t": {}}
    current_team = None

    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line_str = line.strip()
            if not line_str or line_str.startswith(";"):
                continue

            sec_match = re.match(r"^\[([A-Za-z0-9_]+)\]$", line_str)
            if sec_match:
                sec_name = sec_match.group(1).upper()
                if sec_name in ("CT_ACTIVE", "CT"):
                    current_team = "ct"
                elif sec_name in ("T_ACTIVE", "T"):
                    current_team = "t"
                else:
                    current_team = None
                continue

            if not current_team:
                continue

            kv_match = re.match(r"^([A-Za-z0-9_]+)\s*=\s*\"?([^\";\r\n]+)\"?$", line_str)
            if kv_match:
                slot_key = kv_match.group(1).upper()
                val = kv_match.group(2).strip().strip('"')
                loadout[current_team][slot_key] = val

    return loadout


def set_active_loadout(
    loadout_path: Optional[Union[str, Path]] = None,
    team: str = "ct",
    weapon: str = "usp",
    model_path: Optional[str] = None,
    slot: Optional[str] = None,
    root_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Sets active loadout weapon for a team in active_loadout.ini.
    Defaults root_dir to config.get_game_root().
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    p = Path(loadout_path) if loadout_path else (root / ACTIVE_LOADOUT_REL)
    team_clean = team.lower().strip()
    w_clean = _clean_weapon_key(weapon)

    if not slot:
        if w_clean == "cz75":
            target_slot = "MAC10" if team_clean == "t" else "TMP"
        else:
            target_slot = WEAPON_TO_SLOT.get(w_clean, w_clean.upper())
    else:
        target_slot = slot.upper()

    target_slot = target_slot.upper()

    # If model_path was not explicitly provided, look up the canonical path
    if not model_path:
        inv_file = root / SKIN_INVENTORY_REL
        if not inv_file.is_file():
            inv_file = p.parent / "skin_inventory.ini"

        if inv_file.is_file():
            catalog = parse_skin_inventory(inv_file)
            entries = catalog.get(team_clean, {}).get(target_slot, [])
            for e in entries:
                if e.get("weapon_key") == w_clean:
                    model_path = e.get("v_model")
                    break

            if not model_path:
                for t_key in (team_clean, "ct" if team_clean == "t" else "t"):
                    for s_key, s_entries in catalog.get(t_key, {}).items():
                        for e in s_entries:
                            if e.get("weapon_key") == w_clean:
                                model_path = e.get("v_model")
                                break
                        if model_path:
                            break
                    if model_path:
                        break

        if not model_path:
            try:
                resolved = resolve_model_path(w_clean, team=team_clean, root_dir=root)
                if resolved and resolved.is_file():
                    cstrike_dir = root / "cstrike"
                    if cstrike_dir in resolved.parents:
                        model_path = str(resolved.relative_to(cstrike_dir)).replace("\\", "/")
                    elif root in resolved.parents:
                        model_path = str(resolved.relative_to(root)).replace("\\", "/")
                    else:
                        model_path = f"models/custom_skins/{team_clean}/{resolved.name}"
            except Exception:
                pass

        if not model_path:
            model_path = f"models/custom_skins/{team_clean}/v_{w_clean}.mdl"

    section_header = f"[{team_clean.upper()}_ACTIVE]"

    lines: List[str] = []
    if p.is_file():
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "; ==============================================================================\n",
            "; CS2 ACTIVE LOADOUT CONFIGURATION\n",
            "; Synchronized automatically by CS 1.6 Asset Studio Pro\n",
            "; ==============================================================================\n\n",
            "[CT_ACTIVE]\n",
            "\n",
            "[T_ACTIVE]\n",
            "\n",
        ]

    in_section = False
    section_found = False
    slot_replaced = False
    new_lines = []
    target_entry = f"{target_slot:<8} = \"{model_path}\"\n"

    for line in lines:
        stripped = line.strip()
        sec_match = re.match(r"^\[([A-Za-z0-9_]+)\]$", stripped)
        if sec_match:
            sec_name = sec_match.group(1).upper()
            if in_section:
                if not slot_replaced:
                    new_lines.append(target_entry)
                    slot_replaced = True
                in_section = False

            if sec_name == f"{team_clean.upper()}_ACTIVE" or sec_name == team_clean.upper():
                in_section = True
                section_found = True
            new_lines.append(line)
            continue

        if in_section:
            kv_match = re.match(r"^([A-Za-z0-9_]+)\s*=", stripped)
            if kv_match and kv_match.group(1).upper() == target_slot:
                new_lines.append(target_entry)
                slot_replaced = True
                continue

        new_lines.append(line)

    if in_section and not slot_replaced:
        new_lines.append(target_entry)
        slot_replaced = True

    if not section_found:
        new_lines.append(f"\n{section_header}\n")
        new_lines.append(target_entry)

    temp_path = p.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    shutil.move(temp_path, p)

    return {
        "success": True,
        "team": team_clean,
        "slot": target_slot,
        "weapon": w_clean,
        "model_path": model_path,
        "message": f"Successfully equipped {w_clean.upper()} ({model_path}) for {team_clean.upper()} loadout.",
    }


def find_weapon_audio(root_dir: Optional[Union[str, Path]] = None, weapon_or_path: str = "") -> Optional[Path]:
    """
    Safely resolves sound file path inside game root.
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    sounds_base = root / SOUNDS_DIR_REL
    clean_input = str(weapon_or_path).replace("\\", "/").strip()

    if clean_input.lower().endswith(".wav"):
        if clean_input.startswith("sound/"):
            cand = root / "cstrike" / clean_input
        elif clean_input.startswith("cstrike/"):
            cand = root / clean_input
        else:
            cand = sounds_base / clean_input

        try:
            cand_res = cand.resolve()
            if cand_res.is_file() and (root in cand_res.parents or sounds_base in cand_res.parents):
                return cand_res
        except Exception:
            pass

    inv_file = root / SKIN_INVENTORY_REL
    if inv_file.is_file():
        w_clean = _clean_weapon_key(weapon_or_path)
        catalog = parse_skin_inventory(inv_file)
        for team in ("ct", "t"):
            for slot, entries in catalog.get(team, {}).items():
                for entry in entries:
                    if entry.get("weapon_key") == w_clean and entry.get("sounds"):
                        first_sound = entry["sounds"][0]
                        cand = sounds_base / first_sound
                        try:
                            cand_res = cand.resolve()
                            if cand_res.is_file():
                                return cand_res
                        except Exception:
                            pass

    w_clean = _clean_weapon_key(weapon_or_path)
    weapon_snd_dir = sounds_base / "weapons" / "csgo" / w_clean
    if weapon_snd_dir.is_dir():
        wavs = sorted(weapon_snd_dir.glob("*.wav"))
        if wavs:
            return wavs[0].resolve()

    csgo_dir = sounds_base / "weapons" / "csgo"
    if csgo_dir.is_dir():
        for d in sorted(csgo_dir.iterdir()):
            if d.is_dir() and d.name.lower().startswith(w_clean):
                wavs = sorted(d.glob("*.wav"))
                if wavs:
                    return wavs[0].resolve()

    return None


def get_amxx_catalog(root_dir: Optional[Union[str, Path]] = None) -> dict:
    """
    Returns unified catalog of weapons, variants, active status, and audio.
    Used by frontend Visual Loadout Drawer. Defaults root_dir to config.get_game_root().
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    inv_path = root / SKIN_INVENTORY_REL
    loadout_path = root / ACTIVE_LOADOUT_REL

    inventory_data = parse_skin_inventory(inv_path) if inv_path.is_file() else {"ct": {}, "t": {}}
    active_loadout = parse_active_loadout(loadout_path) if loadout_path.is_file() else {"ct": {}, "t": {}}

    categories = {
        "gear": {
            "label": "Equipment & Knives",
            "icon": "gear-knife",
            "slots": ["KNIFE", "C4", "FLASHBANG", "HEGRENADE", "SMOKEGRENADE"],
        },
        "rifles": {
            "label": "Rifles & Snipers",
            "icon": "rifle",
            "slots": ["M4A1", "AK47", "AWP", "SCOUT", "GALIL", "FAMAS", "SG552", "AUG", "G3SG1", "SG550"],
        },
        "smgs": {
            "label": "SMGs",
            "icon": "smg",
            "slots": ["MP5NAVY", "P90", "UMP45", "MAC10", "TMP"],
        },
        "heavy": {
            "label": "Heavy",
            "icon": "heavy",
            "slots": ["XM1014", "M3", "M249"],
        },
        "pistols": {
            "label": "Pistols",
            "icon": "weapon",
            "slots": ["USP", "GLOCK18", "DEAGLE", "P228", "ELITE", "FIVESEVEN"],
        },
    }

    def model_exists(rel_path: Optional[str]) -> bool:
        if not rel_path:
            return False
        return (root / "cstrike" / rel_path).is_file() or (root / rel_path).is_file()

    teams_catalog = {"ct": {}, "t": {}}

    for team in ("ct", "t"):
        team_inv = inventory_data.get(team, {})
        team_loadout = active_loadout.get(team, {})

        all_slots = set(list(WEAPON_TO_SLOT.values()) + list(team_inv.keys()) + list(team_loadout.keys()))

        for slot in sorted(all_slots):
            entries = team_inv.get(slot, [])
            active_model = team_loadout.get(slot, "")

            variants = []
            seen_weapons = set()

            for e in entries:
                w_key = e["weapon_key"]
                seen_weapons.add(w_key)
                is_active = (e["v_model"] == active_model) or (
                    active_model.endswith(f"v_{w_key}.mdl")
                )
                variants.append({
                    "weapon_key": w_key,
                    "label": e["display_name"],
                    "v_model": e["v_model"],
                    "p_model": e["p_model"],
                    "w_model": e["w_model"],
                    "sounds": e["sounds"],
                    "is_active": is_active,
                    "v_exists": model_exists(e["v_model"]),
                    "p_exists": model_exists(e["p_model"]),
                    "w_exists": model_exists(e["w_model"]),
                })

            if not variants:
                default_w = slot.lower()
                is_active = bool(active_model and default_w in active_model.lower())
                variants.append({
                    "weapon_key": default_w,
                    "label": slot,
                    "v_model": f"models/custom_skins/{team}/v_{default_w}.mdl",
                    "p_model": f"models/pw_models/p_{default_w}.mdl",
                    "w_model": f"models/pw_models/w_{default_w}.mdl",
                    "sounds": [],
                    "is_active": is_active,
                    "v_exists": model_exists(f"models/custom_skins/{team}/v_{default_w}.mdl"),
                    "p_exists": model_exists(f"models/pw_models/p_{default_w}.mdl"),
                    "w_exists": model_exists(f"models/pw_models/w_{default_w}.mdl"),
                })

            teams_catalog[team][slot] = {
                "slot": slot,
                "active_model": active_model,
                "variants": variants,
            }

    return {
        "success": True,
        "categories": categories,
        "catalog": teams_catalog,
        "active_loadout": active_loadout,
    }


def sync_pw_models(
    root_dir: Optional[Union[str, Path]] = None,
    weapon: str = "usp",
    team: str = "ct",
    auto_backup: bool = True,
    v_model_path: Optional[Union[str, Path]] = None,
    p_model_path: Optional[Union[str, Path]] = None,
    w_model_path: Optional[Union[str, Path]] = None,
    include_stickers: bool = False,
    sync_p: bool = True,
    sync_w: bool = True,
) -> dict:
    """
    Bakes viewmodel (v_*.mdl) textures & decals and injects into corresponding
    p_*.mdl and w_*.mdl in cstrike/models/pw_models/.
    Defaults root_dir to config.get_game_root().
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    w_clean = _clean_weapon_key(weapon)
    team_clean = team.lower().strip()

    # 1. Resolve Viewmodel Path
    if v_model_path:
        cand_v = Path(v_model_path)
        if cand_v.is_file():
            v_path = cand_v.resolve()
        elif (root / cand_v).is_file():
            v_path = (root / cand_v).resolve()
        elif (root / "cstrike" / cand_v).is_file():
            v_path = (root / "cstrike" / cand_v).resolve()
        else:
            v_path = resolve_model_path(str(v_model_path), team=team_clean, root_dir=root)
    else:
        v_path = resolve_model_path(w_clean, team=team_clean, root_dir=root)

    if not v_path.is_file():
        raise FileNotFoundError(f"Viewmodel not found: {v_path}")

    inv_file = root / SKIN_INVENTORY_REL
    if not inv_file.is_file():
        inv_file = root / "cstrike" / "addons" / "amxmodx" / "configs" / "skin_inventory.ini"
    catalog = parse_skin_inventory(inv_file) if inv_file.is_file() else {}
    target_entry = None

    target_slot_key = WEAPON_TO_SLOT.get(w_clean, w_clean.upper())
    for entry in catalog.get(team_clean, {}).get(target_slot_key, []):
        if entry.get("weapon_key") == w_clean:
            target_entry = entry
            break

    if not target_entry:
        other_team = "t" if team_clean == "ct" else "ct"
        for s_key, entries in catalog.get(other_team, {}).items():
            for entry in entries:
                if entry.get("weapon_key") == w_clean:
                    target_entry = entry
                    break
            if target_entry:
                break

    pw_dir = root / PW_MODELS_DIR_REL
    if not pw_dir.is_dir():
        pw_dir = root / "cstrike" / "models" / "pw_models"

    def resolve_target(custom_p, entry_key, prefix):
        if custom_p:
            cand = Path(custom_p)
            if cand.is_file():
                return cand.resolve()
            if (root / cand).is_file():
                return (root / cand).resolve()
            if (root / "cstrike" / cand).is_file():
                return (root / "cstrike" / cand).resolve()
            return None
        if target_entry and target_entry.get(entry_key):
            cand = root / "cstrike" / target_entry[entry_key]
            if cand.is_file():
                return cand.resolve()
            cand2 = root / target_entry[entry_key]
            if cand2.is_file():
                return cand2.resolve()

        search_dirs = [pw_dir]
        for extra in [root / "cstrike" / "models", root / "cstrike_hd" / "models"]:
            if extra.is_dir() and extra not in search_dirs:
                search_dirs.append(extra)

        for sdir in search_dirs:
            direct = sdir / f"{prefix}_{w_clean}.mdl"
            if direct.is_file():
                return direct.resolve()
            if "knife" in w_clean:
                knife_cand = sdir / f"{prefix}_knife.mdl"
                if knife_cand.is_file():
                    return knife_cand.resolve()
            if "cz75" in w_clean:
                cz_cand = sdir / f"{prefix}_cz75.mdl"
                if cz_cand.is_file():
                    return cz_cand.resolve()

        return None

    resolved_p = resolve_target(p_model_path, "p_model", "p")
    resolved_w = resolve_target(w_model_path, "w_model", "w")

    if not resolved_p and not resolved_w:
        raise FileNotFoundError(
            f"Neither Player model (p_) nor World model (w_) found for weapon '{w_clean}' in {pw_dir}"
        )

    v_model = MdlModel(v_path)
    skins = v_model.get_skins()
    if skins:
        base_tex = max(skins, key=lambda t: t.width * t.height)
    else:
        non_gloves = [t for t in v_model.textures if t.role != ROLE_GLOVE]
        if not non_gloves:
            raise ValueError(f"No weapon texture found in {v_path.name}")
        base_tex = max(non_gloves, key=lambda t: t.width * t.height)

    composites_by_name = {}
    for st in v_model.textures:
        if st.role == ROLE_GLOVE:
            continue
        st_name_lower = st.name.lower()
        is_submesh_or_decal = st.is_masked and (
            "decal" in st_name_lower
            or "sticker" in st_name_lower
            or st.name.replace(".bmp", "").isdigit()
            or st_name_lower.startswith("st_")
            or st_name_lower.startswith("slot_")
        )
        if is_submesh_or_decal and st.index != base_tex.index:
            continue

        comp_rgba = st.to_rgba_image()
        w_st, h_st = st.width, st.height

        for dt in v_model.textures:
            if dt.index == st.index:
                continue
            dt_name_lower = dt.name.lower()
            is_sticker_slot = (
                "sticker" in dt_name_lower
                or dt.name.replace(".bmp", "").isdigit()
                or dt_name_lower.startswith("st_")
                or dt_name_lower.startswith("slot_")
            )
            if is_sticker_slot and not include_stickers:
                continue

            is_decal = "decal" in dt_name_lower and not is_sticker_slot
            if is_decal and dt.width == w_st and dt.height == h_st:
                dec_img = dt.to_rgba_image()
                comp_rgba = Image.alpha_composite(comp_rgba, dec_img)

        composites_by_name[st.name.lower()] = comp_rgba

    base_rgba = composites_by_name.get(base_tex.name.lower(), base_tex.to_rgba_image())

    results = {
        "success": True,
        "weapon": w_clean,
        "team": team_clean,
        "base_texture": base_tex.name,
        "p_model": str(resolved_p) if resolved_p else None,
        "w_model": str(resolved_w) if resolved_w else None,
        "p_injected": False,
        "w_injected": False,
    }

    def inject_target(mdl_path: Path) -> bool:
        if not mdl_path or not mdl_path.is_file():
            return False

        if auto_backup:
            existing_bak, _ = find_model_backup(mdl_path)
            if not existing_bak:
                bak_path = get_model_backup_path(mdl_path, ext=".orig.mdl")
                shutil.copy2(mdl_path, bak_path)

        target_model = MdlModel(mdl_path)
        if not target_model.textures:
            return False

        injected_any = False

        for t in target_model.textures:
            t_lower = t.name.lower()
            if t_lower in composites_by_name:
                rgba_src = composites_by_name[t_lower]
                if rgba_src.width != t.width or rgba_src.height != t.height:
                    resized = rgba_src.resize((t.width, t.height), Image.Resampling.LANCZOS)
                else:
                    resized = rgba_src

                pix_bytes, pal_bytes = quantize_goldsrc(resized, is_masked=t.is_masked)
                target_model.inject_texture_payload(t, pix_bytes + pal_bytes)
                injected_any = True

        if not injected_any:
            target_tex = None
            if len(target_model.textures) == 1:
                target_tex = target_model.textures[0]
            if not target_tex:
                tgt_skins = target_model.get_skins()
                if tgt_skins:
                    target_tex = max(tgt_skins, key=lambda t: t.width * t.height)
            if not target_tex:
                tgt_non_gloves = [t for t in target_model.textures if t.role != ROLE_GLOVE]
                if tgt_non_gloves:
                    target_tex = max(tgt_non_gloves, key=lambda t: t.width * t.height)

            if target_tex:
                if base_rgba.width != target_tex.width or base_rgba.height != target_tex.height:
                    resized_rgba = base_rgba.resize(
                        (target_tex.width, target_tex.height), Image.Resampling.LANCZOS
                    )
                else:
                    resized_rgba = base_rgba

                pix_bytes, pal_bytes = quantize_goldsrc(resized_rgba, is_masked=target_tex.is_masked)
                target_model.inject_texture_payload(target_tex, pix_bytes + pal_bytes)
                injected_any = True

        if injected_any:
            target_model.save_atomic(create_backup=auto_backup)
            return True
        return False

    if resolved_p and sync_p:
        results["p_injected"] = inject_target(resolved_p)
    if resolved_w and sync_w:
        results["w_injected"] = inject_target(resolved_w)

    synced_names = []
    if results["p_injected"]:
        synced_names.append(f"p_{w_clean}.mdl")
    if results["w_injected"]:
        synced_names.append(f"w_{w_clean}.mdl")

    if synced_names:
        results["message"] = f"Successfully synced viewmodel textures to {', '.join(synced_names)}."
    else:
        results["message"] = "No matching textures could be injected into P/W models."

    return results


def resolve_triplet_models(
    weapon: str,
    team: str = "ct",
    root_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Resolves triplet file paths (v_, p_, w_) for the specified weapon and team.
    Returns:
        dict: {'v': Path or None, 'p': Path or None, 'w': Path or None}
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    w_clean = _clean_weapon_key(weapon)
    team_clean = team.lower().strip()

    # 1. Resolve Viewmodel (v_*.mdl)
    try:
        v_path = resolve_model_path(w_clean, team=team_clean, root_dir=root)
        if not (v_path and v_path.is_file()):
            v_path = None
    except Exception:
        v_path = None

    # 2. Check skin_inventory.ini for custom p_ and w_ model definitions
    inv_file = root / SKIN_INVENTORY_REL
    if not inv_file.is_file():
        inv_file = root / "cstrike" / "addons" / "amxmodx" / "configs" / "skin_inventory.ini"
    catalog = parse_skin_inventory(inv_file) if inv_file.is_file() else {}
    target_entry = None

    target_slot_key = WEAPON_TO_SLOT.get(w_clean, w_clean.upper())
    for entry in catalog.get(team_clean, {}).get(target_slot_key, []):
        if entry.get("weapon_key") == w_clean:
            target_entry = entry
            break

    if not target_entry:
        other_team = "t" if team_clean == "ct" else "ct"
        for s_key, entries in catalog.get(other_team, {}).items():
            for entry in entries:
                if entry.get("weapon_key") == w_clean:
                    target_entry = entry
                    break
            if target_entry:
                break

    pw_dir = root / PW_MODELS_DIR_REL
    if not pw_dir.is_dir():
        pw_dir = root / "cstrike" / "models" / "pw_models"

    def find_target(entry_key: str, prefix: str) -> Optional[Path]:
        if target_entry and target_entry.get(entry_key):
            cand = root / "cstrike" / target_entry[entry_key]
            if cand.is_file():
                return cand.resolve()
            cand2 = root / target_entry[entry_key]
            if cand2.is_file():
                return cand2.resolve()

        search_dirs = [pw_dir]
        for extra in [root / "cstrike" / "models", root / "cstrike_hd" / "models"]:
            if extra.is_dir() and extra not in search_dirs:
                search_dirs.append(extra)

        for sdir in search_dirs:
            direct = sdir / f"{prefix}_{w_clean}.mdl"
            if direct.is_file():
                return direct.resolve()
            if "knife" in w_clean:
                knife_cand = sdir / f"{prefix}_knife.mdl"
                if knife_cand.is_file():
                    return knife_cand.resolve()
            if "cz75" in w_clean:
                cz_cand = sdir / f"{prefix}_cz75.mdl"
                if cz_cand.is_file():
                    return cz_cand.resolve()
        return None

    p_path = find_target("p_model", "p")
    w_path = find_target("w_model", "w")

    return {
        "v": v_path,
        "p": p_path,
        "w": w_path,
    }


def get_triplet_status(
    weapon: str,
    team: str = "ct",
    root_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Returns real-time sync telemetry for weapon triplets (v_, p_, w_).
    """
    import datetime
    triplets = resolve_triplet_models(weapon=weapon, team=team, root_dir=root_dir)
    w_clean = _clean_weapon_key(weapon)
    team_clean = team.lower().strip()

    v_path = triplets.get("v")
    p_path = triplets.get("p")
    w_path = triplets.get("w")

    v_mtime = v_path.stat().st_mtime if v_path and v_path.is_file() else 0.0

    def get_info(path: Optional[Path], prefix: str) -> dict:
        if not path or not path.is_file():
            return {
                "name": f"{prefix}_{w_clean}.mdl",
                "path": str(path) if path else None,
                "exists": False,
                "size_kb": 0,
                "mtime": 0,
                "mtime_str": "Not Found",
                "has_backup": False,
                "synced": False,
                "status": "MISSING",
            }

        st = path.stat()
        mtime = st.st_mtime
        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        size_kb = round(st.st_size / 1024, 1)

        has_bak = find_model_backup(path)[0] is not None

        if prefix == "v":
            synced = True
            status = "ACTIVE"
        else:
            synced = (mtime >= v_mtime - 2.0) if v_mtime > 0 else True
            status = "SYNCED" if synced else "PENDING"

        return {
            "name": path.name,
            "path": str(path),
            "exists": True,
            "size_kb": size_kb,
            "mtime": mtime,
            "mtime_str": mtime_str,
            "has_backup": has_bak,
            "synced": synced,
            "status": status,
        }

    return {
        "success": True,
        "weapon": w_clean,
        "team": team_clean,
        "v_model": get_info(v_path, "v"),
        "p_model": get_info(p_path, "p"),
        "w_model": get_info(w_path, "w"),
    }
