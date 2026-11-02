"""
chrome_injector.py - Pure-Python Dual-Layer Chrome Overlay Injection Engine
for Counter-Strike 1.6 GoldSrc StudioModels (IDST v10).

Architecture & Features:
1. Pure-Python binary MDL v10 rebuilder:
   - Block 1 (offset 0 to bodypartindex): Headers, bones, sequences, animation data,
     attachments, hitboxes preserved bit-for-bit.
   - Block 2 (Geometry): Original bodyparts followed by duplicated chrome bodyparts
     (chrome_1..chrome_N) for weapon skin submodels.
   - Block 3 (Textures): Texture headers (including new 64x64 chrome texture with flags
     0x0022 = STUDIO_NF_CHROME | STUDIO_NF_ADDITIVE), skinref table, and 8-bit paletted payloads.
   - Header updates: numtextures, textureindex, numbodyparts, bodypartindex, numskinref,
     skinindex, length.
2. Presets & Embedded Palettes:
   - Procedural 64x64 reflection maps:
     * silver: default reflection map (gumus.bmp spec: 88.7% index 0 black background,
       average RGB ~7, peak specular ~174).
     * subtle: scaled to peak specular ~120.
     * intense: scaled to peak specular ~220.
     * gold: warm golden tint for Lore / Case Hardened finishes.
     * custom: converts any user image to 64x64 8-bit paletted chrome reflection map.
3. Multi-Mesh & Isolation Safeties:
   - Only duplicate submodels/meshes associated with ROLE_SKIN.
   - Strictly excludes gloves, sleeves, bare arms (view_skin, arms, hand, glove).
   - In submodels with multiple meshes (e.g. AWP scope lens, StatTrak screen),
     non-skin meshes in duplicated chrome submodels have triangle streams emptied (numtris = 0).
   - Scaled UV coordinates: scale s, t UVs by (chrome_w / base_w, chrome_h / base_h)
     to prevent 8x tiling artifacts in WebGL and HLMV viewers.
4. Engine Limits & Pre-flight:
   - Checks numbodyparts + len(target_bodyparts) <= 32 (GoldSrc MAXSTUDIOBODYPARTS).
   - Checks that duplicated submodels do not exceed 2048 vertices (GoldSrc MAXSTUDIOVERTS).
5. Idempotence & Reversion:
   - inspect_chrome_status: detects existing chrome layers, bodyparts, and presets.
   - inject_chrome_overlay: creates .orig.mdl backup on first edit, injects cleanly,
     and re-injects idempotently.
   - remove_chrome_overlay: cleanly strips chrome submodels and textures, restoring
     the model to pristine pre-injection state.
"""

import base64
import colorsys
import io
import math
import os
from pathlib import Path
import shutil
import struct
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image

from .mdl_core import (
    STUDIO_MAGIC,
    STUDIO_VERSION,
    STUDIO_NF_CHROME,
    STUDIO_NF_ADDITIVE,
    ROLE_SKIN,
    ROLE_GLOVE,
    ROLE_STICKER,
    ROLE_STATTRAK,
    ROLE_OTHER,
    classify_texture,
)
from .slot_geometry import validate_model_health

# Constants
CHROME_FLAGS = STUDIO_NF_CHROME | STUDIO_NF_ADDITIVE  # 0x0022
CHROME_PRESETS = (
    "silver",
    "gunmetal",
    "mirror",
    "gold",
    "24k gold",
    "gold arabesque",
    "sapphire",
    "ruby",
    "emerald",
    "black pearl",
    "doppler phase 1",
    "doppler phase 2",
    "doppler phase 3",
    "doppler phase 4",
    "gamma doppler phase 1",
    "gamma doppler phase 2",
    "gamma doppler phase 3",
    "gamma doppler phase 4",
    "gamma emerald",
    "blue gem",
    "case hardened",
    "case hardened tier 1",
    "fade",
    "full fade",
    "marble fade",
    "marble fade fire & ice",
    "amber fade",
    "acid fade",
    "damascus steel",
    "printstream",
    "hyper beast",
    "tiger tooth",
    "slaughter",
    "ultraviolet",
    "rust coat",
    "hot rod",
    "cyan phosphor",
    "neon rider",
    "subtle",
    "intense",
    "custom",
)
EXCLUDED_KEYWORDS = ("view_skin", "arms", "hand", "glove", "sleeve", "finger", "arm")
NON_GLOVE_PARTS = (
    "handguard",
    "hand_guard",
    "handle",
    "handlebar",
    "sidearm",
    "firearm",
    "charm",
    "weapon_charm",
    "armor",
    "armour",
    "armature",
    "alarm",
    "swarm",
    "disarm",
)
MAXSTUDIOBODYPARTS = 32
MAXSTUDIOVERTS = 2048


# =========================================================================
# 1. Preset & Procedural Texture Generator
# =========================================================================

def generate_chrome_texture(
    preset: str = "silver",
    custom_image: Optional[Union[str, Path, bytes, Image.Image]] = None,
    intensity: Optional[float] = None,
    tightness: Optional[float] = None,
    tint: Optional[float] = None,
) -> Tuple[bytes, bytes]:
    """
    Generates an 8-bit paletted 64x64 chrome reflection map and a 768-byte RGB palette.
    Returns (pixels_bytes, palette_bytes).
    Total size = 4096 (pixels) + 768 (palette) = 4864 bytes.
    Supports parametric falloff curve (tightness p), peak luminance (intensity),
    and multi-spectral presets (Silver, Gunmetal, Mirror, 24K Gold, Sapphire, Ruby, Emerald, Blue Gem).
    """
    w, h = 64, 64

    if custom_image is not None:
        # Load and convert custom image
        if isinstance(custom_image, (str, Path)):
            img = Image.open(custom_image).convert("RGBA")
        elif isinstance(custom_image, bytes):
            img = Image.open(io.BytesIO(custom_image)).convert("RGBA")
        elif isinstance(custom_image, Image.Image):
            img = custom_image.convert("RGBA")
        else:
            raise TypeError(f"Unsupported custom_image type: {type(custom_image)}")

        img = img.resize((w, h), Image.Resampling.LANCZOS)
        # Quantize to 256 colors with index 0 reserved for pure black background
        p_img = img.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT)
        pal = p_img.getpalette() or [0] * 768
        # Ensure palette has 768 bytes
        pal = (pal + [0] * 768)[:768]
        pix_arr = np.array(p_img, dtype=np.uint8)

        # Shift indices by 1 to guarantee index 0 is pure black (0, 0, 0)
        shifted_pix = np.where(pix_arr < 255, pix_arr + 1, 1).astype(np.uint8)
        # Respect alpha transparency if original image had alpha
        alpha = np.array(img.split()[-1])
        shifted_pix[alpha < 128] = 0

        shifted_pal = bytearray(768)
        # index 0 is [0, 0, 0]
        shifted_pal[3:768] = bytes(pal[:765])
        return bytes(shifted_pix.tobytes()), bytes(shifted_pal)

    preset_lower = str(preset).lower().strip().replace("_", " ")
    if preset_lower == "custom" and custom_image is None:
        raise ValueError("custom_image must be provided when preset is 'custom'")

    peak_map = {
        "silver": 174.0,
        "subtle": 120.0,
        "intense": 220.0,
        "gold": 174.0,
        "24k gold": 180.0,
        "gold arabesque": 190.0,
        "gunmetal": 135.0,
        "mirror": 245.0,
        "sapphire": 190.0,
        "ruby": 185.0,
        "emerald": 180.0,
        "black pearl": 160.0,
        "doppler phase 1": 180.0,
        "doppler phase 2": 210.0,
        "doppler phase 3": 175.0,
        "doppler phase 4": 195.0,
        "gamma doppler phase 1": 180.0,
        "gamma doppler phase 2": 215.0,
        "gamma doppler phase 3": 190.0,
        "gamma doppler phase 4": 195.0,
        "gamma emerald": 210.0,
        "blue gem": 195.0,
        "case hardened": 190.0,
        "case hardened tier 1": 205.0,
        "oil slick": 195.0,
        "fade": 200.0,
        "full fade": 215.0,
        "marble fade": 205.0,
        "marble fade fire & ice": 215.0,
        "amber fade": 185.0,
        "acid fade": 190.0,
        "damascus steel": 220.0,
        "printstream": 225.0,
        "hyper beast": 205.0,
        "tiger tooth": 200.0,
        "slaughter": 190.0,
        "ultraviolet": 165.0,
        "rust coat": 140.0,
        "hot rod": 210.0,
        "cyan phosphor": 215.0,
        "neon rider": 210.0,
    }
    peak = peak_map.get(preset_lower, 174.0)

    # Parametric intensity scaling
    if intensity is not None:
        try:
            int_val = float(intensity)
            scale = int_val / 100.0 if int_val > 3.0 else int_val
            peak = float(np.clip(peak * scale, 10.0, 255.0))
        except (ValueError, TypeError):
            pass

    # Center of 64x64 grid
    cx, cy = 31.5, 31.5
    y, x = np.ogrid[:h, :w]
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

    # 88.7% index 0 black background: exactly 463 non-zero pixels out of 4096
    sorted_dist = np.sort(dist.flatten())
    r_cut = float((sorted_dist[462] + sorted_dist[463]) / 2.0)  # ~12.10

    mask = dist <= r_cut
    intensity_map = np.zeros((h, w), dtype=np.float32)

    # Parametric curvature falloff
    # Tightness p: 1.0 = standard gumus cosine falloff; > 1.0 = sharper spot; < 1.0 = softer satin
    p = 1.0
    if tightness is not None:
        try:
            p = max(0.2, min(5.0, float(tightness)))
        except (ValueError, TypeError):
            p = 1.0
    elif preset_lower in ("mirror", "printstream", "hot rod"):
        p = 1.6

    if p == 1.0:
        intensity_map[mask] = peak * 0.5 * (1.0 + np.cos(np.pi * dist[mask] / r_cut))
    else:
        cosine_base = 0.5 * (1.0 + np.cos(np.pi * dist[mask] / r_cut))
        intensity_map[mask] = peak * np.power(cosine_base, p)

    pix_arr = np.clip(np.round(intensity_map), 0, 255).astype(np.uint8)
    pix_arr[~mask] = 0
    # Ensure all pixels within the specular highlight mask are non-zero (>= 1)
    pix_arr[mask] = np.maximum(pix_arr[mask], 1)

    # Construct 768-byte palette (256 RGB entries)
    # Index 0 is always [0, 0, 0] (transparent in additive mode)
    palette = np.zeros((256, 3), dtype=np.uint8)
    for i in range(1, 256):
        if preset_lower in ("gold", "24k gold", "gold arabesque"):
            # Golden specular tint for Lore / Case Hardened finishes
            r_val = i
            g_val = int(round(i * 0.82))
            b_val = int(round(i * 0.35))
            palette[i] = [r_val, g_val, b_val]
        elif preset_lower == "gunmetal":
            # Cold dark steel luster
            palette[i] = [int(round(i * 0.72)), int(round(i * 0.78)), int(round(i * 0.88))]
        elif preset_lower == "mirror":
            # Ultra-sharp monochrome
            palette[i] = [i, i, i]
        elif preset_lower == "sapphire":
            # Cobalt blue sapphire
            palette[i] = [int(round(i * 0.22)), int(round(i * 0.55)), i]
        elif preset_lower == "ruby":
            # Blood crimson ruby
            palette[i] = [i, int(round(i * 0.15)), int(round(i * 0.28))]
        elif preset_lower in ("emerald", "gamma emerald"):
            # Radiant emerald green
            palette[i] = [int(round(i * 0.15)), i, int(round(i * 0.35))]
        elif preset_lower == "black pearl":
            # Smoky deep violet obsidian
            palette[i] = [int(round(i * 0.45)), int(round(i * 0.22)), int(round(i * 0.58))]
        elif preset_lower == "doppler phase 1":
            # Dark navy indigo with crimson fringe
            if i < 120:
                palette[i] = [int(round(i * 0.2)), int(round(i * 0.2)), int(round(i * 0.85))]
            else:
                palette[i] = [int(round(i * 0.65)), int(round(i * 0.15)), i]
        elif preset_lower == "doppler phase 2":
            # Vivid hot pink / magenta
            palette[i] = [i, int(round(i * 0.22)), int(round(i * 0.72))]
        elif preset_lower == "doppler phase 3":
            # Dark cyan and deep oceanic blue
            palette[i] = [int(round(i * 0.12)), int(round(i * 0.62)), int(round(i * 0.88))]
        elif preset_lower == "doppler phase 4":
            # Electric aqua and sapphire
            palette[i] = [int(round(i * 0.18)), int(round(i * 0.72)), i]
        elif preset_lower == "gamma doppler phase 1":
            # Dark teal / deep emerald
            palette[i] = [int(round(i * 0.1)), int(round(i * 0.85)), int(round(i * 0.55))]
        elif preset_lower == "gamma doppler phase 2":
            # Vivid neon lime / mint
            palette[i] = [int(round(i * 0.3)), i, int(round(i * 0.42))]
        elif preset_lower == "gamma doppler phase 3":
            # Aqua cyan green
            palette[i] = [int(round(i * 0.15)), int(round(i * 0.92)), int(round(i * 0.85))]
        elif preset_lower == "gamma doppler phase 4":
            # Deep cyan lime
            palette[i] = [int(round(i * 0.18)), int(round(i * 0.95)), int(round(i * 0.7))]
        elif preset_lower in ("blue gem", "case hardened", "case hardened tier 1", "oil slick"):
            # Case Hardened iridescent shift across highlight radii
            if i < 90:
                palette[i] = [int(round(i * 0.70)), int(round(i * 0.20)), int(round(i * 0.95))]
            elif i < 175:
                ratio = (i - 90) / 85.0
                palette[i] = [int(round(i * (0.70 - 0.50 * ratio))), int(round(i * (0.20 + 0.60 * ratio))), i]
            else:
                palette[i] = [i, int(round(i * 0.85)), int(round(i * 0.35))]
        elif preset_lower in ("fade", "full fade"):
            # CS spectrum fade: gold -> pink -> violet
            if i < 85:
                palette[i] = [int(round(i * 0.6)), int(round(i * 0.15)), i]
            elif i < 170:
                palette[i] = [i, int(round(i * 0.25)), int(round(i * 0.65))]
            else:
                palette[i] = [i, int(round(i * 0.82)), int(round(i * 0.25))]
        elif preset_lower in ("marble fade", "marble fade fire & ice"):
            # Fire & Ice: vibrant crimson and sapphire blue
            if i < 128:
                palette[i] = [int(round(i * 0.15)), int(round(i * 0.55)), i]
            else:
                palette[i] = [i, int(round(i * 0.15)), int(round(i * 0.25))]
        elif preset_lower == "amber fade":
            palette[i] = [i, int(round(i * 0.70)), int(round(i * 0.18))]
        elif preset_lower == "acid fade":
            palette[i] = [int(round(i * 0.45)), i, int(round(i * 0.15))]
        elif preset_lower == "tiger tooth":
            palette[i] = [i, int(round(i * 0.76)), int(round(i * 0.12))]
        elif preset_lower == "slaughter":
            palette[i] = [i, int(round(i * 0.18)), int(round(i * 0.22))]
        elif preset_lower == "hot rod":
            palette[i] = [i, int(round(i * 0.08)), int(round(i * 0.08))]
        elif preset_lower == "cyan phosphor":
            palette[i] = [int(round(i * 0.08)), int(round(i * 0.92)), i]
        elif preset_lower == "neon rider":
            palette[i] = [i, int(round(i * 0.22)), int(round(i * 0.88))]
        elif preset_lower == "ultraviolet":
            palette[i] = [int(round(i * 0.55)), int(round(i * 0.12)), i]
        elif preset_lower == "damascus steel":
            palette[i] = [int(round(i * 0.82)), int(round(i * 0.84)), int(round(i * 0.90))]
        elif preset_lower == "printstream":
            palette[i] = [int(round(i * 0.95)), int(round(i * 0.98)), i]
        elif preset_lower == "rust coat":
            palette[i] = [int(round(i * 0.78)), int(round(i * 0.38)), int(round(i * 0.18))]
        elif preset_lower == "hyper beast":
            palette[i] = [int(round(i * 0.2)), i, int(round(i * 0.8))]
        else:
            # Grayscale silver / subtle / intense reflection
            palette[i] = [i, i, i]

    # Parametric hue tint rotation (0° - 360°)
    if tint is not None:
        try:
            t_deg = float(tint) % 360.0
            if t_deg != 0.0:
                h_shift = t_deg / 360.0
                for i in range(1, 256):
                    r_c, g_c, b_c = palette[i]
                    h_val, s_val, v_val = colorsys.rgb_to_hsv(r_c / 255.0, g_c / 255.0, b_c / 255.0)
                    new_h = (h_val + h_shift) % 1.0
                    nr, ng, nb = colorsys.hsv_to_rgb(new_h, s_val, v_val)
                    palette[i] = [int(round(nr * 255.0)), int(round(ng * 255.0)), int(round(nb * 255.0))]
        except (ValueError, TypeError):
            pass

    return bytes(pix_arr.tobytes()), bytes(palette.tobytes())


def generate_chrome_preview_uri(
    preset: str = "silver",
    custom_image: Optional[Union[str, Path, bytes, Image.Image]] = None,
    intensity: Optional[float] = None,
    tightness: Optional[float] = None,
    tint: Optional[float] = None,
) -> str:
    """
    Generates a real-time base64 PNG data URI for the 64x64 environment reflection map.
    Used for 3D Chrome Orb visualizer and material preview.
    """
    pix_bytes, pal_bytes = generate_chrome_texture(
        preset=preset,
        custom_image=custom_image,
        intensity=intensity,
        tightness=tightness,
        tint=tint,
    )
    img = Image.frombytes("P", (64, 64), pix_bytes)
    img.putpalette(pal_bytes)
    rgba = img.convert("RGBA")
    buf = io.BytesIO()
    rgba.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


# =========================================================================
# 2. Identification & Classification Helpers
# =========================================================================

def is_chrome_bodypart(name: str) -> bool:
    """
    Checks if a bodypart name matches chrome overlay naming conventions.
    Accepts both 'chrome_' and community alias 'chorme_'.
    """
    lower = name.lower().strip()
    return lower.startswith("chrome") or lower.startswith("chorme")


def is_chrome_texture(name: str, flags: int) -> bool:
    """Checks if a texture header corresponds to a chrome overlay texture."""
    if (flags & STUDIO_NF_CHROME) and (flags & STUDIO_NF_ADDITIVE):
        return True
    lower = name.lower().strip()
    base = os.path.splitext(lower)[0]
    return base in ("chrome", "chorme", "gumus", "chrome_overlay") or base.startswith("chrome_")


def is_excluded_geometry(name: str) -> bool:
    """Checks if a bodypart, submodel, or texture name indicates arms, gloves, or hands."""
    lower = name.lower()
    # Check if this name represents a weapon part that contains "arm" or "hand" as a substring
    if any(k in lower for k in NON_GLOVE_PARTS) and not any(k in lower for k in ("glove", "sport")):
        return False
    return any(k in lower for k in EXCLUDED_KEYWORDS)


# =========================================================================
# 3. Low-Level Binary Parser & Rebuilder
# =========================================================================

def parse_model_geometry(data: bytes) -> Dict[str, Any]:
    """
    Parses a GoldSrc IDST v10 model binary into structured Python objects
    ready for duplication, filtering, and reconstruction.
    """
    if len(data) < 220:
        raise ValueError(f"File too small for GoldSrc StudioModel: {len(data)} bytes")

    magic, ver, name, length = struct.unpack_from("<4sI64sI", data, 0)
    if magic != STUDIO_MAGIC or ver != STUDIO_VERSION:
        raise ValueError(f"Invalid GoldSrc MDL header: magic={magic}, ver={ver}")

    numtextures, textureindex, texturedataindex = struct.unpack_from("<III", data, 180)
    numskinref, numskinfamilies, skinindex = struct.unpack_from("<III", data, 192)
    numbodyparts, bodypartindex = struct.unpack_from("<II", data, 204)

    # Read skinref table
    skin_table = []
    if numskinref > 0 and 0 < skinindex < len(data):
        total_entries = numskinref * max(1, numskinfamilies)
        if skinindex + total_entries * 2 <= len(data):
            skin_table = list(struct.unpack_from(f"<{total_entries}h", data, skinindex))

    # Read textures
    textures = []
    for t_i in range(numtextures):
        t_off = textureindex + t_i * 80
        if t_off + 80 > len(data):
            break
        tname, flags, w, h, idx = struct.unpack_from("<64sIIII", data, t_off)
        tname_s = tname.split(b"\x00")[0].decode("latin1", errors="ignore")
        role, label = classify_texture(tname_s, flags, w, h)
        # Texture payload
        payload_size = w * h + 768
        payload = bytes(data[idx : idx + payload_size])
        textures.append({
            "index": t_i,
            "name": tname_s,
            "name_raw": tname,
            "flags": flags,
            "width": w,
            "height": h,
            "data_offset": idx,
            "payload": payload,
            "role": role,
            "label": label,
        })

    # Read bodyparts, submodels, meshes, and triangle command streams
    bodyparts = []
    for bp_i in range(numbodyparts):
        bp_off = bodypartindex + bp_i * 76
        if bp_off + 76 > len(data):
            break
        bp_name, bp_nummodels, bp_base, bp_modelindex = struct.unpack_from("<64siii", data, bp_off)
        bp_name_s = bp_name.split(b"\x00")[0].decode("latin1", errors="ignore")

        models = []
        if bp_nummodels <= 0 or bp_nummodels > 32 or bp_modelindex <= 0 or bp_modelindex + bp_nummodels * 112 > len(data):
            # Model table out of bounds or invalid
            continue

        for m_i in range(bp_nummodels):
            m_off = bp_modelindex + m_i * 112
            if m_off + 112 > len(data):
                break
            (
                m_name, m_type, m_radius,
                nummesh, meshindex,
                numverts, vertinfoindex, vertindex,
                numnorms, norminfoindex, normindex,
                numgroups, groupindex
            ) = struct.unpack_from("<64sif10I", data, m_off)
            m_name_s = m_name.split(b"\x00")[0].decode("latin1", errors="ignore")

            if numverts < 0 or numverts > 65535 or vertindex + numverts * 12 > len(data):
                continue
            if numnorms < 0 or numnorms > 65535 or normindex + numnorms * 12 > len(data):
                continue

            verts_raw = bytes(data[vertindex : vertindex + numverts * 12])
            vertinfo_raw = bytes(data[vertinfoindex : vertinfoindex + numverts])
            norms_raw = bytes(data[normindex : normindex + numnorms * 12])
            norminfo_raw = bytes(data[norminfoindex : norminfoindex + numnorms])

            meshes = []
            if nummesh <= 0 or nummesh > 32 or meshindex <= 0 or meshindex + nummesh * 20 > len(data):
                continue

            for mi in range(nummesh):
                mesh_off = meshindex + mi * 20
                if mesh_off + 20 > len(data):
                    break
                numtris, triindex, skinref, n1, n2 = struct.unpack_from("<5i", data, mesh_off)

                # Parse triangle command stream
                if triindex <= 0 or triindex + 2 > len(data):
                    continue

                pos = triindex
                tri_commands = []
                while 0 <= pos and pos + 2 <= len(data):
                    strip_len = struct.unpack_from("<h", data, pos)[0]
                    pos += 2
                    if strip_len == 0:
                        break
                    count = abs(strip_len)
                    if count > 2048 or pos + count * 8 > len(data):
                        break
                    strip_verts = []
                    for _ in range(count):
                        v_i, n_i, s, t = struct.unpack_from("<4h", data, pos)
                        pos += 8
                        strip_verts.append((v_i, n_i, s, t))
                    tri_commands.append((strip_len, strip_verts))

                actual_tex = skin_table[skinref] if (skin_table and 0 <= skinref < len(skin_table)) else skinref
                meshes.append({
                    "numtris": numtris,
                    "skinref": skinref,
                    "actual_tex_idx": actual_tex,
                    "tri_commands": tri_commands,
                    "n1": n1,
                    "n2": n2,
                })

            models.append({
                "name": m_name_s,
                "name_raw": m_name,
                "type": m_type,
                "radius": m_radius,
                "numverts": numverts,
                "verts_raw": verts_raw,
                "vertinfo_raw": vertinfo_raw,
                "numnorms": numnorms,
                "norms_raw": norms_raw,
                "norminfo_raw": norminfo_raw,
                "meshes": meshes,
                "numgroups": numgroups,
                "groupindex": groupindex,
            })

        bodyparts.append({
            "name": bp_name_s,
            "name_raw": bp_name,
            "base": bp_base,
            "models": models,
        })

    return {
        "header_block1": bytes(data[:bodypartindex]),
        "bodyparts": bodyparts,
        "textures": textures,
        "skin_table": skin_table,
        "numskinref": numskinref,
        "numskinfamilies": max(1, numskinfamilies),
        "orig_bodypartindex": bodypartindex,
    }


def serialize_model_binary(
    header_block1: bytes,
    bodyparts: List[Dict[str, Any]],
    textures: List[Dict[str, Any]],
    skin_table: List[int],
    numskinfamilies: int,
) -> bytearray:
    """
    Serializes structured GoldSrc StudioModel components into an exact binary buffer.
    Maintains strict 4-byte pointer alignment and updates all table headers and file length.
    """
    out_buf = bytearray()

    # Block 1: Preserve header and animation tables (0 to bodypartindex) bit-for-bit
    out_buf.extend(header_block1)
    new_bodypartindex = len(out_buf)

    num_bodyparts = len(bodyparts)
    total_models = sum(len(bp["models"]) for bp in bodyparts)

    bodyparts_table_size = num_bodyparts * 76
    models_table_start = new_bodypartindex + bodyparts_table_size

    # Reserve space for bodyparts headers table and models headers table
    out_buf.extend(b"\x00" * (bodyparts_table_size + total_models * 112))

    current_model_idx = 0

    # Block 2: Geometry
    for bp_i, bp in enumerate(bodyparts):
        bp_models = bp["models"]
        bp_nummodels = len(bp_models)
        bp_modelindex = models_table_start + current_model_idx * 112

        # Pack bodypart header
        name_raw = bp["name_raw"]
        if len(name_raw) < 64:
            name_raw = name_raw + b"\x00" * (64 - len(name_raw))
        else:
            name_raw = name_raw[:64]

        struct.pack_into(
            "<64siii",
            out_buf,
            new_bodypartindex + bp_i * 76,
            name_raw,
            bp_nummodels,
            bp["base"],
            bp_modelindex,
        )

        for m in bp_models:
            m_header_offset = models_table_start + current_model_idx * 112
            current_model_idx += 1

            # Mesh headers table
            while len(out_buf) % 4 != 0:
                out_buf.append(0)
            meshindex = len(out_buf)
            nummesh = len(m["meshes"])
            out_buf.extend(b"\x00" * (nummesh * 20))

            # Vertices
            while len(out_buf) % 4 != 0:
                out_buf.append(0)
            vertindex = len(out_buf)
            out_buf.extend(m["verts_raw"])

            # Vertinfo
            vertinfoindex = len(out_buf)
            out_buf.extend(m["vertinfo_raw"])

            # Normals
            while len(out_buf) % 4 != 0:
                out_buf.append(0)
            normindex = len(out_buf)
            out_buf.extend(m["norms_raw"])

            # Norminfo
            norminfoindex = len(out_buf)
            out_buf.extend(m["norminfo_raw"])

            # Triangle streams for each mesh
            for mi, mesh in enumerate(m["meshes"]):
                while len(out_buf) % 4 != 0:
                    out_buf.append(0)
                triindex = len(out_buf)

                # Pack triangle command stream
                for strip_len, sverts in mesh["tri_commands"]:
                    out_buf.extend(struct.pack("<h", strip_len))
                    for v_i, n_i, s, t in sverts:
                        out_buf.extend(struct.pack("<4h", v_i, n_i, s, t))
                # Stream end terminator (0x0000)
                out_buf.extend(struct.pack("<h", 0))

                # Pack mesh header into meshindex table
                struct.pack_into(
                    "<5i",
                    out_buf,
                    meshindex + mi * 20,
                    mesh["numtris"],
                    triindex,
                    mesh["skinref"],
                    mesh["n1"],
                    mesh["n2"],
                )

            # Pack model header
            m_name_raw = m["name_raw"]
            if len(m_name_raw) < 64:
                m_name_raw = m_name_raw + b"\x00" * (64 - len(m_name_raw))
            else:
                m_name_raw = m_name_raw[:64]

            struct.pack_into(
                "<64sif10I",
                out_buf,
                m_header_offset,
                m_name_raw,
                m["type"],
                m["radius"],
                nummesh,
                meshindex,
                m["numverts"],
                vertinfoindex,
                vertindex,
                m["numnorms"],
                norminfoindex,
                normindex,
                m["numgroups"],
                m["groupindex"],
            )

    # 4-byte align before Block 3 (Textures)
    while len(out_buf) % 4 != 0:
        out_buf.append(0)
    new_textureindex = len(out_buf)
    num_textures = len(textures)

    # Reserve space for texture headers
    out_buf.extend(b"\x00" * (num_textures * 80))

    # Skinref table
    while len(out_buf) % 4 != 0:
        out_buf.append(0)
    new_skinindex = len(out_buf)
    for sref in skin_table:
        out_buf.extend(struct.pack("<h", sref))

    # 4-byte align before texture pixel payloads
    while len(out_buf) % 4 != 0:
        out_buf.append(0)
    new_texturedataindex = len(out_buf)

    # Write texture payloads
    for ti, tex in enumerate(textures):
        while len(out_buf) % 4 != 0:
            out_buf.append(0)
        data_offset = len(out_buf)
        out_buf.extend(tex["payload"])

        t_name_raw = tex["name_raw"]
        if len(t_name_raw) < 64:
            t_name_raw = t_name_raw + b"\x00" * (64 - len(t_name_raw))
        else:
            t_name_raw = t_name_raw[:64]

        # Pack texture header
        struct.pack_into(
            "<64sIIII",
            out_buf,
            new_textureindex + ti * 80,
            t_name_raw,
            tex["flags"],
            tex["width"],
            tex["height"],
            data_offset,
        )

    new_length = len(out_buf)
    numskinref = len(skin_table) // max(1, numskinfamilies)

    # Update header pointers and lengths in Block 1
    struct.pack_into("<I", out_buf, 72, new_length)
    struct.pack_into("<III", out_buf, 180, num_textures, new_textureindex, new_texturedataindex)
    struct.pack_into("<III", out_buf, 192, numskinref, max(1, numskinfamilies), new_skinindex)
    struct.pack_into("<II", out_buf, 204, num_bodyparts, new_bodypartindex)

    return out_buf


def strip_chrome_components(
    bodyparts: List[Dict[str, Any]],
    textures: List[Dict[str, Any]],
    skin_table: List[int],
    numskinfamilies: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[int], List[str]]:
    """
    Strips chrome bodyparts and textures from model components, correctly remapping
    multi-family skin tables and mesh skin references without index collisions.
    """
    cleaned_bodyparts = [bp for bp in bodyparts if not is_chrome_bodypart(bp["name"])]

    cleaned_textures = []
    old_to_new_tex: Dict[int, int] = {}
    removed_tex_names: List[str] = []

    for old_idx, t in enumerate(textures):
        if is_chrome_texture(t["name"], t["flags"]):
            removed_tex_names.append(t["name"])
            continue
        new_idx = len(cleaned_textures)
        old_to_new_tex[old_idx] = new_idx
        cleaned_textures.append(t)

    # Reconstruct cleaned skin table column-by-column
    orig_numskinref = len(skin_table) // max(1, numskinfamilies) if skin_table else len(textures)

    kept_cols = []
    for col in range(orig_numskinref):
        is_chrome_col = False
        for fam in range(max(1, numskinfamilies)):
            entry_idx = fam * orig_numskinref + col
            if entry_idx < len(skin_table):
                old_t = skin_table[entry_idx]
                if old_t not in old_to_new_tex:
                    is_chrome_col = True
                    break
        if not is_chrome_col:
            kept_cols.append(col)

    col_map = {old_col: new_col for new_col, old_col in enumerate(kept_cols)}

    cleaned_skin_table = []
    for fam in range(max(1, numskinfamilies)):
        for old_col in kept_cols:
            entry_idx = fam * orig_numskinref + old_col
            old_t = skin_table[entry_idx] if entry_idx < len(skin_table) else old_col
            cleaned_skin_table.append(old_to_new_tex.get(old_t, 0))

    # Remap mesh skinrefs and actual_tex_idx in all remaining bodyparts
    for bp in cleaned_bodyparts:
        for m in bp["models"]:
            for mesh in m["meshes"]:
                old_actual = mesh["actual_tex_idx"]
                if old_actual in old_to_new_tex:
                    mesh["actual_tex_idx"] = old_to_new_tex[old_actual]
                mesh["skinref"] = col_map.get(mesh["skinref"], 0)

    return cleaned_bodyparts, cleaned_textures, cleaned_skin_table, removed_tex_names


# =========================================================================
# 4. Chrome Status Inspector
# =========================================================================

def inspect_chrome_status(model_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Inspects a GoldSrc MDL model to determine if dual-layer chrome overlay
    is currently injected, and verifies capacity for new injection.
    """
    path = Path(model_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Model file not found: {path}")

    with open(path, "rb") as f:
        data = f.read()

    parsed = parse_model_geometry(data)
    bodyparts = parsed["bodyparts"]
    textures = parsed["textures"]

    chrome_bodyparts = []
    base_skin_bodyparts = []
    detected_submodels = []

    for bp_idx, bp in enumerate(bodyparts):
        bp_name = bp["name"]
        if is_chrome_bodypart(bp_name):
            chrome_bodyparts.append({"index": bp_idx, "name": bp_name})
            continue

        if is_excluded_geometry(bp_name):
            continue

        # Check if this bodypart contains weapon skin submodels
        has_skin = False
        is_excluded = False
        for m in bp["models"]:
            if is_excluded_geometry(m["name"]):
                is_excluded = True
                break
            for mesh in m["meshes"]:
                tex_idx = mesh["actual_tex_idx"]
                if 0 <= tex_idx < len(textures):
                    t = textures[tex_idx]
                    if is_excluded_geometry(t["name"]):
                        is_excluded = True
                        break
                    if t["role"] == ROLE_SKIN:
                        has_skin = True
            if is_excluded:
                break

        if has_skin and not is_excluded:
            base_skin_bodyparts.append({"index": bp_idx, "name": bp_name})
            for m in bp["models"]:
                detected_submodels.append({
                    "name": m["name"],
                    "bodypart": bp_name,
                    "bodypart_index": bp_idx,
                    "numverts": m["numverts"],
                })

    chrome_textures = []
    detected_preset = None

    for t in textures:
        if is_chrome_texture(t["name"], t["flags"]):
            chrome_textures.append({
                "index": t["index"],
                "name": t["name"],
                "flags": t["flags"],
                "width": t["width"],
                "height": t["height"],
            })
            # Try to infer preset from rendered pixel brightness and palette tint
            if len(t["payload"]) >= 4096 + 768:
                pix = np.frombuffer(t["payload"][:4096], dtype=np.uint8)
                pal = np.frombuffer(t["payload"][4096:4864], dtype=np.uint8).reshape((256, 3))
                active_colors = pal[pix[pix > 0]] if (pix > 0).any() else pal[1:255]
                max_channels = active_colors.max(axis=0) if len(active_colors) > 0 else np.array([0, 0, 0])
                # Check palette values to accurately identify procedural presets vs custom images
                p100 = pal[100].tolist()
                p50 = pal[50].tolist()
                if p100 == [100, 82, 35] or (max_channels[0] > max_channels[1] + 10 and max_channels[1] > max_channels[2] + 20 and p100[0] > p100[1] > p100[2] and p50[0] > p50[1] > p50[2]):
                    detected_preset = "gold"
                elif p100 == [22, 55, 100]:
                    detected_preset = "sapphire"
                elif p100 == [100, 15, 28]:
                    detected_preset = "ruby"
                elif p100 == [20, 100, 40]:
                    detected_preset = "emerald"
                elif p100 == [72, 78, 88]:
                    detected_preset = "gunmetal"
                elif pal[60].tolist() == [42, 12, 57]:
                    detected_preset = "blue gem"
                elif max_channels[0] == max_channels[1] == max_channels[2] and p100 == [100, 100, 100]:
                    peak_b = int(max_channels[0])
                    if peak_b <= 135:
                        detected_preset = "subtle"
                    elif peak_b >= 235:
                        detected_preset = "mirror"
                    elif peak_b >= 200:
                        detected_preset = "intense"
                    else:
                        detected_preset = "silver"
                else:
                    detected_preset = "custom"

    has_chrome = bool(chrome_bodyparts or chrome_textures)
    target_count = len(base_skin_bodyparts)
    clean_bodyparts_count = len(bodyparts) - len(chrome_bodyparts)
    can_inject = (clean_bodyparts_count + target_count <= MAXSTUDIOBODYPARTS)

    return {
        "model_name": path.name,
        "model_path": str(path),
        "has_chrome": has_chrome,
        "chrome_bodyparts": chrome_bodyparts,
        "chrome_textures": chrome_textures,
        "preset": detected_preset if has_chrome else None,
        "num_bodyparts": len(bodyparts),
        "num_textures": len(textures),
        "target_skin_bodyparts": [bp["name"] for bp in base_skin_bodyparts],
        "detected_submodels": detected_submodels,
        "target_count": target_count,
        "can_inject": can_inject,
        "max_bodyparts_limit": MAXSTUDIOBODYPARTS,
    }


# =========================================================================
# 5. Dual-Layer Chrome Overlay Injector
# =========================================================================

def inject_chrome_overlay(
    model_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    preset: str = "silver",
    custom_image: Optional[Union[str, Path, bytes, Image.Image]] = None,
    bodypart_prefix: str = "chrome_",
    force: bool = True,
    intensity: Optional[float] = None,
    tightness: Optional[float] = None,
    tint: Optional[float] = None,
    target_parts: Optional[Union[List[str], str]] = None,
) -> Dict[str, Any]:
    """
    Injects a dual-layer metallic chrome overlay onto a Counter-Strike 1.6 model.

    Process:
    1. Pre-flight checks on engine limits (<= 32 bodyparts, <= 2048 submodel vertices).
    2. Automatic immutable backup (.orig.mdl) on first edit.
    3. Idempotently cleans any existing chrome layer if re-injecting with force=True.
    4. Procedurally builds a 64x64 reflection map with flags 0x0022 (CHROME | ADDITIVE).
    5. Duplicates weapon skin bodyparts (chrome_1..N), scaling UV coordinates by
       (chrome_w / base_w, chrome_h / base_h) to eliminate 8x tiling artifacts.
    6. Empties non-skin meshes in duplicated submodels (e.g. scopes/StatTrak) to numtris = 0.
    7. Atomically rebuilds the binary MDL and verifies with validate_model_health (100/100).
    """
    path = Path(model_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Model file not found: {path}")

    target_out = Path(output_path).resolve() if output_path else path

    # 1. Immutable original backup (.orig.mdl)
    orig_path = path.with_suffix(".orig.mdl")
    if not orig_path.exists():
        shutil.copy2(path, orig_path)

    with open(path, "rb") as f:
        data = f.read()

    numbodyparts_hdr = struct.unpack_from("<I", data, 204)[0] if len(data) >= 208 else 0
    if numbodyparts_hdr > MAXSTUDIOBODYPARTS:
        raise ValueError(
            f"Cannot inject chrome: model header declares {numbodyparts_hdr} bodyparts, "
            f"exceeding GoldSrc MAXSTUDIOBODYPARTS ({MAXSTUDIOBODYPARTS})."
        )

    parsed = parse_model_geometry(data)
    bodyparts = parsed["bodyparts"]
    textures = parsed["textures"]
    skin_table = parsed["skin_table"]
    numskinfamilies = parsed["numskinfamilies"]
    header_block1 = parsed["header_block1"]

    # 2. Check for existing chrome overlay (Idempotence)
    existing_chrome_bps = [bp for bp in bodyparts if is_chrome_bodypart(bp["name"])]
    has_existing_chrome = bool(existing_chrome_bps) or any(
        is_chrome_texture(t["name"], t["flags"]) for t in textures
    )

    if has_existing_chrome:
        if not force:
            return {
                "success": False,
                "message": "Model already has chrome overlay injected. Use force=True to re-inject.",
                "model_name": path.name,
                "has_chrome": True,
            }
        bodyparts, textures, skin_table, _ = strip_chrome_components(
            bodyparts, textures, skin_table, numskinfamilies
        )

    # 3. Identify target skin bodyparts to duplicate
    target_bodyparts: List[Tuple[int, Dict[str, Any]]] = []
    for bp_idx, bp in enumerate(bodyparts):
        bp_name = bp["name"]
        if is_excluded_geometry(bp_name):
            continue

        has_skin = False
        is_excluded = False
        for m in bp["models"]:
            if is_excluded_geometry(m["name"]):
                is_excluded = True
                break
            for mesh in m["meshes"]:
                tex_idx = mesh["actual_tex_idx"]
                if 0 <= tex_idx < len(textures):
                    t = textures[tex_idx]
                    if is_excluded_geometry(t["name"]):
                        is_excluded = True
                        break
                    if t["role"] == ROLE_SKIN:
                        has_skin = True
            if is_excluded:
                break

        if has_skin and not is_excluded:
            target_bodyparts.append((bp_idx, bp))

    # Selective component filtering if target_parts is specified
    if target_parts is not None:
        if isinstance(target_parts, str):
            target_parts = [p.strip() for p in target_parts.split(",") if p.strip()]
        if len(target_parts) > 0:
            parts_set = {str(p).lower().strip() for p in target_parts}
            filtered = []
            for bp_idx, bp in target_bodyparts:
                bp_name_lower = bp["name"].lower().strip()
                if (
                    bp_name_lower in parts_set
                    or str(bp_idx) in parts_set
                    or any(m["name"].lower().strip() in parts_set for m in bp["models"])
                ):
                    filtered.append((bp_idx, bp))
            if filtered:
                target_bodyparts = filtered
            else:
                raise ValueError(
                    f"None of the target_parts {target_parts} matched skin bodyparts in {path.name}"
                )

    if not target_bodyparts:
        raise ValueError(f"No weapon skin geometry found to chrome in {path.name}")

    # 4. Pre-flight engine limits validation
    effective_clean_count = (
        max(len(bodyparts), numbodyparts_hdr - len(existing_chrome_bps))
        if has_existing_chrome
        else max(len(bodyparts), numbodyparts_hdr)
    )
    new_total_bodyparts = effective_clean_count + len(target_bodyparts)
    if new_total_bodyparts > MAXSTUDIOBODYPARTS:
        raise ValueError(
            f"Cannot inject chrome: total bodyparts ({new_total_bodyparts}) would exceed "
            f"GoldSrc MAXSTUDIOBODYPARTS ({MAXSTUDIOBODYPARTS})."
        )

    for _, bp in target_bodyparts:
        for m in bp["models"]:
            if m["numverts"] > MAXSTUDIOVERTS:
                raise ValueError(
                    f"Submodel '{m['name']}' exceeds GoldSrc MAXSTUDIOVERTS limit: "
                    f"{m['numverts']} > {MAXSTUDIOVERTS} vertices."
                )

    # 5. Build 64x64 chrome reflection map
    chrome_pix, chrome_pal = generate_chrome_texture(
        preset=preset,
        custom_image=custom_image,
        intensity=intensity,
        tightness=tightness,
        tint=tint,
    )
    chrome_payload = chrome_pix + chrome_pal

    chrome_tex_idx = len(textures)
    chrome_tex_name = "chrome.bmp"
    chrome_tex_name_raw = chrome_tex_name.encode("latin1") + b"\x00" * (64 - len(chrome_tex_name))

    new_tex = {
        "index": chrome_tex_idx,
        "name": chrome_tex_name,
        "name_raw": chrome_tex_name_raw,
        "flags": CHROME_FLAGS,
        "width": 64,
        "height": 64,
        "payload": chrome_payload,
        "role": ROLE_SKIN,
        "label": "Chrome Overlay",
    }
    all_textures = list(textures) + [new_tex]

    # 6. Update skin table
    numskinref_current = len(skin_table) // max(1, numskinfamilies) if skin_table else len(textures)
    new_skin_table = []
    for fam in range(max(1, numskinfamilies)):
        fam_slice = (
            skin_table[fam * numskinref_current : (fam + 1) * numskinref_current]
            if skin_table
            else list(range(len(textures)))
        )
        new_skin_table.extend(fam_slice + [chrome_tex_idx])

    chrome_skinref_val = numskinref_current  # Points to chrome_tex_idx in the new family slice

    # 7. Duplicate target skin bodyparts with UV scaling & multi-mesh isolation
    chrome_bodyparts = []
    for c_idx, (orig_bp_idx, orig_bp) in enumerate(target_bodyparts):
        bp_name_lower = orig_bp["name"].lower().strip()
        new_bp_name = f"{bodypart_prefix}{c_idx + 1}"
        new_bp_name_raw = new_bp_name.encode("latin1") + b"\x00" * max(0, 64 - len(new_bp_name))

        new_models = []
        for orig_m in orig_bp["models"]:
            new_m_name = f"{new_bp_name}"
            new_m_name_raw = new_m_name.encode("latin1") + b"\x00" * max(0, 64 - len(new_m_name))

            is_submodel_targeted = True
            if target_parts is not None and len(target_parts) > 0:
                is_submodel_targeted = (
                    bp_name_lower in parts_set
                    or str(orig_bp_idx) in parts_set
                    or orig_m["name"].lower().strip() in parts_set
                )

            new_meshes = []
            for orig_mesh in orig_m["meshes"]:
                actual_tex_idx = orig_mesh["actual_tex_idx"]
                tex_info = textures[actual_tex_idx] if 0 <= actual_tex_idx < len(textures) else None
                is_skin_mesh = tex_info and tex_info["role"] == ROLE_SKIN

                if is_skin_mesh and is_submodel_targeted:
                    base_w = max(1.0, float(tex_info["width"]))
                    base_h = max(1.0, float(tex_info["height"]))
                    scale_u = 64.0 / base_w
                    scale_v = 64.0 / base_h

                    new_tri_commands = []
                    new_tris_count = 0
                    for strip_len, strip_verts in orig_mesh["tri_commands"]:
                        new_verts = []
                        for v_i, n_i, s, t in strip_verts:
                            # Scale UVs to prevent 8x tiling in Three.js / HLMV viewers
                            new_s = int(round(s * scale_u))
                            new_t = int(round(t * scale_v))
                            new_verts.append((v_i, n_i, new_s, new_t))
                        new_tri_commands.append((strip_len, new_verts))
                        new_tris_count += (abs(strip_len) - 2)

                    new_meshes.append({
                        "numtris": new_tris_count,
                        "skinref": chrome_skinref_val,
                        "actual_tex_idx": chrome_tex_idx,
                        "tri_commands": new_tri_commands,
                        "n1": orig_mesh["n1"],
                        "n2": orig_mesh["n2"],
                    })
                else:
                    # Multi-mesh safety & selective targeting: empty triangle stream for untargeted or non-skin meshes
                    new_meshes.append({
                        "numtris": 0,
                        "skinref": 0,
                        "actual_tex_idx": 0,
                        "tri_commands": [],
                        "n1": 0,
                        "n2": 0,
                    })

            new_models.append({
                "name": new_m_name,
                "name_raw": new_m_name_raw,
                "type": orig_m["type"],
                "radius": orig_m["radius"],
                "numverts": orig_m["numverts"],
                "verts_raw": orig_m["verts_raw"],
                "vertinfo_raw": orig_m["vertinfo_raw"],
                "numnorms": orig_m["numnorms"],
                "norms_raw": orig_m["norms_raw"],
                "norminfo_raw": orig_m["norminfo_raw"],
                "meshes": new_meshes,
                "numgroups": orig_m["numgroups"],
                "groupindex": orig_m["groupindex"],
            })

        chrome_bodyparts.append({
            "name": new_bp_name,
            "name_raw": new_bp_name_raw,
            "base": orig_bp["base"],
            "models": new_models,
        })

    all_bodyparts = list(bodyparts) + chrome_bodyparts

    # 8. Rebuild binary MDL
    rebuilt_buf = serialize_model_binary(
        header_block1=header_block1,
        bodyparts=all_bodyparts,
        textures=all_textures,
        skin_table=new_skin_table,
        numskinfamilies=numskinfamilies,
    )

    # 9. Atomic save
    target_out.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_out.with_suffix(".tmp")
    with open(tmp_path, "wb") as f:
        f.write(rebuilt_buf)
    os.replace(tmp_path, target_out)

    # 10. Model Health Check
    health = validate_model_health(target_out)
    if not health.get("healthy", False):
        raise RuntimeError(
            f"Health check failed on rebuilt chrome model: {health.get('issues')}"
        )

    return {
        "success": True,
        "message": f"Successfully injected dual-layer chrome overlay ({preset}) into {target_out.name}",
        "saved_path": str(target_out),
        "preset": preset,
        "has_chrome": True,
        "num_bodyparts": len(all_bodyparts),
        "chrome_bodyparts_added": len(chrome_bodyparts),
        "num_textures": len(all_textures),
        "health": health,
    }


# =========================================================================
# 6. Reversion & Chrome Overlay Remover
# =========================================================================

def remove_chrome_overlay(
    model_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Strips chrome overlay bodyparts and texture from a model, restoring it
    to its pristine pre-injection state.
    """
    path = Path(model_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Model file not found: {path}")

    target_out = Path(output_path).resolve() if output_path else path

    with open(path, "rb") as f:
        data = f.read()

    parsed = parse_model_geometry(data)
    bodyparts = parsed["bodyparts"]
    textures = parsed["textures"]
    skin_table = parsed["skin_table"]
    numskinfamilies = parsed["numskinfamilies"]
    header_block1 = parsed["header_block1"]

    cleaned_bodyparts, cleaned_textures, cleaned_skin_table, removed_tex_names = strip_chrome_components(
        bodyparts, textures, skin_table, numskinfamilies
    )

    if not removed_tex_names and len(cleaned_bodyparts) == len(bodyparts):
        if output_path and target_out != path:
            shutil.copy2(path, target_out)
        return {
            "success": True,
            "message": "No chrome overlay detected. Model is already pristine.",
            "removed": False,
            "has_chrome": False,
            "saved_path": str(target_out),
        }

    # Rebuild binary MDL
    rebuilt_buf = serialize_model_binary(
        header_block1=header_block1,
        bodyparts=cleaned_bodyparts,
        textures=cleaned_textures,
        skin_table=cleaned_skin_table,
        numskinfamilies=numskinfamilies,
    )

    # Atomic save
    target_out.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_out.with_suffix(".tmp")
    with open(tmp_path, "wb") as f:
        f.write(rebuilt_buf)
    os.replace(tmp_path, target_out)

    # Validate health
    health = validate_model_health(target_out)
    if not health.get("healthy", False):
        raise RuntimeError(
            f"Health check failed on stripped model: {health.get('issues')}"
        )

    return {
        "success": True,
        "message": f"Successfully removed chrome overlay from {target_out.name}",
        "removed": True,
        "has_chrome": False,
        "saved_path": str(target_out),
        "removed_bodyparts_count": len(bodyparts) - len(cleaned_bodyparts),
        "removed_textures": removed_tex_names,
        "health": health,
    }
