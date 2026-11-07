"""
color_adjuster.py - Photographic Color Grading & Selective HSL Engine for Counter-Strike 1.6
weapon skins, gloves, and sleeves.

Supports:
- Sigmoid Soft S-Curve contrast with asymptotic knee roll-off (no 1-bit posterization or clipping)
- Luminance-preserving Kelvin/Planckian color temperature and tint shifts
- Smooth Gaussian/Cosine roll-off shadows boost and highlights recovery
- Smart vibrance with skin/wood tone protection and standard saturation
- Halo-free clarity (mid-tone unsharp mask) and fine detail sharpening
- 8-Channel Selective HSL Color Mixer (Red, Orange, Yellow, Green, Cyan, Blue, Purple, Magenta)
  with Gaussian membership weighting: w_i = exp(-Delta h^2 / (2 * sigma^2))
- Preset configurations (Vibrant CS2 Style, Dark Ops / Stealth, Warm Golden, Cyber Neon, Neutral)
- Lossless GoldSrc 256-color palette quantization preserving mask index 255.
"""

from typing import Dict, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageFilter

from .image_pipeline import load_image, quantize_goldsrc

PRESETS: Dict[str, Dict[str, float]] = {
    "neutral": {
        "brightness": 0,
        "contrast": 0,
        "saturation": 0,
        "vibrance": 0,
        "clarity": 0,
        "shadows": 0,
        "highlights": 0,
        "temperature": 0,
        "tint": 0,
        "hue": 0,
        "sharpen": 0,
    },
    "vibrant_cs2": {
        "brightness": 5,
        "contrast": 15,
        "saturation": 18,
        "vibrance": 45,
        "clarity": 30,
        "shadows": 15,
        "highlights": -10,
        "temperature": 5,
        "tint": 0,
        "hue": 0,
        "sharpen": 15,
    },
    "dark_ops": {
        "brightness": -12,
        "contrast": 25,
        "saturation": -40,
        "vibrance": -25,
        "clarity": 20,
        "shadows": -20,
        "highlights": -15,
        "temperature": -10,
        "tint": -5,
        "hue": 0,
        "sharpen": 20,
    },
    "warm_golden": {
        "brightness": 8,
        "contrast": 10,
        "saturation": 12,
        "vibrance": 25,
        "clarity": 15,
        "shadows": 10,
        "highlights": 20,
        "temperature": 35,
        "tint": -5,
        "hue": 0,
        "sharpen": 10,
    },
    "cyber_neon": {
        "brightness": 5,
        "contrast": 20,
        "saturation": 35,
        "vibrance": 60,
        "clarity": 35,
        "shadows": 5,
        "highlights": 10,
        "temperature": -30,
        "tint": 25,
        "hue": 0,
        "sharpen": 25,
    },

    "ruby": {
        "brightness": 5,
        "contrast": 40,
        "saturation": 90,
        "vibrance": 95,
        "clarity": 35,
        "shadows": -10,
        "highlights": 25,
        "temperature": 15,
        "tint": 45,
        "hue": 0,
        "sharpen": 25,
    },
    "sapphire": {
        "brightness": 0,
        "contrast": 40,
        "saturation": 90,
        "vibrance": 95,
        "clarity": 35,
        "shadows": -20,
        "highlights": 25,
        "temperature": -45,
        "tint": 10,
        "hue": 240,
        "sharpen": 25,
    },
    "emerald": {
        "brightness": 2,
        "contrast": 35,
        "saturation": 90,
        "vibrance": 95,
        "clarity": 35,
        "shadows": -15,
        "highlights": 25,
        "temperature": -20,
        "tint": -50,
        "hue": 125,
        "sharpen": 25,
    },
    "gamma_emerald": {
        "brightness": 8,
        "contrast": 40,
        "saturation": 95,
        "vibrance": 100,
        "clarity": 40,
        "shadows": 0,
        "highlights": 30,
        "temperature": -15,
        "tint": -60,
        "hue": 130,
        "sharpen": 30,
    },
    "gamma_doppler_phase_1": {
        "brightness": -5,
        "contrast": 30,
        "saturation": 70,
        "vibrance": 80,
        "clarity": 30,
        "shadows": -20,
        "highlights": 20,
        "temperature": -25,
        "tint": -40,
        "hue": 145,
        "sharpen": 20,
    },
    "gamma_doppler_phase_2": {
        "brightness": 10,
        "contrast": 35,
        "saturation": 95,
        "vibrance": 100,
        "clarity": 40,
        "shadows": 10,
        "highlights": 30,
        "temperature": -10,
        "tint": -55,
        "hue": 115,
        "sharpen": 25,
    },
    "gamma_doppler_phase_3": {
        "brightness": 0,
        "contrast": 30,
        "saturation": 75,
        "vibrance": 85,
        "clarity": 35,
        "shadows": -15,
        "highlights": 25,
        "temperature": -35,
        "tint": -30,
        "hue": 170,
        "sharpen": 20,
    },
    "gamma_doppler_phase_4": {
        "brightness": 5,
        "contrast": 30,
        "saturation": 85,
        "vibrance": 90,
        "clarity": 35,
        "shadows": -10,
        "highlights": 25,
        "temperature": -25,
        "tint": -45,
        "hue": 155,
        "sharpen": 20,
    },
    "blue_gem": {
        "brightness": 10,
        "contrast": 40,
        "saturation": 95,
        "vibrance": 100,
        "clarity": 45,
        "shadows": -10,
        "highlights": 35,
        "temperature": -40,
        "tint": 15,
        "hue": 200,
        "sharpen": 30,
    },
    "gold_arabesque": {
        "brightness": 12,
        "contrast": 30,
        "saturation": 75,
        "vibrance": 85,
        "clarity": 30,
        "shadows": 15,
        "highlights": 35,
        "temperature": 50,
        "tint": -10,
        "hue": 40,
        "sharpen": 25,
    },
    "tiger_tooth": {
        "brightness": 15,
        "contrast": 35,
        "saturation": 85,
        "vibrance": 95,
        "clarity": 40,
        "shadows": 10,
        "highlights": 30,
        "temperature": 40,
        "tint": -15,
        "hue": 42,
        "sharpen": 30,
    },
    "slaughter": {
        "brightness": 2,
        "contrast": 45,
        "saturation": 85,
        "vibrance": 90,
        "clarity": 45,
        "shadows": -15,
        "highlights": 25,
        "temperature": 25,
        "tint": 35,
        "hue": 355,
        "sharpen": 35,
    },
    "hot_rod": {
        "brightness": 10,
        "contrast": 50,
        "saturation": 100,
        "vibrance": 100,
        "clarity": 40,
        "shadows": 5,
        "highlights": 35,
        "temperature": 30,
        "tint": 40,
        "hue": 0,
        "sharpen": 25,
    },
    "cyan_phosphor": {
        "brightness": 8,
        "contrast": 35,
        "saturation": 95,
        "vibrance": 100,
        "clarity": 40,
        "shadows": 0,
        "highlights": 30,
        "temperature": -50,
        "tint": -20,
        "hue": 185,
        "sharpen": 25,
    },
    "neon_rider": {
        "brightness": 12,
        "contrast": 40,
        "saturation": 90,
        "vibrance": 100,
        "clarity": 40,
        "shadows": 5,
        "highlights": 30,
        "temperature": -10,
        "tint": 50,
        "hue": 310,
        "sharpen": 30,
    },
    "ultraviolet": {
        "brightness": -8,
        "contrast": 35,
        "saturation": 60,
        "vibrance": 70,
        "clarity": 30,
        "shadows": -25,
        "highlights": 15,
        "temperature": 10,
        "tint": 60,
        "hue": 275,
        "sharpen": 20,
    },
    "printstream": {
        "brightness": 18,
        "contrast": 30,
        "saturation": -40,
        "vibrance": 30,
        "clarity": 50,
        "shadows": 20,
        "highlights": 40,
        "temperature": -10,
        "tint": 5,
        "hue": 0,
        "sharpen": 45,
    },
    "hyper_beast": {
        "brightness": 8,
        "contrast": 45,
        "saturation": 95,
        "vibrance": 100,
        "clarity": 50,
        "shadows": -10,
        "highlights": 30,
        "temperature": -15,
        "tint": 25,
        "hue": 290,
        "sharpen": 40,
    },
    "rust_coat": {
        "brightness": -15,
        "contrast": 40,
        "saturation": 20,
        "vibrance": 30,
        "clarity": 45,
        "shadows": -30,
        "highlights": 10,
        "temperature": 35,
        "tint": 5,
        "hue": 25,
        "sharpen": 35,
    },
}


# 8 Selective HSL Color Channels with center hue angles in degrees [0, 360)
HSL_CHANNELS: Dict[str, float] = {
    "red": 0.0,
    "orange": 30.0,
    "yellow": 60.0,
    "green": 120.0,
    "cyan": 180.0,
    "blue": 240.0,
    "purple": 280.0,
    "magenta": 320.0,
}


def rgb_to_hsl_numpy(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Converts float RGB array [H, W, 3] in [0, 1] to Hue [0, 360), Saturation [0, 1], Lightness [0, 1].
    Vectorized NumPy implementation for maximum throughput.
    """
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    c = max_c - min_c
    l = 0.5 * (max_c + min_c)

    # Saturation
    s = np.zeros_like(l)
    denom = 1.0 - np.abs(2.0 * l - 1.0)
    valid_s = (c > 1e-6) & (denom > 1e-6)
    s[valid_s] = c[valid_s] / denom[valid_s]
    s = np.clip(s, 0.0, 1.0)

    # Hue
    h = np.zeros_like(l)
    mask_c = c > 1e-6
    mask_r = mask_c & (max_c == r)
    mask_g = mask_c & (~mask_r) & (max_c == g)
    mask_b = mask_c & (~mask_r) & (~mask_g)

    h[mask_r] = 60.0 * (((g[mask_r] - b[mask_r]) / c[mask_r]) % 6.0)
    h[mask_g] = 60.0 * (((b[mask_g] - r[mask_g]) / c[mask_g]) + 2.0)
    h[mask_b] = 60.0 * (((r[mask_b] - g[mask_b]) / c[mask_b]) + 4.0)
    h = h % 360.0

    return h, s, l


def hsl_to_rgb_numpy(h: np.ndarray, s: np.ndarray, l: np.ndarray) -> np.ndarray:
    """
    Converts Hue [0, 360), Saturation [0, 1], Lightness [0, 1] to float RGB array [H, W, 3] in [0, 1].
    Vectorized piecewise conversion.
    """
    h_norm = (h % 360.0) / 60.0
    c = (1.0 - np.abs(2.0 * l - 1.0)) * s
    x = c * (1.0 - np.abs((h_norm % 2.0) - 1.0))
    m = l - 0.5 * c

    rgb = np.zeros((*h.shape, 3), dtype=np.float32)
    h_idx = np.floor(h_norm).astype(np.int32) % 6

    # 0: C, X, 0
    mask = h_idx == 0
    rgb[mask, 0] = c[mask]
    rgb[mask, 1] = x[mask]
    rgb[mask, 2] = 0.0

    # 1: X, C, 0
    mask = h_idx == 1
    rgb[mask, 0] = x[mask]
    rgb[mask, 1] = c[mask]
    rgb[mask, 2] = 0.0

    # 2: 0, C, X
    mask = h_idx == 2
    rgb[mask, 0] = 0.0
    rgb[mask, 1] = c[mask]
    rgb[mask, 2] = x[mask]

    # 3: 0, X, C
    mask = h_idx == 3
    rgb[mask, 0] = 0.0
    rgb[mask, 1] = x[mask]
    rgb[mask, 2] = c[mask]

    # 4: X, 0, C
    mask = h_idx == 4
    rgb[mask, 0] = x[mask]
    rgb[mask, 1] = 0.0
    rgb[mask, 2] = c[mask]

    # 5: C, 0, X
    mask = h_idx == 5
    rgb[mask, 0] = c[mask]
    rgb[mask, 1] = 0.0
    rgb[mask, 2] = x[mask]

    rgb += m[:, :, None]
    return np.clip(rgb, 0.0, 1.0)


def apply_selective_hsl(
    rgb: np.ndarray,
    global_hue: float = 0.0,
    hsl_adjustments: Optional[Dict[str, Dict[str, float]]] = None,
    sigma: float = 20.0,
) -> np.ndarray:
    """
    Applies global hue shift and 8-channel selective HSL adjustments using
    Gaussian membership weighting: w_i = exp(-Delta h_i^2 / (2 * sigma^2)).
    Protects achromatic/grayscale regions (gun metal, wood, gloves).
    """
    has_global = (global_hue % 360.0) != 0.0
    has_hsl = False
    if hsl_adjustments:
        for ch, vals in hsl_adjustments.items():
            if any(vals.get(k, 0.0) != 0.0 for k in ("hue", "saturation", "lightness")):
                has_hsl = True
                break

    if not has_global and not has_hsl:
        return rgb

    h, s, l = rgb_to_hsl_numpy(rgb)

    # 1. Global Hue Rotation
    if has_global:
        h = (h + global_hue) % 360.0

    # 2. 8-Channel Selective HSL Mixer
    if has_hsl and hsl_adjustments:
        # Saturation gating: protects grayscale/achromatic pixels (blacks, metal, whites)
        sat_gate = np.clip(s / 0.10, 0.0, 1.0)

        delta_h_acc = np.zeros_like(h)
        delta_s_acc = np.zeros_like(s)
        delta_l_acc = np.zeros_like(l)
        total_w_h = np.zeros_like(h)
        total_w_s = np.zeros_like(s)
        total_w_l = np.zeros_like(l)

        for ch_name, center_h in HSL_CHANNELS.items():
            adj = hsl_adjustments.get(ch_name)
            if not adj:
                continue
            ch_hue = float(adj.get("hue", 0.0))
            ch_sat = float(adj.get("saturation", 0.0)) / 100.0
            ch_light = float(adj.get("lightness", 0.0)) / 100.0

            if ch_hue == 0.0 and ch_sat == 0.0 and ch_light == 0.0:
                continue

            # Circular angular distance in degrees [0, 180]
            d_h = np.abs(h - center_h) % 360.0
            d_h = np.minimum(d_h, 360.0 - d_h)

            # Gaussian membership weight
            w = np.exp(-(d_h ** 2) / (2.0 * (sigma ** 2))) * sat_gate

            if ch_hue != 0.0:
                delta_h_acc += w * ch_hue
                total_w_h += w
            if ch_sat != 0.0:
                delta_s_acc += w * ch_sat
                total_w_s += w
            if ch_light != 0.0:
                delta_l_acc += w * ch_light
                total_w_l += w

        # Normalize weights per component if multiple channels overlap
        delta_h_acc /= np.maximum(1.0, total_w_h)
        delta_s_acc /= np.maximum(1.0, total_w_s)
        delta_l_acc /= np.maximum(1.0, total_w_l)

        # Apply Hue shift
        h = (h + delta_h_acc) % 360.0

        # Apply Saturation
        mask_s_pos = delta_s_acc > 0
        s[mask_s_pos] += delta_s_acc[mask_s_pos] * (1.0 - s[mask_s_pos])
        mask_s_neg = delta_s_acc < 0
        s[mask_s_neg] += delta_s_acc[mask_s_neg] * s[mask_s_neg]
        s = np.clip(s, 0.0, 1.0)

        # Apply Lightness
        mask_l_pos = delta_l_acc > 0
        l[mask_l_pos] += delta_l_acc[mask_l_pos] * (1.0 - l[mask_l_pos])
        mask_l_neg = delta_l_acc < 0
        l[mask_l_neg] += delta_l_acc[mask_l_neg] * l[mask_l_neg]
        l = np.clip(s if False else l, 0.0, 1.0)

    return hsl_to_rgb_numpy(h, s, l)


def adjust_color_grading(
    source_image: Union[str, bytes, Image.Image],
    brightness: float = 0.0,
    contrast: float = 0.0,
    saturation: float = 0.0,
    vibrance: float = 0.0,
    clarity: float = 0.0,
    shadows: float = 0.0,
    highlights: float = 0.0,
    temperature: float = 0.0,
    tint: float = 0.0,
    hue: float = 0.0,
    sharpen: float = 0.0,
    hsl_adjustments: Optional[Dict[str, Dict[str, float]]] = None,
    **kwargs,
) -> Image.Image:
    """
    Applies professional photographic color grading adjustments to an image.
    Values are clamped to range [-100, 100] (hue [-180, 180]).

    Features:
    - Sigmoid Soft S-Curve contrast with smooth knee roll-off.
    - Luminance-preserving Kelvin/Planckian white balance shifts.
    - Gaussian roll-off shadows boost and highlights recovery.
    - Smart vibrance with tone protection.
    - Halo-free clarity and fine sharpening.
    - 8-Channel Selective HSL color mixer.

    Returns:
        Adjusted PIL Image in RGBA mode.
    """
    img = load_image(source_image)
    orig_rgba = np.array(img, dtype=np.float32)

    rgb = orig_rgba[:, :, :3] / 255.0
    alpha = orig_rgba[:, :, 3] if orig_rgba.shape[2] == 4 else None

    # Clamp parameters to [-100, 100]
    b = float(np.clip(brightness, -100, 100)) / 100.0
    c = float(np.clip(contrast, -100, 100)) / 100.0
    s = float(np.clip(saturation, -100, 100)) / 100.0
    v = float(np.clip(vibrance, -100, 100)) / 100.0
    cl = float(np.clip(clarity, -100, 100)) / 100.0
    sh = float(np.clip(shadows, -100, 100)) / 100.0
    hi = float(np.clip(highlights, -100, 100)) / 100.0
    temp = float(np.clip(temperature, -100, 100)) / 100.0
    ti = float(np.clip(tint, -100, 100)) / 100.0
    global_hue = float(np.clip(hue, -180, 180))
    sh_sharp = float(np.clip(sharpen, -100, 100)) / 100.0

    # Parse any flattened HSL kwargs like hsl_yellow_hue
    if hsl_adjustments is None:
        hsl_adjustments = {}
    for ch_name in HSL_CHANNELS:
        prefix = f"hsl_{ch_name}_"
        ch_h = kwargs.get(f"{prefix}hue")
        ch_s = kwargs.get(f"{prefix}saturation")
        ch_l = kwargs.get(f"{prefix}lightness")
        if ch_h is not None or ch_s is not None or ch_l is not None:
            if ch_name not in hsl_adjustments:
                hsl_adjustments[ch_name] = {}
            if ch_h is not None:
                hsl_adjustments[ch_name]["hue"] = float(ch_h)
            if ch_s is not None:
                hsl_adjustments[ch_name]["saturation"] = float(ch_s)
            if ch_l is not None:
                hsl_adjustments[ch_name]["lightness"] = float(ch_l)

    # 1. Luminance-Preserving Color Temperature & Tint (Kelvin / Planckian)
    if temp != 0.0 or ti != 0.0:
        lum_orig = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

        # Kelvin temperature shift: Warm boosts R, pulls B; Cool boosts B, pulls R
        k_temp = temp * 0.35
        rgb[:, :, 0] *= (1.0 + k_temp)
        rgb[:, :, 2] *= (1.0 - k_temp)

        # Tint shift: Magenta boosts R & B, pulls G; Green boosts G, pulls R & B
        k_tint = ti * 0.30
        rgb[:, :, 1] *= (1.0 - k_tint)
        rgb[:, :, 0] *= (1.0 + 0.5 * k_tint)
        rgb[:, :, 2] *= (1.0 + 0.5 * k_tint)

        # Enforce strict luminance conservation to eliminate neon clipping
        lum_new = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
        mask = lum_new > 1e-5
        lum_ratio = np.ones_like(lum_orig)
        lum_ratio[mask] = lum_orig[mask] / lum_new[mask]
        rgb *= lum_ratio[:, :, None]
        rgb = np.clip(rgb, 0.0, 1.0)

    # 2. Exposure / Brightness with Soft Knee Headroom Compression
    if b != 0.0:
        if b > 0.0:
            rgb += b * 0.35 * (1.0 - rgb * 0.5)
        else:
            rgb += b * 0.35 * (0.5 + rgb * 0.5)
        rgb = np.clip(rgb, 0.0, 1.0)

    # 3. Smooth Shadows Boost & Highlights Recovery (Gaussian Roll-off)
    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

    if sh != 0.0:
        w_shadow = np.exp(-(lum ** 2) / (2.0 * (0.35 ** 2)))[:, :, None]
        if sh > 0.0:
            rgb += sh * 0.35 * w_shadow * (1.0 - rgb)
        else:
            rgb += sh * 0.35 * w_shadow * rgb

    if hi != 0.0:
        w_highlight = np.exp(-((1.0 - lum) ** 2) / (2.0 * (0.35 ** 2)))[:, :, None]
        if hi < 0.0:
            rgb += hi * 0.35 * w_highlight * rgb
        else:
            rgb += hi * 0.35 * w_highlight * (1.0 - rgb)

    rgb = np.clip(rgb, 0.0, 1.0)

    # 4. Contrast: Sigmoid Soft S-Curve with Asymptotic Knee Roll-off
    if c != 0.0:
        if c > 0.0:
            k = 8.0 * c
            s_0 = 1.0 / (1.0 + np.exp(0.5 * k))
            s_1 = 1.0 / (1.0 + np.exp(-0.5 * k))
            s_diff = s_1 - s_0
            s_x = 1.0 / (1.0 + np.exp(-k * (rgb - 0.5)))
            rgb = (s_x - s_0) / s_diff
        else:
            # Contrast compression towards 0.5 midpoint
            rgb = 0.5 + (rgb - 0.5) * (1.0 + c)
        rgb = np.clip(rgb, 0.0, 1.0)

    # 5. Smart Vibrance & Standard Saturation
    if s != 0.0 or v != 0.0:
        max_c = np.max(rgb, axis=-1)
        min_c = np.min(rgb, axis=-1)
        cur_sat = np.zeros_like(max_c)
        mask = max_c > 1e-5
        cur_sat[mask] = (max_c[mask] - min_c[mask]) / max_c[mask]

        cur_lum = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2])[:, :, None]

        sat_factor = 1.0 + s
        if v != 0.0:
            # Smart vibrance: boosts desaturated pixels more, protects already vivid and skin tones
            vib_boost = v * (1.0 - cur_sat[:, :, None]) * 1.5
            sat_factor = sat_factor + vib_boost

        rgb = cur_lum + (rgb - cur_lum) * sat_factor
        rgb = np.clip(rgb, 0.0, 1.0)

    # 6. Global Hue Rotation & 8-Channel Selective HSL Color Mixer
    rgb = apply_selective_hsl(rgb, global_hue=global_hue, hsl_adjustments=hsl_adjustments)

    # 7. Halo-Free Clarity (Mid-tone Contrast) & Sharpening (Unsharp Mask)
    if cl != 0.0 or sh_sharp != 0.0:
        cur_img = Image.fromarray((rgb * 255.0).astype(np.uint8), mode="RGB")

        # Clarity: radius 3.0 Gaussian with soft tanh edge compression to eliminate halos
        if cl != 0.0:
            blurred_cl = cur_img.filter(ImageFilter.GaussianBlur(radius=3.0))
            detail = rgb - (np.array(blurred_cl, dtype=np.float32) / 255.0)
            detail_soft = np.tanh(detail * 2.5) / 2.5
            cur_lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
            midtone_weight = np.clip(4.0 * cur_lum * (1.0 - cur_lum), 0.0, 1.0)[:, :, None]
            rgb += detail_soft * (cl * 0.7) * midtone_weight

        # Sharpening: radius 1.0 Gaussian high-frequency detail boost
        if sh_sharp != 0.0:
            blurred_sh = cur_img.filter(ImageFilter.GaussianBlur(radius=1.0))
            fine_detail = rgb - (np.array(blurred_sh, dtype=np.float32) / 255.0)
            fine_soft = np.tanh(fine_detail * 3.5) / 3.5
            rgb += fine_soft * (sh_sharp * 0.8)

        rgb = np.clip(rgb, 0.0, 1.0)

    # Final reconstruction
    final_rgb = np.clip(np.round(rgb * 255.0), 0, 255).astype(np.uint8)
    if alpha is not None:
        final_rgba = np.dstack([final_rgb, np.clip(np.round(alpha), 0, 255).astype(np.uint8)])
        out_img = Image.fromarray(final_rgba, mode="RGBA")
    else:
        out_img = Image.fromarray(final_rgb, mode="RGB").convert("RGBA")

    # Wear & scratch patina simulation
    wear_val = float(kwargs.get("wear", 0.0))
    if wear_val > 0.0:
        from .wear_simulator import apply_wear_simulation
        out_img = apply_wear_simulation(out_img, min(1.0, max(0.0, wear_val / 100.0)))

    return out_img


def adjust_and_quantize(
    source_image: Union[str, bytes, Image.Image],
    is_masked: bool = False,
    dither: str = "floyd_steinberg",
    **color_params,
) -> Tuple[bytes, Image.Image]:
    """
    Applies photographic color grading adjustments and quantizes to 8-bit GoldSrc format.
    Returns:
        (goldsrc_payload_bytes, adjusted_rgba_image)
    """
    adjusted_img = adjust_color_grading(source_image, **color_params)
    pix_bytes, pal_bytes = quantize_goldsrc(
        adjusted_img,
        is_masked=is_masked,
        defringe=is_masked,
        dither=dither,
    )
    payload = pix_bytes + pal_bytes
    return payload, adjusted_img
