"""
sticker_scraper.py - Procedural Sticker Scraping (Wear / Abrasion) Engine
Simulates CS:GO / CS2-style sticker scraping from Mint / Factory New (0%)
to Heavily Scraped / Battle-Worn (100%).

Features:
- Edge Erosion: Stickers peel and erode inward from the outer transparent border.
- Procedural Scratches: Sharp abrasion cuts across the sticker surface.
- Multi-scale Noise Pitting: Fractal noise masks that simulate peeling vinyl/foil flakes.
- Authentic Wear Fading: Faded paper backing / scuff desaturation near scraped boundaries.
- Full compatibility with GoldSrc 8-bit palette quantization and alpha transparency.
"""

from pathlib import Path
from typing import Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .image_pipeline import load_image, quantize_goldsrc


def get_scrape_condition_name(scrape_percent: float) -> str:
    """Returns descriptive wear tier name for sticker scrape level."""
    s = float(scrape_percent)
    if s > 1.0:
        s = s / 100.0
    s = max(0.0, min(1.0, s))

    if s <= 0.05:
        return "Mint / Factory New (0%)"
    elif s <= 0.25:
        return "Light Scrape (25%)"
    elif s <= 0.50:
        return "Moderate Scrape (50%)"
    elif s <= 0.75:
        return "Heavy Scrape (75%)"
    else:
        return "Battle-Worn Scrape (100%)"


def generate_scrape_mask(
    width: int,
    height: int,
    scrape_ratio: float,
    seed: int = 1337,
) -> np.ndarray:
    """
    Generates a deterministic float32 procedural scratch and abrasion mask in range [0.0, 1.0].
    Higher values represent more intense erosion/loss of sticker material.
    """
    rng = np.random.default_rng(seed)
    ratio = float(np.clip(scrape_ratio, 0.0, 1.0))

    if ratio <= 0.001:
        return np.zeros((height, width), dtype=np.float32)

    # 1. Multi-scale noise pitting (simulating organic flaking and peeling)
    # Scale 1: Coarse flakes
    scale_c = max(4, min(width, height) // 8)
    cw, ch = max(4, width // scale_c), max(4, height // scale_c)
    coarse_res = rng.uniform(0.0, 1.0, (ch, cw)).astype(np.float32)
    coarse_img = Image.fromarray((coarse_res * 255).astype(np.uint8), mode="L")
    coarse_noise = np.array(
        coarse_img.resize((width, height), Image.Resampling.BICUBIC),
        dtype=np.float32,
    ) / 255.0

    # Scale 2: Medium flakes
    scale_m = max(2, min(width, height) // 16)
    mw, mh = max(4, width // scale_m), max(4, height // scale_m)
    med_res = rng.uniform(0.0, 1.0, (mh, mw)).astype(np.float32)
    med_img = Image.fromarray((med_res * 255).astype(np.uint8), mode="L")
    med_noise = np.array(
        med_img.resize((width, height), Image.Resampling.BICUBIC),
        dtype=np.float32,
    ) / 255.0

    noise_combined = coarse_noise * 0.6 + med_noise * 0.4

    # 2. Procedural sharp scratch lines (blade/coin scraper marks)
    scratch_img = Image.new("L", (width, height), 0)
    scratch_draw = ImageDraw.Draw(scratch_img)

    num_scratches = int(ratio * 90)
    for _ in range(num_scratches):
        x1 = int(rng.integers(0, width))
        y1 = int(rng.integers(0, height))
        length = float(rng.integers(8, max(12, int(min(width, height) * 0.45))))
        angle = float(rng.uniform(-np.pi, np.pi))
        x2 = int(x1 + length * np.cos(angle))
        y2 = int(y1 + length * np.sin(angle))
        w = int(rng.integers(1, 3))
        fill_val = int(rng.integers(180, 255))
        scratch_draw.line([(x1, y1), (x2, y2)], fill=fill_val, width=w)

    scratch_arr = np.array(scratch_img, dtype=np.float32) / 255.0

    # Combine noise and scratch lines
    wear_field = noise_combined * 0.55 + scratch_arr * 0.45
    return np.clip(wear_field, 0.0, 1.0)


def apply_sticker_scraping(
    source_image: Union[str, Path, bytes, Image.Image],
    scrape_percent: Union[float, int] = 0.0,
    seed: int = 1337,
) -> Image.Image:
    """
    Applies procedural scratch, peeling, and erosion masks to a sticker RGBA image.

    scrape_percent:
        0.0 (or 0) = Clean / Factory New / Mint.
        1.0 (or 100) = Heavily scraped / Battle-worn / Completely eroded.
    seed:
        Deterministic PRNG seed for reproducible scrape patterns.

    Returns:
        Modified PIL Image in RGBA mode.
    """
    if source_image is None:
        raise ValueError("source_image cannot be None")
    img = load_image(source_image).convert("RGBA")
    w, h = img.width, img.height

    if w <= 0 or h <= 0:
        return img.copy()

    # Safely normalize scrape_percent to [0.0, 1.0]
    if scrape_percent is None:
        return img.copy()
    try:
        val = float(scrape_percent)
    except (ValueError, TypeError):
        val = 0.0

    if val > 1.0:
        val = val / 100.0
    ratio = float(np.clip(val, 0.0, 1.0))

    # Pristine shortcut
    if ratio <= 0.001:
        return img.copy()

    img_arr = np.array(img, dtype=np.float32)
    rgb = img_arr[:, :, :3]
    orig_alpha = img_arr[:, :, 3]

    # If already completely transparent
    if np.max(orig_alpha) < 1.0:
        return img.copy()

    # 1. Edge Erosion (Stickers peel from perimeter inward first)
    if min(w, h) >= 3:
        alpha_img = Image.fromarray(orig_alpha.astype(np.uint8), mode="L")
        # Multi-step morphological min filter to detect distance from perimeter
        eroded1 = alpha_img.filter(ImageFilter.MinFilter(size=3))
        eroded2 = eroded1.filter(ImageFilter.MinFilter(size=3))
        eroded3 = eroded2.filter(ImageFilter.MinFilter(size=3))

        edge_dist1 = (orig_alpha - np.array(eroded1, dtype=np.float32)) / 255.0
        edge_dist2 = (orig_alpha - np.array(eroded2, dtype=np.float32)) / 255.0
        edge_dist3 = (orig_alpha - np.array(eroded3, dtype=np.float32)) / 255.0

        # Progressive edge wear based on scrape level
        edge_wear = np.clip(
            edge_dist1 * 1.5 + edge_dist2 * 1.0 + edge_dist3 * 0.7,
            0.0,
            1.0,
        )
    else:
        edge_wear = np.zeros_like(orig_alpha)

    # 2. Surface abrasion & scratch noise
    noise_mask = generate_scrape_mask(w, h, ratio, seed=seed)

    # 3. Combined erosion field
    # Edges erode with higher sensitivity as scrape increases
    erosion_field = edge_wear * (0.35 + ratio * 0.65) + noise_mask * (0.65 + ratio * 0.35)

    # Threshold curve: As ratio increases, threshold lowers so more material is scraped away.
    # At ratio 0.05: only the very highest noise peaks erode
    # At ratio 0.50: ~35-40% worn away
    # At ratio 1.00: heavily scraped (~80-85% eroded), with visible scratch cuts and peeled edge remnants
    threshold = 1.08 - (ratio * 0.88)
    softness = 0.20 - (ratio * 0.10)  # Sharper tear edges as wear progresses

    # Erosion factor: 0.0 (intact) to 1.0 (fully scraped)
    wear_factor = np.clip((erosion_field - threshold) / max(0.01, softness), 0.0, 1.0)

    # Compute new alpha channel
    new_alpha = orig_alpha * (1.0 - wear_factor)
    new_alpha = np.clip(new_alpha, 0.0, 255.0).astype(np.uint8)

    # 4. Realistic CS:GO / CS2 Sticker Scuff Residue
    # In areas undergoing abrasion, desaturate slightly and blend faint whitish paper residue
    paper_color = np.array([225.0, 225.0, 220.0], dtype=np.float32)
    lum = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])[:, :, None]
    desat_rgb = lum * 0.4 + rgb * 0.6

    # Paper backing fringe shows where wear_factor is between 0.3 and 0.8
    paper_fringe = np.clip(1.0 - np.abs(wear_factor - 0.55) / 0.35, 0.0, 1.0)[:, :, None]
    worn_rgb = desat_rgb * (1.0 - paper_fringe * 0.5) + paper_color * (paper_fringe * 0.5)

    final_rgb = np.clip(worn_rgb, 0.0, 255.0).astype(np.uint8)
    final_rgba = np.dstack([final_rgb, new_alpha])

    return Image.fromarray(final_rgba, mode="RGBA")


def scrape_and_quantize(
    source_image: Union[str, Path, bytes, Image.Image],
    scrape_percent: float = 0.0,
    target_w: int = 256,
    target_h: int = 256,
    is_masked: bool = True,
    seed: int = 1337,
) -> Tuple[bytes, Image.Image]:
    """
    Applies procedural scrape wear to a sticker, resizes to target slot size,
    and quantizes into GoldSrc 8-bit format.
    Returns:
        (goldsrc_payload_bytes, preview_rgba_image)
    """
    worn_img = apply_sticker_scraping(source_image, scrape_percent=scrape_percent, seed=seed)
    if worn_img.size != (target_w, target_h):
        worn_img = worn_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    pix_bytes, pal_bytes = quantize_goldsrc(worn_img, is_masked=is_masked, defringe=is_masked)
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
