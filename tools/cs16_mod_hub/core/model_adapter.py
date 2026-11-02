"""
tools/cs16_mod_hub/core/model_adapter.py
Model skin transfer, glove injection, player/world synchronization,
model discovery, and non-destructive GoldSrc backup management.
"""

from datetime import datetime
import hashlib
import os
from pathlib import Path
import shutil
import struct
from typing import Any, Callable, Dict, List, Optional, Union

from .common import AdapterResult, get_project_root, run_script_streaming

# Relative script paths inside repository
SKIN_TRANSFER_SCRIPT = ".agents/skills/cs16-skin-transfer/scripts/transfer_weapon_skin.py"
GLOVE_INJECTOR_SCRIPT = ".agents/skills/cs16-glove-injector/scripts/inject_gloves.py"
PW_INJECTOR_SCRIPT = ".agents/skills/cs16-pw-injector/scripts/bake_and_inject_pw.py"

# Default search directories for models and donor packs
DEFAULT_DONOR_DIRS = [
    "CSGO Weapon Pack - Update #4/cstrike/models",
    "CSGO Weapon Pack - Update #4/cstrike/models/alt",
    "cstrike/models/custom_skins/ct",
    "cstrike/models/custom_skins/t",
    "cstrike/models/csgo_skins/ct",
    "cstrike/models/csgo_skins/t",
    "cstrike_hd/models",
]

DEFAULT_BACKUP_DIRS = [
    "cstrike/models",
    "cstrike_hd/models",
]


def verify_goldsrc_mdl_header(file_path: Union[str, Path]) -> bool:
    """
    Inspects binary header of a file. Returns True if magic is b'IDST' and version is 10.
    """
    path = Path(file_path)
    if not path.is_file() or path.stat().st_size < 8:
        return False
    try:
        with open(path, "rb") as f:
            magic, ver = struct.unpack("<4sI", f.read(8))
            return magic == b"IDST" and ver == 10
    except Exception:
        return False


from .profiles import get_active_profile_path


def transfer_skin(
    source: str,
    target: str,
    dir_path: Optional[str] = None,
    sync_pw: bool = False,
    no_backup: bool = False,
    log_callback: Optional[Callable[[str], None]] = None,
) -> AdapterResult:
    """
    Wraps transfer_weapon_skin.py to transfer weapon body skin from donor to target model,
    preserving animations, gloves, StatTrak, and stickers.
    """
    if not source or not target:
        return AdapterResult(False, "Both source and target models must be specified.", returncode=-1)

    effective_dir = dir_path or get_active_profile_path()
    args = [
        "-s", str(source),
        "-t", str(target),
        "-d", str(effective_dir),
    ]
    if sync_pw:
        args.append("--sync-pw")
    if no_backup:
        args.append("--no-backup")

    return run_script_streaming(SKIN_TRANSFER_SCRIPT, args, log_callback=log_callback)


def inject_gloves(
    target: str,
    source: str = "awp",
    dir_path: Optional[str] = None,
    no_backup: bool = False,
    log_callback: Optional[Callable[[str], None]] = None,
) -> AdapterResult:
    """
    Wraps inject_gloves.py to inject glove/arm textures from donor model into target viewmodel.
    """
    if not target:
        return AdapterResult(False, "Target viewmodel must be specified.", returncode=-1)

    effective_dir = dir_path or get_active_profile_path()
    args = [
        "-t", str(target),
        "-s", str(source),
        "-d", str(effective_dir),
    ]
    if no_backup:
        args.append("--no-backup")

    return run_script_streaming(GLOVE_INJECTOR_SCRIPT, args, log_callback=log_callback)


def inject_pw(
    weapon: Optional[str] = None,
    v_model: Optional[str] = None,
    p_model: Optional[str] = None,
    w_model: Optional[str] = None,
    dir_path: Optional[str] = None,
    no_backup: bool = False,
    log_callback: Optional[Callable[[str], None]] = None,
) -> AdapterResult:
    """
    Wraps bake_and_inject_pw.py to bake decals and inject skins into player (p_) and world (w_) models.
    """
    if not weapon and not v_model:
        return AdapterResult(
            False,
            "Either 'weapon' or 'v_model' must be provided for P/W injection.",
            returncode=-1,
        )

    effective_dir = dir_path or get_active_profile_path()
    args = ["-d", str(effective_dir)]
    if weapon:
        args.extend(["-w", str(weapon)])
    if v_model:
        args.extend(["--v-model", str(v_model)])
    if p_model:
        args.extend(["--p-model", str(p_model)])
    if w_model:
        args.extend(["--w-model", str(w_model)])
    if no_backup:
        args.append("--no-backup")

    return run_script_streaming(PW_INJECTOR_SCRIPT, args, log_callback=log_callback)


def list_viewmodels(dir_path: Optional[str] = None) -> List[str]:
    """
    Lists active weapon viewmodels (v_*.mdl) in the given directory or active profile.
    Returns sorted list of filenames (e.g. ['v_ak47.mdl', 'v_m4a1.mdl']).
    """
    root = get_project_root()
    effective_dir = dir_path or get_active_profile_path()
    p = Path(effective_dir)
    target_dir = p if p.is_absolute() else (root / p)

    if not target_dir.is_dir():
        return []

    models: List[str] = []
    for entry in target_dir.iterdir():
        if entry.is_file():
            name_lower = entry.name.lower()
            if name_lower.startswith("v_") and name_lower.endswith(".mdl") and not name_lower.endswith(".bak"):
                models.append(entry.name)

    return sorted(models)


def list_donor_models(search_dirs: Optional[List[str]] = None) -> List[str]:
    """
    Scans donor collections and custom skin folders for available donor viewmodels.
    Returns sorted list of paths relative to project root with forward slashes.
    """
    root = get_project_root()
    dirs_to_search = search_dirs if search_dirs is not None else DEFAULT_DONOR_DIRS

    discovered: List[str] = []
    for sdir in dirs_to_search:
        p = Path(sdir)
        abs_dir = p if p.is_absolute() else (root / p)
        if not abs_dir.is_dir():
            continue

        for entry in abs_dir.iterdir():
            if entry.is_file():
                name_lower = entry.name.lower()
                if name_lower.startswith("v_") and name_lower.endswith(".mdl") and not name_lower.endswith(".bak"):
                    try:
                        rel = entry.relative_to(root).as_posix()
                    except ValueError:
                        rel = entry.as_posix()
                    discovered.append(rel)

    return sorted(list(dict.fromkeys(discovered)))


def list_backups(search_dirs: Optional[List[str]] = None) -> List[dict]:
    """
    Recursively scans model directories for .mdl.bak backup files, verifies their
    GoldSrc IDST header, and returns structured metadata dictionaries.
    """
    root = get_project_root()
    dirs = search_dirs if search_dirs is not None else DEFAULT_BACKUP_DIRS

    results: List[dict] = []
    seen_paths = set()

    for sdir in dirs:
        p = Path(sdir)
        abs_dir = p if p.is_absolute() else (root / p)
        if not abs_dir.is_dir():
            continue

        for bak_file in abs_dir.rglob("*.bak"):
            # Exclude non-model files (such as .gam.bak or .wav.bak)
            stem_name = bak_file.name[:-4]  # strip .bak
            if not stem_name.lower().endswith(".mdl"):
                continue

            abs_bak_str = str(bak_file.resolve())
            if abs_bak_str in seen_paths:
                continue
            seen_paths.add(abs_bak_str)

            target_file = bak_file.with_name(stem_name)
            has_target = target_file.is_file()

            try:
                rel_backup = bak_file.relative_to(root).as_posix()
            except ValueError:
                rel_backup = bak_file.as_posix()

            try:
                rel_target = target_file.relative_to(root).as_posix()
            except ValueError:
                rel_target = target_file.as_posix()

            bak_stat = bak_file.stat()
            bak_size = bak_stat.st_size
            tgt_size = target_file.stat().st_size if has_target else None

            is_valid_idst = verify_goldsrc_mdl_header(bak_file)
            is_modified = has_target and (bak_size != tgt_size)
            mtime_iso = datetime.fromtimestamp(bak_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            results.append({
                "backup_path": abs_bak_str,
                "relative_backup": rel_backup,
                "target_path": str(target_file.resolve()),
                "relative_target": rel_target,
                "model_name": target_file.name,
                "backup_size": bak_size,
                "target_size": tgt_size,
                "has_target": has_target,
                "is_modified": is_modified,
                "is_valid_idst": is_valid_idst,
                "backup_mtime": mtime_iso,
            })

    return sorted(results, key=lambda x: x["relative_backup"])


def restore_model_backup(model_name_or_path: str) -> AdapterResult:
    """
    Restores an active model from its .bak backup after verifying the GoldSrc IDST header.
    Does NOT delete the .bak file to ensure idempotent rollback safety.
    """
    root = get_project_root()
    p = Path(model_name_or_path)

    # Determine candidate backup and target paths
    bak_path: Optional[Path] = None
    target_path: Optional[Path] = None

    if p.is_absolute():
        if p.name.lower().endswith(".bak"):
            bak_path = p
            target_path = p.with_name(p.name[:-4])
        else:
            target_path = p
            bak_path = p.with_name(p.name + ".bak")
    else:
        # Check direct relative path from root
        cand = (root / p).resolve()
        if cand.name.lower().endswith(".bak") and cand.is_file():
            bak_path = cand
            target_path = cand.with_name(cand.name[:-4])
        elif cand.is_file():
            target_path = cand
            bak_path = cand.with_name(cand.name + ".bak")
        elif cand.with_name(cand.name + ".bak").is_file():
            target_path = cand
            bak_path = cand.with_name(cand.name + ".bak")
        else:
            # Search in known backup directories
            norm_name = p.name
            if not norm_name.lower().endswith(".bak"):
                if not norm_name.lower().endswith(".mdl"):
                    norm_name = f"v_{norm_name}.mdl"
                bak_name = norm_name + ".bak"
            else:
                bak_name = norm_name

            for sdir in DEFAULT_BACKUP_DIRS:
                abs_sdir = root / sdir
                found = list(abs_sdir.rglob(bak_name))
                if found:
                    bak_path = found[0]
                    target_path = bak_path.with_name(bak_path.name[:-4])
                    break

    if not bak_path or not bak_path.is_file():
        return AdapterResult(
            success=False,
            message=f"Backup file not found for: {model_name_or_path}",
            returncode=-1,
        )

    # Validate GoldSrc IDST header before restoring
    if not verify_goldsrc_mdl_header(bak_path):
        return AdapterResult(
            success=False,
            message=f"Restoration aborted: Invalid GoldSrc MDL header in backup ({bak_path.name}).",
            returncode=-1,
        )

    try:
        shutil.copy2(str(bak_path), str(target_path))
        return AdapterResult(
            success=True,
            message=f"Successfully restored '{target_path.name}' from backup.",
            stdout=f"Restored: {bak_path.name} -> {target_path.name}",
            returncode=0,
        )
    except Exception as exc:
        return AdapterResult(
            success=False,
            message=f"Failed to restore model backup: {exc}",
            stderr=str(exc),
            returncode=-1,
        )


def restore_all_backups(search_dirs: Optional[List[str]] = None) -> AdapterResult:
    """
    Batch restores all valid discovered model backups.
    """
    backups = list_backups(search_dirs=search_dirs)
    if not backups:
        return AdapterResult(True, "No backup files found to restore.")

    restored_count = 0
    failed_items: List[str] = []

    for b in backups:
        res = restore_model_backup(b["backup_path"])
        if res.success:
            restored_count += 1
        else:
            failed_items.append(f"{b['model_name']}: {res.message}")

    if failed_items:
        summary_err = "\n".join(failed_items)
        return AdapterResult(
            success=False,
            message=f"Restored {restored_count} model(s), but {len(failed_items)} failed.",
            stderr=summary_err,
            returncode=-1,
        )

    return AdapterResult(
        success=True,
        message=f"Successfully restored all {restored_count} model backup(s).",
        stdout=f"Restored count: {restored_count}",
        returncode=0,
    )


def get_model_category(model_name: str) -> str:
    """Returns tactical weapon category badge text for UI manifest."""
    name = model_name.lower()
    if any(k in name for k in ["ak47", "m4a1", "m4a4", "galil", "famas", "sg552", "aug"]):
        return "PRIMARY RIFLE"
    if any(k in name for k in ["awp", "scout", "g3sg1", "sg550"]):
        return "SNIPER RIFLE"
    if any(k in name for k in ["deagle", "elite"]):
        return "HEAVY PISTOL"
    if any(k in name for k in ["usp", "glock", "p228", "fiveseven", "cz75", "tec9"]):
        return "SIDEARM PISTOL"
    if any(k in name for k in ["mp5", "p90", "mac10", "tmp", "ump45", "bizon", "mp7"]):
        return "SUBMACHINE GUN"
    if any(k in name for k in ["m3", "xm1014", "sawedoff", "mag7"]):
        return "TACTICAL SHOTGUN"
    if any(k in name for k in ["m249", "negev"]):
        return "HEAVY MACHINE GUN"
    if any(k in name for k in ["knife", "bayonet", "karambit"]):
        return "COMBAT MELEE"
    if any(k in name for k in ["c4", "hegrenade", "flashbang", "smokegrenade"]):
        return "TACTICAL UTILITY"
    return "CUSTOM ASSET"


def calculate_file_sha256(file_path: Union[str, Path]) -> Optional[str]:
    """Computes SHA-256 hash of a file."""
    path = Path(file_path)
    if not path.is_file():
        return None
    hasher = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None


def verify_all_backups(search_dirs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Scans all backup files, verifies binary GoldSrc IDST header, and computes SHA-256 hash.
    """
    backups = list_backups(search_dirs=search_dirs)
    results: List[Dict[str, Any]] = []
    for b in backups:
        bak_path = Path(b["backup_path"])
        is_idst = verify_goldsrc_mdl_header(bak_path)
        sha = calculate_file_sha256(bak_path) if is_idst else None
        results.append({
            "model_name": b["model_name"],
            "category": get_model_category(b["model_name"]),
            "backup_path": b["backup_path"],
            "relative_backup": b["relative_backup"],
            "target_path": b["target_path"],
            "size_bytes": b["backup_size"],
            "modified_str": b["backup_mtime"],
            "is_valid_idst": is_idst,
            "sha256": sha,
            "has_target": b["has_target"],
            "is_modified": b["is_modified"],
        })
    return results


def get_backup_telemetry(search_dirs: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Returns telemetry metrics for safety backup vault: file count, disk volume MB, write access lock.
    """
    root = get_project_root()
    effective_dirs = search_dirs if search_dirs is not None else [get_active_profile_path()]
    backups = list_backups(search_dirs=effective_dirs)
    total_files = len(backups)
    total_bytes = sum(b.get("backup_size", 0) for b in backups)
    total_mb = round(total_bytes / (1024 * 1024), 2)

    primary_dir = Path(effective_dirs[0]) if effective_dirs else (root / "cstrike" / "models" / "custom_skins" / "ct")
    abs_primary = primary_dir if primary_dir.is_absolute() else (root / primary_dir)
    write_guarded = os.access(abs_primary, os.W_OK) if abs_primary.is_dir() else False
    valid_idst_count = sum(1 for b in backups if b.get("is_valid_idst"))

    return {
        "success": True,
        "total_files": total_files,
        "total_bytes": total_bytes,
        "total_mb": total_mb,
        "write_guarded": write_guarded,
        "vault_path": str(abs_primary),
        "valid_idst_count": valid_idst_count,
        "integrity_pct": 100.0 if total_files == 0 else round((valid_idst_count / total_files) * 100, 1),
    }
