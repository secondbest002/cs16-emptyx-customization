"""
baker.py - 2D Texture Baking Engine for Counter-Strike 1.6 weapon skins.
Allows placing transparent PNG stickers directly onto weapon surfaces
(e.g., silencer, slide, receiver) before 8-bit GoldSrc quantization.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from .image_pipeline import load_image, quantize_goldsrc

PRESET_POSITIONS: Dict[str, Dict[str, Tuple[int, int]]] = {
    "usp": {
        "silencer": (360, 180),
        "slide": (220, 180),
        "grip": (150, 320),
    },
    "ak47": {
        "wood": (180, 240),
        "body": (280, 230),
        "mag": (310, 360),
        "stock": (40, 260),
    },
    "m4a1": {
        "silencer": (380, 180),
        "body": (250, 220),
        "mag": (260, 340),
        "stock": (90, 230),
    },
    "m4a4": {
        "body": (250, 220),
        "mag": (260, 340),
        "barrel": (390, 180),
        "stock": (90, 230),
    },
    "awp": {
        "body": (240, 260),
        "scope": (250, 100),
        "stock": (80, 280),
        "front": (380, 240),
    },
    "deagle": {
        "slide": (230, 180),
        "grip": (160, 320),
        "front": (340, 180),
    },
    "glock18": {
        "slide": (230, 180),
        "grip": (160, 320),
    },
}


def resolve_bake_position(
    weapon_key: str,
    canvas_w: int,
    canvas_h: int,
    preset: Optional[str] = None,
    custom_coords: Optional[Tuple[int, int]] = None,
) -> Tuple[int, int]:
    if custom_coords:
        return custom_coords

    weapon_clean = weapon_key.lower().replace("v_", "").replace(".mdl", "")
    matched_key = None
    for k in PRESET_POSITIONS:
        if k in weapon_clean:
            matched_key = k
            break

    if preset and matched_key and preset.lower() in PRESET_POSITIONS[matched_key]:
        px, py = PRESET_POSITIONS[matched_key][preset.lower()]
        if canvas_w != 512 or canvas_h != 512:
            px = int(px * (canvas_w / 512.0))
            py = int(py * (canvas_h / 512.0))
        return (px, py)

    preset_lower = (preset or "center").lower()
    if preset_lower == "center":
        return (int(canvas_w * 0.4), int(canvas_h * 0.45))
    elif preset_lower == "top-left":
        return (int(canvas_w * 0.2), int(canvas_h * 0.2))
    elif preset_lower == "top-right":
        return (int(canvas_w * 0.65), int(canvas_h * 0.2))
    elif preset_lower == "bottom-left":
        return (int(canvas_w * 0.2), int(canvas_h * 0.65))
    elif preset_lower == "bottom-right":
        return (int(canvas_w * 0.65), int(canvas_h * 0.65))

    return (int(canvas_w * 0.4), int(canvas_h * 0.45))


def bake_sticker_onto_texture(
    base_image: Union[str, Path, bytes, Image.Image],
    sticker_image: Union[str, Path, bytes, Image.Image],
    weapon_key: str = "generic",
    preset: Optional[str] = "center",
    custom_coords: Optional[Tuple[int, int]] = None,
    scale_multiplier: float = 1.0,
    rotation_deg: float = 0.0,
    scrape: float = 0.0,
    pre_emphasis: bool = False,
    chrome_effect: Optional[str] = None,
) -> Tuple[bytes, Image.Image]:
    base_rgba = load_image(base_image)
    sticker_rgba = load_image(sticker_image)

    if scrape > 0:
        from .sticker_scraper import apply_sticker_scraping
        sticker_rgba = apply_sticker_scraping(sticker_rgba, scrape_percent=scrape)

    bw, bh = base_rgba.width, base_rgba.height

    base_dim = max(8, int(round(bw * 0.25 * max(0.05, float(scale_multiplier)))))

    orig_sw, orig_sh = sticker_rgba.width, sticker_rgba.height
    aspect = orig_sw / float(orig_sh) if orig_sh > 0 else 1.0

    if aspect >= 1.0:
        target_sw = base_dim
        target_sh = max(8, int(round(target_sw / aspect)))
    else:
        target_sh = base_dim
        target_sw = max(8, int(round(target_sh * aspect)))

    scaled_sticker = sticker_rgba.resize((target_sw, target_sh), Image.Resampling.LANCZOS)

    if rotation_deg % 360 != 0:
        scaled_sticker = scaled_sticker.rotate(
            -rotation_deg, resample=Image.Resampling.BICUBIC, expand=True
        )

    if chrome_effect:
        from .chrome_injector import generate_chrome_texture
        try:
            chrome_img = generate_chrome_texture(preset=chrome_effect, width=scaled_sticker.width, height=scaled_sticker.height)
            ch_arr = np.array(chrome_img.convert("RGBA"), dtype=np.float32)
            st_arr = np.array(scaled_sticker, dtype=np.float32)
            shine = (ch_arr[:, :, :3] / 255.0) * 0.45
            st_arr[:, :, :3] = np.clip(st_arr[:, :, :3] * (1.0 + shine), 0, 255)
            scaled_sticker = Image.fromarray(st_arr.astype(np.uint8), mode="RGBA")
        except Exception:
            pass

    if pre_emphasis:
        scaled_sticker = ImageEnhance.Color(scaled_sticker).enhance(1.15)
        scaled_sticker = ImageEnhance.Contrast(scaled_sticker).enhance(1.10)
        scaled_sticker = scaled_sticker.filter(
            ImageFilter.UnsharpMask(radius=1.2, percent=130, threshold=2)
        )

    px, py = resolve_bake_position(weapon_key, bw, bh, preset=preset, custom_coords=custom_coords)

    center_x = px - (scaled_sticker.width // 2)
    center_y = py - (scaled_sticker.height // 2)

    if not custom_coords:
        if center_x + scaled_sticker.width > bw:
            center_x = max(0, bw - scaled_sticker.width)
        if center_y + scaled_sticker.height > bh:
            center_y = max(0, bh - scaled_sticker.height)
        center_x = max(0, center_x)
        center_y = max(0, center_y)

    composite = base_rgba.copy()
    composite.paste(scaled_sticker, (center_x, center_y), scaled_sticker)

    pix_bytes, pal_bytes = quantize_goldsrc(composite, is_masked=False)
    payload = pix_bytes + pal_bytes

    return payload, composite
