"""
slot_geometry.py - Modular 3D Geometry Engine for Counter-Strike 1.6 GoldSrc StudioModels (IDST v10).

Provides:
1. Coordinate transformation solvers between Three.js world space and GoldSrc world space.
2. Local bone matrix inversion and forward transformation solvers.
3. In-place slot quad repositioning (Solusi B) with 0 byte size change.
4. Native 3D submesh & texture slot injection (Solusi A) via Appended Table Pointer Relocation.
5. Immutable backups (.orig.mdl) and snapshot undo caches (.undo_cache/).
"""

import io
import math
import os
from pathlib import Path
import shutil
import struct
import time
from typing import Dict, List, Optional, Tuple, Union, Any
import numpy as np
from PIL import Image

# GoldSrc StudioModel Constants
STUDIO_MAGIC = b"IDST"
STUDIO_VERSION = 10

STUDIO_NF_FLATSHADE = 0x0001
STUDIO_NF_CHROME = 0x0002
STUDIO_NF_FULLBRIGHT = 0x0004
STUDIO_NF_NOMIPS = 0x0008
STUDIO_NF_ALPHA = 0x0010
STUDIO_NF_ADDITIVE = 0x0020
STUDIO_NF_MASKED = 0x0040

ROLE_SKIN = "skin"
ROLE_STICKER = "sticker"
ROLE_GLOVE = "glove"
ROLE_STATTRAK = "stattrak"
ROLE_OTHER = "other"


# =========================================================================
# 1. Coordinate Space & Matrix Solvers
# =========================================================================

def threejs_to_goldsrc_world(
    pos: Union[List[float], Tuple[float, float, float], np.ndarray],
    normal: Optional[Union[List[float], Tuple[float, float, float], np.ndarray]] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Converts coordinates from Three.js world space to GoldSrc world space.
    Three.js: X=right, Y=up, Z=towards camera
    GoldSrc:  X=forward, Y=left, Z=up
    Formulas:
        P_goldsrc = (-P_three_z, -P_three_x, P_three_y)
        N_goldsrc = (-N_three_z, -N_three_x, N_three_y)
    """
    px, py, pz = float(pos[0]), float(pos[1]), float(pos[2])
    if math.isnan(px) or math.isnan(py) or math.isnan(pz) or math.isinf(px) or math.isinf(py) or math.isinf(pz):
        raise ValueError("Position coordinates contain NaN or Inf")
    gw_pos = np.array([-pz, -px, py], dtype=np.float32)

    gw_norm = None
    if normal is not None:
        nx, ny, nz = float(normal[0]), float(normal[1]), float(normal[2])
        if math.isnan(nx) or math.isnan(ny) or math.isnan(nz) or math.isinf(nx) or math.isinf(ny) or math.isinf(nz):
            nx, ny, nz = 0.0, 1.0, 0.0
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length > 1e-6:
            nx /= length
            ny /= length
            nz /= length
        else:
            nx, ny, nz = 0.0, 1.0, 0.0
        gw_norm = np.array([-nz, -nx, ny], dtype=np.float32)
        norm_len = np.linalg.norm(gw_norm)
        if norm_len > 1e-6:
            gw_norm /= norm_len
        else:
            gw_norm = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    return gw_pos, gw_norm


def goldsrc_world_to_threejs(
    pos: Union[List[float], Tuple[float, float, float], np.ndarray],
    normal: Optional[Union[List[float], Tuple[float, float, float], np.ndarray]] = None,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Converts coordinates from GoldSrc world space to Three.js world space.
    Inverse of threejs_to_goldsrc_world:
        P_three = (-P_goldsrc_y, P_goldsrc_z, -P_goldsrc_x)
        N_three = (-N_goldsrc_y, N_goldsrc_z, -N_goldsrc_x)
    """
    gx, gy, gz = float(pos[0]), float(pos[1]), float(pos[2])
    three_pos = np.array([-gy, gz, -gx], dtype=np.float32)

    three_norm = None
    if normal is not None:
        gnx, gny, gnz = float(normal[0]), float(normal[1]), float(normal[2])
        three_norm = np.array([-gny, gnz, -gnx], dtype=np.float32)
        norm_len = np.linalg.norm(three_norm)
        if norm_len > 1e-6:
            three_norm /= norm_len

    return three_pos, three_norm


def compute_tangent_basis(
    target_normal: Union[List[float], Tuple[float, float, float], np.ndarray],
    rotation_deg: float = 0.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Computes an orthonormal tangent basis (U, V, N) for a given surface normal in Three.js world space,
    rotated around N by rotation_deg (matching Three.js PlaneGeometry orientation).
    """
    n = np.array(target_normal, dtype=np.float32)
    norm_len = np.linalg.norm(n)
    if norm_len < 1e-6:
        n = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    else:
        n = n / norm_len

    # Pick an arbitrary reference vector not collinear with n
    if abs(n[1]) < 0.9:
        ref = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    elif abs(n[0]) < 0.9:
        ref = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    else:
        ref = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    u0 = np.cross(ref, n)
    u0_len = np.linalg.norm(u0)
    if u0_len > 1e-6:
        u0 /= u0_len
    else:
        u0 = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    v0 = np.cross(n, u0)
    v0 /= max(1e-6, np.linalg.norm(v0))

    # Rotate U0 and V0 around N by rotation_deg (counter-clockwise around N)
    rad = math.radians(rotation_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    u = cos_a * u0 + sin_a * v0
    v = -sin_a * u0 + cos_a * v0

    return u, v, n


def make_bone_matrix(pos: List[float], rot: List[float]) -> np.ndarray:
    """Half-Life SDK AngleMatrix (rot: [0]=roll/X, [1]=pitch/Y, [2]=yaw/Z)."""
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


def compute_bone_world_matrices(data: Union[bytes, bytearray]) -> List[np.ndarray]:
    """
    Computes 4x4 world transformation matrices for all bones in the StudioModel,
    including frame 0 animation deltas for Sequence 0 (matching extract_model_3d).
    """
    if len(data) < 188:
        raise ValueError("Model data too short")

    numbones, boneindex = struct.unpack_from("<II", data, 140)
    bones = []
    for b in range(numbones):
        b_offset = boneindex + b * 112
        if b_offset + 112 > len(data):
            break
        name_bytes, parent, flags = struct.unpack_from("<32sii", data, b_offset)
        vals = struct.unpack_from("<6f", data, b_offset + 64)
        scales = struct.unpack_from("<6f", data, b_offset + 88)
        bones.append({
            "parent": parent,
            "pos": list(vals[:3]),
            "rot": list(vals[3:]),
            "scale": list(scales),
        })

    # Evaluate sequence 0 frame 0 anim deltas
    if len(data) >= 180:
        numseq, seqindex = struct.unpack_from("<II", data, 164)
        numseqgroups, seqgroupindex = struct.unpack_from("<II", data, 172)
        if numseq > 0 and 0 < seqindex < len(data) and numseqgroups > 0 and 0 < seqgroupindex < len(data):
            try:
                _, _, _, seqgroup_data_off = struct.unpack_from("<32s64sii", data, seqgroupindex)
                if seqindex + 176 <= len(data):
                    animindex = struct.unpack_from("<i", data, seqindex + 124)[0]
                    seqgroup = struct.unpack_from("<i", data, seqindex + 156)[0]
                    if seqgroup == 0 and animindex > 0:
                        anim_base = seqgroup_data_off + animindex
                        for b_idx in range(len(bones)):
                            bone_anim_off = anim_base + b_idx * 12
                            if bone_anim_off + 12 <= len(data):
                                anim_offsets = struct.unpack_from("<6H", data, bone_anim_off)
                                b_scales = bones[b_idx]["scale"]
                                for j in range(3):
                                    off_j = anim_offsets[j]
                                    if off_j != 0:
                                        ptr = bone_anim_off + off_j
                                        if ptr + 4 <= len(data):
                                            valid, _ = struct.unpack_from("<BB", data, ptr)
                                            if valid > 0:
                                                anim_val = struct.unpack_from("<h", data, ptr + 2)[0]
                                                bones[b_idx]["pos"][j] += anim_val * b_scales[j]
                                for j in range(3):
                                    off_j = anim_offsets[j + 3]
                                    if off_j != 0:
                                        ptr = bone_anim_off + off_j
                                        if ptr + 4 <= len(data):
                                            valid, _ = struct.unpack_from("<BB", data, ptr)
                                            if valid > 0:
                                                anim_val = struct.unpack_from("<h", data, ptr + 2)[0]
                                                bones[b_idx]["rot"][j] += anim_val * b_scales[j + 3]
            except Exception:
                pass

    world_matrices = []
    for b in bones:
        local_m = make_bone_matrix(b["pos"], b["rot"])
        if b["parent"] == -1 or b["parent"] < 0 or b["parent"] >= len(world_matrices):
            world_matrices.append(local_m)
        else:
            world_matrices.append(np.matmul(world_matrices[b["parent"]], local_m))

    return world_matrices


def world_to_local_bone(
    gw_pos: np.ndarray,
    gw_normal: Optional[np.ndarray],
    bone_world_matrix: np.ndarray,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Transforms position and normal from GoldSrc world space into local bone coordinate space.
        P_local = inv(M_bone) * P_goldsrc
        N_local = inv(R_bone) * N_goldsrc
    """
    inv_m = np.linalg.inv(bone_world_matrix)
    pos_hom = np.array([gw_pos[0], gw_pos[1], gw_pos[2], 1.0], dtype=np.float32)
    local_pos_hom = np.matmul(inv_m, pos_hom)
    local_pos = local_pos_hom[:3] / max(1e-9, local_pos_hom[3])

    local_normal = None
    if gw_normal is not None:
        rot_sub = bone_world_matrix[:3, :3]
        inv_rot = np.linalg.inv(rot_sub)
        local_normal = np.matmul(inv_rot, gw_normal[:3])
        norm_len = np.linalg.norm(local_normal)
        if norm_len > 1e-6:
            local_normal /= norm_len
        else:
            local_normal = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    return local_pos, local_normal


def local_bone_to_world(
    local_pos: np.ndarray,
    local_normal: Optional[np.ndarray],
    bone_world_matrix: np.ndarray,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Transforms position and normal from local bone coordinate space into GoldSrc world space.
        P_goldsrc = M_bone * P_local
        N_goldsrc = R_bone * N_local
    """
    pos_hom = np.array([local_pos[0], local_pos[1], local_pos[2], 1.0], dtype=np.float32)
    world_pos_hom = np.matmul(bone_world_matrix, pos_hom)
    world_pos = world_pos_hom[:3] / max(1e-9, world_pos_hom[3])

    world_normal = None
    if local_normal is not None:
        rot_sub = bone_world_matrix[:3, :3]
        world_normal = np.matmul(rot_sub, local_normal[:3])
        norm_len = np.linalg.norm(world_normal)
        if norm_len > 1e-6:
            world_normal /= norm_len

    return world_pos, world_normal


def find_weapon_root_bone(data: Union[bytes, bytearray]) -> int:
    """
    Identifies the primary weapon bone ID in the StudioModel.
    Checks for parent/root/weapon keywords or the most frequently referenced bone in weapon bodyparts.
    """
    numbones, boneindex = struct.unpack_from("<II", data, 140)
    weapon_bones = []
    for b in range(numbones):
        b_offset = boneindex + b * 112
        name = struct.unpack_from("<32s", data, b_offset)[0].split(b"\x00")[0].decode("latin1", errors="ignore").lower()
        if "parent" in name or "weapon" in name or "root" in name:
            weapon_bones.append(b)

    if weapon_bones:
        # Prefer bones with 'parent'
        for wb in weapon_bones:
            b_offset = boneindex + wb * 112
            bname = struct.unpack_from("<32s", data, b_offset)[0].split(b"\x00")[0].decode("latin1", errors="ignore").lower()
            if "parent" in bname:
                return wb
        return weapon_bones[0]

    # Fallback: scan bodyparts for most common non-hand bone
    numbodyparts, bodypartindex = struct.unpack_from("<II", data, 204)
    bone_counts: Dict[int, int] = {}
    for bp in range(numbodyparts):
        bp_offset = bodypartindex + bp * 76
        nummodels, base, modelindex = struct.unpack_from("<3i", data, bp_offset + 64)
        for m in range(nummodels):
            m_offset = modelindex + m * 112
            numverts, vertinfoindex = struct.unpack_from("<II", data, m_offset + 80)
            for v in range(numverts):
                if vertinfoindex + v < len(data):
                    bid = data[vertinfoindex + v]
                    bone_counts[bid] = bone_counts.get(bid, 0) + 1

    if bone_counts:
        sorted_bones = sorted(bone_counts.items(), key=lambda item: item[1], reverse=True)
        return sorted_bones[0][0]

    return 0


# =========================================================================
# 2. Immutable Backups & Snapshot Cache
# =========================================================================

def save_geometry_snapshot(mdl_path: Union[str, Path], action: str = "geometry") -> Path:
    """
    Creates an immutable original backup (.orig.mdl) if missing, and saves a timestamped snapshot
    to .undo_cache/ for robust multi-step Ctrl+Z undo/redo.
    """
    path = Path(mdl_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Model file not found: {path}")

    # 1. Immutable original in dedicated backup folder
    existing_bak, _ = find_model_backup(path)
    if not existing_bak:
        orig_path = get_model_backup_path(path, ext=".orig.mdl")
        shutil.copy2(path, orig_path)

    # 2. Undo cache
    undo_dir = path.parent / ".undo_cache" / path.stem
    undo_dir.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time() * 1000)
    snap_path = undo_dir / f"{timestamp}_{action}.mdl"
    shutil.copy2(path, snap_path)

    # Maintain max 20 snapshots
    snaps = sorted(undo_dir.glob("*.mdl"), key=lambda p: p.stat().st_mtime)
    if len(snaps) > 20:
        for old_snap in snaps[:-20]:
            try:
                old_snap.unlink()
            except OSError:
                pass

    return snap_path


def restore_geometry_snapshot(mdl_path: Union[str, Path], snapshot_id: Optional[str] = None) -> bool:
    """
    Restores model binary from the latest snapshot in .undo_cache/, or from snapshot_id if given.
    Falls back to .orig.mdl if no snapshots remain.
    """
    path = Path(mdl_path).resolve()
    undo_dir = path.parent / ".undo_cache" / path.stem

    target_snap = None
    if snapshot_id and undo_dir.exists():
        cand = undo_dir / snapshot_id
        if cand.is_file():
            target_snap = cand

    if not target_snap and undo_dir.exists():
        snaps = sorted(undo_dir.glob("*.mdl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if snaps:
            target_snap = snaps[0]

    if target_snap and target_snap.is_file():
        # Validate target snap
        with open(target_snap, "rb") as f:
            magic, ver = struct.unpack_from("<4sI", f.read(8), 0)
        if magic == STUDIO_MAGIC and ver == STUDIO_VERSION:
            tmp = path.with_suffix(".tmp")
            shutil.copy2(target_snap, tmp)
            os.replace(tmp, path)
            try:
                target_snap.unlink()
            except OSError:
                pass
            return True

    # Fallback to backup
    orig_bak, _ = find_model_backup(path)
    if orig_bak and orig_bak.is_file():
        tmp = path.with_suffix(".tmp")
        shutil.copy2(orig_bak, tmp)
        os.replace(tmp, path)
        return True

    return False


# =========================================================================
# 3. Solusi B: In-Place Slot Quad Repositioning
# =========================================================================

def reposition_slot_quad(
    mdl_path: Union[str, Path],
    slot_identifier: Union[int, str],
    target_pos_three: Union[List[float], Tuple[float, float, float], np.ndarray],
    target_normal_three: Union[List[float], Tuple[float, float, float], np.ndarray],
    scale: float = 1.0,
    rotation: float = 0.0,
    bone_id: Optional[int] = None,
) -> dict:
    """
    Reposition an existing sticker slot's quad vertices and surface normals in-place.
    Zero file offset change, zero file size change, 100% engine compatibility.
    """
    path = Path(mdl_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Model file not found: {path}")

    # Snapshot for undo
    snap_path = save_geometry_snapshot(path, action="reposition")

    with open(path, "rb") as f:
        data = bytearray(f.read())

    if len(data) < 188:
        raise ValueError(f"File too small for GoldSrc StudioModel: {len(data)} bytes")

    magic, ver = struct.unpack_from("<4sI", data, 0)
    if magic != STUDIO_MAGIC or ver != STUDIO_VERSION:
        raise ValueError(f"Invalid StudioModel header: magic={magic}, ver={ver}")

    # Textures table
    numtextures, textureindex = struct.unpack_from("<II", data, 180)
    textures = []
    for i in range(numtextures):
        offset = textureindex + i * 80
        tname, flags, w, h, idx = struct.unpack_from("<64sIIII", data, offset)
        name_str = tname.split(b"\x00")[0].decode("latin1", errors="ignore")
        textures.append({
            "index": i,
            "name": name_str,
            "flags": flags,
            "width": w,
            "height": h,
        })

    # Resolve target texture
    from .mdl_core import classify_texture
    target_tex = None
    slot_raw = str(slot_identifier).strip()
    slot_str = slot_raw.lower()
    if slot_str.startswith("slot"):
        slot_clean = slot_str[4:].strip(" _-:")
        if slot_clean:
            slot_str = slot_clean

    # Exact name match or slot index
    for t in textures:
        role, _ = classify_texture(t["name"], t["flags"], t["width"], t["height"])
        t["role"] = role

    # 1. Check numeric slot index
    if slot_str.isdigit():
        val = int(slot_str)
        # Check by 0-based texture index
        if 0 <= val < len(textures) and textures[val]["role"] == ROLE_STICKER:
            target_tex = textures[val]
        else:
            # Check sticker slot 1..N
            stickers = [t for t in textures if t["role"] == ROLE_STICKER]
            for s in stickers:
                if f"_{val}." in s["name"].lower() or s["name"].lower().startswith(f"{val}."):
                    target_tex = s
                    break
            if not target_tex and 1 <= val <= len(stickers):
                target_tex = stickers[val - 1]

    # 2. Check name match
    if not target_tex:
        for t in textures:
            if t["name"].lower() == slot_str or t["name"].lower() == f"{slot_str}.bmp":
                target_tex = t
                break

    if not target_tex:
        for t in textures:
            if slot_str in t["name"].lower() and t["role"] == ROLE_STICKER:
                target_tex = t
                break

    if not target_tex:
        raise KeyError(f"Sticker slot '{slot_identifier}' not found in {path.name}")

    # Read skin table
    numskinref, numskinfamilies, skinindex = struct.unpack_from("<III", data, 192)
    skin_table = []
    if numskinref > 0 and 0 < skinindex < len(data):
        skin_table = list(struct.unpack_from(f"<{numskinref}h", data, skinindex))

    # Find the mesh corresponding to target_tex
    target_tex_idx = target_tex["index"]
    target_mesh = None
    target_model = None

    numbodyparts, bodypartindex = struct.unpack_from("<II", data, 204)
    for bp in range(numbodyparts):
        bp_offset = bodypartindex + bp * 76
        nummodels, base, modelindex = struct.unpack_from("<3i", data, bp_offset + 64)
        for m in range(nummodels):
            m_offset = modelindex + m * 112
            (
                m_name, m_type, m_radius,
                nummesh, meshindex,
                numverts, vertinfoindex, vertindex,
                numnorms, norminfoindex, normindex,
                numgroups, groupindex
            ) = struct.unpack_from("<64sif10I", data, m_offset)

            for mi in range(nummesh):
                mesh_offset = meshindex + mi * 20
                numtris, triindex, skinref, _, _ = struct.unpack_from("<5i", data, mesh_offset)
                actual_tex_index = skin_table[skinref] if (skin_table and 0 <= skinref < len(skin_table)) else skinref
                if actual_tex_index == target_tex_idx:
                    target_mesh = {
                        "mesh_offset": mesh_offset,
                        "triindex": triindex,
                        "skinref": skinref,
                    }
                    target_model = {
                        "model_offset": m_offset,
                        "numverts": numverts,
                        "vertindex": vertindex,
                        "vertinfoindex": vertinfoindex,
                        "numnorms": numnorms,
                        "normindex": normindex,
                        "norminfoindex": norminfoindex,
                    }
                    break
            if target_mesh:
                break
        if target_mesh:
            break

    if not target_mesh or not target_model:
        raise ValueError(f"Mesh geometry for slot '{target_tex['name']}' not found in model hierarchy.")

    # Parse triangle command stream of the target mesh
    pos = target_mesh["triindex"]
    mesh_vert_uvs: Dict[int, Tuple[int, int]] = {}
    mesh_norm_indices: Dict[int, int] = {}

    while pos + 2 <= len(data):
        strip_len = struct.unpack_from("<h", data, pos)[0]
        pos += 2
        if strip_len == 0:
            break
        count = abs(strip_len)
        for _ in range(count):
            if pos + 8 > len(data):
                break
            v_idx, n_idx, s, t = struct.unpack_from("<4h", data, pos)
            pos += 8
            if v_idx not in mesh_vert_uvs:
                mesh_vert_uvs[v_idx] = (s, t)
            mesh_norm_indices[v_idx] = n_idx

    if not mesh_vert_uvs:
        raise ValueError(f"No vertices found in triangle stream for slot '{target_tex['name']}'.")

    # Determine bone ID
    bone_world_matrices = compute_bone_world_matrices(data)
    if bone_id is None or bone_id < 0 or bone_id >= len(bone_world_matrices):
        # Look at existing vertices' bone assignments
        vertinfoindex = target_model["vertinfoindex"]
        b_counts: Dict[int, int] = {}
        for vi in mesh_vert_uvs.keys():
            if vertinfoindex + vi < len(data):
                bid = data[vertinfoindex + vi]
                b_counts[bid] = b_counts.get(bid, 0) + 1
        if b_counts:
            bone_id = sorted(b_counts.items(), key=lambda i: i[1], reverse=True)[0][0]
        else:
            bone_id = find_weapon_root_bone(data)

    target_bone_matrix = bone_world_matrices[bone_id]

    try:
        scale_f = float(scale)
        if math.isnan(scale_f) or math.isinf(scale_f) or scale_f <= 0:
            scale_f = 1.0
    except (ValueError, TypeError):
        scale_f = 1.0

    try:
        rot_f = float(rotation)
        if math.isnan(rot_f) or math.isinf(rot_f):
            rot_f = 0.0
    except (ValueError, TypeError):
        rot_f = 0.0

    # Compute tangent basis (U, V, N) in Three.js world space
    u_vec, v_vec, n_vec = compute_tangent_basis(target_normal_three, rotation_deg=rot_f)

    # Base dimension for quad
    base_dim = 4.0 * max(0.1, scale_f)
    half_dim = base_dim / 2.0
    normal_offset = 0.04

    target_center = np.array(target_pos_three, dtype=np.float32) + normal_offset * n_vec

    tex_w = max(1.0, float(target_tex["width"]))
    tex_h = max(1.0, float(target_tex["height"]))

    # In-place update of vertices and normals in the MDL buffer
    vertindex = target_model["vertindex"]
    vertinfoindex = target_model["vertinfoindex"]
    normindex = target_model["normindex"]
    norminfoindex = target_model["norminfoindex"]

    # Precalculate local normal
    _, gw_norm = threejs_to_goldsrc_world(target_center, n_vec)
    _, loc_norm = world_to_local_bone(np.zeros(3, dtype=np.float32), gw_norm, target_bone_matrix)
    if loc_norm is None:
        loc_norm = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    for v_idx, (s, t) in mesh_vert_uvs.items():
        if v_idx >= target_model["numverts"]:
            continue

        u_norm = float(s) / max(1.0, tex_w - 1.0)
        v_norm = float(t) / max(1.0, tex_h - 1.0)

        # Planar quad point in Three.js space
        p_three = target_center + (u_norm - 0.5) * base_dim * u_vec + (0.5 - v_norm) * base_dim * v_vec

        # Convert to GoldSrc world space
        gw_pt, _ = threejs_to_goldsrc_world(p_three)

        # Invert bone matrix to local bone space
        loc_pt, _ = world_to_local_bone(gw_pt, None, target_bone_matrix)

        # Pack in-place into vertindex
        v_off = vertindex + v_idx * 12
        if v_off + 12 <= len(data):
            struct.pack_into("<3f", data, v_off, float(loc_pt[0]), float(loc_pt[1]), float(loc_pt[2]))

        # Update vertex bone assignment
        if vertinfoindex + v_idx < len(data):
            data[vertinfoindex + v_idx] = bone_id

        # Update normal if index exists
        n_idx = mesh_norm_indices.get(v_idx)
        if n_idx is not None and n_idx < target_model["numnorms"]:
            n_off = normindex + n_idx * 12
            if n_off + 12 <= len(data):
                struct.pack_into("<3f", data, n_off, float(loc_norm[0]), float(loc_norm[1]), float(loc_norm[2]))
            if norminfoindex + n_idx < len(data):
                data[norminfoindex + n_idx] = bone_id

    # Atomic write back to file
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "wb") as f:
        f.write(data)
    os.replace(tmp_path, path)

    return {
        "success": True,
        "message": f"Slot '{target_tex['name']}' successfully repositioned in-place.",
        "slot_name": target_tex["name"],
        "slot_index": target_tex["index"],
        "saved_path": str(path),
        "snapshot_id": snap_path.name,
    }


# =========================================================================
# 4. Solusi A: Native 3D Submesh & Slot Injection
# =========================================================================

def inject_new_slot_quad(
    mdl_path: Union[str, Path],
    slot_name: Optional[str] = None,
    target_pos_three: Optional[Union[List[float], Tuple[float, float, float], np.ndarray]] = None,
    target_normal_three: Optional[Union[List[float], Tuple[float, float, float], np.ndarray]] = None,
    scale: float = 1.0,
    rotation: float = 0.0,
    image_source: Optional[Union[str, Path, bytes, Image.Image]] = None,
    fx: str = "foil",
    bone_id: Optional[int] = None,
) -> dict:
    """
    Disabled: Appending table structures past 2.8MB causes GoldSrc engine heap corruption,
    vertex shards, and crashes. Use reposition_slot_quad for safe, zero-byte-drift geometry relocation.
    """
    raise RuntimeError(
        "inject_new_slot_quad is disabled to protect GoldSrc IDST v10 engine stability. "
        "Use safe in-place reposition_slot_quad instead."
    )


# =========================================================================
# 5. Model Health Check & Integrity Validator
# =========================================================================

def validate_model_health(mdl_path: Union[str, Path]) -> dict:
    """
    GoldSrc IDST v10 Model Integrity Validator:
    1. Verifies magic (IDST) and version (10).
    2. Verifies file size matches header length (0 byte drift / no truncation).
    3. Verifies submodel vertices <= 2048 (GoldSrc MAXSTUDIOVERTS engine limit).
    4. Verifies all table pointer offsets and buffers remain within valid file bounds.
    """
    path = Path(mdl_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Model file not found: {path}")

    actual_size = path.stat().st_size
    with open(path, "rb") as f:
        data = f.read()

    issues: List[str] = []

    if len(data) < 188:
        return {
            "healthy": False,
            "status": "Corrupt",
            "score": 0,
            "file_size": actual_size,
            "header_length": 0,
            "size_match": False,
            "max_verts_submodel": 0,
            "total_vertices": 0,
            "goldsrc_vert_limit": 2048,
            "exceeds_vert_limit": False,
            "issues": [f"File is smaller than minimal GoldSrc header ({len(data)} < 188 bytes)"],
            "model_name": path.name,
        }

    magic, ver, name_bytes, header_length = struct.unpack_from("<4sI64sI", data, 0)
    if magic != STUDIO_MAGIC:
        issues.append(f"Invalid magic identifier: expected {STUDIO_MAGIC}, got {magic}")
    if ver != STUDIO_VERSION:
        issues.append(f"Invalid StudioModel version: expected {STUDIO_VERSION}, got {ver}")

    # Check file size match
    if actual_size != header_length:
        issues.append(
            f"File size mismatch: header declares {header_length} bytes, actual disk size is {actual_size} bytes."
        )

    # Check table pointers
    numbones, boneindex = struct.unpack_from("<II", data, 140)
    if boneindex + numbones * 112 > actual_size:
        issues.append(f"Bones table out of file bounds ({boneindex + numbones * 112} > {actual_size})")

    numseq, seqindex = struct.unpack_from("<II", data, 164)
    if seqindex + numseq * 176 > actual_size:
        issues.append(f"Sequences table out of file bounds ({seqindex + numseq * 176} > {actual_size})")

    numtextures, textureindex = struct.unpack_from("<II", data, 180)
    if textureindex + numtextures * 80 > actual_size:
        issues.append(f"Textures table out of file bounds ({textureindex + numtextures * 80} > {actual_size})")

    # Check texture data offsets
    for i in range(numtextures):
        t_off = textureindex + i * 80
        if t_off + 80 <= actual_size:
            tname, tflags, tw, th, tdata_idx = struct.unpack_from("<64sIIII", data, t_off)
            tname_str = tname.split(b"\x00")[0].decode("latin1", errors="ignore")
            t_end = tdata_idx + tw * th + 768
            if t_end > actual_size:
                issues.append(f"Texture '{tname_str}' pixel payload out of file bounds ({t_end} > {actual_size})")

    # Check bodyparts, submodels, and vertex limits
    numbodyparts, bodypartindex = struct.unpack_from("<II", data, 204)
    if bodypartindex + numbodyparts * 76 > actual_size:
        issues.append(f"Bodyparts table out of file bounds ({bodypartindex + numbodyparts * 76} > {actual_size})")

    max_submodel_verts = 0
    total_model_verts = 0

    if bodypartindex + numbodyparts * 76 <= actual_size:
        for bp in range(numbodyparts):
            bp_offset = bodypartindex + bp * 76
            nummodels, base, modelindex = struct.unpack_from("<3i", data, bp_offset + 64)
            for m in range(nummodels):
                m_offset = modelindex + m * 112
                if m_offset + 112 <= actual_size:
                    (
                        m_name, m_type, m_radius,
                        nummesh, meshindex,
                        numverts, vertinfoindex, vertindex,
                        numnorms, norminfoindex, normindex,
                        numgroups, groupindex
                    ) = struct.unpack_from("<64sif10I", data, m_offset)
                    m_name_str = m_name.split(b"\x00")[0].decode("latin1", errors="ignore")
                    max_submodel_verts = max(max_submodel_verts, numverts)
                    total_model_verts += numverts

                    if numverts > 2048:
                        issues.append(
                            f"Submodel '{m_name_str}' exceeds GoldSrc MAXSTUDIOVERTS limit: {numverts} > 2048 vertices."
                        )
                    if vertindex + numverts * 12 > actual_size:
                        issues.append(f"Submodel '{m_name_str}' vertex array out of bounds")
                    if normindex + numnorms * 12 > actual_size:
                        issues.append(f"Submodel '{m_name_str}' normal array out of bounds")

    healthy = len(issues) == 0
    score = 100 if healthy else max(0, 100 - len(issues) * 25)
    status_str = "100% Clean" if healthy else f"{len(issues)} Issues Detected"

    return {
        "healthy": healthy,
        "status": status_str,
        "score": score,
        "file_size": actual_size,
        "header_length": header_length,
        "size_match": actual_size == header_length,
        "num_textures": numtextures,
        "num_bodyparts": numbodyparts,
        "max_verts_submodel": max_submodel_verts,
        "total_vertices": total_model_verts,
        "goldsrc_vert_limit": 2048,
        "exceeds_vert_limit": max_submodel_verts > 2048,
        "issues": issues,
        "model_name": path.name,
    }
