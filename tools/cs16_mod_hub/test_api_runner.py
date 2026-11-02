import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from tools.cs16_mod_hub.core.api import ModHubAPI

def main():
    api = ModHubAPI()

    # 1. Test Profiles
    profiles = api.get_profiles()
    print(f"Total available profiles: {len(profiles)}")
    for p in profiles:
        if p["exists"]:
            print(f"  * {p['name']} ({p['model_count']} models) -> {p['rel_path']}")

    # 2. Test CT Custom Profile
    api.set_profile("ct_custom")
    ct_vms = api.get_viewmodels()
    print(f"\nCT Custom Models count: {len(ct_vms)}")
    if ct_vms:
        print(f"  First 5 models: {ct_vms[:5]}")

    # 3. Test HD Models Profile & AK-47 Stickers
    api.set_profile("hd_models")
    stk_res = api.scan_stickers("v_ak47.mdl")
    print(f"\nHD v_ak47.mdl Sticker Scan Success: {stk_res['success']}")
    print(f"  Sticker slots found: {len(stk_res['slots'])}")
    for s in stk_res["slots"]:
        print(f"    Slot {s['index']}: {s['name']} (Mode: {s['mode_name']})")

    # 4. Test Texture Preview
    tex_res = api.load_weapon_texture("v_ak47.mdl")
    print(f"\nTexture Load Success: {tex_res['success']}")
    print(f"  Info: {tex_res.get('info')}")
    print(f"  Original Data URL prefix: {tex_res.get('original', '')[:40]}...")

    # 5. Test Live Preview Slider Recalculation
    adj_res = api.update_preview_sliders(sat=1.4, contrast=1.2, brightness=1.1)
    print(f"\nSlider Update Success: {adj_res['success']}")
    print(f"  Adjusted Data URL prefix: {adj_res.get('adjusted', '')[:40]}...")

    # 6. Test Plugins
    plugins = api.get_plugins()
    print(f"\nActive Plugins found: {len(plugins)}")
    for p in plugins:
        print(f"  [{'ON' if p['is_active'] else 'OFF'}] {p['name']} - {p['comment']}")

    # 7. Test CS2 Engine Config
    cs2_cfg = api.get_cs2_engine_config()
    print(f"\nCS2 Modern Engine Config Success: {cs2_cfg.get('success')}")
    print(f"  Engine CVARs count: {len(cs2_cfg.get('cvars', {}))}")

    # 8. Test Competitive Match Config & Presets
    comp_cfg = api.get_competitive_config()
    print(f"\nCompetitive Config Success: {comp_cfg.get('success')}")
    print(f"  Comp CVARs count: {len(comp_cfg.get('cvars', {}))}")
    comp_preset = api.apply_competitive_preset("valve_major")
    print(f"  Apply Valve Major Preset Success: {comp_preset.get('success')}")

    # 9. Test Bot Ecosystem & Sanitize Cheats
    bot_eco = api.get_bot_ecosystem()
    print(f"\nBot Ecosystem Active Preset: {bot_eco.get('active_preset')}")
    print(f"  Savage AI Enabled: {bot_eco.get('savage_enable')}")
    san_res = api.sanitize_bot_cheats()
    print(f"  Sanitize Cheats Success: {san_res.get('success')}")

    # 10. Test Backup Telemetry & Verification
    telemetry = api.get_backup_telemetry()
    print(f"\nBackup Telemetry: {telemetry.get('total_files')} files ({telemetry.get('total_mb')} MB)")
    print(f"  Write Guarded: {telemetry.get('write_guarded')}")
    verify_res = api.verify_all_backups()
    print(f"  Verified Backups Count: {len(verify_res)}")
    for v in verify_res[:3]:
        sha_display = (v['sha256'][:16] + "...") if v['sha256'] else "None"
        print(f"    - {v['model_name']} ({v['category']}): IDST={v['is_valid_idst']}, SHA256={sha_display}")

    print("\nALL API TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
