---
name: cs16-pw-injector
description: >-
  Use this skill when the user wants to bake and inject weapon skins and decals
  from a Counter-Strike 1.6 viewmodel (v_*.mdl) into its corresponding player model
  (p_*.mdl) and world model (w_*.mdl).
---

# CS 1.6 P & W Model Injector

This skill synchronizes weapon textures and decals from first-person viewmodels (`v_*.mdl`) into third-person player models (`p_*.mdl`) and dropped world models (`w_*.mdl`).

All operations in `D:\Counter-Strike 1.6\cs16-emptyx-customization` resolve game models dynamically via `config.json`.

## Quick Command Usage

```powershell
# Sync P and W models for a specific weapon
python scripts/cs16_studio.py sync-pw -w usp --team ct
python scripts/cs16_studio.py sync-pw -w ak47 --team ct

# Restore P and W models from backup (.orig.mdl)
python scripts/cs16_studio.py restore -w usp --team ct --pw-only
```

Or click **"Sync P/W"** directly in the top bar of the CS 1.6 Asset Studio Pro Web Dashboard (`http://127.0.0.1:5160/`).
