"""
cli.py - Command Line Interface for CS 1.6 Asset Studio.
"""

import argparse
import os
from pathlib import Path
import sys
import webbrowser

from .config_manager import StudioConfig
from .baker import bake_sticker_onto_texture
from .color_adjuster import PRESETS, adjust_and_quantize
from .sleeve_injector import SLEEVE_PRESETS, transplant_3d_sleeves
from .glove_transfer import batch_transfer_gloves
from .image_pipeline import process_image_for_texture
from .pw_restore import find_model_backup, migrate_loose_backups
from .pw_restore import find_model_backup, migrate_loose_backups
from .mdl_core import (
    MdlModel,
    ROLE_SKIN,
    ROLE_STICKER,
    STUDIO_NF_CHROME,
    STUDIO_NF_MASKED,
    STUDIO_NF_ADDITIVE,
    discover_available_models,
    resolve_model_path,
)
from .pw_restore import restore_weapon_models, resolve_weapon_triplet
from .stattrak_customizer import customize_stattrak_texture
from .wear_simulator import get_wear_condition_name, simulate_and_quantize
from .pov_manager import (
    PovConfig,
    PRESETS as POV_PRESETS,
    get_preset,
    validate_and_clamp,
    export_cfg_string,
    apply_to_game,
    reset_to_vanilla,
    read_current_config,
)


def print_banner():
    banner = r"""
   _____ _____  __   __    ___              _      _____ _             _ _       
  / ____/ ____|/_ | / /   / _ \            | |    / ____| |           | (_)      
 | |   | (___   | |/ /_  / /_\ \ ___ ___  ___| |_  | (___ | |_ _   _  __| |_  ___  
 | |    \___ \  | | '_ \ |  _  |/ __/ __|/ _ \ __|  \___ \| __| | | |/ _` | |/ _ \ 
 | |________) | | | (_) || | | |\__ \__ \  __/ |_   ____) | |_| |_| | (_| | | (_) |
  \_____|_____/ |_|\___/ \_| |_/|___/___/\___|\__| |_____/ \__|\__,_|\__,_|_|\___/ 
                     GoldSrc IDST v10 Skin & Sticker Studio
"""
    print(banner)


def cmd_info(args):
    mdl_path = resolve_model_path(args.weapon, team=args.team)
    model = MdlModel(mdl_path)
    orig_bak_tuple = find_model_backup(mdl_path)
    orig_exists = orig_bak_tuple[0] is not None

    print(f"\nModel File   : {mdl_path}")
    print(f"File Size    : {len(model.data):,} bytes")
    print(f"Backup (.orig): {'Yes (Protected)' if orig_exists else 'Not yet created'}")
    print(f"Textures     : {len(model.textures)} found\n")

    print(f"{'Idx':<4} {'Name':<24} {'Size':<12} {'Flags':<8} {'Role':<14} {'Classification'}")
    print("-" * 78)
    for t in model.textures:
        dim_str = f"{t.width}x{t.height}"
        flag_str = f"0x{t.flags:04X}"
        print(f"[{t.index:2d}] {t.name:<24} {dim_str:<12} {flag_str:<8} {t.role:<14} {t.role_label}")
    print()


def cmd_clean_backups(args):
    root = args.cstrike if getattr(args, "cstrike", None) else None
    print("\n[Asset Studio Pro] Scanning model folders for loose backup files...")
    moved = migrate_loose_backups(root_dir=root)
    if not moved:
        print("[Asset Studio Pro] All backup files are already organized in their respective 'backup/' folders!\n")
    else:
        print(f"[Asset Studio Pro] Successfully organized {len(moved)} backup file(s) into dedicated 'backup/' folders:")
        for item in moved:
            print(f"  -> {Path(item['source']).name}  -->  {item['dest']}")
        print()


def cmd_skin(args):
    mdl_path = resolve_model_path(args.weapon, team=args.team)
    model = MdlModel(mdl_path)

    # Find target weapon skin
    target_tex = None
    if args.texture:
        target_tex = model.find_texture(args.texture)
        if not target_tex:
            print(f"Error: Specified texture '{args.texture}' not found in model.", file=sys.stderr)
            sys.exit(1)
    else:
        skins = model.get_skins()
        if not skins:
            print("Error: No weapon skin textures identified in this model.", file=sys.stderr)
            sys.exit(1)
        # Main body skin is usually the largest
        target_tex = max(skins, key=lambda t: t.width * t.height)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: Input image file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Target Model   : {mdl_path}")
    print(f"Target Texture : '{target_tex.name}' ({target_tex.width}x{target_tex.height})")
    print(f"Input Image    : {input_path}")
    print(f"Mode           : {args.mode.upper()}")

    model.save_slot_snapshot(target_tex)

    payload, _ = process_image_for_texture(
        input_path,
        target_tex.width,
        target_tex.height,
        is_masked=target_tex.is_masked,
        mode=args.mode,
    )

    model.inject_texture_payload(target_tex, payload)
    dest = Path(args.output) if args.output else mdl_path
    saved = model.save_atomic(dest, create_backup=True)

    print(f"\n[Success] Weapon skin injected into '{target_tex.name}'. Saved to: {saved}")


def cmd_sticker(args):
    mdl_path = resolve_model_path(args.weapon, team=args.team)
    model = MdlModel(mdl_path)

    stickers = model.get_stickers()
    if not stickers:
        print("Error: No dedicated 3D sticker slots found in this model! Use 'bake' mode instead.", file=sys.stderr)
        sys.exit(1)

    # Resolve slot
    target_tex = None
    slot_input = str(args.slot).strip()

    if slot_input.isdigit():
        idx_val = int(slot_input)
        # Check by 1-based index or match name digit
        for s in stickers:
            if slot_input in s.name:
                target_tex = s
                break
        if not target_tex and 1 <= idx_val <= len(stickers):
            target_tex = stickers[idx_val - 1]
    else:
        target_tex = model.find_texture(slot_input)

    if not target_tex:
        target_tex = stickers[0]

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: Input sticker image '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    # Visual finish flag
    new_flags = target_tex.flags
    if args.fx == "chrome" or args.fx == "foil":
        new_flags = STUDIO_NF_MASKED | STUDIO_NF_CHROME
    elif args.fx == "glow":
        new_flags = STUDIO_NF_MASKED | STUDIO_NF_ADDITIVE
    elif args.fx == "matte":
        new_flags = STUDIO_NF_MASKED

    print(f"Target Model   : {mdl_path}")
    print(f"Target Slot    : '{target_tex.name}' ({target_tex.width}x{target_tex.height}) [Flags: 0x{new_flags:04X}]")
    print(f"Input Sticker  : {input_path}")
    print(f"Mode           : {args.mode.upper()} (Scale: {args.scale:.2f}x)")

    model.save_slot_snapshot(target_tex)

    payload, _ = process_image_for_texture(
        input_path,
        target_tex.width,
        target_tex.height,
        is_masked=True,
        mode=args.mode,
        scale_multiplier=args.scale,
    )

    model.inject_texture_payload(target_tex, payload, new_flags=new_flags)
    dest = Path(args.output) if args.output else mdl_path
    saved = model.save_atomic(dest, create_backup=True)

    print(f"\n[Success] Sticker injected into slot '{target_tex.name}'. Saved to: {saved}")


def cmd_bake(args):
    mdl_path = resolve_model_path(args.weapon, team=args.team)
    model = MdlModel(mdl_path)

    # Find weapon skin
    target_tex = None
    if args.texture:
        target_tex = model.find_texture(args.texture)
    else:
        skins = model.get_skins()
        target_tex = max(skins, key=lambda t: t.width * t.height) if skins else None

    if not target_tex:
        print("Error: No weapon skin found to bake sticker onto.", file=sys.stderr)
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: Sticker file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    custom_coords = None
    if args.pos:
        parts = args.pos.split(",")
        custom_coords = (int(parts[0].strip()), int(parts[1].strip()))

    print(f"Target Model   : {mdl_path}")
    print(f"Weapon Body    : '{target_tex.name}' ({target_tex.width}x{target_tex.height})")
    print(f"Sticker Image  : {input_path}")
    print(f"Preset / Pos   : {args.pos or args.preset}")

    model.save_slot_snapshot(target_tex)

    base_rgba = target_tex.to_rgba_image()
    pre_emph = getattr(args, "pre_emphasis", True)
    payload, _ = bake_sticker_onto_texture(
        base_rgba,
        input_path,
        weapon_key=args.weapon,
        preset=args.preset,
        custom_coords=custom_coords,
        scale_multiplier=args.scale,
        rotation_deg=args.rotation,
        pre_emphasis=pre_emph,
    )

    model.inject_texture_payload(target_tex, payload)
    dest = Path(args.output) if args.output else mdl_path
    saved = model.save_atomic(dest, create_backup=True)

    print(f"\n[Success] Baked sticker onto '{target_tex.name}'. Saved to: {saved}")


def cmd_revert(args):
    mdl_path = resolve_model_path(args.weapon, team=args.team)
    model = MdlModel(mdl_path)

    slot_target = args.slot
    if not slot_target:
        print("Error: Specify --slot <name_or_index> to revert.", file=sys.stderr)
        sys.exit(1)

    print(f"Reverting slot '{slot_target}' in {mdl_path.name}...")
    success = model.revert_texture_from_backup(slot_target)
    if success:
        print(f"[Success] Slot '{slot_target}' reverted to backup.")
    else:
        print(f"[Error] Failed to revert slot '{slot_target}'. No backup found.", file=sys.stderr)
        sys.exit(1)


def cmd_batch_sticker(args):
    from .mdl_core import batch_inject_sticker

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: Input sticker image '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    weapon_list = [w.strip() for w in args.weapons.split(",") if w.strip()]
    if not weapon_list:
        print("Error: Specify at least one weapon name in --weapons (e.g. -w ak47,m4a1,awp,usp).", file=sys.stderr)
        sys.exit(1)

    print(f"\nBatch Applying Sticker '{input_path.name}' across {len(weapon_list)} weapons...")
    print(f"Team: {args.team.upper()} | Slot: {args.slot} | Mode: {args.mode} | Scale: {args.scale}x | FX: {args.fx}\n")

    results = batch_inject_sticker(
        weapons=weapon_list,
        sticker_image=input_path,
        slot=args.slot,
        team=args.team,
        mode=args.mode,
        scale=args.scale,
        fx=args.fx,
    )

    success_count = 0
    for w, res in results.items():
        if res.get("success"):
            success_count += 1
            print(f"  [OK]   {w.upper():<8} -> Injected into '{res['slot_name']}' ({res['model_name']})")
        else:
            print(f"  [FAIL] {w.upper():<8} -> Failed: {res.get('error')}", file=sys.stderr)

    print(f"\n[Result] {success_count}/{len(weapon_list)} weapons successfully updated.\n")
    if success_count == 0:
        sys.exit(1)


def cmd_restore(args):
    # Determine scope: shortcuts override --scope
    if getattr(args, "v_only", False):
        scope = "v"
    elif getattr(args, "pw_only", False):
        scope = "pw"
    elif getattr(args, "restore_all", False):
        scope = "all"
    else:
        scope = getattr(args, "scope", "all")

    print(f"\nRestoring weapon '{args.weapon}' (Team: {args.team.upper()}, Scope: {scope.upper()})...")
    try:
        res = restore_weapon_models(args.weapon, team=args.team, scope=scope)
    except Exception as e:
        print(f"[Error] Failed to resolve or restore weapon '{args.weapon}': {e}", file=sys.stderr)
        sys.exit(1)

    for role, m_info in res.get("models", {}).items():
        role_label = m_info.get("role_label", role)
        filename = m_info.get("filename", "")
        if m_info.get("restored"):
            b_type = m_info.get("backup_type", "backup")
            print(f"  [OK]   {role_label:<28} -> Restored '{filename}' from {b_type}")
        else:
            msg = m_info.get("message", "No backup available")
            print(f"  [SKIP] {role_label:<28} -> {msg}")

    restored = res.get("restored_count", 0)
    total = len(res.get("target_roles", []))
    print(f"\n[Result] {restored}/{total} models successfully restored to original.\n")

    if restored == 0:
        sys.exit(1)


def cmd_color(args):
    mdl_path = resolve_model_path(args.weapon, team=args.team)
    model = MdlModel(mdl_path)
    if args.texture:
        target_tex = model.find_texture(args.texture)
        if not target_tex:
            print(f"Error: Texture '{args.texture}' not found in model.", file=sys.stderr)
            sys.exit(1)
    else:
        skins = model.get_skins()
        if not skins:
            print("Error: No skin textures identified in this model.", file=sys.stderr)
            sys.exit(1)
        target_tex = max(skins, key=lambda t: t.width * t.height)

    params = {}
    if args.preset and args.preset in PRESETS:
        params.update(PRESETS[args.preset])
    for k in ("vibrance", "saturation", "clarity", "contrast", "brightness", "shadows", "highlights", "temperature", "tint", "hue", "sharpen"):
        val = getattr(args, k, None)
        if val is not None and (val != 0.0 or args.preset is None):
            params[k] = val

    print(f"Color Grading Target : {target_tex.name} ({target_tex.width}x{target_tex.height}) in {mdl_path.name}")
    if args.preset:
        print(f"Preset Applied       : {args.preset}")

    model.save_slot_snapshot(target_tex)
    payload, _ = adjust_and_quantize(target_tex.to_rgba_image(), is_masked=target_tex.is_masked, **params)
    model.inject_texture_payload(target_tex, payload)
    saved = model.save_atomic(create_backup=True)
    print(f"[Success] Applied color grading to '{target_tex.name}'. Saved to: {saved}")


def cmd_stattrak(args):
    mdl_path = resolve_model_path(args.weapon, team=args.team)
    model = MdlModel(mdl_path)
    target_tex = model.find_texture("stat_digit.bmp")
    if not target_tex:
        for t in model.textures:
            if t.role == "stattrak" or "stat_" in t.name.lower():
                target_tex = t
                break
    if not target_tex:
        print(f"Error: No StatTrak digit texture found in {mdl_path.name}.", file=sys.stderr)
        sys.exit(1)

    print(f"StatTrak Target : {target_tex.name} ({target_tex.width}x{target_tex.height}) in {mdl_path.name}")
    print(f"LED Glow Color  : {args.color.upper()}")
    if args.number:
        print(f"Custom Counter  : {args.number}")

    model.save_slot_snapshot(target_tex)
    payload, _ = customize_stattrak_texture(
        target_tex.to_rgba_image(),
        color_name=args.color,
        custom_number=args.number,
    )
    model.inject_texture_payload(target_tex, payload)
    saved = model.save_atomic(create_backup=True)
    print(f"[Success] StatTrak LED updated to {args.color.upper()}. Saved to: {saved}")


def cmd_wear(args):
    mdl_path = resolve_model_path(args.weapon, team=args.team)
    model = MdlModel(mdl_path)
    if args.texture:
        target_tex = model.find_texture(args.texture)
        if not target_tex:
            print(f"Error: Texture '{args.texture}' not found in model.", file=sys.stderr)
            sys.exit(1)
    else:
        skins = model.get_skins()
        if not skins:
            print("Error: No skin textures identified in this model.", file=sys.stderr)
            sys.exit(1)
        target_tex = max(skins, key=lambda t: t.width * t.height)

    tier_name = get_wear_condition_name(args.wear_float)
    print(f"Wear Simulation Target : {target_tex.name} in {mdl_path.name}")
    print(f"Wear Float             : {args.wear_float:.3f} -> {tier_name}")

    model.save_slot_snapshot(target_tex)
    payload, _ = simulate_and_quantize(
        target_tex.to_rgba_image(),
        wear_float=args.wear_float,
        seed=args.seed,
        is_masked=target_tex.is_masked,
    )
    model.inject_texture_payload(target_tex, payload)
    saved = model.save_atomic(create_backup=True)
    print(f"[Success] Applied {tier_name} wear to '{target_tex.name}'. Saved to: {saved}")


def cmd_transfer_gloves(args):
    tgt_list = [t.strip() for t in args.target.split(",")] if args.target else ["all"]
    sync_sleeves = not args.no_sleeves

    print(f"Transferring gloves from '{args.source}' to {tgt_list} (Team: {args.team.upper()})...")
    results = batch_transfer_gloves(
        source_weapon=args.source,
        target_weapons=tgt_list,
        team=args.team,
        sync_sleeves=sync_sleeves,
    )
    success_count = 0
    for w, res in results.items():
        if res.get("success"):
            success_count += 1
            print(f"  [OK]   {w.upper():<8} -> Transferred: {res.get('transferred')}")
        else:
            print(f"  [FAIL] {w.upper():<8} -> {res.get('error')}", file=sys.stderr)

    print(f"\n[Result] Gloves transferred to {success_count}/{len(results)} target weapons.\n")
    if success_count == 0:
        sys.exit(1)


def cmd_chrome(args):
    mdl_path = resolve_model_path(args.weapon, team=args.team)
    model = MdlModel(mdl_path)
    target_tex = model.find_texture(args.slot)
    if not target_tex:
        print(f"Error: Texture slot '{args.slot}' not found in {mdl_path.name}.", file=sys.stderr)
        sys.exit(1)

    enable = None
    if args.enable:
        enable = True
    elif args.disable:
        enable = False

    model.save_slot_snapshot(target_tex)
    model.toggle_chrome_shimmer(target_tex, enable=enable)
    saved = model.save_atomic(create_backup=True)
    is_chrome = bool(target_tex.flags & STUDIO_NF_CHROME)
    print(f"[Success] Chrome shimmer {'enabled' if is_chrome else 'disabled'} for '{target_tex.name}'. Saved to: {saved}")


def cmd_pov(args):
    cstrike_dir = Path(args.cstrike) if getattr(args, "cstrike", None) else None

    # Handle --reset
    if getattr(args, "reset", False):
        success = reset_to_vanilla(cstrike_dir)
        if success:
            print("\n[Success] Viewmodel POV reset to vanilla CS 1.6 defaults.")
            print("  modern_pov.cfg updated and hooked in userconfig.cfg.\n")
        else:
            print("Error: Failed to reset viewmodel POV configuration.", file=sys.stderr)
            sys.exit(1)
        return

    # Handle --status
    if getattr(args, "status", False):
        cfg = read_current_config(cstrike_dir)
        if cfg is None:
            print("\n[POV Status] No modern_pov.cfg found. Game is running in vanilla CS 1.6 state.\n")
        else:
            matched_preset = "custom"
            for pname, pcfg in POV_PRESETS.items():
                if (
                    abs(cfg.offset_x - pcfg.offset_x) < 0.001
                    and abs(cfg.offset_y - pcfg.offset_y) < 0.001
                    and abs(cfg.offset_z - pcfg.offset_z) < 0.001
                    and cfg.bobstyle == pcfg.bobstyle
                    and abs(cfg.lag_scale - pcfg.lag_scale) < 0.001
                ):
                    matched_preset = pname
                    break

            print("\n[POV Status] Active Viewmodel POV Configuration:")
            print(f"  Preset Profile   : {matched_preset}")
            print(f"  Offsets (X, Y, Z): ({cfg.offset_x:.2f}, {cfg.offset_y:.2f}, {cfg.offset_z:.2f})")
            print(f"  Lag Scale / Speed: {cfg.lag_scale:.2f} / {cfg.lag_speed:.2f}")
            print(f"  Bobstyle         : {cfg.bobstyle} ({'CS:GO/CS2 dynamic' if cfg.bobstyle == 2 else 'Vanilla 1.6'})")
            print(f"  Bob Dynamics     : lat={cfg.bobamt_lat:.2f}, vert={cfg.bobamt_vert:.2f}, lower={cfg.bob_lower_amt:.1f}, cycle={cfg.bobcycle:.2f}")
            print(f"  Wall Retract     : {'Enabled' if cfg.retract else 'Disabled'}")
            print(f"  Inspect Bind     : bind 'f' 'lookatweapon'\n")
        return

    has_input = (
        getattr(args, "preset", None) is not None
        or getattr(args, "x", None) is not None
        or getattr(args, "y", None) is not None
        or getattr(args, "z", None) is not None
        or getattr(args, "bob", None) is not None
        or getattr(args, "lag", None) is not None
    )

    if not has_input and not getattr(args, "output", None):
        cfg = read_current_config(cstrike_dir)
        if cfg:
            args.status = True
            cmd_pov(args)
            return
        else:
            print("\nUsage: cs16_studio.py pov [--preset NAME] [--x X] [--y Y] [--z Z] [--bob STYLE] [--lag LAG] [--status] [--reset]")
            print(f"Available presets: {', '.join(POV_PRESETS.keys())}\n")
            return

    # Determine base configuration
    preset_name = getattr(args, "preset", None)
    if preset_name:
        cfg = get_preset(preset_name)
        if not cfg:
            print(f"Error: Unknown preset '{preset_name}'. Available: {', '.join(POV_PRESETS.keys())}", file=sys.stderr)
            sys.exit(1)
    else:
        existing = read_current_config(cstrike_dir)
        cfg = existing if existing else get_preset("cs2_classic")

    # Apply individual overrides
    if getattr(args, "x", None) is not None:
        cfg.offset_x = args.x
    if getattr(args, "y", None) is not None:
        cfg.offset_y = args.y
    if getattr(args, "z", None) is not None:
        cfg.offset_z = args.z
    if getattr(args, "bob", None) is not None:
        cfg.bobstyle = args.bob
    if getattr(args, "lag", None) is not None:
        cfg.lag_scale = args.lag

    # Validate and clamp
    cfg, warnings = validate_and_clamp(cfg)
    for w in warnings:
        print(f"[Warning] {w}")

    # Output to custom path or apply directly to game
    output_target = getattr(args, "output", None)
    if output_target:
        out_path = Path(output_target)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(export_cfg_string(cfg), encoding="utf-8")
        print(f"\n[Success] POV configuration exported to '{out_path}'.")
    else:
        success = apply_to_game(cstrike_dir, cfg)
        if success:
            print("\n[Success] Modern POV configuration successfully applied!")
            print(f"  Offsets  : X={cfg.offset_x:.2f}, Y={cfg.offset_y:.2f}, Z={cfg.offset_z:.2f}")
            print(f"  Bobstyle : {cfg.bobstyle} ({'CS:GO/CS2 dynamic' if cfg.bobstyle == 2 else 'Vanilla 1.6'})")
            print(f"  Lag Scale: {cfg.lag_scale:.2f}")
            print(f"  Hooked in userconfig.cfg (bind 'f' 'lookatweapon' active)\n")
        else:
            print("Error: Failed to apply POV configuration to game.", file=sys.stderr)
            sys.exit(1)


def cmd_transplant_sleeves(args):
    """Handler for 'transplant-sleeves' command."""
    if not args.weapon and not args.target:
        print("Error: Either -w/--weapon or -t/--target must be specified.", file=sys.stderr)
        sys.exit(1)

    target_path = Path(args.target).resolve() if args.target else resolve_model_path(args.weapon, team=args.team)
    donor_path = Path(args.donor).resolve() if args.donor else None

    print(f"\n[Asset Studio Pro] 3D Sleeve Transplant Engine")
    print(f"Target Model   : {target_path}")
    print(f"Preset / Donor : {args.preset if not donor_path else donor_path}")
    if args.scale is not None:
        print(f"Scale Override : {args.scale:.4f}x")
    if args.cuff_offset != 0.0:
        print(f"Cuff Offset    : {args.cuff_offset:.2f} units")

    result = transplant_3d_sleeves(
        target_model_path=target_path,
        donor_path=donor_path,
        donor_preset=args.preset,
        scale_ratio=args.scale,
        cuff_offset=args.cuff_offset,
        output_path=Path(args.output).resolve() if args.output else None,
        create_backup=not args.no_backup,
        force_save=getattr(args, "force", False),
    )

    if result.get("success"):
        print(f"\n[SUCCESS] {result.get('message')}")
        if result.get("rig_archetype"):
            print(f"Rig Archetype        : {result['rig_archetype']}")
        if result.get("rig_cluster"):
            print(f"Skeletal Rig Cluster : {result['rig_cluster']}")
        if result.get("method"):
            print(f"Execution Method     : {result['method']}")
        if result.get("donor_used"):
            print(f"Donor Model Used     : {Path(result['donor_used']).name}")
        if result.get("scale_ratio"):
            print(f"Applied Scale Ratio  : {result['scale_ratio']:.4f}x ({result.get('scale_description', '')})")
        if result.get("fit_metrics"):
            fit = result["fit_metrics"]
            status = "FLUSH (Seamless)" if fit.get("is_flush") else "Gap Detected"
            print(f"Fit Quality Score    : {fit.get('score', 100)}/100 ({status}) [Left Gap: {fit.get('min_gap_left', 0.0)}u, Right Gap: {fit.get('min_gap_right', 0.0)}u]")
        print()
    else:
        print(f"\n[ERROR] Sleeve transplant failed: {result.get('error')}", file=sys.stderr)
        sys.exit(1)


def cmd_ui(args):
    from .web.server import run_studio_server

    port = args.port or 5160
    url = f"http://127.0.0.1:{port}/"
    print(f"\nLaunching CS 1.6 Asset Studio Web Dashboard at: {url}")
    print("Zero dependencies, runs directly in your default browser.\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    run_studio_server(port=port)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cs16_studio",
        description="CS 1.6 Asset Studio - Modern Skin & Sticker Auto-Injector for Counter-Strike 1.6",
    )
    parser.add_argument("--ui", action="store_true", help="Launch the modern local Web Dashboard in browser")
    parser.add_argument("--port", type=int, default=5160, help="Web dashboard server port (default: 5160)")
    parser.add_argument("--game-dir", default=None, help="Explicit game directory override (default from config.json)")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # ui
    p_ui = subparsers.add_parser("ui", help="Launch the modern local Web Dashboard in browser")
    p_ui.add_argument("--port", type=int, default=5160, help="Web dashboard server port (default: 5160)")

    # info
    p_info = subparsers.add_parser("info", help="Display texture layout and roles for a model")
    p_info.add_argument("-w", "--weapon", required=True, help="Weapon name (e.g. usp, awp, ak47) or model path")
    p_info.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")

    # skin
    p_skin = subparsers.add_parser("skin", help="Inject weapon body skin texture")
    p_skin.add_argument("-w", "--weapon", required=True, help="Weapon name (e.g. usp, awp, ak47) or model path")
    p_skin.add_argument("-i", "--input", required=True, help="Input skin image (PNG, JPG, BMP, WEBP)")
    p_skin.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")
    p_skin.add_argument("--texture", default=None, help="Specific texture name or index (auto-detects if omitted)")
    p_skin.add_argument("--mode", choices=["stretch", "fit"], default="stretch", help="Resize mode (default: stretch)")
    p_skin.add_argument("-o", "--output", default=None, help="Output MDL path (default: in-place)")

    # sticker
    p_sticker = subparsers.add_parser("sticker", help="Inject sticker into 3D submesh slot")
    p_sticker.add_argument("-w", "--weapon", required=True, help="Weapon name or model path")
    p_sticker.add_argument("-i", "--input", required=True, help="Input sticker PNG image")
    p_sticker.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")
    p_sticker.add_argument("--slot", default="1", help="Slot number (1..4) or slot name (e.g. 1.bmp, sticker_1.bmp)")
    p_sticker.add_argument("--mode", choices=["fit", "stretch"], default="fit", help="Resize mode (default: fit)")
    p_sticker.add_argument("--scale", type=float, default=1.0, help="Scale multiplier (default: 1.0)")
    p_sticker.add_argument("--fx", choices=["matte", "foil", "chrome", "glow"], default="matte", help="Visual effect")
    p_sticker.add_argument("-o", "--output", default=None, help="Output MDL path (default: in-place)")

    # batch-sticker
    p_batch = subparsers.add_parser("batch-sticker", help="Batch apply sticker across multiple weapons in 1 command")
    p_batch.add_argument("-w", "--weapons", required=True, help="Comma-separated weapon names (e.g. ak47,m4a1,awp,usp)")
    p_batch.add_argument("-i", "--input", required=True, help="Input sticker PNG image")
    p_batch.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")
    p_batch.add_argument("--slot", default="1", help="Slot number (1..4) or slot name (default: 1)")
    p_batch.add_argument("--mode", choices=["fit", "stretch"], default="fit", help="Resize mode (default: fit)")
    p_batch.add_argument("--scale", type=float, default=1.0, help="Scale multiplier (default: 1.0)")
    p_batch.add_argument("--fx", choices=["matte", "foil", "chrome", "glow"], default="matte", help="Visual effect")

    # bake
    p_bake = subparsers.add_parser("bake", help="Bake sticker directly onto weapon surface (2D composite)")
    p_bake.add_argument("-w", "--weapon", required=True, help="Weapon name or model path")
    p_bake.add_argument("-i", "--input", required=True, help="Input sticker PNG image")
    p_bake.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")
    p_bake.add_argument("--texture", default=None, help="Target weapon skin texture name/index")
    p_bake.add_argument("--preset", default="center", help="Placement preset (silencer, slide, wood, body, mag, stock, center)")
    p_bake.add_argument("--pos", default=None, help="Custom X,Y pixel coordinates on texture canvas (e.g. 250,220)")
    p_bake.add_argument("--scale", type=float, default=1.0, help="Scale factor (default: 1.0)")
    p_bake.add_argument("--rotation", type=float, default=0.0, help="Rotation in degrees (default: 0)")
    p_bake.add_argument("--pre-emphasis", action="store_true", default=True, help="Apply pre-emphasis saturation, contrast & unsharp masking (default: True)")
    p_bake.add_argument("--no-pre-emphasis", action="store_false", dest="pre_emphasis", help="Disable pre-emphasis enhancement")
    p_bake.add_argument("-o", "--output", default=None, help="Output MDL path (default: in-place)")

    # color
    p_color = subparsers.add_parser("color", help="Apply photographic color grading to skin, gloves, or sleeves")
    p_color.add_argument("-w", "--weapon", required=True, help="Weapon name or model path")
    p_color.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")
    p_color.add_argument("--texture", default=None, help="Target texture name or index (defaults to main body skin)")
    p_color.add_argument("--preset", choices=["neutral", "vibrant_cs2", "dark_ops", "warm_golden", "cyber_neon"], default=None, help="Preset style")
    p_color.add_argument("--vibrance", type=float, default=0.0, help="Smart vibrance (-100 to 100)")
    p_color.add_argument("--saturation", type=float, default=0.0, help="Saturation (-100 to 100)")
    p_color.add_argument("--clarity", type=float, default=0.0, help="Clarity & mid-tones (-100 to 100)")
    p_color.add_argument("--contrast", type=float, default=0.0, help="Contrast (-100 to 100)")
    p_color.add_argument("--brightness", type=float, default=0.0, help="Brightness (-100 to 100)")
    p_color.add_argument("--shadows", type=float, default=0.0, help="Shadows boost (-100 to 100)")
    p_color.add_argument("--highlights", type=float, default=0.0, help="Highlights (-100 to 100)")
    p_color.add_argument("--temperature", type=float, default=0.0, help="Color temp (-100 to 100)")
    p_color.add_argument("--tint", type=float, default=0.0, help="Tint (-100 to 100)")
    p_color.add_argument("--hue", type=float, default=0.0, help="Global Hue shift in degrees (-180 to 180)")
    p_color.add_argument("--sharpen", type=float, default=0.0, help="Sharpening (-100 to 100)")

    # stattrak
    p_st = subparsers.add_parser("stattrak", help="Customize StatTrak digital LED counter glow and digits")
    p_st.add_argument("-w", "--weapon", required=True, help="Weapon name or model path")
    p_st.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")
    p_st.add_argument("--color", choices=["orange", "cyan", "red", "green", "violet"], default="orange", help="LED glow color")
    p_st.add_argument("--number", default=None, help="Custom counter digits (e.g. 001337)")

    # wear
    p_wear = subparsers.add_parser("wear", help="Apply procedural wear and scratches (Factory New -> Battle-Scarred)")
    p_wear.add_argument("-w", "--weapon", required=True, help="Weapon name or model path")
    p_wear.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")
    p_wear.add_argument("--texture", default=None, help="Target skin texture name/index (auto-detects if omitted)")
    p_wear.add_argument("--float", type=float, default=0.35, dest="wear_float", help="Float value 0.00 to 1.00 (default: 0.35)")
    p_wear.add_argument("--seed", type=int, default=1337, help="Deterministic scratch seed (default: 1337)")

    # transfer-gloves
    p_glove = subparsers.add_parser("transfer-gloves", help="Synchronize glove and sleeve textures between weapons")
    p_glove.add_argument("-s", "--source", required=True, help="Source weapon model with desired gloves (e.g. usp)")
    p_glove.add_argument("-t", "--target", default="all", help="Target weapon(s) comma-separated, or 'all' (default: all)")
    p_glove.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")
    p_glove.add_argument("--no-sleeves", action="store_true", help="Exclude sleeve/arm textures from synchronization")

    # chrome
    p_chrome = subparsers.add_parser("chrome", help="Toggle STUDIO_NF_CHROME (0x02) flag for metallic environment shine")
    p_chrome.add_argument("-w", "--weapon", required=True, help="Weapon name or model path")
    p_chrome.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")
    p_chrome.add_argument("--slot", required=True, help="Texture name or index to toggle")
    p_chrome.add_argument("--enable", action="store_true", default=None, help="Force enable chrome")
    p_chrome.add_argument("--disable", action="store_true", default=None, help="Force disable chrome")

    # revert
    p_revert = subparsers.add_parser("revert", help="Revert a single texture slot to backup")
    p_revert.add_argument("-w", "--weapon", required=True, help="Weapon name or model path")
    p_revert.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")
    p_revert.add_argument("--slot", required=True, help="Slot name or index to revert")

    # restore
    p_restore = subparsers.add_parser("restore", help="Restore weapon models (V, P, W) from backup (.orig.mdl / .bak)")
    p_restore.add_argument("-w", "--weapon", required=True, help="Weapon name (e.g. ak47, usp, awp) or model path")
    p_restore.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")
    p_restore.add_argument(
        "--scope",
        choices=["all", "pw", "v", "p", "w"],
        default="all",
        help="Scope of models to restore: 'all' (V+P+W, default), 'pw' (Player & World), 'v' (Viewmodel only), 'p', 'w'",
    )
    p_restore.add_argument("--v-only", action="store_true", help="Shortcut for --scope v (restore viewmodel only)")
    p_restore.add_argument("--pw-only", action="store_true", help="Shortcut for --scope pw (restore P & W models only)")
    p_restore.add_argument("--all", action="store_true", dest="restore_all", help="Explicitly restore all models (V+P+W)")

    # clean-backups
    p_clean = subparsers.add_parser("clean-backups", help="Move loose .orig.mdl and .bak files into dedicated backup/ subfolders")
    p_clean.add_argument("--cstrike", default=None, help="Optional game root or cstrike directory")

    # pov
    p_pov = subparsers.add_parser("pov", help="Configure first-person viewmodel camera (Modern CS POV)")
    p_pov.add_argument(
        "--preset",
        type=str.lower,
        choices=list(POV_PRESETS.keys()),
        default=None,
        help="Apply a predefined viewmodel POV preset (cs2_classic, csgo_desktop, couch, quake_centered, vanilla_16)",
    )
    p_pov.add_argument("--status", action="store_true", help="Display active POV configuration from modern_pov.cfg")
    p_pov.add_argument("--reset", action="store_true", help="Reset viewmodel POV configuration to vanilla CS 1.6 defaults")
    p_pov.add_argument("--x", type=float, default=None, help="Viewmodel X translation offset [-2.5 to 2.5] (right/left)")
    p_pov.add_argument("--y", type=float, default=None, help="Viewmodel Y translation offset [-2.0 to 2.0] (forward/back)")
    p_pov.add_argument("--z", type=float, default=None, help="Viewmodel Z translation offset [-2.0 to 2.0] (up/down)")
    p_pov.add_argument("--bob", type=int, choices=[0, 2], default=None, help="Bobbing style: 0=Vanilla 1.6, 2=CS:GO/CS2 dynamic")
    p_pov.add_argument("--lag", type=float, default=None, help="Weapon inertia lag scale (e.g. 1.5)")
    p_pov.add_argument("-o", "--output", default=None, help="Output custom CFG path (default: in-place cstrike/modern_pov.cfg)")
    p_pov.add_argument("--cstrike", default=None, help="Path to cstrike directory or game root (default: auto-detected)")

    # transplant-sleeves
    p_sleeve = subparsers.add_parser("transplant-sleeves", help="Transplant 3D sleeves/arms from donor model or preset")
    p_sleeve.add_argument("-w", "--weapon", default=None, help="Weapon name (e.g. knife, ak47, usp) or use -t/--target")
    p_sleeve.add_argument("-t", "--target", default=None, help="Direct path to target .mdl file")
    p_sleeve.add_argument("--team", choices=["ct", "t"], default="ct", help="Team loadout (default: ct)")
    p_sleeve.add_argument("-d", "--donor", default=None, help="Direct path to donor .mdl file")
    p_sleeve.add_argument("--preset", choices=list(SLEEVE_PRESETS.keys()), default="sas_navy", help="Sleeve preset (default: sas_navy)")
    p_sleeve.add_argument("--scale", type=float, default=None, help="Scale multiplier override (default: auto bone ratio)")
    p_sleeve.add_argument("--cuff-offset", type=float, default=0.0, help="Wrist cuff longitudinal offset along forearm bone (default: 0.0)")
    p_sleeve.add_argument("-o", "--output", default=None, help="Output MDL path (default: in-place)")
    p_sleeve.add_argument("--no-backup", action="store_true", help="Do not create a backup file")
    p_sleeve.add_argument("--force", action="store_true", help="Force save even if safety check detects fit gaps")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Handle explicit game-dir override
    if getattr(args, "game_dir", None):
        StudioConfig.get_instance().set_game_root(args.game_dir)

    if args.ui or args.command == "ui":
        cmd_ui(args)
        return

    if not args.command:
        print_banner()
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "info": cmd_info,
        "skin": cmd_skin,
        "sticker": cmd_sticker,
        "batch-sticker": cmd_batch_sticker,
        "bake": cmd_bake,
        "color": cmd_color,
        "stattrak": cmd_stattrak,
        "wear": cmd_wear,
        "transfer-gloves": cmd_transfer_gloves,
        "chrome": cmd_chrome,
        "revert": cmd_revert,
        "restore": cmd_restore,
        "clean-backups": cmd_clean_backups,
        "pov": cmd_pov,
        "transplant-sleeves": cmd_transplant_sleeves,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
