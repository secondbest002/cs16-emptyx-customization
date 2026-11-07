"""
inventory_manager.py - Core Skin Inventory & Vault Manager for CS 1.6 Asset Studio Pro.
Integrated with EmptyX Customization config_manager and amxx_manager.

Provides:
1. Saving customized viewmodels (v_*.mdl) and knives into a persistent Skin Inventory Vault.
2. Synchronizing matching player (p_*.mdl) and world (w_*.mdl) models alongside viewmodels.
3. Decoupling weapon skins from glove textures (Dual-Mode Glove Swapping Mitigation Engine).
4. Auto-Glove Synchronization on Equip (adapts hands to current active loadout gloves).
5. 1-Click Batch Glove Synchronization across the entire inventory vault.
6. Optional registration into CS 1.6 AMXX in-game menu (skin_inventory.ini) and active loadout (active_loadout.ini).
"""

import base64
from datetime import datetime
import io
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image

from .config_manager import config
from .mdl_core import (
    STUDIO_NF_CHROME,
    STUDIO_NF_MASKED,
    MdlModel,
    ROLE_GLOVE,
    ROLE_SKIN,
    ROLE_STICKER,
    ROLE_STATTRAK,
    classify_texture,
    resolve_model_path,
)
from .glove_transfer import (
    classify_glove_role,
    transfer_gloves,
    load_glove_preset,
    _load_image_input,
)
from .amxx_manager import (
    SKIN_INVENTORY_REL,
    ACTIVE_LOADOUT_REL,
    WEAPON_TO_SLOT,
    _clean_weapon_key,
    set_active_loadout,
    sync_pw_models,
)
from .image_pipeline import quantize_goldsrc

INVENTORY_SUBDIR = Path("cstrike") / "models" / "custom_skins" / "inventory"
ACTIVE_EQUIPPED_FILE = ".active_equipped.json"


def get_inventory_dir(root_dir: Optional[Union[str, Path]] = None) -> Path:
    """Returns and ensures the inventory vault directory exists in the game folder."""
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    inv_dir = root / INVENTORY_SUBDIR
    inv_dir.mkdir(parents=True, exist_ok=True)
    return inv_dir


def _load_active_equipped(root_dir: Optional[Union[str, Path]] = None) -> dict:
    """Loads current vault skin assignments per team and weapon slot."""
    inv_dir = get_inventory_dir(root_dir)
    f = inv_dir / ACTIVE_EQUIPPED_FILE
    if f.is_file():
        try:
            with open(f, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:
            pass
    return {"ct": {}, "t": {}}


def _save_active_equipped(data: dict, root_dir: Optional[Union[str, Path]] = None):
    """Saves active vault skin assignments."""
    inv_dir = get_inventory_dir(root_dir)
    f = inv_dir / ACTIVE_EQUIPPED_FILE
    with open(f, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2)


def slugify(text: str) -> str:
    """Generates a safe filesystem slug from a skin name."""
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "_", s)
    return s.strip("_") or "skin_custom"


def is_knife_model(weapon_or_path: str) -> bool:
    """Detects whether weapon identifier or model filename represents a knife."""
    lower = str(weapon_or_path).lower()
    return "knife" in lower or lower.startswith("v_knife")


def detect_knife_variant(model_name_or_path: str) -> Optional[str]:
    """Identifies the knife variant (karambit, m9, butterfly, bayonet, huntsman, default)."""
    lower = str(model_name_or_path).lower()
    for variant in ("karambit", "butterfly", "m9", "bayonet", "huntsman", "bowie", "falchion", "daggers", "flip", "gut"):
        if variant in lower:
            return variant
    if "knife" in lower:
        return "knife_default"
    return None


def extract_skin_metadata(model: MdlModel) -> dict:
    """Extracts stickers, gloves, and StatTrak information from an in-memory MdlModel."""
    stickers = []
    glove_slots = []
    has_stattrak = False
    skin_slots = []

    for t in model.textures:
        role, _ = classify_texture(t.name, t.flags, t.width, t.height)
        glove_role = classify_glove_role(t.name)

        if glove_role or role == ROLE_GLOVE:
            glove_slots.append({
                "name": t.name,
                "role": glove_role or "glove",
                "width": t.width,
                "height": t.height,
            })
        elif role == ROLE_STICKER:
            stickers.append({
                "name": t.name,
                "width": t.width,
                "height": t.height,
                "flags": t.flags,
                "is_chrome": bool(t.flags & STUDIO_NF_CHROME),
                "is_masked": bool(t.flags & STUDIO_NF_MASKED),
            })
        elif role == ROLE_STATTRAK:
            has_stattrak = True
        elif role == ROLE_SKIN:
            skin_slots.append(t.name)

    return {
        "sticker_count": len(stickers),
        "stickers": stickers,
        "glove_slot_count": len(glove_slots),
        "glove_slots": glove_slots,
        "has_stattrak": has_stattrak,
        "skin_slots": skin_slots,
    }


def add_to_skin_inventory_ini(
    display_name: str,
    v_model_rel: str,
    p_model_rel: str = "",
    w_model_rel: str = "",
    team: str = "ct",
    weapon_key: str = "ak47",
    root_dir: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Registers a skin entry into cstrike/addons/amxmodx/configs/skin_inventory.ini.
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    inv_ini = root / SKIN_INVENTORY_REL
    if not inv_ini.parent.is_dir():
        inv_ini.parent.mkdir(parents=True, exist_ok=True)

    team_upper = team.upper().strip()
    w_clean = _clean_weapon_key(weapon_key)

    if is_knife_model(w_clean):
        section_name = f"{team_upper}_KNIVES"
    else:
        slot = WEAPON_TO_SLOT.get(w_clean, w_clean.upper())
        section_name = f"{team_upper}_{slot}"

    v_clean = str(v_model_rel).replace("\\", "/").lstrip("/")
    p_clean = str(p_model_rel).replace("\\", "/").lstrip("/") if p_model_rel else "models/pw_models/p_knife.mdl" if is_knife_model(w_clean) else f"models/pw_models/p_{w_clean}.mdl"
    w_clean_path = str(w_model_rel).replace("\\", "/").lstrip("/") if w_model_rel else "models/pw_models/w_knife.mdl" if is_knife_model(w_clean) else f"models/pw_models/w_{w_clean}.mdl"

    entry_line = f'"{display_name}" "{v_clean}" "{p_clean}" "{w_clean_path}"\n'

    lines = []
    if inv_ini.is_file():
        with open(inv_ini, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

    in_section = False
    section_found = False
    entry_replaced = False
    new_lines = []

    for line in lines:
        stripped = line.strip()
        sec_m = re.match(r"^\[([A-Za-z0-9_]+)\]$", stripped)
        if sec_m:
            cur_sec = sec_m.group(1).upper()
            if in_section:
                if not entry_replaced:
                    new_lines.append(entry_line)
                    entry_replaced = True
                in_section = False

            if cur_sec == section_name:
                in_section = True
                section_found = True
            new_lines.append(line)
            continue

        if in_section:
            tokens = re.findall(r'"([^"]*)"', stripped)
            if tokens:
                if tokens[0].lower() == display_name.lower() or (len(tokens) > 1 and tokens[1].lower() == v_clean.lower()):
                    new_lines.append(entry_line)
                    entry_replaced = True
                    continue

        new_lines.append(line)

    if in_section and not entry_replaced:
        new_lines.append(entry_line)
        entry_replaced = True

    if not section_found:
        new_lines.append(f"\n[{section_name}]\n")
        new_lines.append(entry_line)

    temp_ini = inv_ini.with_suffix(".tmp")
    with open(temp_ini, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    shutil.move(temp_ini, inv_ini)
    return True


def remove_from_skin_inventory_ini(
    v_model_rel: str,
    root_dir: Optional[Union[str, Path]] = None,
) -> bool:
    """Removes a skin entry from skin_inventory.ini matching the given v_model path."""
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    inv_ini = root / SKIN_INVENTORY_REL
    if not inv_ini.is_file():
        return False

    v_clean = str(v_model_rel).replace("\\", "/").lstrip("/").lower()
    with open(inv_ini, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    new_lines = []
    removed = False
    for line in lines:
        tokens = re.findall(r'"([^"]*)"', line.strip())
        if len(tokens) >= 2 and tokens[1].replace("\\", "/").lstrip("/").lower() == v_clean:
            removed = True
            continue
        new_lines.append(line)

    if removed:
        temp_ini = inv_ini.with_suffix(".tmp")
        with open(temp_ini, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        shutil.move(temp_ini, inv_ini)
    return removed


def save_to_inventory(
    name: str,
    weapon: str,
    team: str = "ct",
    source_mdl_path: Optional[Union[str, Path]] = None,
    sync_pw: bool = True,
    register_amxx: bool = False,
    equip_now: bool = False,
    thumb_b64: Optional[str] = None,
    knife_variant: Optional[str] = None,
    root_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Saves a customized viewmodel (or knife) into the Skin Inventory Vault.
    Generates v_*.mdl, p_*.mdl, w_*.mdl, manifest.json, and thumb.png.
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    inv_base = get_inventory_dir(root)

    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Skin name cannot be empty.")

    w_clean = _clean_weapon_key(weapon)
    is_knife = is_knife_model(w_clean) or is_knife_model(str(source_mdl_path or ""))

    # Resolve source model
    if source_mdl_path:
        src_path = Path(source_mdl_path).resolve()
    else:
        src_path = resolve_model_path(w_clean, team=team, root_dir=root)

    if not src_path.is_file():
        raise FileNotFoundError(f"Source model file not found: {src_path}")

    # Detect knife variant if knife
    k_var = knife_variant or detect_knife_variant(src_path.name) or detect_knife_variant(w_clean)
    category_key = "knife" if is_knife else w_clean
    slug = slugify(f"{w_clean}_{clean_name}")

    # Build unique destination folder under inventory/
    item_dir = inv_base / category_key / slug
    counter = 1
    orig_slug = slug
    while item_dir.exists() and (item_dir / "manifest.json").exists():
        counter += 1
        slug = f"{orig_slug}_{counter}"
        item_dir = inv_base / category_key / slug

    item_dir.mkdir(parents=True, exist_ok=True)

    # Copy Viewmodel
    dest_v_filename = src_path.name
    dest_v_path = item_dir / dest_v_filename
    shutil.copy2(src_path, dest_v_path)

    # Inspect model for metadata
    model_obj = MdlModel(dest_v_path)
    meta = extract_skin_metadata(model_obj)

    # Handle P and W models
    cstrike_dir = root / "cstrike"
    dest_p_path: Optional[Path] = None
    dest_w_path: Optional[Path] = None

    if sync_pw and not is_knife:
        dest_p_name = f"p_{w_clean}.mdl"
        dest_w_name = f"w_{w_clean}.mdl"
        dest_p_path = item_dir / dest_p_name
        dest_w_path = item_dir / dest_w_name

        try:
            sync_pw_models(
                root_dir=root,
                weapon=w_clean,
                team=team,
                auto_backup=False,
                v_model_path=dest_v_path,
                p_model_path=dest_p_path,
                w_model_path=dest_w_path,
                sync_p=True,
                sync_w=True,
            )
        except Exception:
            try:
                pw_dir = root / "cstrike" / "models" / "pw_models"
                src_p = pw_dir / dest_p_name
                src_w = pw_dir / dest_w_name
                if src_p.is_file():
                    shutil.copy2(src_p, dest_p_path)
                if src_w.is_file():
                    shutil.copy2(src_w, dest_w_path)
            except Exception:
                pass
    elif is_knife:
        dest_p_path = item_dir / "p_knife.mdl"
        dest_w_path = item_dir / "w_knife.mdl"
        pw_dir = root / "cstrike" / "models" / "pw_models"
        src_p = pw_dir / "p_knife.mdl"
        src_w = pw_dir / "w_knife.mdl"
        if src_p.is_file():
            shutil.copy2(src_p, dest_p_path)
        if src_w.is_file():
            shutil.copy2(src_w, dest_w_path)

    # Handle Thumbnail
    thumb_path = item_dir / "thumb.png"
    if thumb_b64:
        try:
            raw_b64 = thumb_b64.split(",", 1)[1] if "," in thumb_b64 else thumb_b64
            img_data = base64.b64decode(raw_b64)
            with open(thumb_path, "wb") as f:
                f.write(img_data)
        except Exception:
            pass

    # If no thumbnail provided, try to generate one from the first skin texture
    if not thumb_path.is_file():
        try:
            for t in model_obj.textures:
                if classify_texture(t.name, t.flags, t.width, t.height)[0] == ROLE_SKIN:
                    with open(thumb_path, "wb") as f:
                        f.write(t.to_png_bytes())
                    break
        except Exception:
            pass

    # Relative paths for CS 1.6 / AMXX
    rel_v = str(dest_v_path.relative_to(cstrike_dir)).replace("\\", "/") if cstrike_dir in dest_v_path.parents else str(dest_v_path.relative_to(root)).replace("\\", "/")
    rel_p = str(dest_p_path.relative_to(cstrike_dir)).replace("\\", "/") if dest_p_path and dest_p_path.is_file() and cstrike_dir in dest_p_path.parents else ""
    rel_w = str(dest_w_path.relative_to(cstrike_dir)).replace("\\", "/") if dest_w_path and dest_w_path.is_file() and cstrike_dir in dest_w_path.parents else ""

    manifest = {
        "id": slug,
        "name": clean_name,
        "weapon": w_clean,
        "category": "knife" if is_knife else w_clean,
        "is_knife": is_knife,
        "knife_variant": k_var,
        "team": team.lower(),
        "created_at": datetime.now().isoformat(),
        "v_model": rel_v,
        "p_model": rel_p,
        "w_model": rel_w,
        "metadata": meta,
        "amxx_registered": bool(register_amxx),
    }

    manifest_path = item_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Optional AMXX Registration
    if register_amxx:
        add_to_skin_inventory_ini(
            display_name=clean_name,
            v_model_rel=rel_v,
            p_model_rel=rel_p,
            w_model_rel=rel_w,
            team=team,
            weapon_key=w_clean,
            root_dir=root,
        )

    # Optional Immediate Equip
    equip_result = None
    if equip_now:
        equip_result = equip_inventory_skin(
            item_id_or_path=slug,
            team=team,
            sync_active_glove=True,
            root_dir=root,
        )

    return {
        "success": True,
        "id": slug,
        "name": clean_name,
        "weapon": w_clean,
        "is_knife": is_knife,
        "knife_variant": k_var,
        "team": team.lower(),
        "item_path": str(item_dir),
        "v_model": rel_v,
        "p_model": rel_p,
        "w_model": rel_w,
        "amxx_registered": bool(register_amxx),
        "equip_result": equip_result,
        "manifest": manifest,
    }


def find_inventory_item(item_id_or_path: str, root_dir: Optional[Union[str, Path]] = None) -> Optional[Tuple[Path, dict]]:
    """Locates an inventory item by slug ID or directory path and returns (item_dir, manifest)."""
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    inv_base = get_inventory_dir(root)

    cand_path = Path(item_id_or_path)
    if cand_path.is_dir() and (cand_path / "manifest.json").is_file():
        try:
            with open(cand_path / "manifest.json", "r", encoding="utf-8") as f:
                return cand_path, json.load(f)
        except Exception:
            pass

    target_id = item_id_or_path.strip().lower()
    for cat_dir in inv_base.iterdir():
        if cat_dir.is_dir():
            for item_dir in cat_dir.iterdir():
                if item_dir.is_dir() and (item_dir / "manifest.json").is_file():
                    if item_dir.name.lower() == target_id or item_dir.name.lower().startswith(target_id):
                        try:
                            with open(item_dir / "manifest.json", "r", encoding="utf-8") as f:
                                return item_dir, json.load(f)
                        except Exception:
                            pass
    return None


def list_inventory(
    weapon: Optional[str] = None,
    team: Optional[str] = None,
    root_dir: Optional[Union[str, Path]] = None,
) -> List[dict]:
    """
    Lists all saved skins and knives from the inventory vault.
    Determines if each item is currently equipped in active_loadout.ini.
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    inv_base = get_inventory_dir(root)
    loadout_path = root / ACTIVE_LOADOUT_REL

    from .amxx_manager import parse_active_loadout
    active_loadout = parse_active_loadout(loadout_path) if loadout_path.is_file() else {"ct": {}, "t": {}}
    active_equipped = _load_active_equipped(root)

    cstrike_dir = root / "cstrike"
    results = []

    filter_w = _clean_weapon_key(weapon) if weapon and weapon.lower() != "all" else None
    filter_team = team.lower().strip() if team and team.lower() in ("ct", "t") else None

    for cat_dir in sorted(inv_base.iterdir()):
        if not cat_dir.is_dir():
            continue
        for item_dir in sorted(cat_dir.iterdir()):
            if not item_dir.is_dir():
                continue
            manifest_file = item_dir / "manifest.json"
            if not manifest_file.is_file():
                continue

            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            item_id = data.get("id", item_dir.name)
            item_weapon = data.get("weapon", "")
            item_is_knife = data.get("is_knife", False)
            item_team = data.get("team", "ct")

            # Filters
            if filter_w:
                if filter_w == "knife" and not item_is_knife:
                    continue
                elif filter_w != "knife" and item_weapon != filter_w:
                    continue

            if filter_team and item_team != filter_team:
                if not item_is_knife:
                    continue

            # Verify Viewmodel
            v_model_rel = data.get("v_model", "")
            v_full_path = (cstrike_dir / v_model_rel) if v_model_rel else None
            if not v_full_path or not v_full_path.is_file():
                mdls = list(item_dir.glob("v_*.mdl"))
                if mdls:
                    v_full_path = mdls[0]
                    v_model_rel = str(v_full_path.relative_to(cstrike_dir)).replace("\\", "/")
                    data["v_model"] = v_model_rel
                else:
                    continue

            # Check if active
            v_clean_norm = v_model_rel.replace("\\", "/").lower()
            slot_key = "KNIFE" if item_is_knife else WEAPON_TO_SLOT.get(item_weapon, item_weapon.upper())

            equipped_ct = (
                active_equipped.get("ct", {}).get(slot_key) == item_id
                or active_loadout.get("ct", {}).get(slot_key, "").replace("\\", "/").lower() == v_clean_norm
            )
            equipped_t = (
                active_equipped.get("t", {}).get(slot_key) == item_id
                or active_loadout.get("t", {}).get(slot_key, "").replace("\\", "/").lower() == v_clean_norm
            )

            # Load thumbnail preview as data URI
            thumb_path = item_dir / "thumb.png"
            thumb_uri = ""
            if thumb_path.is_file():
                try:
                    with open(thumb_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("ascii")
                    thumb_uri = f"data:image/png;base64,{b64}"
                except Exception:
                    pass

            item_dict = {
                "id": item_id,
                "name": data.get("name", item_dir.name),
                "weapon": item_weapon,
                "category": data.get("category", "weapon"),
                "is_knife": item_is_knife,
                "knife_variant": data.get("knife_variant"),
                "team": item_team,
                "created_at": data.get("created_at", ""),
                "v_model": v_model_rel,
                "p_model": data.get("p_model", ""),
                "w_model": data.get("w_model", ""),
                "thumbnail": thumb_uri,
                "metadata": data.get("metadata", {}),
                "amxx_registered": data.get("amxx_registered", False),
                "is_equipped_ct": equipped_ct,
                "is_equipped_t": equipped_t,
                "folder_path": str(item_dir),
            }
            results.append(item_dict)

    return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)


def find_active_glove_source(
    team: str = "ct",
    root_dir: Optional[Union[str, Path]] = None,
) -> Optional[MdlModel]:
    """
    Finds a current active model for the team to use as the master glove donor.
    Prioritizes USP, AK47, M4A1, or Knife from active_loadout or custom_skins.
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    team_clean = team.lower().strip()

    for w in ("usp", "ak47", "m4a1", "deagle", "knife"):
        try:
            p = resolve_model_path(w, team=team_clean, root_dir=root)
            if p.is_file():
                m = MdlModel(p)
                has_gloves = any(classify_glove_role(t.name) is not None for t in m.textures)
                if has_gloves:
                    return m
        except Exception:
            continue
    return None


def equip_inventory_skin(
    item_id_or_path: str,
    team: str = "ct",
    sync_active_glove: bool = True,
    root_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Equips a skin or knife from the inventory vault into the active loadout.
    Features the Glove Swapping Mitigation Engine: automatically synchronizes
    the player's active glove preset into the equipped model on the fly!
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    found = find_inventory_item(item_id_or_path, root_dir=root)
    if not found:
        raise FileNotFoundError(f"Inventory item '{item_id_or_path}' not found in vault.")

    item_dir, manifest = found
    team_clean = team.lower().strip()
    item_id = manifest.get("id", item_dir.name)
    weapon_key = manifest.get("weapon", "usp")
    is_knife = manifest.get("is_knife", False)
    k_var = manifest.get("knife_variant")

    cstrike_dir = root / "cstrike"
    v_rel = manifest.get("v_model")
    v_vault_path = cstrike_dir / v_rel if v_rel else (item_dir / f"v_{weapon_key}.mdl")

    if not v_vault_path.is_file():
        mdls = list(item_dir.glob("v_*.mdl"))
        if mdls:
            v_vault_path = mdls[0]
        else:
            raise FileNotFoundError(f"Viewmodel file not found in vault: {v_vault_path}")

    # Step 1: Mitigate Gloves (Auto-Glove Sync)
    glove_sync_status = "Skipped"
    if sync_active_glove:
        try:
            glove_donor = find_active_glove_source(team=team_clean, root_dir=root)
            if glove_donor:
                sync_res = transfer_gloves(glove_donor, v_vault_path, sync_sleeves=False)
                glove_sync_status = "Synchronized with active loadout gloves"
        except Exception as e:
            glove_sync_status = f"Glove sync notice: {str(e)}"

    # Step 2: Determine deployment path in cstrike/models/custom_skins/<team>/
    custom_skins_team_dir = root / "cstrike" / "models" / "custom_skins" / team_clean
    custom_skins_team_dir.mkdir(parents=True, exist_ok=True)

    dest_filename = v_vault_path.name
    deployed_v_path = custom_skins_team_dir / dest_filename
    shutil.copy2(v_vault_path, deployed_v_path)

    deployed_v_rel = str(deployed_v_path.relative_to(cstrike_dir)).replace("\\", "/")

    # Step 3: Deploy P and W models if present
    p_vault_path = item_dir / f"p_{weapon_key}.mdl" if not is_knife else item_dir / "p_knife.mdl"
    w_vault_path = item_dir / f"w_{weapon_key}.mdl" if not is_knife else item_dir / "w_knife.mdl"
    pw_dest_dir = root / "cstrike" / "models" / "pw_models"
    pw_dest_dir.mkdir(parents=True, exist_ok=True)

    if p_vault_path.is_file():
        shutil.copy2(p_vault_path, pw_dest_dir / p_vault_path.name)
    if w_vault_path.is_file():
        shutil.copy2(w_vault_path, pw_dest_dir / w_vault_path.name)

    # Step 4: Update active_loadout.ini
    slot_key = "KNIFE" if is_knife else WEAPON_TO_SLOT.get(weapon_key, weapon_key.upper())
    loadout_res = set_active_loadout(
        team=team_clean,
        weapon=weapon_key if not is_knife else (k_var or "knife"),
        model_path=deployed_v_rel,
        root_dir=root,
    )

    # Step 5: Update .active_equipped.json
    active_equipped = _load_active_equipped(root)
    if team_clean not in active_equipped:
        active_equipped[team_clean] = {}
    active_equipped[team_clean][slot_key] = item_id
    _save_active_equipped(active_equipped, root)

    return {
        "success": True,
        "name": manifest.get("name"),
        "weapon": weapon_key,
        "team": team_clean,
        "is_knife": is_knife,
        "knife_variant": k_var,
        "model_path": deployed_v_rel,
        "glove_sync_status": glove_sync_status,
        "loadout": loadout_res,
        "message": f"Successfully equipped '{manifest.get('name')}' for {team_clean.upper()} loadout.",
    }


def sync_gloves_to_inventory(
    glove_preset_name: Optional[str] = None,
    donor_weapon_or_path: Optional[str] = None,
    team: Optional[str] = None,
    target_item_ids: Optional[List[str]] = None,
    root_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Batch synchronizes glove textures across all or selected inventory items.
    Sourced from high-resolution glove master preset OR current active weapon.
    """
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    cstrike_dir = root / "cstrike"
    inv_items = list_inventory(root_dir=root)

    if target_item_ids:
        norm_targets = [str(x).lower().strip() for x in target_item_ids]
        items_to_process = [it for it in inv_items if it["id"].lower() in norm_targets]
    else:
        items_to_process = inv_items

    if not items_to_process:
        return {"success": False, "message": "No inventory items to update.", "updated_count": 0}

    # Resolve donor source
    preset_data = None
    donor_model = None

    if glove_preset_name:
        try:
            preset_data = load_glove_preset(glove_preset_name, root_dir=root)
        except Exception as e:
            return {"success": False, "error": f"Failed to load glove preset '{glove_preset_name}': {str(e)}"}
    else:
        donor_team = team or "ct"
        if donor_weapon_or_path:
            try:
                p = resolve_model_path(donor_weapon_or_path, team=donor_team, root_dir=root)
                donor_model = MdlModel(p)
            except Exception:
                donor_model = find_active_glove_source(donor_team, root_dir=root)
        else:
            donor_model = find_active_glove_source(donor_team, root_dir=root)

    updated_items = []
    failed_items = []

    for item in items_to_process:
        v_rel = item.get("v_model")
        v_path = cstrike_dir / v_rel if v_rel else Path(item["folder_path"]) / f"v_{item['weapon']}.mdl"
        if not v_path.is_file():
            continue

        try:
            if preset_data:
                left_src = preset_data.get("left_image")
                right_src = preset_data.get("right_image")
                left_img = _load_image_input(left_src, root_dir=root) if left_src else None
                right_img = _load_image_input(right_src, root_dir=root) if right_src else None

                target_m = MdlModel(v_path)
                changed = False
                for t in target_m.textures:
                    role = classify_glove_role(t.name, guard_bare=True)
                    if role == "bare_arm":
                        continue
                    src_img = None
                    if role == "left_glove" and left_img:
                        src_img = left_img
                    elif role == "right_glove" and right_img:
                        src_img = right_img
                    elif role == "general_glove":
                        src_img = left_img or right_img

                    if src_img:
                        target_m.save_slot_snapshot(t)
                        resized = src_img.resize((t.width, t.height), Image.Resampling.LANCZOS)
                        pix_bytes, pal_bytes = quantize_goldsrc(resized, is_masked=t.is_masked, defringe=t.is_masked)
                        target_m.inject_texture_payload(t, pix_bytes + pal_bytes, new_flags=t.flags)
                        changed = True

                if changed:
                    target_m.save_atomic(create_backup=True)
                    updated_items.append(item["name"])
            elif donor_model:
                res = transfer_gloves(donor_model, v_path, sync_sleeves=False)
                if res.get("success"):
                    updated_items.append(item["name"])
                else:
                    failed_items.append({"item": item["name"], "error": res.get("error", "transfer failed")})
        except Exception as e:
            failed_items.append({"item": item["name"], "error": str(e)})

    return {
        "success": True,
        "updated_count": len(updated_items),
        "updated_items": updated_items,
        "failed_count": len(failed_items),
        "failed_items": failed_items,
        "message": f"Successfully synchronized gloves across {len(updated_items)} inventory items.",
    }


def delete_inventory_skin(item_id_or_path: str, root_dir: Optional[Union[str, Path]] = None) -> dict:
    """Deletes an item from the Skin Inventory Vault and removes its AMXX registration."""
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    found = find_inventory_item(item_id_or_path, root_dir=root)
    if not found:
        return {"success": False, "error": f"Item '{item_id_or_path}' not found."}

    item_dir, manifest = found
    v_rel = manifest.get("v_model")
    item_id = manifest.get("id", item_dir.name)

    # Clean active equipped if present
    active_equipped = _load_active_equipped(root)
    changed = False
    for t_key in ("ct", "t"):
        for s_key, eq_id in list(active_equipped.get(t_key, {}).items()):
            if eq_id == item_id:
                del active_equipped[t_key][s_key]
                changed = True
    if changed:
        _save_active_equipped(active_equipped, root)

    # Unregister from AMXX if present
    if v_rel:
        remove_from_skin_inventory_ini(v_rel, root_dir=root)

    # Safely delete item folder
    shutil.rmtree(item_dir, ignore_errors=True)

    return {
        "success": True,
        "id": manifest.get("id"),
        "name": manifest.get("name"),
        "message": f"Deleted skin '{manifest.get('name')}' from inventory vault.",
    }


def toggle_amxx_registration(
    item_id_or_path: str,
    enable: bool,
    root_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """Toggles registration of an inventory item in skin_inventory.ini."""
    root = Path(root_dir).resolve() if root_dir else config.get_game_root()
    found = find_inventory_item(item_id_or_path, root_dir=root)
    if not found:
        return {"success": False, "error": f"Item '{item_id_or_path}' not found."}

    item_dir, manifest = found
    v_rel = manifest.get("v_model")
    p_rel = manifest.get("p_model", "")
    w_rel = manifest.get("w_model", "")
    name = manifest.get("name", "Custom Skin")
    team = manifest.get("team", "ct")
    weapon = manifest.get("weapon", "ak47")

    if enable:
        add_to_skin_inventory_ini(
            display_name=name,
            v_model_rel=v_rel,
            p_model_rel=p_rel,
            w_model_rel=w_rel,
            team=team,
            weapon_key=weapon,
            root_dir=root,
        )
        manifest["amxx_registered"] = True
    else:
        if v_rel:
            remove_from_skin_inventory_ini(v_rel, root_dir=root)
        manifest["amxx_registered"] = False

    # Save manifest update
    with open(item_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return {
        "success": True,
        "id": manifest.get("id"),
        "amxx_registered": manifest["amxx_registered"],
        "message": f"Updated AMXX registration for '{name}': {'Enabled' if enable else 'Disabled'}.",
    }
