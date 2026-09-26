import json
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from trajectory_pipeline import (AnalysisConfig, prepare_trajectories, construct_features,
    make_folds, validate_ties, shuffled_ties, fit_predict, run_pipeline, movement_summary)
from generate_demo import generate
from run_analysis import publish_result, digest


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.ties, cls.truth = generate(groups=2, sessions=2, animals=3, steps=20)
        cls.config = AnalysisConfig(n_folds=2, n_bootstrap=100, shuffle_seeds=(11,), ties_independent=True)
        cls.result = run_pipeline(cls.data, cls.config, cls.ties)

    def test_full_pipeline_matched_keys_and_biological_clusters(self):
        r = self.result
        self.assertEqual(r["scores"].group_id.nunique(), 2)
        models = set(r["predictions"].model)
        self.assertEqual(models, {"persistence", "constant_turn", "M0", "M1", "M2", "M3", "distance", "shuffle_11"})
        counts = r["predictions"].groupby("model").size()
        self.assertEqual(counts.nunique(), 1)
        self.assertTrue((r["predictions"].timestamp > r["predictions"].predictor_timestamp).all())
        self.assertTrue((r["comparisons"].n_blocks == 2).all())
        pairs = set(zip(r["comparisons"].reference, r["comparisons"].alternative))
        self.assertTrue({("M0", "M2"), ("distance", "M2"), ("M0", "M3"), ("M1", "M3"), ("M2", "M3")} <= pairs)

    def test_known_speed_and_alignment(self):
        rows = []
        for i in range(2):
            for t in range(4):
                rows.append(dict(group_id="g", bout_id="b", individual_id=str(i), timestamp=f"2026-01-01T00:00:0{t}Z", x=t, y=i*2))
        d, _ = prepare_trajectories(pd.DataFrame(rows), self.config)
        np.testing.assert_allclose(d.speed.dropna(), 1)
        m = movement_summary(d)
        np.testing.assert_allclose(m.alignment.dropna(), 1)
        np.testing.assert_allclose(m.spread_m, 1)

    def test_poor_fix_does_not_bridge(self):
        data = self.data.copy()
        data["accuracy_m"] = 0.0
        data.loc[3, "accuracy_m"] = 100
        prepared, audit = prepare_trajectories(data, self.config)
        row = data.iloc[3]
        own = prepared[(prepared.group_id == row.group_id) & (prepared.bout_id == row.bout_id) & (prepared.individual_id == row.individual_id)]
        bad = pd.Timestamp(row.timestamp)
        self.assertFalse(own.loc[own.timestamp == bad, "interval_usable"].iloc[0])
        self.assertFalse(own.loc[own.previous_time == bad, "interval_usable"].iloc[0])
        self.assertEqual(audit["filters"]["poor_accuracy_fixes"], 1)

    def test_timezones_and_duplicate_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            prepare_trajectories(self.data.assign(timestamp="2026-01-01T00:00:00"), self.config)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            prepare_trajectories(pd.concat([self.data, self.data.iloc[[0]]]), self.config)

    def test_gps_projection_known_central_meridian(self):
        frame = self.data.copy()
        frame["longitude"] = 3.0
        frame["latitude"] = 0.0
        d, _ = prepare_trajectories(frame, replace(self.config, coordinate_mode="gps", crs="EPSG:32631"))
        np.testing.assert_allclose(d.x, 500000, atol=1e-6)
        np.testing.assert_allclose(d.y, 0, atol=1e-6)
        with self.assertRaisesRegex(ValueError, "projected"):
            prepare_trajectories(frame, replace(self.config, coordinate_mode="gps", crs="EPSG:4326"))

    def test_frozen_folds_invariant_and_wrong_coverage_rejected(self):
        folds = self.result["folds"]
        again = make_folds(self.data.sample(frac=1, random_state=2), self.config, folds)
        pd.testing.assert_frame_equal(folds.sort_values(["group_id", "bout_id"]).reset_index(drop=True), again)
        with self.assertRaisesRegex(ValueError, "coverage|populate"):
            make_folds(self.data, self.config, folds.iloc[:-1])

    def test_tie_independence_completeness_and_shuffle_reproducibility(self):
        with self.assertRaisesRegex(ValueError, "independent"):
            validate_ties(self.ties, self.data, replace(self.config, ties_independent=False))
        with self.assertRaisesRegex(ValueError, "every directed"):
            validate_ties(self.ties.iloc[1:], self.data, self.config)
        lookup = validate_ties(self.ties, self.data, self.config)
        a = shuffled_ties(lookup, self.data, 11)
        self.assertEqual(a, shuffled_ties(lookup, self.data, 11))
        self.assertEqual(sorted(a.values()), sorted(lookup.values()))
        self.assertNotEqual(a, lookup)

    def test_holdout_target_cannot_change_its_training_parameters(self):
        features = self.result["features"].copy()
        folds = self.result["folds"]
        joined = features.merge(folds, on=["group_id", "bout_id"])
        changed = features.copy()
        mask = joined.fold.to_numpy() == 0
        changed.loc[mask, "observed_heading"] += .4
        _, params = fit_predict(changed, folds, self.config, True)
        before = self.result["parameters"]
        pd.testing.assert_frame_equal(before[before.fold == 0].reset_index(drop=True), params[params.fold == 0].reset_index(drop=True))

    def test_radius_sensitivity_uses_identical_observations(self):
        prepared = self.result["prepared"]
        lookup = validate_ties(self.ties, prepared, self.config)
        a, _ = construct_features(prepared, self.config, lookup)
        b, _ = construct_features(prepared, replace(self.config, radius=.001), lookup)
        keys = ["group_id", "bout_id", "individual_id", "timestamp"]
        pd.testing.assert_frame_equal(a[keys], b[keys])
        self.assertTrue((b.n_neighbours == 0).all())

    def test_atomic_output_and_hash_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"run"
            with patch("run_analysis.figures", side_effect=RuntimeError("figure failure")):
                with self.assertRaisesRegex(RuntimeError, "figure failure"):
                    publish_result(self.result, root)
            self.assertFalse(root.exists())
            with patch("run_analysis.figures"):
                publish_result(self.result, root)
            manifest = json.loads((root/"manifest.json").read_text())
            for name, sha in manifest["outputs_sha256"].items():
                self.assertEqual(digest(root/name), sha)
            with self.assertRaises(FileExistsError):
                publish_result(self.result, root)

    def test_invalid_configuration_rejected(self):
        for c in (replace(self.config, radius=0), replace(self.config, n_folds=True), replace(self.config, shuffle_seeds=(11,11)), replace(self.config, uncertainty_columns=("bout_id",))):
            with self.assertRaises(ValueError):
                c.validate()


if __name__ == "__main__":
    unittest.main()
