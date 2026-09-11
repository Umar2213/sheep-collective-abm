import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from merge_shards import merge_shards


class MergeShardTests(unittest.TestCase):
    def _write_production_shard(self, root, idx, sigma, duplicate=False):
        directory = root / f"shard_{idx:03d}_of_002"
        directory.mkdir(parents=True)
        (directory / "run_metadata.toml").write_text(
            "\n".join([
                'experiment = "production"',
                f"shard_index = {idx}",
                "shard_count = 2",
                "full_condition_count = 2",
                "trait_replicates = 1",
                "dynamic_replicates = 2",
                "full_run_count = 4",
                'sigma = [0.0, 0.3]',
                'noise = [0.5]',
                'recorded_utc = "2026-09-11T00:00:0' + str(idx) + '"',
                'threads = ' + str(idx),
            ]) + "\n",
            encoding="utf-8",
        )
        sigma_value = 0.0 if duplicate else sigma
        pd.DataFrame({
            "sigma_std": [sigma_value, sigma_value],
            "noise": [0.5, 0.5],
            "trait_rep": [1, 1],
            "dynamic_rep": [1, 2],
            "phi": [0.9 - 0.1 * idx, 0.89 - 0.1 * idx],
        }).to_csv(directory / "sweep_replicates.csv", index=False)
        pd.DataFrame({
            "sigma_std": [sigma_value],
            "noise": [0.5],
            "phi_mean": [0.895 - 0.1 * idx],
        }).to_csv(directory / "sweep_condition_means.csv", index=False)

    def _write_distribution_shard(self, root, idx, sigma, duplicate_pair=False):
        directory = root / f"shard_{idx:03d}_of_002"
        directory.mkdir(parents=True)
        (directory / "run_metadata.toml").write_text(
            "\n".join([
                'experiment = "distribution_controls"',
                f"shard_index = {idx}",
                "shard_count = 2",
                "full_condition_count = 2",
                "full_run_count = 4",
                "sigma = [0.1, 0.3]",
                "noise = [0.5]",
                "trait_replicates = 1",
                "dynamic_replicates = 1",
                'trait_families = ["beta", "two_point"]',
            ]) + "\n",
            encoding="utf-8",
        )
        pd.DataFrame({
            "sigma_std": [sigma, sigma],
            "noise": [0.5, 0.5],
            "trait_distribution": ["beta", "two_point"],
            "trait_rep": [1, 1],
            "dynamic_rep": [1, 1],
            "phi": [0.9 - 0.1 * idx, 0.88 - 0.1 * idx],
        }).to_csv(directory / "distribution_replicates.csv", index=False)
        pd.DataFrame({
            "sigma_std": [sigma, sigma],
            "noise": [0.5, 0.5],
            "trait_distribution": ["beta", "two_point"],
            "phi_mean": [0.9 - 0.1 * idx, 0.88 - 0.1 * idx],
        }).to_csv(directory / "distribution_condition_means.csv", index=False)
        pair_sigma = 0.0 if duplicate_pair else sigma
        pd.DataFrame({
            "sigma_std": [pair_sigma],
            "noise": [0.5],
            "trait_rep": [1],
            "dynamic_rep": [1],
            "phi_beta": [0.9 - 0.1 * idx],
            "phi_two_point": [0.88 - 0.1 * idx],
            "delta_phi": [-0.02],
        }).to_csv(directory / "paired_distribution_effects.csv", index=False)
        pd.DataFrame({
            "sigma_std": [pair_sigma],
            "noise": [0.5],
            "delta_phi_mean": [-0.02],
            "n": [1],
        }).to_csv(directory / "paired_distribution_summary.csv", index=False)

    def test_complete_production_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_production_shard(root, 1, 0.0)
            self._write_production_shard(root, 2, 0.3)
            report = merge_shards(root, "production")
            self.assertEqual(report["replicate_rows"], 4)
            self.assertEqual(report["condition_summary_rows"], 2)
            merged = pd.read_csv(root / "merged" / "sweep_replicates.csv")
            self.assertEqual(len(merged), 4)
            self.assertEqual(sorted(merged.sigma_std.unique().tolist()), [0.0, 0.3])
            self.assertTrue((root / "merged" / "merge_report.json").exists())

    def test_missing_shard_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_production_shard(root, 1, 0.0)
            with self.assertRaisesRegex(ValueError, "Incomplete shard set"):
                merge_shards(root, "production")

    def test_duplicate_condition_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_production_shard(root, 1, 0.0)
            self._write_production_shard(root, 2, 0.3, duplicate=True)
            with self.assertRaisesRegex(ValueError, "Duplicate (condition summaries|replicate keys)"):
                merge_shards(root, "production")

    def test_distribution_merge_includes_paired_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_distribution_shard(root, 1, 0.1)
            self._write_distribution_shard(root, 2, 0.3)
            report = merge_shards(root, "distribution_controls")
            self.assertEqual(report["replicate_rows"], 4)
            self.assertEqual(report["condition_summary_rows"], 4)
            self.assertEqual(report["supplemental_rows"]["paired_distribution_effects.csv"], 2)
            self.assertEqual(report["supplemental_rows"]["paired_distribution_summary.csv"], 2)
            pairs = pd.read_csv(root / "merged" / "paired_distribution_effects.csv")
            self.assertEqual(sorted(pairs.sigma_std.tolist()), [0.1, 0.3])

    def test_duplicate_supplemental_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_distribution_shard(root, 1, 0.1, duplicate_pair=True)
            self._write_distribution_shard(root, 2, 0.3, duplicate_pair=True)
            with self.assertRaisesRegex(ValueError, "Duplicate keys found in paired_distribution_effects"):
                merge_shards(root, "distribution_controls")

    def test_wrong_replicate_id_with_correct_row_count_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_production_shard(root, 1, 0.0)
            self._write_production_shard(root, 2, 0.3)
            path = root / "shard_002_of_002/sweep_replicates.csv"
            frame = pd.read_csv(path)
            frame.loc[0, "dynamic_rep"] = 99
            frame.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "design keys"):
                merge_shards(root, "production")
            self.assertFalse((root / "merged").exists())

    def test_failed_supplemental_leaves_no_partial_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_distribution_shard(root, 1, 0.1)
            self._write_distribution_shard(root, 2, 0.3)
            (root / "shard_002_of_002/paired_distribution_summary.csv").unlink()
            with self.assertRaisesRegex(ValueError, "Missing required shard file"):
                merge_shards(root, "distribution_controls")
            self.assertFalse((root / "merged").exists())

    def test_stale_summary_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_production_shard(root, 1, 0.0)
            self._write_production_shard(root, 2, 0.3)
            path = root / "shard_002_of_002/sweep_condition_means.csv"
            frame = pd.read_csv(path)
            frame.loc[0, "phi_mean"] = 0.1
            frame.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "does not reproduce"):
                merge_shards(root, "production")

    def test_scientific_metadata_difference_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_production_shard(root, 1, 0.0)
            self._write_production_shard(root, 2, 0.3)
            path = root / "shard_002_of_002/run_metadata.toml"
            path.write_text(path.read_text() + 'git_commit = "different"\n')
            with self.assertRaisesRegex(ValueError, "inconsistent"):
                merge_shards(root, "production")


if __name__ == "__main__":
    unittest.main()
