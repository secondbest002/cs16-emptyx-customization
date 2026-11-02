---
name: cs16-glove-injector
description: >-
  Use this skill when the user wants to copy, swap, or inject glove/hand textures
  from one Counter-Strike 1.6 viewmodel (v_*.mdl) to another viewmodel to keep gloves consistent.
---

# CS 1.6 Glove Injector

This skill provides glove and hand texture synchronization across weapon viewmodels (`v_*.mdl`) while strictly protecting sleeve/arm textures and animations.

All operations in `D:\Counter-Strike 1.6\cs16-emptyx-customization` resolve game models dynamically via `config.json`.

## Quick Command Usage

```powershell
# Transfer gloves from source weapon to a target weapon
python scripts/cs16_studio.py transfer-gloves -s usp -t deagle --team ct

# Synchronize gloves from reference weapon across ALL weapons in loadout
python scripts/cs16_studio.py transfer-gloves -s usp -t all --team ct

# Synchronize to a specific list of weapons
python scripts/cs16_studio.py transfer-gloves -s usp -t ak47,m4a1,awp --team ct
```

## How It Works
1. **Reads MDL Headers:** Parses GoldSrc StudioModel format (`IDST`, version 10).
2. **Finds Glove Textures:** Detects glove/hand textures (`sport_right.bmp`, `sport_left.bmp`) while strictly preserving sleeves (`sleeve.bmp`, `arm.bmp`).
3. **Safety Backup:** Automatically creates immutable `.orig.mdl` backup before modifying.
4. **Lossless Injection:** Injects pixel data and 256-color palette with automatic resizing if needed.
