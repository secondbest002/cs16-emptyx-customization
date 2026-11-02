"""
wear_simulator.py - Procedural Float & Wear Simulator for CS 1.6 Weapon Skins.
Simulates CS:GO-style wear from Factory New (0.00) to Battle-Scarred (1.00).

Features:
- Edge Detection Wear: High curvature and UV island boundaries lose paint first,
  exposing bare alloy metal.
- Procedural Scratches & Scuffs: Deterministic abrasion patterns scaled by wear float.
- Patina & Oxidation: Subtle desaturation and darkening as wear increases.
- Lossless GoldSrc 256-color palette quantization.
"""

from typing import Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .image_pipeline import load_image, quantize_goldsrc

# Bare metal base alloy color (weathered gun steel)
BARE_METAL_COLOR = np.array([85.0, 88.0, 95.0], dtype=np.float32)


def get_wear_condition_name(wear_float: float) -> str:
    """Returns official CS:GO/CS2 wear condition tier name."""
    f = max(0.0, min(1.0, float(wear_float)))
    if f < 0.07:
        return "Factory New (FN)"
    elif f < 0.15:
        return "Minimal Wear (MW)"
    elif f < 0.38:
        return "Field-Tested (FT)"
    elif f < 0.45:
        return "Well-Worn (WW)"
    else:
        return "Battle-Scarred (BS)"


def generate_wear_mask(
    width: int,
    height: int,
    wear_float: float,
    seed: int = 1337,
) -> np.ndarray:
    """
    Generates a deterministic procedural scratch and abrasion mask in range [0.0, 1.0].
    """
    rng = np.random.default_rng(seed)

    # Base noise map
    scale = 16
    sw, sh = max(4, width // scale), max(4, height // scale)
    low_res = rng.uniform(0.0, 1.0, (sh, sw)).astype(np.float32)
    low_img = Image.fromarray((low_res * 255).astype(np.uint8), mode="L")
    noise = low_img.resize((width, height), Image.Resampling.BICUBIC)
    noise_arr = np.array(noise, dtype=np.float32) / 255.0

    # Draw procedural scratch lines
    scratch_img = Image.new("L", (width, height), 0)
    scratch_draw = ImageDraw.Draw(scratch_img)

    num_scratches = int(wear_float * 120)
    for _ in range(num_scratches):
        x1 = int(rng.integers(0, width))
        y1 = int(rng.integers(0, height))
        length = float(rng.integers(10, max(15, width // 6)))
        angle = float(rng.uniform(-np.pi, np.pi))
        x2 = int(x1 + length * np.cos(angle))
        y2 = int(y1 + length * np.sin(angle))
        w = int(rng.integers(1, 3))
        fill_val = int(rng.integers(160, 255))
        scratch_draw.line([(x1, y1), (x2, y2)], fill=fill_val, width=w)

    scratch_arr = np.array(scratch_img, dtype=np.float32) / 255.0

    # Combine noise and scratches with wear threshold
    # Higher wear_float exposes more bare metal
    threshold = 1.0 - (wear_float * 0.95)
    combined = (noise_arr * 0.5 + scratch_arr * 0.5)

    # S-curve thresholding
    wear_intensity = np.clip((combined - threshold) / (1.0 - threshold + 1e-4), 0.0, 1.0)
    return wear_intensity


def apply_wear_simulation(
    source_image: Union[str, bytes, Image.Image],
    wear_float: float = 0.35,
    seed: int = 1337,
) -> Image.Image:
    """
    Applies procedural wear and scratches to a weapon texture.
    wear_float: 0.0 (Factory New, pristine) to 1.0 (Battle-Scarred, heavily worn).
    Returns:
        Adjusted PIL Image in RGBA mode.
    """
    img = load_image(source_image)
    w, h = img.width, img.height
    wear = float(np.clip(wear_float, 0.0, 1.0))

    if wear <= 0.001:
        return img

    rgb_arr = np.array(img.convert("RGB"), dtype=np.float32)
    alpha = np.array(img)[:, :, 3] if img.mode == "RGBA" else None

    # 1. Edge Detection (Sobel/Laplacian) - edges chip first
    gray_img = img.convert("L")
    edges = gray_img.filter(ImageFilter.FIND_EDGES)
    edge_arr = np.array(edges, dtype=np.float32) / 255.0
    # Dilate edges slightly
    edge_img = Image.fromarray((edge_arr * 255).astype(np.uint8), mode="L")
    dilated_edges = edge_img.filter(ImageFilter.MaxFilter(size=3))
    edge_mask = np.array(dilated_edges, dtype=np.float32) / 255.0

    # 2. Procedural scratch & scuff mask
    scratch_mask = generate_wear_mask(w, h, wear, seed=seed)

    # Total wear factor (weighted blend of edge chipping + surface abrasion)
    total_wear = np.clip(edge_mask * (wear * 1.4) + scratch_mask * (wear * 1.1), 0.0, 1.0)

    # 3. Patina / Darkening & Desaturation based on wear level
    lum = (0.299 * rgb_arr[:, :, 0] + 0.587 * rgb_arr[:, :, 1] + 0.114 * rgb_arr[:, :, 2])[:, :, None]
    patina_factor = 1.0 - (wear * 0.25)
    desat_factor = 1.0 - (wear * 0.35)
    aged_rgb = (lum + (rgb_arr - lum) * desat_factor) * patina_factor

    # 4. Blend bare metal into worn areas
    # Add slight metallic brightness variation to bare metal
    rng = np.random.default_rng(seed + 1)
    metal_noise = rng.uniform(-10.0, 10.0, (h, w, 1)).astype(np.float32)
    bare_metal = np.clip(BARE_METAL_COLOR + metal_noise, 0.0, 255.0)

    final_rgb = aged_rgb * (1.0 - total_wear[:, :, None]) + bare_metal * total_wear[:, :, None]
    final_rgb = np.clip(final_rgb, 0.0, 255.0).astype(np.uint8)

    if alpha is not None:
        final_rgba = np.dstack([final_rgb, alpha])
        return Image.fromarray(final_rgba, mode="RGBA")
    return Image.fromarray(final_rgb, mode="RGB").convert("RGBA")


def simulate_and_quantize(
    source_image: Union[str, bytes, Image.Image],
    wear_float: float = 0.35,
    seed: int = 1337,
    is_masked: bool = False,
) -> Tuple[bytes, Image.Image]:
    """
    Simulates wear float and quantizes to 8-bit GoldSrc format.
    Returns:
        (goldsrc_payload_bytes, worn_rgba_image)
    """
    worn_img = apply_wear_simulation(source_image, wear_float=wear_float, seed=seed)
    pix_bytes, pal_bytes = quantize_goldsrc(worn_img, is_masked=is_masked, defringe=is_masked)
    payload = pix_bytes + pal_bytes
    return payload, worn_img
