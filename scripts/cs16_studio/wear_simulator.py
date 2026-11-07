"""
wear_simulator.py - Curvature & Edge-Aware Float Wear Simulator for CS 1.6 Weapon Skins.
Simulates CS:GO/CS2-style float wear from Factory New (0.00) to Battle-Scarred (1.00).

Features:
- Sobel Curvature & Edge Detection: High curvature and UV island boundaries lose paint first,
  confining early wear strictly to sharp bevels and slide perimeters.
- Procedural Scratches & Scuffs: Deterministic abrasion patterns scaled by wear float.
- 65/35 Edge/Surface Wear Synthesis: WearSignal = (0.65 * EdgeGradient) + (0.35 * Noise).
- Directional Brushed Metal Alloy: Exposed metal features directional grain and alloy shading.
- 3D Chipped Paint Rim Shadow: Darkened peel edge at the transition between paint and bare alloy.
- Patina & Oxidation: Subtle desaturation and darkening as wear increases.
- Lossless GoldSrc 256-color palette quantization with adaptive error diffusion.
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


def generate_edge_gradient_mask(img: Image.Image) -> np.ndarray:
    """
    Computes a high-precision Sobel luminance gradient across the weapon texture
    to identify geometric curvature, slide corners, ejection ports, and UV island perimeters.
    Returns:
        np.ndarray of shape (H, W) with float values in [0.0, 1.0].
    """
    gray = img.convert("L")

    # 1. Gaussian pre-filter to smooth out high-frequency texture noise (decals/fonts)
    smooth_gray = gray.filter(ImageFilter.GaussianBlur(radius=1.5))
    lum = np.array(smooth_gray, dtype=np.float32)

    # 2. Vectorized Sobel convolution in NumPy
    gx = np.zeros_like(lum)
    gy = np.zeros_like(lum)
    gx[1:-1, 1:-1] = (lum[:-2, 2:] + 2 * lum[1:-1, 2:] + lum[2:, 2:]) - (lum[:-2, :-2] + 2 * lum[1:-1, :-2] + lum[2:, :-2])
    gy[1:-1, 1:-1] = (lum[2:, :-2] + 2 * lum[2:, 1:-1] + lum[2:, 2:]) - (lum[:-2, :-2] + 2 * lum[:-2, 1:-1] + lum[:-2, 2:])
    edge_mag = np.hypot(gx, gy)

    # 3. Alpha / Perimeter silhouette integration
    if img.mode == "RGBA":
        alpha = np.array(img)[:, :, 3].astype(np.float32)
        agx = np.zeros_like(alpha)
        agy = np.zeros_like(alpha)
        agx[1:-1, 1:-1] = (alpha[:-2, 2:] + 2 * alpha[1:-1, 2:] + alpha[2:, 2:]) - (alpha[:-2, :-2] + 2 * alpha[1:-1, :-2] + alpha[2:, :-2])
        agy[1:-1, 1:-1] = (alpha[2:, :-2] + 2 * alpha[2:, 1:-1] + alpha[2:, 2:]) - (alpha[:-2, :-2] + 2 * alpha[:-2, 1:-1] + alpha[:-2, 2:])
        alpha_edges = np.hypot(agx, agy)
        edge_mag = np.maximum(edge_mag, alpha_edges * 1.5)

    # 4. Normalize to [0, 1] using 98th percentile to resist outlier spikes
    pos_edges = edge_mag[edge_mag > 0]
    p_high = np.percentile(pos_edges, 98) if len(pos_edges) > 0 else 1.0
    norm_edges = np.clip(edge_mag / max(float(p_high), 1e-4), 0.0, 1.0)

    # 5. Multi-scale soft edge expansion (bevel falloff)
    norm_img = Image.fromarray((norm_edges * 255).astype(np.uint8), mode="L")
    dilated_3 = np.array(norm_img.filter(ImageFilter.MaxFilter(size=3)), dtype=np.float32) / 255.0
    blurred = np.array(norm_img.filter(ImageFilter.GaussianBlur(radius=2.5)), dtype=np.float32) / 255.0

    # Combine sharp edge ridge (50%) + immediate dilation (35%) + soft falloff (15%)
    curvature_gradient = np.clip(norm_edges * 0.50 + dilated_3 * 0.35 + blurred * 0.15, 0.0, 1.0)
    return curvature_gradient


def generate_wear_noise(
    width: int,
    height: int,
    wear_float: float,
    seed: int = 1337,
) -> np.ndarray:
    """
    Generates procedural organic scuff noise and micro-scratches.
    """
    rng = np.random.default_rng(seed)

    # Multi-octave coarse noise
    scale = 16
    sw, sh = max(4, width // scale), max(4, height // scale)
    low_res = rng.uniform(0.0, 1.0, (sh, sw)).astype(np.float32)
    low_img = Image.fromarray((low_res * 255).astype(np.uint8), mode="L")
    noise = low_img.resize((width, height), Image.Resampling.BICUBIC)
    noise_arr = np.array(noise, dtype=np.float32) / 255.0

    # Procedural scratches scaled by float
    scratch_img = Image.new("L", (width, height), 0)
    scratch_draw = ImageDraw.Draw(scratch_img)

    num_scratches = int(wear_float * 100)
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
    return np.clip(noise_arr * 0.55 + scratch_arr * 0.45, 0.0, 1.0)


def generate_wear_mask(
    width: int,
    height: int,
    wear_float: float,
    seed: int = 1337,
) -> np.ndarray:
    """
    Legacy wrapper for procedural wear noise in range [0.0, 1.0].
    """
    return generate_wear_noise(width, height, wear_float, seed=seed)


def apply_wear_simulation(
    source_image: Union[str, bytes, Image.Image],
    wear_float: float = 0.35,
    seed: int = 1337,
) -> Image.Image:
    """
    Curvature & Edge-Aware Float Wear Simulator.
    Blends:
        WearSignal = (0.65 * EdgeGradient) + (0.35 * Noise)
    Applies CS:GO float progression, brushed alloy shader, and chipped paint rim shadow.
    
    wear_float: 0.0 (Factory New, pristine) to 1.0 (Battle-Scarred, heavily worn).
    Returns:
        Adjusted PIL Image in RGBA mode.
    """
    img = load_image(source_image)
    f = float(np.clip(wear_float, 0.0, 1.0))
    if f <= 0.001:
        return img.convert("RGBA")

    w, h = img.width, img.height
    rgb_arr = np.array(img.convert("RGB"), dtype=np.float32)
    alpha = np.array(img)[:, :, 3] if img.mode == "RGBA" else None

    # 1. Compute curvature and edge-gradient map
    edge_gradient = generate_edge_gradient_mask(img)

    # 2. Compute organic noise & scratches
    noise_map = generate_wear_noise(w, h, wear_float=f, seed=seed)

    # 3. Blend wear signal: 65% Edge Gradient, 35% Noise
    wear_signal = (0.65 * edge_gradient) + (0.35 * noise_map)

    # 4. Float-dependent threshold curve across CS:GO condition tiers
    if f < 0.07:
        # Factory New: microscopic edge chipping only
        thresh = 0.90 - (f * 1.5)
        wear_amount = np.clip((wear_signal - thresh) / max(1.0 - thresh, 1e-4), 0.0, 1.0)
        # Suppress flat surface noise completely
        wear_amount = np.where(edge_gradient > 0.4, wear_amount * 0.8, 0.0)
    elif f < 0.15:
        # Minimal Wear: visible edge chipping along perimeter
        thresh = 0.80 - ((f - 0.07) * 1.8)
        wear_amount = np.clip((wear_signal - thresh) / max(1.0 - thresh, 1e-4), 0.0, 1.0)
        wear_amount = np.where(edge_gradient > 0.25, wear_amount, wear_amount * 0.15)
    elif f < 0.38:
        # Field-Tested: edges peel inward, light surface wear
        thresh = 0.65 - ((f - 0.15) * 1.0)
        wear_amount = np.clip((wear_signal - thresh) / max(1.0 - thresh, 1e-4), 0.0, 1.0)
    elif f < 0.45:
        # Well-Worn: significant paint stripping
        thresh = 0.42 - ((f - 0.38) * 1.2)
        wear_amount = np.clip((wear_signal - thresh) / max(1.0 - thresh, 1e-4), 0.0, 1.0)
    else:
        # Battle-Scarred: extensive bare alloy exposure
        thresh = 0.33 - ((f - 0.45) * 0.45)
        wear_amount = np.clip((wear_signal - thresh) / max(1.0 - thresh, 1e-4), 0.0, 1.0)

    # 5. Patina / Aged Paint (Desaturation & slight oxidation darkening)
    lum = (0.299 * rgb_arr[:, :, 0] + 0.587 * rgb_arr[:, :, 1] + 0.114 * rgb_arr[:, :, 2])[:, :, None]
    patina_factor = 1.0 - (f * 0.22)
    desat_factor = 1.0 - (f * 0.30)
    aged_rgb = (lum + (rgb_arr - lum) * desat_factor) * patina_factor

    # 6. Directional brushed metal alloy texture
    rng = np.random.default_rng(seed + 1)
    brushed_x = rng.uniform(-6.0, 6.0, (h, 1)).astype(np.float32)
    metal_grain = np.repeat(brushed_x, w, axis=1)[:, :, None]
    metal_noise = rng.uniform(-8.0, 8.0, (h, w, 1)).astype(np.float32)
    bare_metal = np.clip(BARE_METAL_COLOR + metal_grain * 0.6 + metal_noise * 0.4, 0.0, 255.0)

    # 7. Chipped paint perimeter shadow (3D peel edge effect)
    peel_rim = np.clip(wear_amount * (1.0 - wear_amount) * 3.5, 0.0, 1.0)
    rim_shadow = 1.0 - (peel_rim[:, :, None] * 0.30)

    # 8. Final composite
    wear_factor = wear_amount[:, :, None]
    painted_composite = aged_rgb * rim_shadow
    final_rgb = painted_composite * (1.0 - wear_factor) + bare_metal * wear_factor
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
    Simulates curvature-aware wear float and quantizes to 8-bit GoldSrc format
    using adaptive error diffusion and lossless candidate benchmarking.
    Returns:
        (goldsrc_payload_bytes, worn_rgba_image)
    """
    worn_img = apply_wear_simulation(source_image, wear_float=wear_float, seed=seed)
    pix_bytes, pal_bytes = quantize_goldsrc(worn_img, is_masked=is_masked, defringe=is_masked, dither="auto")
    payload = pix_bytes + pal_bytes
    return payload, worn_img
