---
name: cs16-color-vibrance
description: >-
  Use this skill when the user wants to adjust, boost, or toggle color saturation, contrast,
  and brightness on CS 1.6 weapon models, gloves, or entire viewmodels, with presets and quick resets.
---

# CS 1.6 Color Vibrance & Contrast Enhancer

This skill performs color palette transformations on Counter-Strike 1.6 GoldSrc StudioModels (`v_*.mdl`). It operates directly on the 768-byte RGB palette tables, delivering instant results with **0% loss of detail**, no re-quantization artifacts, and 100% reversible resets.

All operations in `D:\Counter-Strike 1.6\cs16-emptyx-customization` resolve game models dynamically via `config.json`.

---

## Command Usage & Parameter Guide

Using `scripts/cs16_studio.py color`:

### 1. Apply Color Presets

```powershell
# Vivid CS2 Look
python scripts/cs16_studio.py color -w ak47 --team ct --preset vibrant_cs2

# Dark Ops / Stealth Look
python scripts/cs16_studio.py color -w ak47 --team ct --preset dark_ops

# Warm Golden Look
python scripts/cs16_studio.py color -w ak47 --team ct --preset warm_golden

# Cyber Neon Look
python scripts/cs16_studio.py color -w ak47 --team ct --preset cyber_neon
```

---

### 2. Choosing Target Texture

```powershell
# Target specific texture (e.g. gloves or sleeves)
python scripts/cs16_studio.py color -w ak47 --team ct --texture sport_right.bmp --vibrance 40 --clarity 20

# Target main weapon skin body
python scripts/cs16_studio.py color -w ak47 --team ct --vibrance 30 --contrast 15
```

---

### 3. Resetting Back to Factory Colors

```powershell
# Revert texture or model to original state
python scripts/cs16_studio.py restore -w ak47 --team ct --v-only
```
