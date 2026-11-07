"""
image_pipeline.py - Image ingestion, Lanczos resampling, Smart Fit & Pad,
Matte Defringing, and GoldSrc 8-bit quantization with strict Index 255 Pinning.
"""

import io
from pathlib import Path
from typing import Optional, Tuple, Union
import numpy as np
from PIL import Image

GOLDSRC_MASK_COLOR = (0, 0, 255)


def load_image(source: Union[str, Path, bytes, Image.Image]) -> Image.Image:
    if isinstance(source, Image.Image):
        return source.convert("RGBA")
    if isinstance(source, bytes):
        return Image.open(io.BytesIO(source)).convert("RGBA")
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"Source image not found: {path}")
    return Image.open(path).convert("RGBA")


def defringe_matte(img: Image.Image, alpha_thresh: int = 128) -> Image.Image:
    rgba = np.array(img, dtype=np.float32)
    r = rgba[:, :, 0]
    g = rgba[:, :, 1]
    b = rgba[:, :, 2]
    a = rgba[:, :, 3]

    semi_mask = (a > 0) & (a < 255)
    if np.any(semi_mask):
        alpha_factor = 255.0 / np.maximum(a[semi_mask], 1.0)
        r[semi_mask] = np.clip(r[semi_mask] * alpha_factor, 0, 255)
        g[semi_mask] = np.clip(g[semi_mask] * alpha_factor, 0, 255)
        b[semi_mask] = np.clip(b[semi_mask] * alpha_factor, 0, 255)

    solid_mask = a >= alpha_thresh
    a[solid_mask] = 255.0
    a[~solid_mask] = 0.0

    result_arr = np.stack([r, g, b, a], axis=-1).astype(np.uint8)
    return Image.fromarray(result_arr, mode="RGBA")


def resize_smart_fit(
    img: Image.Image,
    target_w: int,
    target_h: int,
    scale_multiplier: float = 1.0,
    background_color: Tuple[int, int, int, int] = (0, 0, 0, 0),
) -> Image.Image:
    orig_w, orig_h = img.width, img.height
    if orig_w <= 0 or orig_h <= 0:
        return Image.new("RGBA", (target_w, target_h), background_color)

    fit_scale = min(target_w / float(orig_w), target_h / float(orig_h))
    scale = fit_scale * max(0.01, scale_multiplier)
    if scale > fit_scale:
        scale = fit_scale

    new_w = max(4, min(target_w, int(round(orig_w * scale))))
    new_h = max(4, min(target_h, int(round(orig_h * scale))))

    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (target_w, target_h), background_color)
    offset_x = (target_w - new_w) // 2
    offset_y = (target_h - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y))

    return canvas


def resize_stretch_uv(
    img: Image.Image,
    target_w: int,
    target_h: int,
) -> Image.Image:
    return img.resize((target_w, target_h), Image.Resampling.LANCZOS)


def quantize_goldsrc(
    img: Image.Image,
    is_masked: bool = False,
    alpha_thresh: int = 128,
    defringe: bool = True,
    dither: str = "floyd_steinberg",
) -> Tuple[bytes, bytes]:
    dither_mode = Image.Dither.NONE if str(dither).lower() in ("none", "off", "0") else Image.Dither.FLOYDSTEINBERG
    w, h = img.width, img.height

    if is_masked:
        if defringe:
            img = defringe_matte(img, alpha_thresh=alpha_thresh)

        alpha = np.array(img.split()[-1])
        solid_mask = alpha >= alpha_thresh

        if not np.any(solid_mask):
            pixels = np.full((h, w), 255, dtype=np.uint8)
            pal = [0] * 765 + list(GOLDSRC_MASK_COLOR)
            return pixels.tobytes(), bytes(pal)

        img_arr = np.array(img)
        solid_rgb = img_arr[:, :, :3][solid_mask]
        solid_patch = Image.fromarray(solid_rgb.reshape(-1, 1, 3), mode="RGB")
        q_patch = solid_patch.quantize(colors=255, method=Image.Quantize.MEDIANCUT)

        raw_pal = list(q_patch.getpalette() or [])[: 255 * 3]
        while len(raw_pal) < 255 * 3:
            raw_pal.extend([0, 0, 0])

        raw_pal = raw_pal[: 255 * 3] + list(GOLDSRC_MASK_COLOR)

        rgb_img = img.convert("RGB")
        q_img = rgb_img.quantize(palette=q_patch, dither=dither_mode)

        pixel_arr = np.array(q_img, dtype=np.uint8)
        pixel_arr[pixel_arr >= 255] = 254
        pixel_arr[~solid_mask] = 255

        return pixel_arr.tobytes(), bytes(raw_pal)

    else:
        rgb_img = img.convert("RGB")
        q_img = rgb_img.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=dither_mode)

        raw_pal = list(q_img.getpalette() or [])[: 256 * 3]
        while len(raw_pal) < 256 * 3:
            raw_pal.extend([0, 0, 0])
        raw_pal = raw_pal[: 256 * 3]

        pixel_arr = np.array(q_img, dtype=np.uint8)
        return pixel_arr.tobytes(), bytes(raw_pal)


def process_image_for_texture(
    input_image: Union[str, Path, bytes, Image.Image],
    target_w: int,
    target_h: int,
    is_masked: bool,
    mode: str = "auto",
    scale_multiplier: float = 1.0,
    alpha_thresh: int = 128,
) -> Tuple[bytes, Image.Image]:
    img = load_image(input_image)

    if mode == "auto":
        mode = "fit" if is_masked else "stretch"

    if mode == "fit":
        processed_img = resize_smart_fit(
            img, target_w, target_h, scale_multiplier=scale_multiplier
        )
    else:
        processed_img = resize_stretch_uv(img, target_w, target_h)

    pix_bytes, pal_bytes = quantize_goldsrc(
        processed_img,
        is_masked=is_masked,
        alpha_thresh=alpha_thresh,
        defringe=is_masked,
    )

    payload = pix_bytes + pal_bytes

    p_img = Image.frombytes("P", (target_w, target_h), pix_bytes)
    p_img.putpalette(list(pal_bytes))
    preview_rgba = p_img.convert("RGBA")

    if is_masked:
        pix_arr = np.frombuffer(pix_bytes, dtype=np.uint8)
        rgba_arr = np.array(preview_rgba)
        rgba_arr[pix_arr.reshape((target_h, target_w)) == 255, 3] = 0
        preview_rgba = Image.fromarray(rgba_arr, mode="RGBA")

    return payload, preview_rgba


def process_slot_sticker_with_transform(
    input_image: Union[str, Path, bytes, Image.Image],
    target_w: int,
    target_h: int,
    scale: float = 1.0,
    offset_x: int = 0,
    offset_y: int = 0,
    rotation: float = 0.0,
    fit_mode: str = "fit",
    alpha_thresh: int = 128,
    scrape: float = 0.0,
) -> Tuple[bytes, Image.Image]:
    img = load_image(input_image)
    if scrape > 0:
        from .sticker_scraper import apply_sticker_scraping
        img = apply_sticker_scraping(img, scrape_percent=scrape)
    orig_w, orig_h = img.width, img.height

    if orig_w <= 0 or orig_h <= 0:
        empty = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        pix_bytes, pal_bytes = quantize_goldsrc(empty, is_masked=True)
        return pix_bytes + pal_bytes, empty

    if str(fit_mode).lower() == "stretch":
        sw = max(4, int(round(target_w * max(0.05, float(scale)))))
        sh = max(4, int(round(target_h * max(0.05, float(scale)))))
    else:
        fit_scale = min(target_w / float(orig_w), target_h / float(orig_h))
        applied_scale = fit_scale * max(0.05, float(scale))
        sw = max(4, int(round(orig_w * applied_scale)))
        sh = max(4, int(round(orig_h * applied_scale)))

    scaled_sticker = img.resize((sw, sh), Image.Resampling.LANCZOS)

    rot_val = float(rotation) % 360
    if rot_val != 0:
        scaled_sticker = scaled_sticker.rotate(
            -rot_val, resample=Image.Resampling.BICUBIC, expand=True
        )

    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))

    center_x = (target_w // 2) + int(offset_x)
    center_y = (target_h // 2) + int(offset_y)

    paste_x = center_x - (scaled_sticker.width // 2)
    paste_y = center_y - (scaled_sticker.height // 2)

    canvas.paste(scaled_sticker, (paste_x, paste_y), scaled_sticker)

    pix_bytes, pal_bytes = quantize_goldsrc(
        canvas,
        is_masked=True,
        alpha_thresh=alpha_thresh,
        defringe=True,
    )
    payload = pix_bytes + pal_bytes

    p_img = Image.frombytes("P", (target_w, target_h), pix_bytes)
    p_img.putpalette(list(pal_bytes))
    preview_rgba = p_img.convert("RGBA")

    pix_arr = np.frombuffer(pix_bytes, dtype=np.uint8)
    rgba_arr = np.array(preview_rgba)
    rgba_arr[pix_arr.reshape((target_h, target_w)) == 255, 3] = 0
    preview_rgba = Image.fromarray(rgba_arr, mode="RGBA")

    return payload, preview_rgba
