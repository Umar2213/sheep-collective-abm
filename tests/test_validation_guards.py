"""Regression checks for biological blocks, prediction horizons and missing coverage."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from generate_demo import generate
from trajectory_pipeline import (AnalysisConfig, prepare_trajectories, construct_features,
                                 fit_predict, run_pipeline, validate_ties)


class ValidationGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.ties, _ = generate(groups=2, sessions=4, animals=3, steps=12)
        cls.config = AnalysisConfig(n_folds=2, n_bootstrap=100, shuffle_seeds=(),
                                    ties_independent=True)
        cls.result = run_pipeline(cls.data, cls.config, cls.ties)

    def test_mixed_session_time_steps_cannot_share_a_response_fit(self):
        data = self.data.copy()
        mask = data.bout_id.eq("session_02")
        times = pd.to_datetime(data.loc[mask, "timestamp"], utc=True)
        start = times.min()
        data.loc[mask, "timestamp"] = (start + 2 * (times-start)).map(lambda t: t.isoformat())
        with self.assertRaisesRegex(ValueError, "sampling intervals"):
            run_pipeline(data, self.config)
        features = self.result["features"].copy()
        features.loc[0, "interval_seconds"] = 2.0
        with self.assertRaisesRegex(ValueError, "sampling intervals"):
            fit_predict(features, self.result["folds"], self.config)

    def test_declared_interval_is_checked_and_exported(self):
        config = replace(self.config, sampling_interval_seconds=1.0)
        prepared, _ = prepare_trajectories(self.data, config)
        features, _ = construct_features(prepared, config)
        self.assertTrue(features.interval_seconds.eq(1).all())
        self.assertEqual(self.result["audit"]["sampling_interval_seconds"], 1)
        self.assertTrue(self.result["predictions"].interval_seconds.eq(1).all())
        with self.assertRaisesRegex(ValueError, "sampling intervals"):
            construct_features(prepared, replace(config, sampling_interval_seconds=2))
        for interval in (True, 0, -1, "1", np.nan, np.inf):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                replace(config, sampling_interval_seconds=interval).validate()

    def test_session_blocks_keep_multiple_bouts_together_and_prevent_leakage(self):
        data = self.data.assign(session_id=self.data.bout_id.map({
            "session_01": "visit_a", "session_02": "visit_a",
            "session_03": "visit_b", "session_04": "visit_b"}))
        config = replace(self.config, split_columns=("group_id", "session_id"))
        result = run_pipeline(data, config, self.ties)
        pred = result["predictions"]
        self.assertTrue(pred.groupby(["group_id", "session_id"]).fold.nunique().eq(1).all())
        self.assertTrue(pred.groupby(["group_id", "session_id"]).bout_id.nunique().eq(2).all())
        features = result["features"].copy()
        joined = features.merge(result["folds"], on=list(config.split_columns), how="left")
        features.loc[joined.fold.eq(0).to_numpy(), "observed_heading"] += .7
        _, parameters = fit_predict(features, result["folds"], config, True)
        before = result["parameters"]
        pd.testing.assert_frame_equal(before[before.fold.eq(0)].reset_index(drop=True),
                                      parameters[parameters.fold.eq(0)].reset_index(drop=True))

    def test_explicit_days_reach_predictions_and_uncertainty_scores(self):
        data = self.data.assign(date=self.data.timestamp.str[:10])
        config = replace(self.config, split_columns=("group_id", "date"),
                         uncertainty_columns=("group_id", "date"))
        result = run_pipeline(data, config)
        self.assertEqual(result["audit"]["uncertainty_units"], 8)
        self.assertEqual(set(result["scores"].date), set(data.date))
        self.assertTrue(result["predictions"].groupby(["group_id", "date"]).fold.nunique().eq(1).all())

    def test_invalid_or_changing_block_metadata_fails_before_fitting(self):
        config = replace(self.config, split_columns=("group_id", "session_id"))
        with self.assertRaisesRegex(ValueError, "Missing biological"):
            prepare_trajectories(self.data, config)
        for value in (None, "", " visit "):
            data = self.data.assign(session_id="visit")
            data.loc[0, "session_id"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "blocking identifiers"):
                prepare_trajectories(data, config)
        data = self.data.assign(session_id="visit")
        data.loc[0, "session_id"] = "different_visit"
        with self.assertRaisesRegex(ValueError, "Each bout"):
            prepare_trajectories(data, config)

    def test_incomplete_direct_fold_table_cannot_drop_observations(self):
        folds = self.result["folds"].iloc[1:]
        self.assertEqual(set(folds.fold), {0, 1})
        with self.assertRaisesRegex(ValueError, "Every frozen fold"):
            fit_predict(self.result["features"], folds, self.config, True)

    def test_new_group_fallback_is_visible_and_predictions_reduce_to_common_models(self):
        config = replace(self.config, split_columns=("group_id",))
        result = run_pipeline(self.data, config, self.ties)
        pred = result["predictions"]
        for common, individual in (("M0", "M1"), ("M2", "M3")):
            a, b = pred[pred.model.eq(common)], pred[pred.model.eq(individual)]
            np.testing.assert_allclose(a.predicted_heading, b.predicted_heading)
            self.assertTrue(b.response_status.eq("insufficient_individual_training_common_fallback").all())
            self.assertEqual(result["audit"]["prediction_status_counts"][individual]
                             ["insufficient_individual_training_common_fallback"], len(b))
        self.assertTrue(any("Whole-group holdout" in w for w in result["audit"]["warnings"]))

    def test_coverage_distinguishes_stationary_neighbours_and_missing_records(self):
        data = pd.DataFrame([dict(group_id="g", bout_id="b", individual_id=str(i),
            timestamp=f"2026-01-01T00:00:0{t}Z", x=t if i == 0 else 0, y=i)
            for i in range(2) for t in range(6) if not (i == 1 and t == 2)])
        prepared, _ = prepare_trajectories(data, self.config)
        features, _ = construct_features(prepared, self.config)
        at_one = features[features.predictor_timestamp.eq(pd.Timestamp("2026-01-01T00:00:01Z"))].iloc[0]
        self.assertEqual(at_one.n_nearby_positions, 1)
        self.assertEqual(at_one.n_neighbours, 0)
        self.assertEqual(at_one.n_nearby_without_heading, 1)
        self.assertEqual(at_one.uniform_fallback, "no_usable_neighbours")
        at_two = features[features.predictor_timestamp.eq(pd.Timestamp("2026-01-01T00:00:02Z"))].iloc[0]
        self.assertEqual(at_two.n_bout_roster_unrecorded, 1)
        self.assertEqual(at_two.n_nearby_positions, 0)
        self.assertEqual(at_two.n_bout_roster, 2)

    def test_zero_social_weights_have_a_distinct_fallback_reason(self):
        prepared, _ = prepare_trajectories(self.data, self.config)
        lookup = validate_ties(self.ties.assign(weight=0), prepared, self.config)
        features, _ = construct_features(prepared, self.config, lookup)
        eligible = features[features.n_neighbours.gt(0)]
        self.assertGreater(len(eligible), 0)
        self.assertTrue(eligible.social_fallback.eq("zero_total_weight").all())
        self.assertTrue(eligible.uniform_fallback.eq("none").all())


if __name__ == "__main__":
    unittest.main()
