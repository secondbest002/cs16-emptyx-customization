---
name: cs16-skin-transfer
description: >-
  Use this skill when the user wants to transfer or swap a weapon skin texture from a donor/collection
  viewmodel to a target viewmodel while preserving custom animations (recoil, reload, inspect), gloves,
  stickers, and StatTrak modules, with optional synchronization to p/w models.
---

# CS 1.6 Weapon Skin Transfer

This skill transfers the core weapon body skin from a donor/collection model into an active viewmodel while strictly **preserving**:
* Custom firing and recoil animations (`shoot1`, `shoot2`, `shoot3`).
* Custom inspect, reload, and draw sequences.
* Active gloves and arm textures (e.g. Sport Gloves).
* Existing stickers and decal slots.
* StatTrak modules and counter digits.

All operations in `D:\Counter-Strike 1.6\cs16-emptyx-customization` resolve game models dynamically via `config.json`.

---

## Command Usage & Parameter Guide

```powershell
# Transfer skin texture from image or donor into active viewmodel
python scripts/cs16_studio.py skin -w ak47 --team ct -i "path/to/donor_skin.png"

# Bake & synchronize to P and W models immediately after transfer
python scripts/cs16_studio.py sync-pw -w ak47 --team ct
```

Or drag & drop skin textures directly into the **Skin Assets Library** in the Web Dashboard (`http://127.0.0.1:5160/`) and click **Apply Skin**.
