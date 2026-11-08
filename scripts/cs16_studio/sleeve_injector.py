"""
sleeve_injector.py - 3D Sleeve Injection Engine for Counter-Strike 1.6 GoldSrc StudioModels (IDST v10).

Provides:
1. detect_arm_type: Distinguishes between bare arm (t_arm), 3D jacket sleeves (ct_arms), and gloves only.
2. calculate_scale_ratio: Dynamic bone length ratio solver (||p_target,hand - p_target,forearm|| / ||p_donor,hand - p_donor,forearm||).
3. compute_bone_bind_matrices: Solves 4x4 rest-pose world matrices for forward kinematics.
4. detect_rig_laterality: Classifies whether rig uses standard or inverted bone naming laterality.
5. build_bone_remapping: Spatial laterality-aware bone mapper with ForeTwist -> Forearm -> Hand fallback.
6. SLEEVE_PRESETS: 4 CT uniform presets (SAS Navy Blue, GIGN Urban Camo, GSG-9 Woodland Tactical, Arctic Warfare Heavy Parka) + Custom viewmodel donor.
7. transplant_3d_sleeves: High-fidelity 3D submodel transplant with 3D rigid bone basis transforms,
   spatial laterality remapping, submodel limit validation (MAXSTUDIOVERTS <= 2048, MAXSTUDIOBODYPARTS <= 32),
   and atomic replacement with .bak backup.
"""

import copy
import io
import math
import os
from pathlib import Path
import re
import shutil
import struct
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image

from .config_manager import StudioConfig
from .pw_restore import get_model_backup_dir
from .mdl_core import (
    STUDIO_MAGIC,
    STUDIO_VERSION,
    STUDIO_NF_CHROME,
    STUDIO_NF_MASKED,
    STUDIO_NF_ADDITIVE,
    MdlModel,
    MdlTexture,
    resolve_model_path,
)
from .image_pipeline import quantize_goldsrc, load_image
from .color_adjuster import adjust_color_grading
from .slot_geometry import validate_model_health
from .chrome_injector import parse_model_geometry, serialize_model_binary

MAXSTUDIOBODYPARTS = 32
MAXSTUDIOVERTS = 2048

# Built-in Sleeve Presets
SLEEVE_PRESETS: Dict[str, Dict[str, Any]] = {
    "sas_navy": {
        "id": "sas_navy",
        "name": "SAS Navy Blue Heavy Fleece",
        "description": "Classic CS 1.6 HD British SAS Navy Blue heavyweight fleece uniform.",
        "default_donor": "cstrike/models/custom_skins/ct/v_m4a1.mdl",
        "color_adjustments": None,
    },
    "gign_urban": {
        "id": "gign_urban",
        "name": "GIGN Urban Camo Jacket",
        "description": "French GIGN Tactical high-contrast urban camouflage and ballistic nylon.",
        "default_donor": "cstrike/models/custom_skins/ct/v_m4a1.mdl",
        "color_adjustments": {
            "temperature": -15,
            "tint": -5,
            "contrast": 15,
            "saturation": -10,
        },
    },
    "gsg9_woodland": {
        "id": "gsg9_woodland",
        "name": "GSG-9 Woodland Tactical",
        "description": "German GSG-9 woodland olive-drab tactical combat sleeve with flecktarn tone.",
        "default_donor": "cstrike/models/custom_skins/ct/v_m4a1.mdl",
        "color_adjustments": {
            "hue": 65,
            "saturation": 10,
            "temperature": 10,
            "contrast": 10,
        },
    },
    "arctic_parka": {
        "id": "arctic_parka",
        "name": "Arctic Warfare Heavy Parka",
        "description": "Sub-zero heavy arctic thermal parka with high-durability cold-weather weave.",
        "default_donor": "cstrike/models/custom_skins/ct/v_m4a1.mdl",
        "color_adjustments": {
            "brightness": 20,
            "contrast": 10,
            "saturation": -60,
            "temperature": -25,
        },
    },
    "custom": {
        "id": "custom",
        "name": "Custom Viewmodel Donor",
        "description": "Transplant sleeve geometry directly from any user-selected GoldSrc viewmodel.",
        "default_donor": None,
        "color_adjustments": None,
    },
}


def compute_bone_bind_matrices(data: bytes) -> Tuple[List[Dict[str, Any]], List[np.ndarray]]:
    """
    Computes 4x4 bind-pose world transformation matrices for all bones in a GoldSrc StudioModel.
    Uses the rest pose translation and rotation defined in the bone header table (vals[:3], vals[3:]).
    """
    if len(data) < 188:
        return [], []

    numbones, boneindex = struct.unpack_from("<II", data, 140)
    bones: List[Dict[str, Any]] = []
    for b in range(numbones):
        b_offset = boneindex + b * 112
        if b_offset + 112 > len(data):
            break
        name_bytes, parent, flags = struct.unpack_from("<32sii", data, b_offset)
        name_str = name_bytes.split(b"\x00")[0].decode("latin1", errors="ignore")
        vals = struct.unpack_from("<6f", data, b_offset + 64)
        bones.append({
            "idx": b,
            "name": name_str,
            "parent": parent,
            "flags": flags,
            "pos": list(vals[:3]),
            "rot": list(vals[3:]),
        })

    def _make_matrix(pos: List[float], rot: List[float]) -> np.ndarray:
        sr = math.sin(rot[0]); cr = math.cos(rot[0])
        sp = math.sin(rot[1]); cp = math.cos(rot[1])
        sy = math.sin(rot[2]); cy = math.cos(rot[2])
        m = np.identity(4, dtype=np.float32)
        m[0, 0] = cp * cy
        m[0, 1] = sr * sp * cy + cr * -sy
        m[0, 2] = cr * sp * cy + -sr * -sy
        m[0, 3] = pos[0]

        m[1, 0] = cp * sy
        m[1, 1] = sr * sp * sy + cr * cy
        m[1, 2] = cr * sp * sy + -sr * cy
        m[1, 3] = pos[1]

        m[2, 0] = -sp
        m[2, 1] = sr * cp
        m[2, 2] = cr * cp
        m[2, 3] = pos[2]
        return m

    world_matrices: List[np.ndarray] = []
    for b in bones:
        local_m = _make_matrix(b["pos"], b["rot"])
        if b["parent"] < 0 or b["parent"] >= len(world_matrices):
            world_matrices.append(local_m)
        else:
            world_matrices.append(np.matmul(world_matrices[b["parent"]], local_m))

    return bones, world_matrices


def _bone_name(b: Any) -> str:
    if isinstance(b, dict):
        return str(b.get("name", ""))
    return str(b)


def _clean_bone(name: str) -> str:
    s = name.lower()
    for _ in range(3):
        s = re.sub(r"^(?:valvebiped|v_weapon|bip01|bip)[._\- ]*", "", s)
    return re.sub(r"[._\- ]+", "", s)


def get_bone_rotation_activity(model_data: bytes) -> Dict[int, bool]:
    """
    Scans model animation tracks across all sequences to detect which bones
    have active rotation keyframes. Returns dict of bone_idx -> bool.
    """
    if len(model_data) < 212:
        return {}
    numbones = struct.unpack_from("<I", model_data, 140)[0]
    numseq, seqindex = struct.unpack_from("<II", model_data, 164)
    activity = {b: False for b in range(numbones)}

    for s in range(numseq):
        s_off = seqindex + s * 176
        if s_off + 176 > len(model_data):
            break
        animindex = struct.unpack_from("<I", model_data, s_off + 172)[0]
        for b in range(numbones):
            b_anim_off = animindex + b * 12
            if b_anim_off + 12 <= len(model_data):
                # Rot offsets are at offset +6 (rotX, rotY, rotZ unsigned shorts)
                rot_offsets = struct.unpack_from("<3H", model_data, b_anim_off + 6)
                if any(o > 1 for o in rot_offsets):
                    activity[b] = True
    return activity


def detect_rig_laterality(bones: List[Dict[str, Any]], world_matrices: List[np.ndarray]) -> str:
    """
    Detects whether the rig has 'standard' or 'inverted' bone naming laterality.
    In standard GoldSrc rigs, Left Arm bones (Bip01_L_*) have negative X coordinates (X < 0)
    relative to Right Arm bones (Bip01_R_*) which have positive X coordinates (X > 0).
    Inverted rigs (e.g. some knife models) have Bip01_L_* on positive X and Bip01_R_* on negative X.
    """
    if not bones or not world_matrices or len(bones) != len(world_matrices):
        return "standard"

    l_xs: List[float] = []
    r_xs: List[float] = []
    for idx, b in enumerate(bones):
        name = _bone_name(b).lower()
        if any(k in name for k in ("forearm", "foretwist", "hand")):
            pos = world_matrices[idx][:3, 3]
            if any(k in name for k in ("l_", "left", ".l", " l ", "_l")):
                l_xs.append(float(pos[0]))
            elif any(k in name for k in ("r_", "right", ".r", " r ", "_r")):
                r_xs.append(float(pos[0]))

    if not l_xs or not r_xs:
        return "standard"

    avg_l = float(np.mean(l_xs))
    avg_r = float(np.mean(r_xs))
    return "inverted" if avg_l > avg_r else "standard"


def detect_arm_type(model_path: Union[str, Path, MdlModel]) -> Dict[str, Any]:
    """
    Inspects model bodyparts, submodels, textures, and bones to classify arm configuration:
    - 'bare_arm': Thin bare arms mesh (e.g. Terrorist t_arm or bare_arm texture)
    - 'jacket_sleeve': Volumetric 3D cloth jacket sleeve (e.g. ct_arms_01..03 or sleeve.bmp)
    - 'gloves_only': Model with glove textures/meshes but without separate arm/sleeve meshes
    """
    if isinstance(model_path, MdlModel):
        path = model_path.filepath
        data = model_path.data
    else:
        path = Path(model_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Model file not found: {path}")
        with open(path, "rb") as f:
            data = f.read()

    if len(data) < 212:
        return {
            "arm_type": "unknown",
            "label": "Corrupted / Invalid Header",
            "submodels": [],
            "arm_submodels": [],
            "textures": [],
            "is_bare": False,
            "is_jacket": False,
            "num_bodyparts": 0,
            "rig_laterality": "standard",
        }

    # Textures table
    numtextures, textureindex = struct.unpack_from("<II", data, 180)
    textures: List[str] = []
    for i in range(numtextures):
        t_off = textureindex + i * 80
        if t_off + 80 <= len(data):
            tname = struct.unpack_from("<64s", data, t_off)[0].split(b"\x00")[0].decode("latin1", errors="ignore")
            textures.append(tname)

    # Bodyparts & Submodels table
    numbodyparts, bodypartindex = struct.unpack_from("<II", data, 204)
    all_submodels: List[str] = []
    arm_submodels: List[str] = []
    arm_radii: List[float] = []

    for bp in range(numbodyparts):
        bp_off = bodypartindex + bp * 76
        if bp_off + 76 > len(data):
            break
        bp_name, nummodels, base, modelindex = struct.unpack_from("<64siii", data, bp_off)
        for m in range(nummodels):
            m_off = modelindex + m * 112
            if m_off + 112 > len(data):
                break
            (
                m_name, m_type, m_radius,
                nummesh, meshindex,
                numverts, vertinfoindex, vertindex,
                numnorms, norminfoindex, normindex,
                numgroups, groupindex
            ) = struct.unpack_from("<64sif10I", data, m_off)
            m_name_str = m_name.split(b"\x00")[0].decode("latin1", errors="ignore")
            all_submodels.append(m_name_str)

            lower_m = m_name_str.lower()
            if any(k in lower_m for k in ("t_arm", "bare_arm", "ct_arms", "sleeve", "arm")):
                arm_submodels.append(m_name_str)
                arm_radii.append(float(m_radius))

    # Evaluate classification
    has_ct_arms = any("ct_arms" in s.lower() or "cs_arms_sleeved" in s.lower() for s in all_submodels)
    has_t_arm = any("t_arm" in s.lower() or "cs_arms_reference" in s.lower() or "bare_arm" in s.lower() for s in all_submodels)

    has_sleeve_tex = any("sleeve" in t.lower() for t in textures)
    has_bare_tex = any("bare" in t.lower() or "t_arm" in t.lower() for t in textures)

    has_glove_tex = any(any(k in t.lower() for k in ("sport", "glove", "hand")) for t in textures)

    if has_ct_arms or (has_sleeve_tex and not has_t_arm and not has_bare_tex):
        arm_type = "jacket_sleeve"
        label = "3D Jacket Sleeve (ct_arms detected)"
    elif has_t_arm or has_bare_tex:
        arm_type = "bare_arm"
        label = "Bare Arm (t_arm detected)"
    elif has_glove_tex:
        arm_type = "gloves_only"
        label = "Gloves Only (No Arm Mesh)"
    else:
        arm_type = "unknown"
        label = "Standard Weapon Mesh"

    avg_radius = float(np.mean(arm_radii)) if arm_radii else 0.0

    bones, world_matrices = compute_bone_bind_matrices(data)
    rig_laterality = detect_rig_laterality(bones, world_matrices)

    return {
        "arm_type": arm_type,
        "label": label,
        "submodels": all_submodels,
        "arm_submodels": arm_submodels,
        "textures": textures,
        "is_bare": arm_type == "bare_arm",
        "is_jacket": arm_type == "jacket_sleeve",
        "num_bodyparts": numbodyparts,
        "radius": avg_radius,
        "model_name": path.name,
        "rig_laterality": rig_laterality,
    }


def _get_forearm_and_hand_bone_distance(data: bytes) -> float:
    """
    Computes Euclidean distance between forearm and hand bone positions in world matrix space.
    """
    bones, world_matrices = compute_bone_bind_matrices(data)
    if not bones or not world_matrices:
        return 0.0

    def find_bone_index(patterns: List[str]) -> int:
        for p in patterns:
            p_clean = re.sub(r"[._\- ]+", "", p.lower())
            for idx, b in enumerate(bones):
                b_clean = re.sub(r"[._\- ]+", "", b["name"].lower())
                if p_clean in b_clean:
                    return idx
        return -1

    # Try right arm pair first, then left arm pair
    fa_idx = find_bone_index(["rforearm", "rightforearm", "rforetwist"])
    h_idx = find_bone_index(["rhand", "righthand"])

    if fa_idx < 0 or h_idx < 0:
        fa_idx = find_bone_index(["lforearm", "leftforearm", "lforetwist"])
        h_idx = find_bone_index(["lhand", "lefthand"])

    if fa_idx < 0 or h_idx < 0:
        fa_idx = find_bone_index(["forearm", "foretwist"])
        h_idx = find_bone_index(["hand"])

    if fa_idx < 0 or h_idx < 0 or fa_idx >= len(world_matrices) or h_idx >= len(world_matrices):
        if h_idx >= 0:
            pos = bones[h_idx]["pos"]
            return float(math.sqrt(sum(x * x for x in pos)))
        return 0.0

    p_fa = world_matrices[fa_idx][:3, 3]
    p_h = world_matrices[h_idx][:3, 3]
    dist = float(np.linalg.norm(p_h - p_fa))
    return dist


def calculate_scale_ratio(
    target_path: Union[str, Path],
    donor_path: Union[str, Path],
) -> Tuple[float, str]:
    """
    Calculates scale ratio from bone lengths:
    scale = ||p_target,hand - p_target,forearm|| / ||p_donor,hand - p_donor,forearm||
    Returns (ratio, description).
    """
    t_path = Path(target_path).resolve()
    d_path = Path(donor_path).resolve()

    if not t_path.is_file():
        raise FileNotFoundError(f"Target model not found: {t_path}")
    if not d_path.is_file():
        raise FileNotFoundError(f"Donor model not found: {d_path}")

    with open(t_path, "rb") as f:
        t_data = f.read()
    with open(d_path, "rb") as f:
        d_data = f.read()

    l_target = _get_forearm_and_hand_bone_distance(t_data)
    l_donor = _get_forearm_and_hand_bone_distance(d_data)

    if l_donor <= 1e-4 or l_target <= 1e-4:
        return 1.0, "Auto-detected: 1.0000x (Default fallback)"

    ratio = l_target / l_donor

    # Classify recognizable rig scale relationships
    if abs(ratio - (1.0 / 2.4)) < 0.05:
        return round(ratio, 6), "Auto-detected: 0.4167x (CS:GO Rig to GoldSrc 1.0x)"
    elif abs(ratio - 1.0) < 0.05:
        return 1.0, "Auto-detected: 1.0000x (Same Rig / 1:1 Scale)"
    elif abs(ratio - 2.4) < 0.08:
        return round(ratio, 6), "Auto-detected: 2.4000x (GoldSrc to CS:GO Rig)"
    else:
        return round(ratio, 6), f"Auto-detected: {ratio:.4f}x (Proportional Rig Scale)"


def build_bone_remapping(
    donor_bones: Any,
    target_bones: Any,
    donor_matrices: Optional[List[np.ndarray]] = None,
    target_matrices: Optional[List[np.ndarray]] = None,
    target_activity: Optional[Dict[int, bool]] = None,
) -> Dict[int, int]:
    """
    Builds dynamic bone remapping dictionary mapping donor bone index to target bone index.
    Includes spatial laterality awareness:
    If target rig has inverted laterality (e.g. Left and Right bone names swapped),
    maps donor Left to target spatial Left, and donor Right to target spatial Right.
    Hierarchical fallback:
    ForeTwist -> Forearm -> Hand -> Root(0).
    """
    donor_names = [_bone_name(b) for b in donor_bones]
    target_names = [_bone_name(b) for b in target_bones]

    target_lower = [b.lower() for b in target_names]
    target_clean = [_clean_bone(b) for b in target_names]

    is_swapped = False
    if donor_matrices is not None and target_matrices is not None:
        d_lat = detect_rig_laterality(donor_bones, donor_matrices)
        t_lat = detect_rig_laterality(target_bones, target_matrices)
        is_swapped = (d_lat != t_lat)

    remap: Dict[int, int] = {}

    def find_target_by_terms(terms: List[str]) -> int:
        matches: List[int] = []
        for term in terms:
            t_clean = _clean_bone(term)
            for idx, n_clean in enumerate(target_clean):
                if t_clean in n_clean:
                    matches.append(idx)
        if not matches:
            return -1
        if target_activity:
            # Prioritize candidate bones that actually have active rotation animation!
            active_candidates = [m for m in matches if target_activity.get(m, False)]
            if active_candidates:
                return active_candidates[0]
        return matches[0]

    for d_idx, d_name in enumerate(donor_names):
        d_low = d_name.lower()
        d_clean = _clean_bone(d_name)
        is_arm_bone = any(k in d_clean for k in ("foretwist", "forearm", "hand", "finger", "wrist", "arm"))

        if is_arm_bone and is_swapped:
            # Rig laterality is inverted: swap Left <-> Right search terms
            is_left = any(k in d_low for k in ("l_", "left", ".l", " l ", "_l")) or d_clean.startswith("l")
            # If donor is Left, search target for Right (since target's Right is spatially on the Left side)
            target_side = "r" if is_left else "l"
            target_full = "right" if is_left else "left"

            if "foretwist" in d_clean:
                candidates = [
                    f"{target_side}_foretwist", f"{target_full}_foretwist",
                    f"{target_side}_forearm", f"{target_full}_forearm",
                    f"{target_side}_hand", f"{target_full}_hand"
                ]
            elif "forearm" in d_clean:
                candidates = [
                    f"{target_side}_forearm", f"{target_full}_forearm",
                    f"{target_side}_hand", f"{target_full}_hand"
                ]
            elif "finger" in d_clean:
                candidates = [f"{target_side}_hand", f"{target_full}_hand"]
            elif "hand" in d_clean:
                candidates = [f"{target_side}_hand", f"{target_full}_hand"]
            else:
                candidates = [f"{target_side}_forearm", f"{target_full}_forearm"]

            matched = find_target_by_terms(candidates)
            if matched >= 0:
                remap[d_idx] = matched
                continue

        # 1. Exact match (when laterality is not swapped or for non-arm bones)
        if d_low in target_lower and not (is_arm_bone and is_swapped):
            remap[d_idx] = target_lower.index(d_low)
            continue

        # 2. Cleaned name match
        if d_clean in target_clean and not (is_arm_bone and is_swapped):
            remap[d_idx] = target_clean.index(d_clean)
            continue

        # 3. ForeTwist fallback hierarchy: ForeTwist -> Forearm -> Hand
        if "foretwist" in d_clean:
            is_left = any(k in d_low for k in ("l_", "left", ".l", " l ", "_l")) or d_clean.startswith("l")
            candidates = [
                "l_foretwist", "left_foretwist", "l_forearm", "left_forearm", "l_hand", "left_hand"
            ] if is_left else [
                "r_foretwist", "right_foretwist", "r_forearm", "right_forearm", "r_hand", "right_hand"
            ]
            matched = find_target_by_terms(candidates)
            if matched >= 0:
                remap[d_idx] = matched
                continue

        # 4. Forearm fallback to Hand
        if "forearm" in d_clean:
            is_left = any(k in d_low for k in ("l_", "left", ".l", " l ", "_l")) or d_clean.startswith("l")
            candidates = ["l_forearm", "left_forearm", "l_hand", "left_hand"] if is_left else ["r_forearm", "right_forearm", "r_hand", "right_hand"]
            matched = find_target_by_terms(candidates)
            if matched >= 0:
                remap[d_idx] = matched
                continue

        # 5. Finger fallback to Hand
        if "finger" in d_clean or "hand" in d_clean:
            is_left = any(k in d_low for k in ("l_", "left", ".l", " l ", "_l")) or d_clean.startswith("l")
            candidates = ["l_hand", "left_hand"] if is_left else ["r_hand", "right_hand"]
            matched = find_target_by_terms(candidates)
            if matched >= 0:
                remap[d_idx] = matched
                continue

        # 6. Default fallback to bone 0 (root)
        remap[d_idx] = 0

    return remap


def preflight_safety_check(
    target_data: bytes,
    donor_data: bytes,
    scale_ratio: float,
) -> Tuple[bool, List[str]]:
    """
    Validates GoldSrc engine limits before transplant:
    - Target and donor have valid IDST v10 headers.
    - Resulting bodyparts count <= 32 (MAXSTUDIOBODYPARTS).
    - Submodel vertex count <= 2048 (MAXSTUDIOVERTS).
    """
    issues: List[str] = []

    if len(target_data) < 212:
        return False, ["Target file too short to be a valid GoldSrc StudioModel."]
    if len(donor_data) < 212:
        return False, ["Donor file too short to be a valid GoldSrc StudioModel."]

    t_magic, t_ver = struct.unpack_from("<4sI", target_data, 0)
    if t_magic != STUDIO_MAGIC or t_ver != STUDIO_VERSION:
        issues.append(f"Target has invalid StudioModel magic/version: {t_magic} v{t_ver}")

    d_magic, d_ver = struct.unpack_from("<4sI", donor_data, 0)
    if d_magic != STUDIO_MAGIC or d_ver != STUDIO_VERSION:
        issues.append(f"Donor has invalid StudioModel magic/version: {d_magic} v{d_ver}")

    num_target_bp = struct.unpack_from("<I", target_data, 204)[0]

    # Check donor submodel vertex counts
    d_num_bp, d_bp_idx = struct.unpack_from("<II", donor_data, 204)
    for bp in range(d_num_bp):
        bp_off = d_bp_idx + bp * 76
        if bp_off + 76 <= len(donor_data):
            _, nummodels, _, modelindex = struct.unpack_from("<64siii", donor_data, bp_off)
            for m in range(nummodels):
                m_off = modelindex + m * 112
                if m_off + 112 <= len(donor_data):
                    m_name, _, _, _, _, numverts = struct.unpack_from("<64sif3I", donor_data, m_off)
                    m_name_str = m_name.split(b"\x00")[0].decode("latin1", errors="ignore")
                    if numverts > MAXSTUDIOVERTS:
                        issues.append(
                            f"Donor submodel '{m_name_str}' exceeds MAXSTUDIOVERTS limit: {numverts} > {MAXSTUDIOVERTS}."
                        )

    return len(issues) == 0, issues


def transplant_3d_sleeves(
    target_path: Optional[Union[str, Path]] = None,
    donor_path: Optional[Union[str, Path]] = None,
    out_path: Optional[Union[str, Path]] = None,
    scale_ratio: Optional[float] = None,
    cuff_offset: float = 0.0,
    sleeve_preset: Optional[str] = None,
    sleeve_texture: Optional[Union[str, Path, bytes, Image.Image]] = None,
    create_backup: bool = True,
    root_dir: Optional[Union[str, Path]] = None,
    target_model_path: Optional[Union[str, Path]] = None,
    donor_preset: Optional[str] = None,
    output_path: Optional[Union[str, Path]] = None,
    workspace_root: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Transplants 3D sleeve submodels into a target viewmodel (e.g. Terrorist bare arm model).
    - Removes bare arm bodyparts (t_arm) or replaces existing loose sleeve submodels.
    - Injects volumetric jacket sleeve submodels (preserving 3 separate submodels ct_arms_01..03).
    - Dynamically scales geometry based on bone length ratio.
    - Remaps bones with spatial laterality awareness (inverts matching if rig is flipped).
    - Applies 3D rigid bone basis transforms (inv(M_target) * M_donor) to vertices and normals.
    - Adds / synchronizes sleeve.bmp with optional preset photographic color grading.
    - Performs atomic file replacement with .bak backup.
    """
    tgt = target_path or target_model_path
    if not tgt:
        raise ValueError("Target model path is required.")
    target_p = Path(tgt).resolve()
    if not target_p.is_file():
        raise FileNotFoundError(f"Target model not found: {target_p}")

    config = StudioConfig.get_instance()
    root_val = root_dir or workspace_root or config.get_game_root()
    root = Path(root_val).resolve()
    eff_out = out_path or output_path
    out_p = Path(eff_out).resolve() if eff_out else target_p

    # Resolve sleeve preset and donor
    effective_preset = sleeve_preset or donor_preset
    preset_meta = None
    if effective_preset and effective_preset.lower() in SLEEVE_PRESETS:
        preset_meta = SLEEVE_PRESETS[effective_preset.lower()]

    if donor_path is None:
        if preset_meta and preset_meta["default_donor"]:
            donor_p = root / preset_meta["default_donor"]
            if not donor_p.is_file():
                cand1 = root / "cstrike" / "models" / "custom_skins" / "ct" / "v_m4a1.mdl"
                cand2 = root / "cstrike" / "models" / "custom_skins" / "ct" / "v_ak47.mdl"
                donor_p = cand1 if cand1.is_file() else cand2
        else:
            donor_p = root / "cstrike" / "models" / "custom_skins" / "ct" / "v_m4a1.mdl"
    else:
        donor_p = Path(donor_path).resolve()

    # Prevent self-donor loop
    if donor_p.resolve() == target_p.resolve():
        cand1 = root / "cstrike" / "models" / "custom_skins" / "ct" / "v_m4a1.mdl"
        cand2 = root / "cstrike" / "models" / "custom_skins" / "ct" / "v_ak47.mdl"
        donor_p = cand1 if cand1.is_file() else cand2

    if not donor_p.is_file():
        raise FileNotFoundError(f"Donor model not found: {donor_p}")

    # 1. Load target and donor binaries
    with open(target_p, "rb") as f:
        target_data = bytearray(f.read())
    with open(donor_p, "rb") as f:
        donor_data = f.read()

    # 2. Check if a paired CT model exists for fast-path native sync
    target_weapon_name = target_p.stem
    if target_weapon_name.startswith("v_"):
        target_weapon_name = target_weapon_name[2:]

    paired_ct_model = root / "cstrike" / "models" / "custom_skins" / "ct" / f"v_{target_weapon_name}.mdl"
    is_paired_weapon = (
        donor_path is None
        and paired_ct_model.is_file()
        and paired_ct_model.resolve() != target_p.resolve()
    )

    # 3. Calculate dynamic scale ratio if not explicitly passed
    if scale_ratio is None or scale_ratio <= 0:
        calc_ratio, ratio_desc = calculate_scale_ratio(target_p, donor_p)
        effective_scale = calc_ratio
    else:
        effective_scale = float(scale_ratio)
        ratio_desc = f"Manual override: {effective_scale:.4f}x"

    # 4. Pre-flight engine safety check
    is_safe, safety_issues = preflight_safety_check(target_data, donor_data, effective_scale)
    if not is_safe:
        return {
            "success": False,
            "error": f"Pre-flight safety checks failed: {'; '.join(safety_issues)}",
            "safety_issues": safety_issues,
        }

    # 5. Create atomic backup of target before modification
    if create_backup and target_p.exists():
        arm_info = detect_arm_type(target_p)
        bak_suffix = ".manset_arm.bak" if arm_info["is_bare"] else ".bak"
        b_dir = get_model_backup_dir(target_p, create=True)
        bak_file = b_dir / f"{target_p.stem}{bak_suffix}"
        if not bak_file.exists():
            shutil.copy2(target_p, bak_file)

    # 6. Check fast-path native sync for paired weapons
    if is_paired_weapon and effective_preset is None and sleeve_texture is None:
        base_m = MdlModel(paired_ct_model)
        target_m = MdlModel(target_p)

        for t_tex in target_m.textures:
            lower = t_tex.name.lower()
            if any(k in lower for k in ("arm", "bare", "sleeve")):
                continue
            base_tex = base_m.get_texture_by_name(t_tex.name)
            if base_tex:
                if (base_tex.width, base_tex.height) == (t_tex.width, t_tex.height):
                    base_m.inject_texture_payload(base_tex, t_tex.raw_data, new_flags=base_tex.flags)
                else:
                    rgba = t_tex.to_rgba_image().resize((base_tex.width, base_tex.height), Image.Resampling.LANCZOS)
                    pix, pal = quantize_goldsrc(rgba, is_masked=t_tex.is_masked, defringe=False)
                    base_m.inject_texture_payload(base_tex, pix + pal, new_flags=base_tex.flags)

        saved_path = base_m.save_atomic(out_p, create_backup=False)
        health = validate_model_health(saved_path)

        return {
            "success": True,
            "message": f"Successfully transplanted 3D CT loose sleeves into {out_p.name}.",
            "method": "paired_weapon_sync",
            "scale_ratio": effective_scale,
            "scale_description": ratio_desc,
            "submodels_injected": ["ct_arms_01", "ct_arms_02", "ct_arms_03"],
            "saved_path": str(saved_path),
            "health": health,
        }

    # 7. Generic 3D Submodel Splice Engine with 3D Rigid Basis Transform
    t_parsed = parse_model_geometry(bytes(target_data))
    d_parsed = parse_model_geometry(donor_data)

    donor_bones, donor_matrices = compute_bone_bind_matrices(donor_data)
    target_bones, target_matrices = compute_bone_bind_matrices(bytes(target_data))

    d_laterality = detect_rig_laterality(donor_bones, donor_matrices)
    t_laterality = detect_rig_laterality(target_bones, target_matrices)

    t_activity = get_bone_rotation_activity(bytes(target_data))
    bone_remap = build_bone_remapping(donor_bones, target_bones, donor_matrices, target_matrices, target_activity=t_activity)

    # Find sleeve texture in donor
    donor_sleeve_tex = next((t for t in d_parsed["textures"] if "sleeve" in t["name"].lower()), None)
    if not donor_sleeve_tex:
        donor_sleeve_tex = next((t for t in d_parsed["textures"] if t.get("role") == "glove" or "arm" in t["name"].lower()), None)

    if not donor_sleeve_tex and d_parsed["textures"]:
        donor_sleeve_tex = d_parsed["textures"][0]

    s_w = donor_sleeve_tex["width"] if donor_sleeve_tex else 512
    s_h = donor_sleeve_tex["height"] if donor_sleeve_tex else 512
    s_flags = donor_sleeve_tex["flags"] if donor_sleeve_tex else 0
    s_payload = donor_sleeve_tex["payload"] if donor_sleeve_tex else (b"\x00" * (s_w * s_h + 768))

    # Apply preset color adjustments or custom sleeve texture
    if preset_meta and preset_meta.get("color_adjustments") and len(s_payload) == (s_w * s_h + 768):
        p_img = Image.frombytes("P", (s_w, s_h), s_payload[: s_w * s_h])
        p_img.putpalette(s_payload[s_w * s_h : s_w * s_h + 768])
        rgba = p_img.convert("RGBA")
        adjusted = adjust_color_grading(rgba, **preset_meta["color_adjustments"])
        pix, pal = quantize_goldsrc(adjusted, is_masked=False, defringe=False)
        sleeve_payload = pix + pal
    elif sleeve_texture is not None:
        c_img = load_image(sleeve_texture).convert("RGBA")
        if c_img.size != (s_w, s_h):
            c_img = c_img.resize((s_w, s_h), Image.Resampling.LANCZOS)
        pix, pal = quantize_goldsrc(c_img, is_masked=False, defringe=False)
        sleeve_payload = pix + pal
    else:
        sleeve_payload = s_payload

    # Synchronize sleeve.bmp into target textures
    target_sleeve_idx = -1
    for ti, t in enumerate(t_parsed["textures"]):
        if "sleeve" in t["name"].lower():
            t["name"] = "sleeve.bmp"
            t["name_raw"] = b"sleeve.bmp\x00" + b"\x00" * 53
            t["width"] = s_w
            t["height"] = s_h
            t["flags"] = s_flags
            t["payload"] = sleeve_payload
            target_sleeve_idx = ti
            break

    if target_sleeve_idx < 0:
        for ti, t in enumerate(t_parsed["textures"]):
            if any(k in t["name"].lower() for k in ("bare", "t_arm")):
                t["name"] = "sleeve.bmp"
                t["name_raw"] = b"sleeve.bmp\x00" + b"\x00" * 53
                t["width"] = s_w
                t["height"] = s_h
                t["flags"] = s_flags
                t["payload"] = sleeve_payload
                target_sleeve_idx = ti
                break

    if target_sleeve_idx < 0:
        target_sleeve_idx = len(t_parsed["textures"])
        t_parsed["textures"].append({
            "index": target_sleeve_idx,
            "name": "sleeve.bmp",
            "name_raw": b"sleeve.bmp\x00" + b"\x00" * 53,
            "flags": s_flags,
            "width": s_w,
            "height": s_h,
            "data_offset": 0,
            "payload": sleeve_payload,
            "role": "glove",
            "label": "Gloves / Arm",
        })
        t_parsed["skin_table"].append(target_sleeve_idx)

    # Extract sleeve submodels from donor
    # Note: For knife models, arms animate independently (slashing/stabbing).
    # Omitting connected chest mesh (ct_arms_03) prevents torso stretching.
    is_knife_model = "knife" in target_p.name.lower()
    sleeve_bps = []
    for bp in d_parsed["bodyparts"]:
        s_models = []
        for m in bp["models"]:
            m_low = m["name"].lower()
            bp_low = bp["name"].lower()
            if is_knife_model and "ct_arms_03" in m_low:
                continue
            if (
                any(k in m_low for k in ("ct_arms", "cs_arms_sleeved", "sleeve"))
                or ("sleeve" in bp_low and not any(k in m_low for k in ("sport", "glove", "hand", "finger")))
            ):
                s_models.append(m)
        if s_models:
            sleeve_bps.append((bp, s_models))

    if not sleeve_bps and donor_sleeve_tex:
        d_sleeve_idx = donor_sleeve_tex.get("index", 0)
        for bp in d_parsed["bodyparts"]:
            s_models = []
            for m in bp["models"]:
                if any(mesh.get("actual_tex_idx") == d_sleeve_idx or mesh.get("skinref") == d_sleeve_idx for mesh in m["meshes"]):
                    s_models.append(m)
            if s_models:
                sleeve_bps.append((bp, s_models))

    if not sleeve_bps:
        return {
            "success": False,
            "error": f"No sleeve submodels (ct_arms_01..03) could be extracted from donor model '{donor_p.name}'.",
        }

    # Transform vertices and normals using 3D rigid bone basis transforms (inv(M_target) * M_donor)
    new_sleeve_bps = []
    injected_submodel_names = []
    for bp, models in sleeve_bps:
        scaled_models = []
        for m in models:
            new_m = copy.deepcopy(m)
            injected_submodel_names.append(new_m["name"])
            new_m["radius"] = float(m["radius"]) * float(effective_scale)

            nv = m["numverts"]
            vinfo = list(m["vertinfo_raw"])
            scaled_v = bytearray()
            new_vinfo = bytearray()

            for vi in range(nv):
                vx, vy, vz = struct.unpack_from("<3f", m["verts_raw"], vi * 12)
                b_donor = vinfo[vi] if vi < len(vinfo) else 0
                b_target = bone_remap.get(b_donor, 0)

                m_donor_b = donor_matrices[b_donor] if b_donor < len(donor_matrices) else np.identity(4, dtype=np.float32)
                m_target_b = target_matrices[b_target] if b_target < len(target_matrices) else np.identity(4, dtype=np.float32)

                # 1. Transform vertex to donor world position
                vh = np.array([vx * effective_scale, vy * effective_scale, vz * effective_scale, 1.0], dtype=np.float32)
                w_donor = np.matmul(m_donor_b, vh)[:3]

                # 2. Compute arm-axis direction vector in world space towards hand/wrist
                # Identify whether this arm bone belongs to spatial Right or Left arm
                b_target_clean = _clean_bone(target_bones[b_target]["name"])
                is_r_side = b_target_clean.startswith("r") or "rhand" in b_target_clean or "rfore" in b_target_clean
                target_hand_term = "rhand" if is_r_side else "lhand"

                hand_idx = -1
                for bi, tb in enumerate(target_bones):
                    tb_c = _clean_bone(tb["name"])
                    if target_hand_term in tb_c:
                        hand_idx = bi
                        break

                effective_cuff_shift = float(cuff_offset)
                if effective_cuff_shift == 0.0 and is_knife_model:
                    # Auto-bridge the ~3.4 unit gap between donor sleeve cuff and short sport gloves (overlap ~0.5 unit)
                    effective_cuff_shift = 5.4

                if effective_cuff_shift != 0.0 and hand_idx >= 0 and hand_idx < len(target_matrices):
                    p_hand = target_matrices[hand_idx][:3, 3]
                    p_arm = m_target_b[:3, 3]
                    d_arm = p_hand - p_arm
                    d_len = float(np.linalg.norm(d_arm))
                    if d_len > 1e-4:
                        u_arm = d_arm / d_len
                        w_donor = w_donor + u_arm * effective_cuff_shift

                # 3. Transform to target local bone coordinate space
                inv_m_target = np.linalg.inv(m_target_b)
                w_donor_h = np.array([w_donor[0], w_donor[1], w_donor[2], 1.0], dtype=np.float32)
                v_target = np.matmul(inv_m_target, w_donor_h)[:3]

                scaled_v.extend(struct.pack("<3f", float(v_target[0]), float(v_target[1]), float(v_target[2])))
                new_vinfo.append(min(255, max(0, b_target)))

            new_m["verts_raw"] = bytes(scaled_v)
            new_m["vertinfo_raw"] = bytes(new_vinfo)

            # Normals: transform by rotation submatrix: inv(R_target) * R_donor
            nn = m["numnorms"]
            ninfo = list(m["norminfo_raw"])
            scaled_n = bytearray()
            new_ninfo = bytearray()

            for ni in range(nn):
                nx, ny, nz = struct.unpack_from("<3f", m["norms_raw"], ni * 12)
                b_donor = ninfo[ni] if ni < len(ninfo) else 0
                b_target = bone_remap.get(b_donor, 0)

                m_donor_b = donor_matrices[b_donor] if b_donor < len(donor_matrices) else np.identity(4, dtype=np.float32)
                m_target_b = target_matrices[b_target] if b_target < len(target_matrices) else np.identity(4, dtype=np.float32)

                r_donor = m_donor_b[:3, :3]
                r_target = m_target_b[:3, :3]

                r_trans = np.matmul(np.linalg.inv(r_target), r_donor)
                n_vec = np.array([nx, ny, nz], dtype=np.float32)
                n_target = np.matmul(r_trans, n_vec)
                n_len = np.linalg.norm(n_target)
                if n_len > 1e-6:
                    n_target /= n_len
                else:
                    n_target = np.array([0.0, 1.0, 0.0], dtype=np.float32)

                scaled_n.extend(struct.pack("<3f", float(n_target[0]), float(n_target[1]), float(n_target[2])))
                new_ninfo.append(min(255, max(0, b_target)))

            new_m["norms_raw"] = bytes(scaled_n)
            new_m["norminfo_raw"] = bytes(new_ninfo)

            for mesh in new_m["meshes"]:
                mesh["skinref"] = target_sleeve_idx
                mesh["actual_tex_idx"] = target_sleeve_idx

            scaled_models.append(new_m)

        if scaled_models:
            new_bp = copy.deepcopy(bp)
            new_bp["models"] = scaled_models
            new_sleeve_bps.append(new_bp)

    # Replace bare arm or existing sleeve bodypart(s) in target
    final_bps = []
    inserted = False
    for bp in t_parsed["bodyparts"]:
        is_arm_or_sleeve = any(
            any(k in m["name"].lower() for k in ("t_arm", "bare_arm", "cs_arms_reference", "ct_arms", "cs_arms_sleeved"))
            and not any(k in m["name"].lower() for k in ("sport", "glove", "hand", "finger"))
            for m in bp["models"]
        ) or (
            bp["name"].lower() == "weapon" and any("ct_arms" in m["name"].lower() for m in bp["models"])
        )
        if is_arm_or_sleeve:
            if not inserted:
                final_bps.extend(new_sleeve_bps)
                inserted = True
        else:
            final_bps.append(bp)

    if not inserted:
        glove_idx = -1
        for bi, bp in enumerate(final_bps):
            if any(any(k in m["name"].lower() for k in ("sport", "glove", "hand")) for m in bp["models"]):
                glove_idx = bi
        if glove_idx >= 0:
            final_bps = final_bps[: glove_idx + 1] + new_sleeve_bps + final_bps[glove_idx + 1 :]
        else:
            final_bps.extend(new_sleeve_bps)

    if len(final_bps) > MAXSTUDIOBODYPARTS:
        return {
            "success": False,
            "error": f"Resulting bodyparts count ({len(final_bps)}) exceeds GoldSrc limit of {MAXSTUDIOBODYPARTS}.",
        }

    t_parsed["bodyparts"] = final_bps

    # Serialize new binary
    out_data = serialize_model_binary(
        header_block1=t_parsed["header_block1"],
        bodyparts=t_parsed["bodyparts"],
        textures=t_parsed["textures"],
        skin_table=t_parsed["skin_table"],
        numskinfamilies=t_parsed["numskinfamilies"],
    )

    temp_out = out_p.with_suffix(".tmp_sleeve.mdl")
    temp_out.write_bytes(out_data)
    shutil.move(str(temp_out), str(out_p))

    health = validate_model_health(out_p)

    return {
        "success": True,
        "message": f"Successfully injected 3D sleeves ({len(injected_submodel_names)} submodels) into {out_p.name}.",
        "method": "generic_submodel_splice",
        "scale_ratio": effective_scale,
        "scale_description": ratio_desc,
        "rig_laterality": t_laterality,
        "donor_laterality": d_laterality,
        "submodels_injected": injected_submodel_names,
        "saved_path": str(out_p),
        "health": health,
    }
