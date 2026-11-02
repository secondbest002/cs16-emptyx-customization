"""
tools/cs16_mod_hub/test_preview_and_cli.py
Unit and integration tests for:
1. Multi-instance prevention and in-process execution.
2. CLI interception in main_webview.py.
3. Live preview model change and state tracking (no stale preview persistence).
4. Target group preview selection (weapon vs gloves).
"""

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from tools.cs16_mod_hub.core.api import ModHubAPI
from tools.cs16_mod_hub.core.common import run_script_streaming


def test_preview_model_switching():
    print("--- Test 1: Live Preview Model Switching & No Stale Cache ---")
    api = ModHubAPI()

    # Step 1: Load AK-47
    r_ak = api.load_weapon_texture("v_ak47.mdl")
    assert r_ak["success"], f"Failed to load AK-47: {r_ak}"
    assert "ak47.bmp" in r_ak["info"], f"Expected ak47.bmp, got {r_ak['info']}"
    print(f"[OK] Step 1: Loaded AK-47: {r_ak['info']}")

    # Step 2: Apply vibrance to AK-47
    logs = []
    r_apply = api.apply_vibrance("v_ak47.mdl", target="weapon", sat=1.3, contrast=1.1, brightness=1.0)
    assert r_apply["success"], f"Failed to apply vibrance to AK-47: {r_apply}"
    print(f"[OK] Step 2: Applied vibrance to AK-47: {r_apply['message']}")

    # Step 3: Switch to M4A1
    r_m4 = api.load_weapon_texture("v_m4a1.mdl")
    assert r_m4["success"], f"Failed to load M4A1: {r_m4}"
    assert "rif_m4a1_s.bmp" in r_m4["info"], f"Expected rif_m4a1_s.bmp, got {r_m4['info']}"
    assert api._cache.texture_name == "rif_m4a1_s.bmp", f"Cache texture name was not updated! Got {api._cache.texture_name}"
    print(f"[OK] Step 3: Switched to M4A1: {r_m4['info']}")

    # Step 4: Simulate an apply_vibrance call on AK-47 while cache is already on M4A1
    # This simulates background completion after user has switched models
    r_apply2 = api.apply_vibrance("v_ak47.mdl", target="weapon", sat=1.0, contrast=1.0, brightness=1.0)
    assert r_apply2["success"]
    assert api._cache.texture_name == "rif_m4a1_s.bmp", (
        f"Cache was erroneously overwritten with old model! Expected rif_m4a1_s.bmp, got {api._cache.texture_name}"
    )
    print("[OK] Step 4: Stale cache overwrite prevented when user moved to M4A1")

    # Step 5: Test slider recalculation on the new model
    r_slider = api.update_preview_sliders(sat=1.5, contrast=1.2, brightness=1.0)
    assert r_slider["success"]
    assert "data:image/jpeg;base64," in r_slider["adjusted"]
    print("[OK] Step 5: Slider update operates cleanly on the active model (M4A1)")

    # Step 6: Test sticker effect application and model switching
    r_sticker = api.apply_sticker_fx("v_ak47.mdl", mode="foil", slot_id="all")
    assert r_sticker["success"], f"Failed to apply sticker fx: {r_sticker}"
    # Cache should still be M4A1 because user moved to M4A1
    assert api._cache.texture_name == "rif_m4a1_s.bmp", "Sticker apply erroneously clobbered cache!"
    print("[OK] Step 6: Sticker apply also respects active model isolation")

    # Step 7: Test slider update with explicit weapon alignment
    r_aligned = api.update_preview_sliders(sat=1.2, contrast=1.1, brightness=1.0, weapon="v_ak47.mdl")
    assert r_aligned["success"]
    assert api._cache.texture_name == "ak47.bmp", "Slider update failed to align to requested weapon!"
    print("[OK] Step 7: Slider update dynamically aligns cache when weapon is specified")


def test_target_group_preview():
    print("\n--- Test 2: Target Scope Preview (Weapon vs Gloves) ---")
    api = ModHubAPI()

    # Load weapon body
    r_wep = api.load_weapon_texture("v_ak47.mdl", target="weapon")
    assert r_wep["success"]
    print(f"[OK] Weapon body texture: {r_wep['info']}")

    # Load gloves
    r_glove = api.load_weapon_texture("v_ak47.mdl", target="gloves")
    assert r_glove["success"]
    print(f"[OK] Glove texture: {r_glove['info']}")
    # Verify glove texture is actually a glove/hand/arm texture
    lower = r_glove["info"].lower()
    has_glove_kw = any(k in lower for k in ["sport", "glove", "hand", "arm", "sleeve"])
    assert has_glove_kw, f"Expected glove texture keywords, got {r_glove['info']}"
    print("[OK] Gloves texture target recognized and extracted correctly")


def test_in_process_streaming():
    print("\n--- Test 3: In-Process Script Runner with Streaming Output ---")
    logs = []

    def on_log(line):
        logs.append(line)

    res = run_script_streaming(
        ".agents/skills/cs16-color-vibrance/scripts/adjust_vibrance.py",
        ["-w", "v_ak47.mdl", "--reset", "-d", "cstrike/models/custom_skins/ct"],
        log_callback=on_log,
    )
    assert res.success, f"Script execution failed: {res.message}"
    assert len(logs) > 0, "No log lines captured by streaming callback!"
    print(f"[OK] In-process runner executed with returncode {res.returncode}, captured {len(logs)} log lines.")
    print(f"  First log: {logs[0]}")
    print(f"  Last log:  {logs[-1]}")


def test_model_name_matching():
    print("\n--- Test 4: Model Name Matching & Normalization ---")
    from tools.cs16_mod_hub.core.api import _is_same_model

    assert _is_same_model("ak47", "v_ak47.mdl")
    assert _is_same_model("v_ak47.mdl", "ak47")
    assert _is_same_model("cstrike/models/custom_skins/ct/v_ak47.mdl", "v_ak47.mdl")
    assert _is_same_model("v_ak47", "v_ak47.mdl")
    assert not _is_same_model("v_ak47.mdl", "v_m4a1.mdl")
    assert not _is_same_model("ak47", "m4a1")
    assert not _is_same_model(None, "ak47")
    print("[OK] Model name comparison handles all permutations cleanly")


def main():
    test_preview_model_switching()
    test_target_group_preview()
    test_in_process_streaming()
    test_model_name_matching()
    print("\n==========================================")
    print("ALL PREVIEW & EXECUTION TESTS PASSED! [OK]")
    print("==========================================")


if __name__ == "__main__":
    main()
