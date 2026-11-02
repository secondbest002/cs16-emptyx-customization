---
name: cs16-sticker-fx
description: >-
  Use this skill when the user wants to toggle, switch, or customize sticker visual effects
  (such as Chrome/Foil metallic shine, flat Matte, glow, or temporarily hiding stickers) on CS 1.6 viewmodels.
---

# CS 1.6 Sticker Effects Controller

This skill controls visual rendering flags (such as metallic Chrome/Foil shimmer, additive glow, and transparency) for weapon stickers and decals in Counter-Strike 1.6 GoldSrc StudioModels (`v_*.mdl`).

All operations in `D:\Counter-Strike 1.6\cs16-emptyx-customization` resolve game models dynamically via `config.json`.

---

## Supported Sticker Effects

| Mode | Flag | Description |
| :--- | :--- | :--- |
| `foil` / `chrome` | `0x42` | **Foil / Holo Metallic Gleam**: Reflects environment light dynamically based on view angle. |
| `matte` | `0x40` | **Matte Finish**: Classic flat cutout sticker without reflections. |
| `glow` | `0x60` | **Additive Glow**: Shines brightly in dark hallways/shadows. |

---

## Detailed Command Usage

```powershell
# Toggle Chrome / Foil metallic shine on a sticker slot
python scripts/cs16_studio.py chrome -w usp --team ct --slot 1

# Apply Foil effect across multiple weapons at once
python scripts/cs16_studio.py batch-sticker -w ak47,m4a1,awp,usp --team ct --slot 1 -i assets/stickers/titan_holo.png --fx foil

# Revert sticker slot back to normal / original
python scripts/cs16_studio.py revert -w usp --team ct --slot 1
```

Or toggle the **Foil Shimmer** button with 1 click directly inside the Web Dashboard (`http://127.0.0.1:5160/`).
