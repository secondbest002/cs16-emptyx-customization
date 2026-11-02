---
name: cs16-asset-studio
description: >-
  Use this skill when the user wants to inspect, replace, auto-convert, or inject weapon skins,
  stickers, and decals into Counter-Strike 1.6 models from any image format (PNG, JPG, BMP, WEBP),
  bake stickers onto weapon surfaces, grade colors (vibrance, clarity, temperature), inspect in 3D WebGL,
  customize StatTrak LEDs, transfer gloves, simulate float wear, toggle chrome foil shine, or launch the Web Dashboard.
---

# CS 1.6 Asset Studio Pro (Skin, Sticker & 3D WebGL Studio)

**CS 1.6 Asset Studio Pro** is the modern photographic color grading, 3D model viewport, and skin/sticker auto-injector for Counter-Strike 1.6 viewmodels (`v_*.mdl`).

### Standalone Decoupled Workspace
This workspace (`D:\Counter-Strike 1.6\cs16-emptyx-customization`) is decoupled from the main game directory (`D:\Counter-Strike 1.6\Counter-Strike 1.6 Original`) to keep the codebase light (< 25MB) for fast Gemini pair-programming and indexing. All game model paths are dynamically resolved via `config.json`.

### Core Pro Capabilities:
1. **Interactive 3D WebGL Model Viewport**: Inspect weapons, gloves, and stickers in full 360° 3D with OrbitControls (zoom, pan, turntable auto-rotate, wireframe overlay, and hot-reloading).
2. **Color Grading & Tuning Studio**: Professional photographic adjustment engine for weapon skins, gloves (`sport_right.bmp`, `sport_left.bmp`), and sleeves (`sleeve.bmp`):
   - Sliders: Vibrance (smart saturation), Saturation, Clarity & Mid-tones, Contrast, Brightness, Shadows Boost, Highlights Recovery, Color Temperature (Warm/Cool), and Tint.
   - Quick presets: *Vibrant CS2*, *Dark Ops / Stealth*, *Warm Golden*, *Cyber Neon*, *Neutral Reset*.
   - Live 60fps Before vs After side-by-side comparison with 1-click GoldSrc 256-color palette quantization.
3. **Slot Sticker Scale & Fine-Tuner (Native Resolution)**:
   - Fine-tune stickers inside their exact slot bounding box (`176x161`, `512x512`).
   - Scale (0.5x to 1.5x), Offset X / Y adjustments, and Rotation (0° to 360°).
   - Clean transparent padding with strict Index 255 Pinning and matte defringing (zero black halos in-game).
4. **Interactive WYSIWYG Bake Sticker Canvas**: Click and drag stickers directly on weapon surfaces with sub-pixel crosshairs, scroll wheel zooming, and canvas state sync.
5. **StatTrak Digital LED Customizer**: Customize kill counter glow color (*Classic Orange*, *Neon Cyan*, *Ruby Red*, *Emerald Green*, *Cyber Violet*) and custom counter digits (e.g., `001337`).
6. **1-Click Glove & Sleeve Transfer Studio**: Instantly synchronize glove and arm textures across any or all weapons in your loadout with automatic dimension adaptation.
7. **Float & Wear Simulator**: Procedural paint chipping on edges (Sobel/Laplacian detection), metal alloy abrasion, and patina oxidation from *Factory New (0.00)* to *Battle-Scarred (1.00)*.
8. **GoldSrc Metallic Chrome / Foil Shimmer**: 1-click toggle of `STUDIO_NF_CHROME (0x02)` for reflective environmental shine on stickers and metal weapon parts.
9. **Built-in Asset & Sticker Library**: Instant access to iconic tournament holo badges (Katowice 2014, Titan, iBuyPower, Navi, Crown Foil, Howling Dawn) and custom skins.
10. **Immutable Backup Protection**: Automatic `.orig.mdl` backup on first edit, single-slot snapshots, and 1-click restore.
11. **Multi-Step Undo / Redo History Stack (`Ctrl+Z` / `Ctrl+Y`)**: Seamlessly step backward and forward through texture injections, color grading adjustments, and bake actions without risking loss of work.
12. **Split-Screen Curtain Comparison (Before vs After Slider)**: Smooth draggable vertical divider over weapon textures to inspect fine details between original and graded outputs at 60fps.
13. **Quick Weapon Switcher (`Ctrl+K` or `/`)**: Instant Spotlight search modal to switch active weapons and loadouts in 0.1s with full keyboard navigation.
14. **First-Person View (FPV) & 360° Showcase in 3D Viewport**: Camera presets simulating true CS 1.6 player viewmodel perspective and presentation showcase turntable orbit.
15. **Color Eyedropper Tool**: Direct pixel color sampler from weapon surfaces to coordinate StatTrak LED colors, sticker tints, and color grading palettes.
16. **1-Click Export Custom Mod Pack (`.zip`)**: Bundles all customized models into a clean, ready-to-use CS 1.6 modpack ZIP with game directory structure (`cstrike/models/...`), manifest, and installation guide.

---

## Command Quick Reference

### 1. Launch Web Dashboard Pro
```powershell
# 1-Click launcher directly from Windows Explorer:
CS16_Asset_Studio.bat

# Or via Python:
python scripts/cs16_studio.py --ui
```
Opens modern local dashboard in your browser (`http://127.0.0.1:5160/`).

To create a Windows Desktop shortcut:
```powershell
CS16_Asset_Studio.bat --shortcut
```

### 2. Inspect Model Textures or Images
```powershell
python scripts/cs16_studio.py info -w usp --team ct
python scripts/cs16_studio.py info -w awp --team ct
```

### 3. Replace Weapon Body Skin
```powershell
python scripts/cs16_studio.py skin -w usp --team ct -i "path/to/skin.png"
```

### 4. Inject Sticker into 3D Submesh Slot (Smart-Fit & Index 255 Pinning)
```powershell
python scripts/cs16_studio.py sticker -w usp --team ct --slot 1 -i "assets/stickers/titan_holo.png"
```

### 5. Bake Sticker directly onto Weapon Surface
```powershell
python scripts/cs16_studio.py bake -w usp --team ct -i "assets/stickers/crown_foil.png" --preset silencer
python scripts/cs16_studio.py bake -w ak47 --team ct -i "assets/stickers/howling_dawn.png" --pos 280,230
```

### 6. Photographic Color Grading & Tuning
```powershell
# Apply quick preset style (vibrant_cs2, dark_ops, warm_golden, cyber_neon, neutral)
python scripts/cs16_studio.py color -w usp --team ct --preset vibrant_cs2

# Custom photographic slider tuning on weapon skin, gloves, or sleeves
python scripts/cs16_studio.py color -w usp --team ct --texture sport_right.bmp --vibrance 40 --clarity 25 --temperature 10
```

### 7. StatTrak LED Digital Counter Customizer
```powershell
# Customize glow color (orange, cyan, red, green, violet) and kill count
python scripts/cs16_studio.py stattrak -w usp --team ct --color cyan --number 001337
```

### 8. Wear & Float Simulator (Factory New -> Battle-Scarred)
```powershell
# Apply procedural edge wear and scratches
python scripts/cs16_studio.py wear -w usp --team ct --float 0.35 --seed 1337
```

### 9. 1-Click Glove & Sleeve Transfer
```powershell
# Synchronize gloves from USP to all CT weapons (or specific targets)
python scripts/cs16_studio.py transfer-gloves -s usp -t all --team ct
python scripts/cs16_studio.py transfer-gloves -s usp -t awp,ak47,m4a1 --team ct
```

### 10. GoldSrc Metallic Chrome / Foil Shimmer
```powershell
# Toggle STUDIO_NF_CHROME flag (0x02) for reflective metallic shine
python scripts/cs16_studio.py chrome -w usp --team ct --slot 1
```

### 11. Batch Multi-Weapon Sticker Apply (CLI)
```powershell
python scripts/cs16_studio.py batch-sticker -w ak47,m4a1,awp,usp --team ct --slot 1 -i assets/stickers/titan_holo.png --fx foil
```

### 12. Revert Slot or Restore Models (V, P, W)
```powershell
# Revert specific slot
python scripts/cs16_studio.py revert -w usp --team ct --slot 1

# Restore all models (V, P, and W) to original (default scope: all)
python scripts/cs16_studio.py restore -w usp --team ct

# Restore only Player & World dropped models (P & W)
python scripts/cs16_studio.py restore -w usp --team ct --pw-only

# Restore only first-person viewmodel (V only)
python scripts/cs16_studio.py restore -w usp --team ct --v-only
```

### 13. Export Custom Mod Pack (.zip)
```powershell
python -c "from scripts.cs16_studio import export_modpack; zb, m = export_modpack(); open('my_cs16_modpack.zip', 'wb').write(zb); print('Exported', m['model_count'], 'models!')"
```

### 14. Modern First-Person POV Controller (CS2 Viewmodel Camera)
```powershell
python scripts/cs16_studio.py pov --preset cs2_classic
python scripts/cs16_studio.py pov --status
python scripts/cs16_studio.py pov --reset
```
