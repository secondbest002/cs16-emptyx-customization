"""
asset_library.py - Built-in Sticker & Skin Asset Library Manager & Procedural Generator.
Integrated with EmptyX Customization config_manager.
Provides instant access to iconic tournament/pro stickers and custom skins without manual file browsing.
"""

import base64
import io
import json
import math
import os
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .config_manager import config

STICKER_DEFINITIONS = [
    {
        "filename": "titan_holo.png",
        "name": "Titan Holo",
        "category": "Katowice 2014 Holo",
        "badge_color": (0, 162, 232),
        "accent_color": (0, 220, 255),
    },
    {
        "filename": "ibuypower_holo.png",
        "name": "iBUYPOWER Holo",
        "category": "Katowice 2014 Holo",
        "badge_color": (220, 20, 40),
        "accent_color": (255, 100, 20),
    },
    {
        "filename": "navi_holo.png",
        "name": "Natus Vincere Holo",
        "category": "Tournament Holo",
        "badge_color": (255, 215, 0),
        "accent_color": (255, 240, 50),
    },
    {
        "filename": "crown_foil.png",
        "name": "Crown (Foil)",
        "category": "Foil Collection",
        "badge_color": (245, 190, 30),
        "accent_color": (255, 230, 120),
    },
    {
        "filename": "howling_dawn.png",
        "name": "Howling Dawn",
        "category": "Contraband Decal",
        "badge_color": (210, 40, 30),
        "accent_color": (255, 120, 40),
    },
    {
        "filename": "cloud9_holo.png",
        "name": "Cloud9 Holo",
        "category": "Tournament Holo",
        "badge_color": (0, 174, 239),
        "accent_color": (120, 220, 255),
    },
    {
        "filename": "dignitas_holo.png",
        "name": "Team Dignitas Holo",
        "category": "Katowice 2014 Holo",
        "badge_color": (245, 210, 20),
        "accent_color": (180, 240, 40),
    },
    {
        "filename": "virtus_pro_holo.png",
        "name": "Virtus.Pro Holo",
        "category": "Katowice 2014 Holo",
        "badge_color": (255, 102, 0),
        "accent_color": (255, 160, 50),
    },
]


def _create_holo_gradient(size: int = 512) -> Image.Image:
    """Creates a subtle prismatic rainbow holographic glow."""
    cx, cy = size // 2, size // 2
    y, x = np.ogrid[:size, :size]
    dx = x - cx
    dy = y - cy
    dist = np.sqrt(dx * dx + dy * dy)
    angle = (np.arctan2(dy, dx) + np.pi) / (2 * np.pi)

    r = ((np.sin(angle * 6.28) * 0.5 + 0.5) * 200 + 55).astype(np.uint8)
    g = ((np.sin(angle * 6.28 + 2.09) * 0.5 + 0.5) * 200 + 55).astype(np.uint8)
    b = ((np.sin(angle * 6.28 + 4.18) * 0.5 + 0.5) * 200 + 55).astype(np.uint8)

    max_r = size * 0.48
    alpha = np.clip((1.0 - (dist / max_r)) * 60, 0, 60).astype(np.uint8)
    alpha[dist >= max_r] = 0

    arr = np.dstack([r, g, b, alpha])
    return Image.fromarray(arr, mode="RGBA")


def generate_titan_holo(size: int = 512) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    holo = _create_holo_gradient(size)
    img.alpha_composite(holo)
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2 - 20
    r = int(size * 0.42)

    # Hex shield
    pts = []
    for i in range(6):
        a = math.radians(60 * i + 30)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    draw.polygon(pts, fill=(10, 24, 48, 240), outline=(0, 220, 255, 255), width=8)

    # Giant stylized "T"
    t_width = int(size * 0.5)
    t_height = int(size * 0.45)
    bar_thick = int(size * 0.12)
    top_y = cy - t_height // 2 + 10
    draw.rounded_rectangle(
        [cx - t_width // 2, top_y, cx + t_width // 2, top_y + bar_thick],
        radius=6,
        fill=(0, 162, 232, 255),
        outline=(255, 255, 255, 255),
        width=3,
    )
    draw.rounded_rectangle(
        [cx - bar_thick // 2, top_y, cx + bar_thick // 2, top_y + t_height],
        radius=6,
        fill=(0, 162, 232, 255),
        outline=(255, 255, 255, 255),
        width=3,
    )

    # Banner
    lbl_w = int(size * 0.6)
    lbl_h = int(size * 0.12)
    lx = cx - lbl_w // 2
    ly = size - lbl_h - 35
    draw.rounded_rectangle([lx, ly, lx + lbl_w, ly + lbl_h], radius=8, fill=(5, 12, 28, 245), outline=(0, 220, 255, 255), width=3)
    draw.text((cx, ly + lbl_h // 2), "TITAN", fill=(255, 255, 255, 255), anchor="mm")

    return img


def generate_ibuypower_holo(size: int = 512) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    holo = _create_holo_gradient(size)
    img.alpha_composite(holo)
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2 - 20
    r = int(size * 0.42)

    # Angular shield
    pts = [
        (cx - r, cy - int(r * 0.6)),
        (cx + r, cy - int(r * 0.6)),
        (cx + int(r * 0.8), cy + int(r * 0.3)),
        (cx, cy + r),
        (cx - int(r * 0.8), cy + int(r * 0.3)),
    ]
    draw.polygon(pts, fill=(35, 10, 14, 245), outline=(255, 100, 20, 255), width=8)

    # Aggressive Tiger Head
    tiger_pts = [
        (cx, cy + 90),
        (cx - 70, cy + 40),
        (cx - 100, cy - 30),
        (cx - 80, cy - 80),
        (cx - 30, cy - 60),
        (cx, cy - 90),
        (cx + 30, cy - 60),
        (cx + 80, cy - 80),
        (cx + 100, cy - 30),
        (cx + 70, cy + 40),
    ]
    draw.polygon(tiger_pts, fill=(220, 20, 40, 255), outline=(255, 255, 255, 255), width=4)

    # Eyes & details
    draw.polygon([(cx - 45, cy - 25), (cx - 15, cy - 20), (cx - 35, cy - 10)], fill=(255, 220, 0, 255))
    draw.polygon([(cx + 45, cy - 25), (cx + 15, cy - 20), (cx + 35, cy - 10)], fill=(255, 220, 0, 255))
    draw.polygon([(cx - 20, cy + 15), (cx + 20, cy + 15), (cx, cy + 45)], fill=(255, 255, 255, 255))

    # Banner
    lbl_w = int(size * 0.72)
    lbl_h = int(size * 0.12)
    lx = cx - lbl_w // 2
    ly = size - lbl_h - 35
    draw.rounded_rectangle([lx, ly, lx + lbl_w, ly + lbl_h], radius=8, fill=(20, 5, 8, 245), outline=(220, 20, 40, 255), width=3)
    draw.text((cx, ly + lbl_h // 2), "iBUYPOWER", fill=(255, 255, 255, 255), anchor="mm")

    return img


def generate_navi_holo(size: int = 512) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    holo = _create_holo_gradient(size)
    img.alpha_composite(holo)
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2 - 20
    r = int(size * 0.42)

    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(20, 20, 20, 240), outline=(255, 215, 0, 255), width=8)

    # "NAVI"
    font_size = int(size * 0.22)
    draw.text((cx, cy - 10), "Na`Vi", fill=(255, 215, 0, 255), anchor="mm")

    # Banner
    lbl_w = int(size * 0.65)
    lbl_h = int(size * 0.12)
    lx = cx - lbl_w // 2
    ly = size - lbl_h - 35
    draw.rounded_rectangle([lx, ly, lx + lbl_w, ly + lbl_h], radius=8, fill=(15, 15, 10, 245), outline=(255, 215, 0, 255), width=3)
    draw.text((cx, ly + lbl_h // 2), "NATUS VINCERE", fill=(255, 240, 50, 255), anchor="mm")

    return img


def generate_crown_foil(size: int = 512) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = int(size * 0.44)

    # Golden foil background ring
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(30, 22, 5, 240), outline=(245, 190, 30, 255), width=10)
    draw.ellipse([cx - r + 16, cy - r + 16, cx + r - 16, cy + r - 16], outline=(255, 230, 120, 255), width=3)

    # King's Crown geometry
    cw = int(size * 0.58)
    ch = int(size * 0.42)
    base_y = cy + ch // 2 - 10
    top_y = cy - ch // 2

    crown_pts = [
        (cx - cw // 2, base_y),
        (cx - cw // 2 - 15, top_y + 30),
        (cx - cw // 4, top_y + 70),
        (cx, top_y),
        (cx + cw // 4, top_y + 70),
        (cx + cw // 2 + 15, top_y + 30),
        (cx + cw // 2, base_y),
    ]
    draw.polygon(crown_pts, fill=(245, 190, 30, 255), outline=(255, 240, 150, 255), width=5)

    # Jewels on crown peaks
    jewel_r = 14
    for px, py in [(cx - cw // 2 - 15, top_y + 30), (cx, top_y), (cx + cw // 2 + 15, top_y + 30)]:
        draw.ellipse([px - jewel_r, py - jewel_r, px + jewel_r, py + jewel_r], fill=(220, 30, 30, 255), outline=(255, 255, 255, 255), width=2)

    # Skull inside crown
    skull_cy = cy + 25
    draw.ellipse([cx - 45, skull_cy - 45, cx + 45, skull_cy + 45], fill=(240, 235, 220, 255))
    draw.rounded_rectangle([cx - 28, skull_cy + 15, cx + 28, skull_cy + 60], radius=4, fill=(240, 235, 220, 255))
    # Eye sockets
    draw.ellipse([cx - 30, skull_cy - 10, cx - 10, skull_cy + 15], fill=(30, 20, 10, 255))
    draw.ellipse([cx + 10, skull_cy - 10, cx + 30, skull_cy + 15], fill=(30, 20, 10, 255))

    return img


def generate_howling_dawn(size: int = 512) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = int(size * 0.44)

    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(25, 10, 10, 245), outline=(210, 40, 30, 255), width=8)

    # Roaring Wolf Head
    wolf_pts = [
        (cx - 110, cy + 80),
        (cx - 100, cy - 20),
        (cx - 60, cy - 90),
        (cx - 20, cy - 50),
        (cx + 40, cy - 80),
        (cx + 110, cy - 10),
        (cx + 130, cy + 30),
        (cx + 80, cy + 60),
        (cx + 30, cy + 50),
        (cx - 10, cy + 90),
    ]
    draw.polygon(wolf_pts, fill=(210, 40, 30, 255), outline=(255, 120, 40, 255), width=6)

    # Wolf fiery eye
    draw.polygon([(cx + 25, cy - 15), (cx + 55, cy - 10), (cx + 35, cy)], fill=(255, 220, 0, 255))

    # Blood red fangs
    draw.polygon([(cx + 70, cy + 15), (cx + 85, cy + 40), (cx + 60, cy + 35)], fill=(255, 255, 255, 255))

    return img


def generate_cloud9_holo(size: int = 512) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    holo = _create_holo_gradient(size)
    img.alpha_composite(holo)
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2 - 20
    r = int(size * 0.42)

    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(8, 20, 38, 240), outline=(0, 174, 239, 255), width=8)

    # Cloud9 3-overlap circles
    c_r = int(size * 0.16)
    draw.ellipse([cx - c_r - 25, cy - 20, cx + c_r - 25, cy + 2 * c_r - 20], fill=(0, 174, 239, 255), outline=(255, 255, 255, 255), width=4)
    draw.ellipse([cx - c_r + 25, cy - 20, cx + c_r + 25, cy + 2 * c_r - 20], fill=(0, 174, 239, 255), outline=(255, 255, 255, 255), width=4)
    draw.ellipse([cx - c_r, cy - c_r - 20, cx + c_r, cy + c_r - 20], fill=(0, 174, 239, 255), outline=(255, 255, 255, 255), width=4)

    # Banner
    lbl_w = int(size * 0.6)
    lbl_h = int(size * 0.12)
    lx = cx - lbl_w // 2
    ly = size - lbl_h - 35
    draw.rounded_rectangle([lx, ly, lx + lbl_w, ly + lbl_h], radius=8, fill=(5, 15, 30, 245), outline=(0, 174, 239, 255), width=3)
    draw.text((cx, ly + lbl_h // 2), "CLOUD9", fill=(255, 255, 255, 255), anchor="mm")

    return img


def generate_dignitas_holo(size: int = 512) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    holo = _create_holo_gradient(size)
    img.alpha_composite(holo)
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2 - 20
    r = int(size * 0.42)

    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(22, 18, 5, 240), outline=(245, 210, 20, 255), width=8)

    # Alien face
    aw = int(size * 0.44)
    ah = int(size * 0.48)
    draw.ellipse([cx - aw // 2, cy - ah // 2, cx + aw // 2, cy + ah // 2], fill=(245, 210, 20, 255), outline=(255, 255, 255, 255), width=4)
    # Alien eyes
    draw.ellipse([cx - 65, cy - 25, cx - 15, cy + 25], fill=(20, 20, 20, 255))
    draw.ellipse([cx + 15, cy - 25, cx + 65, cy + 25], fill=(20, 20, 20, 255))

    # Banner
    lbl_w = int(size * 0.64)
    lbl_h = int(size * 0.12)
    lx = cx - lbl_w // 2
    ly = size - lbl_h - 35
    draw.rounded_rectangle([lx, ly, lx + lbl_w, ly + lbl_h], radius=8, fill=(25, 20, 5, 245), outline=(245, 210, 20, 255), width=3)
    draw.text((cx, ly + lbl_h // 2), "TEAM DIGNITAS", fill=(255, 240, 50, 255), anchor="mm")

    return img


def generate_virtus_pro_holo(size: int = 512) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    holo = _create_holo_gradient(size)
    img.alpha_composite(holo)
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2 - 20
    r = int(size * 0.42)

    # Hex shield
    pts = []
    for i in range(6):
        a = math.radians(60 * i)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    draw.polygon(pts, fill=(18, 18, 20, 240), outline=(255, 102, 0, 255), width=8)

    # Roaring Polar Bear Head
    bear_pts = [
        (cx - 100, cy + 80),
        (cx - 110, cy - 10),
        (cx - 60, cy - 90),
        (cx - 20, cy - 50),
        (cx + 30, cy - 80),
        (cx + 80, cy - 40),
        (cx + 120, cy + 20),
        (cx + 90, cy + 80),
        (cx + 50, cy + 40),
        (cx + 10, cy + 70),
    ]
    draw.polygon(bear_pts, fill=(245, 245, 250, 255), outline=(255, 102, 0, 255), width=5)

    draw.polygon([(cx + 60, cy + 10), (cx + 110, cy + 25), (cx + 80, cy + 65)], fill=(255, 102, 0, 255))
    draw.polygon([(cx + 70, cy + 15), (cx + 85, cy + 30), (cx + 95, cy + 18)], fill=(255, 255, 255, 255))
    draw.polygon([(cx + 10, cy - 25), (cx + 35, cy - 15), (cx + 15, cy - 10)], fill=(255, 102, 0, 255))

    # Banner
    lbl_w = int(size * 0.64)
    lbl_h = int(size * 0.12)
    lx = cx - lbl_w // 2
    ly = size - lbl_h - 35
    draw.rounded_rectangle([lx, ly, lx + lbl_w, ly + lbl_h], radius=8, fill=(25, 15, 5, 245), outline=(255, 102, 0, 255), width=3)
    draw.text((cx, ly + lbl_h // 2), "VIRTUS.PRO", fill=(255, 255, 255, 255), anchor="mm")

    return img


GENERATORS = {
    "titan_holo.png": generate_titan_holo,
    "ibuypower_holo.png": generate_ibuypower_holo,
    "navi_holo.png": generate_navi_holo,
    "crown_foil.png": generate_crown_foil,
    "howling_dawn.png": generate_howling_dawn,
    "cloud9_holo.png": generate_cloud9_holo,
    "dignitas_holo.png": generate_dignitas_holo,
    "virtus_pro_holo.png": generate_virtus_pro_holo,
}


def ensure_builtin_assets(
    workspace_root: Optional[Union[str, Path]] = None,
    force_restore: bool = False,
) -> None:
    root = Path(workspace_root).resolve() if workspace_root else config.get_studio_root()
    assets_dir = root / "assets"
    stickers_dir = assets_dir / "stickers"
    my_stickers_dir = assets_dir / "my_stickers"
    my_skins_dir = assets_dir / "my_skins"
    marker_file = assets_dir / ".initialized"

    stickers_dir.mkdir(parents=True, exist_ok=True)
    my_stickers_dir.mkdir(parents=True, exist_ok=True)
    my_skins_dir.mkdir(parents=True, exist_ok=True)

    if marker_file.is_file() and not force_restore:
        return

    for filename, gen_fn in GENERATORS.items():
        dest = stickers_dir / filename
        if force_restore or not dest.exists():
            img = gen_fn(512)
            img.save(dest, format="PNG")

    try:
        marker_file.write_text("cs16_studio_library_initialized=true\n", encoding="utf-8")
    except Exception:
        pass


def _load_user_stickers_meta(folder: Path) -> dict:
    meta_file = folder / ".meta.json"
    if meta_file.is_file():
        try:
            with open(meta_file, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:
            return {}
    return {}


def _save_user_stickers_meta(folder: Path, meta: dict) -> None:
    meta_file = folder / ".meta.json"
    try:
        with open(meta_file, "w", encoding="utf-8") as fp:
            json.dump(meta, fp, indent=2)
    except Exception:
        pass


def get_library_stickers(workspace_root: Optional[Union[str, Path]] = None) -> List[dict]:
    root = Path(workspace_root).resolve() if workspace_root else config.get_studio_root()
    ensure_builtin_assets(root)

    stickers = []
    seen_keys = set()

    scan_folders = [
        (root / "assets" / "stickers", "Tournament Holo"),
        (root / "assets" / "my_stickers", "Custom / User"),
    ]

    for folder, default_cat in scan_folders:
        if not folder.is_dir():
            continue
        user_meta = _load_user_stickers_meta(folder)
        for f in sorted(folder.glob("*.*")):
            if f.suffix.lower() in (".png", ".webp", ".bmp", ".jpg", ".jpeg"):
                stem = f.stem
                key = (folder.name, stem)
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                display_name = stem.replace("_", " ").title()
                cat = default_cat
                for meta in STICKER_DEFINITIONS:
                    if meta["filename"].lower() == f.name.lower():
                        display_name = meta["name"]
                        cat = meta["category"]
                        break

                is_custom = (folder.name == "my_stickers")
                if f.name in user_meta:
                    m = user_meta[f.name]
                    if isinstance(m, dict):
                        display_name = m.get("name", display_name)
                        cat = m.get("category", cat)

                try:
                    with Image.open(f) as img:
                        thumb = img.convert("RGBA").resize((128, 128), Image.Resampling.BILINEAR)
                        buf = io.BytesIO()
                        thumb.save(buf, format="PNG")
                        thumb_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                        thumb_uri = f"data:image/png;base64,{thumb_b64}"
                except Exception:
                    thumb_uri = ""

                try:
                    rel_path = f.relative_to(root).as_posix()
                except ValueError:
                    rel_path = str(f)

                stickers.append({
                    "name": display_name,
                    "filename": f.name,
                    "category": cat,
                    "path": rel_path,
                    "thumbnail": thumb_uri,
                    "preview": thumb_uri,
                    "is_custom": is_custom,
                })

    return stickers


def _load_user_skins_meta(folder: Path) -> dict:
    meta_file = folder / ".meta.json"
    if meta_file.is_file():
        try:
            with open(meta_file, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:
            return {}
    return {}


def _save_user_skins_meta(folder: Path, meta: dict) -> None:
    meta_file = folder / ".meta.json"
    try:
        with open(meta_file, "w", encoding="utf-8") as fp:
            json.dump(meta, fp, indent=2)
    except Exception:
        pass


def _parse_weapon_from_filename(stem: str) -> Tuple[Optional[str], Optional[str], Optional[str], str]:
    lower = stem.lower()
    
    KNIFE_MAP = {
        "knife_karambit": ("knife_karambit", "knives", "Karambit"),
        "karambit": ("knife_karambit", "knives", "Karambit"),
        "knife_butterfly": ("knife_butterfly", "knives", "Butterfly"),
        "butterfly": ("knife_butterfly", "knives", "Butterfly"),
        "knife_m9": ("knife_m9", "knives", "M9 Bayonet"),
        "m9_bayonet": ("knife_m9", "knives", "M9 Bayonet"),
        "m9": ("knife_m9", "knives", "M9 Bayonet"),
        "knife_bayonet": ("knife_bayonet", "knives", "Bayonet"),
        "bayonet": ("knife_bayonet", "knives", "Bayonet"),
        "knife_huntsman": ("knife_huntsman", "knives", "Huntsman"),
        "huntsman": ("knife_huntsman", "knives", "Huntsman"),
        "knife_bowie": ("knife_bowie", "knives", "Bowie"),
        "bowie": ("knife_bowie", "knives", "Bowie"),
        "knife_flip": ("knife_flip", "knives", "Flip"),
        "flip": ("knife_flip", "knives", "Flip"),
        "knife_gut": ("knife_gut", "knives", "Gut"),
        "gut": ("knife_gut", "knives", "Gut"),
        "knife_falchion": ("knife_falchion", "knives", "Falchion"),
        "falchion": ("knife_falchion", "knives", "Falchion"),
        "knife_daggers": ("knife_daggers", "knives", "Daggers"),
        "daggers": ("knife_daggers", "knives", "Daggers"),
        "knife_skeleton": ("knife_skeleton", "knives", "Skeleton"),
        "skeleton": ("knife_skeleton", "knives", "Skeleton"),
        "knife_nomad": ("knife_nomad", "knives", "Nomad"),
        "nomad": ("knife_nomad", "knives", "Nomad"),
        "knife_paracord": ("knife_paracord", "knives", "Paracord"),
        "paracord": ("knife_paracord", "knives", "Paracord"),
        "knife_survival": ("knife_survival", "knives", "Survival"),
        "survival": ("knife_survival", "knives", "Survival"),
        "knife_classic": ("knife_classic", "knives", "Classic"),
        "classic_knife": ("knife_classic", "knives", "Classic"),
        "knife": ("knife", "knives", "Default Knife"),
    }
    for prefix, info in KNIFE_MAP.items():
        if lower.startswith(prefix + "_") or lower == prefix:
            rem = stem[len(prefix):].strip("_-")
            skin_name = rem.replace("_", " ").title() if rem else "Default"
            return info[0], info[1], info[2], skin_name

    WEAPON_MAP = {
        "usp_s": ("usp", "pistols"),
        "usp": ("usp", "pistols"),
        "glock18": ("glock18", "pistols"),
        "glock": ("glock18", "pistols"),
        "deagle": ("deagle", "pistols"),
        "desert_eagle": ("deagle", "pistols"),
        "p228": ("p228", "pistols"),
        "dual_elites": ("elites", "pistols"),
        "elites": ("elites", "pistols"),
        "elite": ("elites", "pistols"),
        "fiveseven": ("fiveseven", "pistols"),
        "five_seven": ("fiveseven", "pistols"),
        "ak47": ("ak47", "rifles"),
        "ak_47": ("ak47", "rifles"),
        "m4a1_s": ("m4a1", "rifles"),
        "m4a1": ("m4a1", "rifles"),
        "m4a4": ("m4a4", "rifles"),
        "awp": ("awp", "rifles"),
        "scout": ("scout", "rifles"),
        "galil": ("galil", "rifles"),
        "famas": ("famas", "rifles"),
        "sg552": ("sg552", "rifles"),
        "aug": ("aug", "rifles"),
        "g3sg1": ("g3sg1", "rifles"),
        "sg550": ("sg550", "rifles"),
        "mp5": ("mp5", "smgs"),
        "mp5sd": ("mp5", "smgs"),
        "p90": ("p90", "smgs"),
        "ump45": ("ump45", "smgs"),
        "ump": ("ump45", "smgs"),
        "mac10": ("mac10", "smgs"),
        "tmp": ("tmp", "smgs"),
        "m3": ("m3", "heavy"),
        "xm1014": ("xm1014", "heavy"),
        "m249": ("m249", "heavy"),
        "sport_gloves": ("sport_gloves", "gloves"),
        "specialist_gloves": ("specialist_gloves", "gloves"),
        "moto_gloves": ("moto_gloves", "gloves"),
        "hand_wraps": ("hand_wraps", "gloves"),
        "driver_gloves": ("driver_gloves", "gloves"),
        "hydra_gloves": ("hydra_gloves", "gloves"),
        "gloves": ("gloves", "gloves"),
        "sleeve": ("sleeves", "gloves"),
    }
    for prefix, (w_key, cat) in WEAPON_MAP.items():
        if lower.startswith(prefix + "_") or lower == prefix:
            rem = stem[len(prefix):].strip("_-")
            skin_name = rem.replace("_", " ").title() if rem else "Custom"
            return w_key, cat, None, skin_name

    return None, None, None, stem.replace("_", " ").title()


def get_library_skins(workspace_root: Optional[Union[str, Path]] = None) -> List[dict]:
    root = Path(workspace_root).resolve() if workspace_root else config.get_studio_root()
    skins = []
    seen = set()

    scan_folders = [
        root / "assets" / "my_skins",
        root / "assets" / "skins",
    ]

    for folder in scan_folders:
        if not folder.is_dir():
            continue
        user_meta = _load_user_skins_meta(folder)
        for f in sorted(folder.glob("*.*")):
            if f.suffix.lower() in (".png", ".webp", ".bmp", ".jpg", ".jpeg"):
                if f.name in seen:
                    continue
                seen.add(f.name)

                m = user_meta.get(f.name, {})
                w_inferred, cat_inferred, knife_inferred, name_inferred = _parse_weapon_from_filename(f.stem)

                skin_name = m.get("skin_name") or m.get("name") or name_inferred
                weapon = m.get("weapon") or w_inferred or ""
                weapon_category = m.get("weapon_category") or cat_inferred or ""
                knife_type = m.get("knife_type") or knife_inferred
                category = m.get("category") or (weapon_category.title() if weapon_category else "Custom Weapon Skins")

                display_name = skin_name
                if weapon and not display_name.lower().startswith(weapon.lower()):
                    display_name = f"{weapon.upper()} {skin_name}"

                try:
                    with Image.open(f) as img:
                        w, h = img.size
                        thumb = img.convert("RGBA").resize((128, 128), Image.Resampling.BILINEAR)
                        buf = io.BytesIO()
                        thumb.save(buf, format="PNG")
                        thumb_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                        thumb_uri = f"data:image/png;base64,{thumb_b64}"
                except Exception:
                    w, h = 0, 0
                    thumb_uri = ""

                try:
                    rel_path = f.relative_to(root).as_posix()
                except ValueError:
                    rel_path = str(f)

                skins.append({
                    "name": display_name,
                    "skin_name": skin_name,
                    "filename": f.name,
                    "weapon": weapon,
                    "weapon_category": weapon_category,
                    "knife_type": knife_type,
                    "width": w,
                    "height": h,
                    "category": category,
                    "path": rel_path,
                    "thumbnail": thumb_uri,
                    "preview": thumb_uri,
                    "is_custom": (folder.name == "my_skins"),
                })

    return skins


def save_custom_sticker(
    name: str,
    image_bytes: bytes,
    category: str = "Custom / User",
    auto_alpha: bool = False,
    workspace_root: Optional[Union[str, Path]] = None,
) -> dict:
    root = Path(workspace_root).resolve() if workspace_root else config.get_studio_root()
    my_stickers = root / "assets" / "my_stickers"
    my_stickers.mkdir(parents=True, exist_ok=True)

    clean_name = name.strip()
    if not clean_name:
        clean_name = "custom_sticker"

    safe_base = re.sub(r"[^a-zA-Z0-9_\-]", "_", clean_name.lower())
    safe_base = re.sub(r"_+", "_", safe_base).strip("_")
    if not safe_base:
        safe_base = "custom_sticker"

    filename = f"{safe_base}.png"
    target_path = my_stickers / filename

    builtin_stickers = root / "assets" / "stickers"
    counter = 1
    while target_path.exists() or (builtin_stickers / filename).exists():
        filename = f"{safe_base}_{counter}.png"
        target_path = my_stickers / filename
        counter += 1

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    if auto_alpha:
        arr = np.array(img)
        r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
        corner_coords = [(0, 0), (0, -1), (-1, 0), (-1, -1)]
        corner_alphas = [arr[cy, cx, 3] for cy, cx in corner_coords]
        if np.mean(corner_alphas) > 128:
            corners_rgb = [arr[cy, cx, :3] for cy, cx in corner_coords]
            avg_corner = np.mean(corners_rgb, axis=0)
            if np.mean(avg_corner) < 50:
                mask = (r < 35) & (g < 35) & (b < 35)
                arr[:, :, 3] = np.where(mask, 0, a)
            elif np.mean(avg_corner) > 215:
                mask = (r > 220) & (g > 220) & (b > 220)
                arr[:, :, 3] = np.where(mask, 0, a)
            img = Image.fromarray(arr, mode="RGBA")

    img.save(target_path, format="PNG")

    smart_tags = [category.lower()] if category else ["custom", "sticker"]
    if "foil" in clean_name.lower():
        smart_tags.append("foil")
    if "holo" in clean_name.lower():
        smart_tags.append("holo")
    smart_tags = list(dict.fromkeys(smart_tags))

    meta = _load_user_stickers_meta(my_stickers)
    meta[target_path.name] = {
        "name": clean_name,
        "category": category or "Custom / User",
        "tags": smart_tags,
    }
    _save_user_stickers_meta(my_stickers, meta)

    thumb = img.resize((128, 128), Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    thumb.save(buf, format="PNG")
    thumb_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    thumb_uri = f"data:image/png;base64,{thumb_b64}"

    try:
        rel_path = target_path.relative_to(root).as_posix()
    except ValueError:
        rel_path = str(target_path)

    return {
        "success": True,
        "name": clean_name,
        "filename": target_path.name,
        "category": category or "Custom / User",
        "tags": smart_tags,
        "path": rel_path,
        "thumbnail": thumb_uri,
        "preview": thumb_uri,
        "is_custom": True,
    }


def edit_custom_sticker(
    filename: str,
    new_name: Optional[str] = None,
    new_category: Optional[str] = None,
    workspace_root: Optional[Union[str, Path]] = None,
) -> dict:
    root = Path(workspace_root).resolve() if workspace_root else config.get_studio_root()
    my_stickers = root / "assets" / "my_stickers"
    builtin_stickers = root / "assets" / "stickers"
    clean_fn = Path(filename).name

    target_folder = None
    if (my_stickers / clean_fn).is_file():
        target_folder = my_stickers
    elif (builtin_stickers / clean_fn).is_file():
        target_folder = builtin_stickers
    else:
        raise FileNotFoundError(f"Sticker '{clean_fn}' not found in library.")

    meta = _load_user_stickers_meta(target_folder)
    default_cat = "Custom / User" if target_folder == my_stickers else "Tournament Holo"
    for item in STICKER_DEFINITIONS:
        if item["filename"].lower() == clean_fn.lower():
            default_cat = item["category"]
            break

    current = meta.get(clean_fn, {
        "name": (target_folder / clean_fn).stem.replace("_", " ").title(),
        "category": default_cat,
    })

    if new_name is not None and new_name.strip():
        current["name"] = new_name.strip()
    if new_category is not None and new_category.strip():
        current["category"] = new_category.strip()

    meta[clean_fn] = current
    _save_user_stickers_meta(target_folder, meta)

    return {
        "success": True,
        "filename": clean_fn,
        "name": current["name"],
        "category": current["category"],
    }


def delete_custom_sticker(
    filename: str,
    workspace_root: Optional[Union[str, Path]] = None,
    allow_builtin: bool = False,
) -> dict:
    root = Path(workspace_root).resolve() if workspace_root else config.get_studio_root()
    clean_fn = Path(filename).name

    my_stickers = root / "assets" / "my_stickers"
    builtin_stickers = root / "assets" / "stickers"

    is_custom = (my_stickers / clean_fn).is_file()
    is_builtin = (builtin_stickers / clean_fn).is_file()

    if not is_custom and not is_builtin:
        raise FileNotFoundError(f"Sticker '{clean_fn}' not found.")

    if is_builtin and not is_custom and not allow_builtin:
        raise ValueError("Cannot delete built-in library stickers. Only custom stickers can be deleted.")

    if is_custom:
        target_path = my_stickers / clean_fn
        target_path.unlink()
        meta = _load_user_stickers_meta(my_stickers)
        if clean_fn in meta:
            del meta[clean_fn]
            _save_user_stickers_meta(my_stickers, meta)
    elif is_builtin and allow_builtin:
        target_path = builtin_stickers / clean_fn
        target_path.unlink()
        meta = _load_user_stickers_meta(builtin_stickers)
        if clean_fn in meta:
            del meta[clean_fn]
            _save_user_stickers_meta(builtin_stickers, meta)

    return {
        "success": True,
        "message": f"Sticker '{clean_fn}' deleted successfully.",
        "filename": clean_fn,
    }


def restore_default_stickers(workspace_root: Optional[Union[str, Path]] = None) -> dict:
    ensure_builtin_assets(workspace_root, force_restore=True)
    return {
        "success": True,
        "message": f"Successfully restored {len(GENERATORS)} default tournament stickers.",
        "count": len(GENERATORS),
    }


def save_custom_skin(
    name: str,
    image_bytes: bytes,
    category: str = "Custom Weapon Skins",
    weapon: Optional[str] = None,
    weapon_category: Optional[str] = None,
    skin_name: Optional[str] = None,
    workspace_root: Optional[Union[str, Path]] = None,
) -> dict:
    root = Path(workspace_root).resolve() if workspace_root else config.get_studio_root()
    my_skins = root / "assets" / "my_skins"
    my_skins.mkdir(parents=True, exist_ok=True)

    w_slug = re.sub(r"[^a-zA-Z0-9_\-]", "", (weapon or "").lower().strip()).replace("-", "_")
    s_raw = (skin_name or name or "custom_skin").strip()
    s_slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", s_raw.lower())
    s_slug = re.sub(r"_+", "_", s_slug).strip("_")
    if not s_slug:
        s_slug = "custom_skin"

    if w_slug and not s_slug.startswith(w_slug + "_"):
        safe_base = f"{w_slug}_{s_slug}"
    else:
        safe_base = s_slug

    filename = f"{safe_base}.png"
    target_path = my_skins / filename

    counter = 1
    while target_path.exists():
        filename = f"{safe_base}_{counter}.png"
        target_path = my_skins / filename
        counter += 1

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    img.save(target_path, format="PNG")

    thumb = img.resize((128, 128), Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    thumb.save(buf, format="PNG")
    thumb_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    thumb_uri = f"data:image/png;base64,{thumb_b64}"

    meta = _load_user_skins_meta(my_skins)
    display_skin = s_raw.replace("_", " ").title()
    meta[target_path.name] = {
        "name": display_skin,
        "skin_name": display_skin,
        "weapon": weapon or w_slug or "",
        "weapon_category": weapon_category or "",
        "category": category or "Custom Weapon Skins",
    }
    _save_user_skins_meta(my_skins, meta)

    try:
        rel_path = target_path.relative_to(root).as_posix()
    except ValueError:
        rel_path = str(target_path)

    display_name = f"{w_slug.upper()} {display_skin}" if w_slug else display_skin

    return {
        "success": True,
        "name": display_name,
        "skin_name": display_skin,
        "filename": target_path.name,
        "weapon": weapon or w_slug or "",
        "weapon_category": weapon_category or "",
        "category": category,
        "path": rel_path,
        "thumbnail": thumb_uri,
        "preview": thumb_uri,
        "is_custom": True,
    }


def edit_custom_skin(
    filename: str,
    new_name: Optional[str] = None,
    new_weapon: Optional[str] = None,
    new_weapon_category: Optional[str] = None,
    workspace_root: Optional[Union[str, Path]] = None,
) -> dict:
    root = Path(workspace_root).resolve() if workspace_root else config.get_studio_root()
    my_skins = root / "assets" / "my_skins"
    clean_fn = Path(filename).name

    target_file = my_skins / clean_fn
    if not target_file.is_file():
        raise FileNotFoundError(f"Skin '{clean_fn}' not found in assets/my_skins.")

    meta = _load_user_skins_meta(my_skins)
    current = meta.get(clean_fn, {
        "name": clean_fn.replace("_", " ").title(),
        "skin_name": clean_fn.replace("_", " ").title(),
        "weapon": "",
        "weapon_category": "",
        "category": "Custom Weapon Skins",
    })

    if new_name is not None and new_name.strip():
        current["name"] = new_name.strip()
        current["skin_name"] = new_name.strip()
    if new_weapon is not None and new_weapon.strip():
        current["weapon"] = new_weapon.strip()
    if new_weapon_category is not None and new_weapon_category.strip():
        current["weapon_category"] = new_weapon_category.strip()

    meta[clean_fn] = current
    _save_user_skins_meta(my_skins, meta)

    return {
        "success": True,
        "filename": clean_fn,
        "name": current["name"],
        "skin_name": current.get("skin_name", current["name"]),
        "weapon": current.get("weapon", ""),
        "weapon_category": current.get("weapon_category", ""),
    }


def delete_custom_skin(
    filename: str,
    workspace_root: Optional[Union[str, Path]] = None,
) -> dict:
    root = Path(workspace_root).resolve() if workspace_root else config.get_studio_root()
    clean_fn = Path(filename).name
    my_skins = root / "assets" / "my_skins"
    target_file = my_skins / clean_fn
    if target_file.is_file():
        target_file.unlink()
        meta = _load_user_skins_meta(my_skins)
        if clean_fn in meta:
            del meta[clean_fn]
            _save_user_skins_meta(my_skins, meta)
        return {"success": True, "message": f"Skin '{clean_fn}' deleted.", "filename": clean_fn}
    raise FileNotFoundError(f"Skin '{clean_fn}' not found in assets/my_skins.")
