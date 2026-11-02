"""
stattrak_customizer.py - StatTrak LED Digital Counter Customizer.
Allows customizing LED digit color (Orange, Neon Cyan, Ruby Red, Emerald Green, Violet)
and digit display values for Counter-Strike 1.6 StatTrak modules.
"""

from typing import Dict, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageDraw

from .image_pipeline import load_image, quantize_goldsrc

LED_COLORS: Dict[str, Tuple[int, int, int]] = {
    "orange": (255, 120, 10),     # Classic CS:GO Amber
    "cyan": (0, 235, 255),        # Neon Cyan
    "red": (255, 35, 45),         # Ruby Red
    "green": (25, 255, 110),      # Emerald Green
    "violet": (195, 60, 255),     # Cyber Violet
}

# 7-Segment digit patterns: a, b, c, d, e, f, g
#   -- a --
#  |       |
#  f       b
#  |       |
#   -- g --
#  |       |
#  e       c
#  |       |
#   -- d --
SEGMENTS = {
    "0": (1, 1, 1, 1, 1, 1, 0),
    "1": (0, 1, 1, 0, 0, 0, 0),
    "2": (1, 1, 0, 1, 1, 0, 1),
    "3": (1, 1, 1, 1, 0, 0, 1),
    "4": (0, 1, 1, 0, 0, 1, 1),
    "5": (1, 0, 1, 1, 0, 1, 1),
    "6": (1, 0, 1, 1, 1, 1, 1),
    "7": (1, 1, 1, 0, 0, 0, 0),
    "8": (1, 1, 1, 1, 1, 1, 1),
    "9": (1, 1, 1, 1, 0, 1, 1),
    " ": (0, 0, 0, 0, 0, 0, 0),
}


def recolor_digit_texture(
    source_image: Union[str, bytes, Image.Image],
    color_name: str = "orange",
) -> Image.Image:
    """
    Recolors an existing StatTrak digit texture (e.g. stat_digit.bmp) to a new LED glow color.
    Uses luminance-based color remapping with bright hot cores and soft glow falloff.
    """
    img = load_image(source_image).convert("RGBA")
    arr = np.array(img, dtype=np.float32)

    target_rgb = np.array(LED_COLORS.get(color_name.lower(), LED_COLORS["orange"]), dtype=np.float32)

    # Calculate luminance of original pixels
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

    # Remap active LED pixels (lum > 0.05)
    active_mask = lum > 0.05

    out_arr = arr.copy()

    # Low-lum background: dark tinted LED glass
    out_arr[~active_mask, 0] = np.clip(target_rgb[0] * 0.05, 0, 20)
    out_arr[~active_mask, 1] = np.clip(target_rgb[1] * 0.05, 0, 20)
    out_arr[~active_mask, 2] = np.clip(target_rgb[2] * 0.05, 0, 20)

    # High lum: blend towards pure white hot core
    high_lum = np.clip((lum - 0.5) / 0.5, 0.0, 1.0)
    core_rgb = target_rgb * (1.0 - high_lum[:, :, None]) + np.array([255.0, 255.0, 255.0]) * high_lum[:, :, None]

    # Mid/low glow
    glow_factor = np.clip(lum / 0.5, 0.0, 1.0)[:, :, None]
    final_rgb = core_rgb * glow_factor

    out_arr[active_mask, :3] = np.clip(final_rgb[active_mask], 0, 255)
    out_arr[:, :, 3] = 255.0

    return Image.fromarray(out_arr.astype(np.uint8), mode="RGBA")


def draw_single_7segment_cell(
    char: str = "0",
    color_name: str = "orange",
    width: int = 32,
    height: int = 47,
) -> Image.Image:
    """
    Renders a single crisp, perfectly centered GoldSrc 7-segment LED digit cell (default 32x47)
    with bevel corners, bright hot core, neon glow, and authentic dim unlit segments.
    """
    img = Image.new("RGBA", (width, height), (10, 12, 16, 255))
    draw = ImageDraw.Draw(img)
    target = LED_COLORS.get(color_name.lower(), LED_COLORS["orange"])
    dim = tuple(max(10, int(c * 0.12)) for c in target)

    segs = SEGMENTS.get(str(char), SEGMENTS[" "])

    # Normalized segment coordinates scaled to width & height
    scale_x = width / 32.0
    scale_y = height / 47.0

    def sx(x): return int(round(x * scale_x))
    def sy(y): return int(round(y * scale_y))

    # Segment polygons
    poly_a = [(sx(7), sy(5)), (sx(25), sy(5)), (sx(23), sy(8)), (sx(9), sy(8))]
    poly_b = [(sx(25), sy(9)), (sx(28), sy(9)), (sx(28), sy(21)), (sx(25), sy(21))]
    poly_c = [(sx(25), sy(24)), (sx(28), sy(24)), (sx(28), sy(38)), (sx(25), sy(38))]
    poly_d = [(sx(9), sy(39)), (sx(23), sy(39)), (sx(25), sy(42)), (sx(7), sy(42))]
    poly_e = [(sx(4), sy(24)), (sx(7), sy(24)), (sx(7), sy(38)), (sx(4), sy(38))]
    poly_f = [(sx(4), sy(9)), (sx(7), sy(9)), (sx(7), sy(21)), (sx(4), sy(21))]
    poly_g = [(sx(8), sy(22)), (sx(24), sy(22)), (sx(22), sy(24)), (sx(10), sy(24))]

    all_polys = [poly_a, poly_b, poly_c, poly_d, poly_e, poly_f, poly_g]

    # Draw faint unlit segments first
    for p in all_polys:
        draw.polygon(p, fill=dim)

    # Draw lit segments with neon glow and hot white core
    for idx, (p, is_lit) in enumerate(zip(all_polys, segs)):
        if is_lit:
            draw.polygon(p, fill=target)
            xs = [pt[0] for pt in p]
            ys = [pt[1] for pt in p]
            if idx in (0, 3, 6):  # Horizontal segment core
                mid_y = (min(ys) + max(ys)) // 2
                draw.line([(min(xs) + 1, mid_y), (max(xs) - 1, mid_y)], fill=(255, 255, 255, 230))
            else:  # Vertical segment core
                mid_x = (min(xs) + max(xs)) // 2
                draw.line([(mid_x, min(ys) + 1), (mid_x, max(ys) - 1)], fill=(255, 255, 255, 230))

    return img


def render_6digit_strip(
    number_str: str = "001337",
    color_name: str = "orange",
    cell_w: int = 32,
    cell_h: int = 47,
) -> Image.Image:
    """
    Renders a full 6-digit StatTrak LED display strip (e.g. 192x47)
    with all 6 digits side-by-side in glowing neon LED style.
    """
    clean_str = str(number_str).strip()
    if clean_str.isdigit():
        clean_str = clean_str.rjust(6, "0")[-6:]
    else:
        clean_str = clean_str.rjust(6, " ")[:6]

    strip_w = cell_w * 6
    strip = Image.new("RGBA", (strip_w, cell_h), (10, 12, 16, 255))

    for i, ch in enumerate(clean_str):
        cell_img = draw_single_7segment_cell(ch, color_name=color_name, width=cell_w, height=cell_h)
        strip.paste(cell_img, (i * cell_w, 0))

    return strip


def render_7segment_display(
    width: int = 32,
    height: int = 47,
    number_str: str = "0",
    color_name: str = "orange",
) -> Image.Image:
    """
    Renders custom 7-segment digital LED numbers.
    For standard single GoldSrc cell (width <= 48), renders a single crisp, centered digit.
    For wide strip, renders multi-digit display.
    """
    clean_str = str(number_str).strip()
    if width <= 48:
        # Single cell: pick representative digit (last digit or '0')
        char = clean_str[-1] if clean_str else "0"
        return draw_single_7segment_cell(char=char, color_name=color_name, width=width, height=height)

    # Multi-digit strip
    return render_6digit_strip(number_str=clean_str, color_name=color_name, cell_w=width // 6, cell_h=height)


def customize_stattrak_texture(
    source_image: Union[str, bytes, Image.Image],
    color_name: str = "orange",
    custom_number: Optional[Union[str, int]] = None,
) -> Tuple[bytes, Image.Image]:
    """
    Produces GoldSrc quantized payload for StatTrak digit texture.
    If custom_number is given, renders a crisp single LED digit cell; otherwise recolors existing digits.
    Returns:
        (goldsrc_payload_bytes, preview_image)
    """
    img = load_image(source_image)
    w, h = img.width, img.height

    if custom_number is not None and str(custom_number).strip():
        rendered = render_7segment_display(w, h, number_str=str(custom_number), color_name=color_name)
    else:
        rendered = recolor_digit_texture(img, color_name=color_name)

    pix_bytes, pal_bytes = quantize_goldsrc(rendered, is_masked=False)
    payload = pix_bytes + pal_bytes
    return payload, rendered
