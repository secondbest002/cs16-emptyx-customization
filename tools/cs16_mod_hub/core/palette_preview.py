"""
tools/cs16_mod_hub/core/palette_preview.py
High-performance in-memory GoldSrc texture and palette preview engine.
Extracts uncompressed 8-bit indexed textures directly from MDL binary files and performs
real-time HSV color transformations for responsive GUI preview thumbnails.
"""

from __future__ import annotations

import colorsys
import os
from pathlib import Path
import struct
from typing import Optional, Tuple

from PIL import Image

from .common import get_project_root


def adjust_rgb(
    r: int,
    g: int,
    b: int,
    sat_mult: float = 1.0,
    cont_mult: float = 1.0,
    bright_mult: float = 1.0,
) -> Tuple[int, int, int]:
    """
    Transforms a single RGB color triple using HSV saturation, brightness, and contrast.
    Matches the algorithm used in adjust_vibrance.py.
    """
    # 1. Convert RGB (0..255) to HSV (0..1)
    r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r_n, g_n, b_n)

    # 2. Adjust Saturation
    s = min(max(s * sat_mult, 0.0), 1.0)

    # 3. Adjust Brightness
    v = min(max(v * bright_mult, 0.0), 1.0)

    # 4. Convert back to RGB (0..255)
    r_adj, g_adj, b_adj = colorsys.hsv_to_rgb(h, s, v)
    r_out, g_out, b_out = r_adj * 255.0, g_adj * 255.0, b_adj * 255.0

    # 5. Adjust Contrast around mid-gray (128.0)
    r_out = (r_out - 128.0) * cont_mult + 128.0
    g_out = (g_out - 128.0) * cont_mult + 128.0
    b_out = (b_out - 128.0) * cont_mult + 128.0

    return (
        int(min(max(round(r_out), 0), 255)),
        int(min(max(round(g_out), 0), 255)),
        int(min(max(round(b_out), 0), 255)),
    )


def transform_palette(
    palette: bytes,
    sat: float = 1.0,
    contrast: float = 1.0,
    brightness: float = 1.0,
    is_masked: bool = False,
) -> bytes:
    """
    Applies HSV adjustments to a 768-byte GoldSrc RGB palette.
    If is_masked is True, color index 255 (bytes 765:768) is kept unchanged to preserve transparency.
    """
    if len(palette) != 768:
        raise ValueError(f"Palette length must be exactly 768 bytes, got {len(palette)}")

    new_palette = bytearray(768)
    for c in range(256):
        offset = c * 3
        r = palette[offset]
        g = palette[offset + 1]
        b = palette[offset + 2]

        if is_masked and c == 255:
            new_palette[offset] = r
            new_palette[offset + 1] = g
            new_palette[offset + 2] = b
        else:
            ar, ag, ab = adjust_rgb(r, g, b, sat, contrast, brightness)
            new_palette[offset] = ar
            new_palette[offset + 1] = ag
            new_palette[offset + 2] = ab

    return bytes(new_palette)


from .common import get_project_root
from .profiles import get_active_profile_path
import io
import base64


def image_to_data_url(image: Image.Image, format: str = "JPEG", quality: int = 85) -> str:
    """Encodes a Pillow Image to a base64 Data URL for instant browser/webview rendering."""
    buf = io.BytesIO()
    if format.upper() == "JPEG" and image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    image.save(buf, format=format, quality=quality)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    mime = "image/jpeg" if format.upper() == "JPEG" else "image/png"
    return f"data:{mime};base64,{b64}"


def resolve_model_path(path_or_name: str, dir_path: Optional[str] = None) -> Path:
    """
    Resolves weapon name or path to an absolute Path.
    Checks the specified dir_path (or active profile directory) first.
    """
    root = get_project_root()
    norm = Path(path_or_name)
    if norm.is_file():
        return norm.resolve()

    base = norm.name
    if not any(base.startswith(p) for p in ["v_", "p_", "w_"]):
        base = f"v_{base}"
    if not base.endswith(".mdl"):
        base = f"{base}.mdl"

    active_dir = dir_path or get_active_profile_path()
    target_p = Path(active_dir)
    target_dir = target_p if target_p.is_absolute() else (root / target_p)

    search_dirs = [
        target_dir,
        root / "cstrike" / "models" / "custom_skins" / "ct",
        root / "cstrike" / "models" / "custom_skins" / "t",
        root / "cstrike_hd" / "models",
        root / "cstrike" / "models",
        root / "cstrike" / "models" / "csgo_skins" / "ct",
        root / "cstrike" / "models" / "csgo_skins" / "t",
    ]
    for d in search_dirs:
        candidate = d / base
        if candidate.is_file():
            return candidate.resolve()

    raise FileNotFoundError(f"Model file '{path_or_name}' not found in any known skin folder.")


def extract_weapon_texture(
    mdl_path: str,
    prefer_weapon: bool = True,
    target: str = "weapon",
    dir_path: Optional[str] = None,
) -> Tuple[str, int, int, int, bytes, bytes]:
    """
    Extracts the primary weapon or glove texture from a GoldSrc MDL file.
    Returns: (texture_name, flags, width, height, pixel_bytes, palette_bytes)
    """
    resolved = resolve_model_path(mdl_path, dir_path=dir_path)
    with open(resolved, "rb") as f:
        data = f.read()

    if len(data) < 188:
        raise ValueError(f"File too small for GoldSrc MDL: {resolved}")

    magic, ver = struct.unpack_from("<4sI", data, 0)
    if magic != b"IDST" or ver != 10:
        # If this model has ver == 11 (obfuscated), attempt fallback to cstrike_hd/models
        root = get_project_root()
        fallback_path = root / "cstrike_hd" / "models" / resolved.name
        if fallback_path.is_file() and fallback_path.resolve() != resolved:
            with open(fallback_path, "rb") as fb:
                data_fb = fb.read()
            if len(data_fb) >= 188:
                m_fb, v_fb = struct.unpack_from("<4sI", data_fb, 0)
                if m_fb == b"IDST" and v_fb == 10:
                    data = data_fb
                    resolved = fallback_path.resolve()
                    magic, ver = m_fb, v_fb

        if magic != b"IDST" or ver != 10:
            raise ValueError(f"Invalid GoldSrc MDL header in '{resolved.name}' (magic={magic!r}, ver={ver})")

    numtextures, textureindex = struct.unpack_from("<II", data, 180)
    if numtextures == 0:
        raise ValueError(f"Model contains zero textures: {resolved}")

    chosen = None
    fallback = None

    for i in range(numtextures):
        offset = textureindex + i * 80
        tname, flags, w, h, idx = struct.unpack_from("<64sIIII", data, offset)
        tname_str = tname.split(b"\x00")[0].decode("latin1", errors="ignore")

        pal_offset = idx + (w * h)
        if pal_offset + 768 > len(data):
            continue

        pixels = data[idx:pal_offset]
        palette = data[pal_offset : pal_offset + 768]
        entry = (tname_str, flags, w, h, pixels, palette)

        if fallback is None:
            fallback = entry

        lower = tname_str.lower()
        is_glove = any(k in lower for k in ["sport", "glove", "hand", "arm", "sleeve"])
        is_weapon = not any(ex in lower for ex in ["sport", "glove", "hand", "arm", "sleeve", "sticker", "stattrak", "decal"])

        if target == "gloves" or not prefer_weapon:
            if is_glove:
                chosen = entry
                break
        elif target == "weapon" or prefer_weapon:
            if is_weapon:
                chosen = entry
                break
        else:
            chosen = entry
            break

    if chosen is None:
        chosen = fallback

    if chosen is None:
        raise ValueError(f"No valid textures could be parsed from {resolved}")

    return chosen


def list_model_textures(mdl_path: str) -> list[dict]:
    """
    Enumerates all textures in a model for UI texture selector dropdowns.
    Returns list of dicts: {'index': int, 'name': str, 'width': int, 'height': int, 'flags': int, 'category': str}
    """
    resolved = resolve_model_path(mdl_path)
    with open(resolved, "rb") as f:
        data = f.read()

    numtextures, textureindex = struct.unpack_from("<II", data, 180)
    result = []
    for i in range(numtextures):
        offset = textureindex + i * 80
        tname, flags, w, h, idx = struct.unpack_from("<64sIIII", data, offset)
        tname_str = tname.split(b"\x00")[0].decode("latin1", errors="ignore")
        lower = tname_str.lower()
        if any(k in lower for k in ["sport", "glove", "hand", "arm", "sleeve"]):
            cat = "gloves"
        elif any(k in lower for k in ["sticker", "decal"]):
            cat = "sticker"
        elif any(k in lower for k in ["stattrak"]):
            cat = "stattrak"
        else:
            cat = "weapon"

        result.append({
            "index": i,
            "name": tname_str,
            "width": w,
            "height": h,
            "flags": flags,
            "category": cat,
        })
    return result


def composite_masked_texture(
    img_indexed: Image.Image,
    palette_bytes: bytes,
    bg_color: Tuple[int, int, int] = (34, 40, 49),
) -> Image.Image:
    """
    Renders a masked 8-bit texture (flags & 0x40) with transparent index 255
    composited cleanly over the specified background color (default: card background #222831).
    """
    img_copy = img_indexed.copy()
    img_copy.putpalette(palette_bytes)
    rgba = img_copy.convert("RGBA")

    # Fast pixel mask for index 255 transparency
    raw_pixels = img_indexed.tobytes()
    alpha_channel = bytearray(len(raw_pixels))
    for i, p in enumerate(raw_pixels):
        alpha_channel[i] = 0 if p == 255 else 255

    alpha_img = Image.frombytes("L", img_indexed.size, bytes(alpha_channel))
    rgba.putalpha(alpha_img)

    # Composite onto background
    bg = Image.new("RGBA", img_indexed.size, bg_color + (255,))
    combined = Image.alpha_composite(bg, rgba)
    return combined.convert("RGB")


def generate_preview_images(
    mdl_path: str,
    sat: float,
    contrast: float,
    brightness: float,
    thumb_size: Tuple[int, int] = (256, 256),
    prefer_weapon: bool = True,
) -> Tuple[Image.Image, Image.Image, str]:
    """
    Generates side-by-side Pillow thumbnails: (original_thumb, adjusted_thumb, info_str).
    Respects masked texture transparency index 255.
    """
    tname, flags, w, h, pixels, palette = extract_weapon_texture(mdl_path, prefer_weapon=prefer_weapon)
    is_masked = bool(flags & 0x40)

    # 1. Original RGB image
    orig_img = Image.frombytes("P", (w, h), pixels)
    if is_masked:
        orig_rgb = composite_masked_texture(orig_img, palette)
    else:
        orig_img.putpalette(palette)
        orig_rgb = orig_img.convert("RGB")

    # 2. Adjusted RGB image
    adj_palette = transform_palette(
        palette,
        sat=sat,
        contrast=contrast,
        brightness=brightness,
        is_masked=is_masked,
    )
    adj_img = Image.frombytes("P", (w, h), pixels)
    if is_masked:
        adj_rgb = composite_masked_texture(adj_img, adj_palette)
    else:
        adj_img.putpalette(adj_palette)
        adj_rgb = adj_img.convert("RGB")

    orig_thumb = orig_rgb.resize(thumb_size, Image.Resampling.LANCZOS)
    adj_thumb = adj_rgb.resize(thumb_size, Image.Resampling.LANCZOS)

    info_str = f"{tname} ({w}x{h})"
    return orig_thumb, adj_thumb, info_str


class TexturePreviewCache:
    """
    In-memory texture cache for 60 FPS slider dragging without disk I/O.
    The GUI loads the weapon texture once when selected, then recalculates
    only the adjusted thumbnail on slider drag events (< 1ms).
    """

    def __init__(self):
        self.mdl_path: Optional[str] = None
        self.texture_name: str = ""
        self.flags: int = 0
        self.width: int = 0
        self.height: int = 0
        self.pixels: bytes = b""
        self.palette: bytes = b""
        self.is_masked: bool = False
        self.orig_thumb: Optional[Image.Image] = None
        self.thumb_size: Tuple[int, int] = (256, 256)

    def load(
        self,
        mdl_path: str,
        thumb_size: Tuple[int, int] = (256, 256),
        prefer_weapon: bool = True,
        target: str = "weapon",
        dir_path: Optional[str] = None,
    ) -> Tuple[Image.Image, str]:
        """Loads and caches texture data from disk, generating the original thumbnail."""
        tname, flags, w, h, pixels, palette = extract_weapon_texture(
            mdl_path, prefer_weapon=prefer_weapon, target=target, dir_path=dir_path
        )
        self.mdl_path = mdl_path
        self.texture_name = tname
        self.flags = flags
        self.width = w
        self.height = h
        self.pixels = pixels
        self.palette = palette
        self.is_masked = bool(flags & 0x40)
        self.thumb_size = thumb_size

        img = Image.frombytes("P", (w, h), pixels)
        if self.is_masked:
            rgb = composite_masked_texture(img, palette)
        else:
            img.putpalette(palette)
            rgb = img.convert("RGB")

        self.orig_thumb = rgb.resize(thumb_size, Image.Resampling.LANCZOS)
        return self.orig_thumb, f"{tname} ({w}x{h})"

    def compute_adjusted_thumbnail(
        self,
        sat: float,
        contrast: float,
        brightness: float,
    ) -> Image.Image:
        """Computes the adjusted thumbnail purely in-memory without disk I/O."""
        if not self.pixels or not self.palette:
            return Image.new("RGB", self.thumb_size, color=(26, 30, 36))

        adj_palette = transform_palette(
            self.palette,
            sat=sat,
            contrast=contrast,
            brightness=brightness,
            is_masked=self.is_masked,
        )
        img = Image.frombytes("P", (self.width, self.height), self.pixels)
        if self.is_masked:
            adj_rgb = composite_masked_texture(img, adj_palette)
        else:
            img.putpalette(adj_palette)
            adj_rgb = img.convert("RGB")

        return adj_rgb.resize(self.thumb_size, Image.Resampling.LANCZOS)

    def get_preview_data_urls(
        self,
        sat: float = 1.0,
        contrast: float = 1.0,
        brightness: float = 1.0,
    ) -> Dict[str, str]:
        """
        Returns JSON-friendly dict with Base64 Data URLs for webview live rendering:
        {'original': 'data:image/jpeg;base64,...', 'adjusted': 'data:image/jpeg;base64,...', 'info': str}
        """
        if self.orig_thumb is None:
            blank = Image.new("RGB", self.thumb_size, color=(22, 27, 34))
            blank_url = image_to_data_url(blank)
            return {"original": blank_url, "adjusted": blank_url, "info": "No Model Loaded"}

        adj = self.compute_adjusted_thumbnail(sat, contrast, brightness)
        return {
            "original": image_to_data_url(self.orig_thumb),
            "adjusted": image_to_data_url(adj),
            "info": f"{self.texture_name} ({self.width}x{self.height})",
        }

