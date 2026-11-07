"""
baker.py - 2D Texture Baking Engine for Counter-Strike 1.6 weapon skins.
Allows placing transparent PNG stickers directly onto weapon surfaces
(e.g., silencer, slide, receiver) before 8-bit GoldSrc quantization.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
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


def transform_sticker_layer(
    sticker_image: Union[str, Path, bytes, Image.Image],
    base_w: int,
    base_h: int,
    scale: float = 1.0,
    rotation: float = 0.0,
    scrape: float = 0.0,
    opacity: float = 1.0,
    chrome_effect: Optional[str] = None,
) -> Image.Image:
    """
    Transforms a single sticker: scales relative to canvas dimensions, applies scrape,
    rotates, optionally applies chrome effect, and adjusts opacity.
    """
    sticker_rgba = load_image(sticker_image).convert("RGBA")

    if scrape > 0:
        from .sticker_scraper import apply_sticker_scraping
        sticker_rgba = apply_sticker_scraping(sticker_rgba, scrape_percent=scrape)

    base_dim = max(8, int(round(base_w * 0.25 * max(0.05, float(scale)))))
    orig_sw, orig_sh = sticker_rgba.width, sticker_rgba.height
    aspect = orig_sw / float(orig_sh) if orig_sh > 0 else 1.0

    if aspect >= 1.0:
        target_sw = base_dim
        target_sh = max(8, int(round(target_sw / aspect)))
    else:
        target_sh = base_dim
        target_sw = max(8, int(round(target_sh * aspect)))

    scaled = sticker_rgba.resize((target_sw, target_sh), Image.Resampling.LANCZOS)

    if rotation % 360 != 0:
        scaled = scaled.rotate(-rotation, resample=Image.Resampling.BICUBIC, expand=True)

    if chrome_effect:
        from .chrome_injector import generate_chrome_texture
        try:
            chrome_img = generate_chrome_texture(
                preset=chrome_effect, width=scaled.width, height=scaled.height
            )
            ch_arr = np.array(chrome_img.convert("RGBA"), dtype=np.float32)
            st_arr = np.array(scaled, dtype=np.float32)
            shine = (ch_arr[:, :, :3] / 255.0) * 0.45
            st_arr[:, :, :3] = np.clip(st_arr[:, :, :3] * (1.0 + shine), 0, 255)
            scaled = Image.fromarray(st_arr.astype(np.uint8), mode="RGBA")
        except Exception:
            pass

    if opacity < 0.999:
        op = max(0.0, min(1.0, float(opacity)))
        r, g, b, a = scaled.split()
        a = a.point(lambda p: int(round(p * op)))
        scaled = Image.merge("RGBA", (r, g, b, a))

    return scaled


def composite_multi_stickers(
    base_image: Union[str, Path, bytes, Image.Image],
    layers: List[Dict[str, Any]],
    weapon_key: str = "generic",
) -> Image.Image:
    """
    Composites multiple free-form sticker layers onto the base texture in 32-bit RGBA space.
    Each layer is a dict with:
        image: str, Path, bytes, or Image
        x, y: center coordinates (int)
        scale: float (default 1.0)
        rotation: float (degrees, default 0.0)
        scrape: float (0-100%, default 0.0)
        opacity: float (0.0-1.0, default 1.0)
        chrome_effect: optional str preset
        visible: bool (default True)
        z_index: int (default 0)
    """
    base_rgba = load_image(base_image).convert("RGBA")
    bw, bh = base_rgba.width, base_rgba.height
    composite = base_rgba.copy()

    sorted_layers = sorted(layers, key=lambda l: l.get("z_index", 0))

    for layer in sorted_layers:
        if not layer.get("visible", True):
            continue

        img_src = layer.get("image") or layer.get("image_source") or layer.get("image_path") or layer.get("image_base64")
        if not img_src:
            continue

        scale = float(layer.get("scale", 1.0))
        rot = float(layer.get("rotation", 0.0))
        scrape = float(layer.get("scrape", 0.0))
        opacity = float(layer.get("opacity", 1.0))
        chrome = layer.get("chrome_effect")

        # Resolve position
        cx = layer.get("x")
        cy = layer.get("y")
        if cx is None or cy is None:
            preset = layer.get("preset", "center")
            px, py = resolve_bake_position(weapon_key, bw, bh, preset=preset)
            cx = px if cx is None else int(cx)
            cy = py if cy is None else int(cy)
        else:
            cx = int(cx)
            cy = int(cy)

        transformed = transform_sticker_layer(
            img_src,
            base_w=bw,
            base_h=bh,
            scale=scale,
            rotation=rot,
            scrape=scrape,
            opacity=opacity,
            chrome_effect=chrome,
        )

        tl_x = cx - (transformed.width // 2)
        tl_y = cy - (transformed.height // 2)

        # High-precision alpha composite via layer canvas
        layer_canvas = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        layer_canvas.paste(transformed, (tl_x, tl_y))
        composite = Image.alpha_composite(composite, layer_canvas)

    return composite


def bake_multi_stickers_onto_texture(
    base_image: Union[str, Path, bytes, Image.Image],
    layers: List[Dict[str, Any]],
    weapon_key: str = "generic",
    dither: str = "floyd_steinberg",
) -> Tuple[bytes, Image.Image]:
    """
    Composites multiple free-form sticker layers onto the base texture
    in 32-bit RGBA space, then performs ONE master 256-color quantization pass.
    Returns (payload_bytes, composite_pil_image).
    """
    composite = composite_multi_stickers(base_image, layers, weapon_key=weapon_key)
    pix_bytes, pal_bytes = quantize_goldsrc(composite, is_masked=False, dither=dither)
    payload = pix_bytes + pal_bytes
    return payload, composite
