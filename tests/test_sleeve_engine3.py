import unittest
import shutil
from pathlib import Path
import sys

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.cs16_studio.sleeve_injector import (
    SkeletalCluster,
    detect_skeletal_cluster,
    resolve_archetype_donor,
    classify_rig_archetype,
    compute_bone_bind_matrices,
    transplant_3d_sleeves,
    validate_sleeve_fit,
    SLEEVE_PRESETS,
)
from scripts.cs16_studio.slot_geometry import validate_model_health


class TestSleeveEngine3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ct_dir = Path(r"D:\Counter-Strike 1.6\Counter-Strike 1.6 Original\cstrike\models\custom_skins\ct")
        cls.game_root = Path(r"D:\Counter-Strike 1.6\Counter-Strike 1.6 Original")
        if not cls.ct_dir.is_dir():
            raise unittest.SkipTest(f"Game CT models directory not found: {cls.ct_dir}")

    def test_01_skeletal_cluster_detection(self):
        """Verify dynamic cluster detection distinguishes Cluster 24, 10, and Knife."""
        models_expected = [
            ("v_ak47.mdl", SkeletalCluster.CLUSTER_24),
            ("v_awp.mdl", SkeletalCluster.CLUSTER_24),
            ("v_galil.mdl", SkeletalCluster.CLUSTER_24),
            ("v_aug.mdl", SkeletalCluster.CLUSTER_24),
            ("v_m4a1.mdl", SkeletalCluster.CLUSTER_10),
            ("v_xm1014.mdl", SkeletalCluster.CLUSTER_10),
            ("v_knife_butterfly.mdl", SkeletalCluster.CLUSTER_KNIFE),
            ("v_knife.mdl", SkeletalCluster.CLUSTER_KNIFE),
        ]
        for mname, expected_cluster in models_expected:
            p = self.ct_dir / mname
            if not p.is_file():
                continue
            data = p.read_bytes()
            bones, _ = compute_bone_bind_matrices(data)
            detected = detect_skeletal_cluster(bones, data, mname)
            self.assertEqual(
                detected,
                expected_cluster,
                f"Model {mname} expected cluster {expected_cluster}, got {detected}",
            )

    def test_02_cluster_aware_donor_resolution(self):
        """Verify donor resolution picks a matching skeletal cluster donor."""
        # 1. AK-47 must resolve to a Cluster 24 donor (NOT v_m4a1)
        ak_p = self.ct_dir / "v_ak47.mdl"
        ak_data = ak_p.read_bytes()
        ak_bones, _ = compute_bone_bind_matrices(ak_data)
        ak_cluster = detect_skeletal_cluster(ak_bones, ak_data, ak_p.name)
        ak_archetype = classify_rig_archetype(ak_bones, ak_p.name)

        donor_ak = resolve_archetype_donor(
            target_path=ak_p,
            archetype=ak_archetype,
            cluster=ak_cluster,
            target_bones=ak_bones,
            root=self.game_root,
        )
        self.assertNotEqual(donor_ak.name.lower(), "v_m4a1.mdl", "AK-47 must NOT be assigned v_m4a1 (10.3) as donor!")
        self.assertIn(donor_ak.name.lower(), ["v_galil.mdl", "v_aug.mdl", "v_scout.mdl", "v_usp.mdl"])

        # 2. M4A1 must resolve to a Cluster 10 donor
        m4_p = self.ct_dir / "v_m4a1.mdl"
        m4_data = m4_p.read_bytes()
        m4_bones, _ = compute_bone_bind_matrices(m4_data)
        m4_cluster = detect_skeletal_cluster(m4_bones, m4_data, m4_p.name)
        m4_archetype = classify_rig_archetype(m4_bones, m4_p.name)

        donor_m4 = resolve_archetype_donor(
            target_path=m4_p,
            archetype=m4_archetype,
            cluster=m4_cluster,
            target_bones=m4_bones,
            root=self.game_root,
        )
        self.assertIn(donor_m4.name.lower(), ["v_xm1014.mdl", "v_m3.mdl", "v_famas.mdl"])

        # 3. Knife must resolve to Knife donor
        bf_p = self.ct_dir / "v_knife_butterfly.mdl"
        bf_data = bf_p.read_bytes()
        bf_bones, _ = compute_bone_bind_matrices(bf_data)
        bf_cluster = detect_skeletal_cluster(bf_bones, bf_data, bf_p.name)
        bf_archetype = classify_rig_archetype(bf_bones, bf_p.name)

        donor_bf = resolve_archetype_donor(
            target_path=bf_p,
            archetype=bf_archetype,
            cluster=bf_cluster,
            target_bones=bf_bones,
            root=self.game_root,
        )
        self.assertIn(donor_bf.name.lower(), ["v_knife_m9.mdl", "v_knife.mdl", "v_knife_bayonet.mdl"])

    def test_03_transplant_ak47_preserves_flush_geometry(self):
        """Verify transplanting SAS Navy preset to AK-47 yields 100/100 fit score."""
        src_ak = self.ct_dir / "v_ak47.mdl"
        temp_ak = self.ct_dir / "v_ak47_unittest_tmp.mdl"
        shutil.copy2(src_ak, temp_ak)

        try:
            res = transplant_3d_sleeves(
                target_path=temp_ak,
                sleeve_preset="gign_urban",
                create_backup=False,
                root_dir=self.game_root,
            )
            self.assertTrue(res.get("success"), f"Transplant failed: {res.get('error')}")
            self.assertIn(res.get("method"), ["native_identity_splice", "adaptive_cross_rig"])
            self.assertEqual(res.get("rig_cluster"), SkeletalCluster.CLUSTER_24)

            fit = res.get("fit_metrics", {})
            self.assertTrue(fit.get("is_flush"), f"AK-47 not flush: {fit}")
            self.assertEqual(fit.get("score"), 100, f"Score < 100: {fit}")
            self.assertLess(fit.get("min_gap_left", 999), 0.15)
            self.assertLess(fit.get("min_gap_right", 999), 0.15)

            health = validate_model_health(temp_ak)
            self.assertTrue(health.get("healthy"))
            self.assertEqual(health.get("score"), 100)
        finally:
            if temp_ak.exists():
                temp_ak.unlink()

    def test_04_transplant_awp_preserves_flush_geometry(self):
        """Verify transplanting Arctic Parka preset to AWP yields 100/100 fit score."""
        src_awp = self.ct_dir / "v_awp.mdl"
        temp_awp = self.ct_dir / "v_awp_unittest_tmp.mdl"
        shutil.copy2(src_awp, temp_awp)

        try:
            res = transplant_3d_sleeves(
                target_path=temp_awp,
                sleeve_preset="arctic_parka",
                create_backup=False,
                root_dir=self.game_root,
            )
            self.assertTrue(res.get("success"), f"Transplant failed: {res.get('error')}")
            self.assertIn(res.get("method"), ["native_identity_splice", "adaptive_cross_rig"])
            self.assertEqual(res.get("rig_cluster"), SkeletalCluster.CLUSTER_24)

            fit = res.get("fit_metrics", {})
            self.assertTrue(fit.get("is_flush"), f"AWP not flush: {fit}")
            self.assertEqual(fit.get("score"), 100, f"Score < 100: {fit}")
            self.assertLess(fit.get("min_gap_left", 999), 0.15)
            self.assertLess(fit.get("min_gap_right", 999), 0.15)
        finally:
            if temp_awp.exists():
                temp_awp.unlink()

    def test_05_transplant_knife_butterfly(self):
        """Verify transplanting to knife butterfly yields 100/100 fit score."""
        src_bf = self.ct_dir / "v_knife_butterfly.mdl"
        temp_bf = self.ct_dir / "v_knife_bf_unittest_tmp.mdl"
        shutil.copy2(src_bf, temp_bf)

        try:
            res = transplant_3d_sleeves(
                target_path=temp_bf,
                sleeve_preset="sas_navy",
                create_backup=False,
                root_dir=self.game_root,
            )
            self.assertTrue(res.get("success"), f"Transplant failed: {res.get('error')}")
            fit = res.get("fit_metrics", {})
            self.assertTrue(fit.get("is_flush"), f"Butterfly not flush: {fit}")
            self.assertEqual(fit.get("score"), 100)
        finally:
            if temp_bf.exists():
                temp_bf.unlink()


if __name__ == "__main__":
    unittest.main()
