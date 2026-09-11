import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from trajectory_validation import (
    assign_grouped_folds,
    audit_trajectory_table,
    circular_absolute_error,
    mean_cosine_alignment,
    validate_trajectory_table,
)


def example_tracks():
    rows = []
    for group in ["g1", "g2"]:
        for bout in ["b1", "b2", "b3"]:
            for animal in ["a", "b"]:
                for second in range(4):
                    rows.append({
                        "group_id": group,
                        "bout_id": bout,
                        "individual_id": animal,
                        "timestamp": f"2026-01-01T00:00:0{second}Z",
                        "x": second + (0.2 if animal == "b" else 0.0),
                        "y": 1.0 if animal == "b" else 0.0,
                    })
    return pd.DataFrame(rows)


class TrajectoryValidationTests(unittest.TestCase):
    def test_valid_tracks_pass_and_report_sampling(self):
        frame = example_tracks().sample(frac=1.0, random_state=4).reset_index(drop=True)
        clean, audit = validate_trajectory_table(frame)
        self.assertEqual(len(clean), len(frame))
        self.assertEqual(audit.groups, 2)
        self.assertEqual(audit.bouts, 6)
        self.assertEqual(audit.tracks, 12)
        self.assertEqual(audit.median_sampling_interval_seconds, 1.0)
        self.assertEqual(audit.duplicate_keys, 0)
        self.assertEqual(audit.nonpositive_time_steps, 0)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(clean["timestamp"]))

    def test_missing_columns_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing required trajectory columns"):
            validate_trajectory_table(example_tracks().drop(columns=["y"]))

    def test_duplicate_observation_is_rejected(self):
        frame = example_tracks()
        frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
        audit = audit_trajectory_table(frame)
        self.assertEqual(audit.duplicate_keys, 2)
        with self.assertRaisesRegex(ValueError, "duplicate observation keys"):
            validate_trajectory_table(frame)

    def test_invalid_time_and_coordinate_are_rejected(self):
        frame = example_tracks()
        frame.loc[0, "timestamp"] = "not-a-time"
        frame.loc[1, "x"] = np.inf
        audit = audit_trajectory_table(frame)
        self.assertEqual(audit.unparseable_timestamps, 1)
        self.assertEqual(audit.nonfinite_coordinates, 1)
        with self.assertRaisesRegex(ValueError, "unparseable timestamps"):
            validate_trajectory_table(frame)

    def test_single_individual_bout_is_rejected(self):
        frame = example_tracks()
        keep = ~((frame.group_id == "g1") & (frame.bout_id == "b1") & (frame.individual_id == "b"))
        with self.assertRaisesRegex(ValueError, "fewer than two individuals"):
            validate_trajectory_table(frame.loc[keep].copy())

    def test_grouped_folds_are_deterministic_and_leakage_free(self):
        frame = example_tracks()
        a = assign_grouped_folds(frame, n_folds=3)
        b = assign_grouped_folds(frame, n_folds=3)
        self.assertTrue(a["fold"].equals(b["fold"]))
        counts = a.groupby(["group_id", "bout_id"])["fold"].nunique()
        self.assertTrue((counts == 1).all())
        self.assertTrue(a["fold"].between(0, 2).all())

    def test_fold_argument_validation(self):
        with self.assertRaisesRegex(ValueError, "n_folds"):
            assign_grouped_folds(example_tracks(), n_folds=1)
        with self.assertRaisesRegex(ValueError, "blocking columns"):
            assign_grouped_folds(example_tracks(), block_columns=("day",), n_folds=2)

    def test_circular_metrics_handle_wraparound(self):
        observed = np.array([np.pi - 0.05, -np.pi + 0.05])
        predicted = np.array([-np.pi + 0.05, np.pi - 0.05])
        errors = circular_absolute_error(observed, predicted)
        np.testing.assert_allclose(errors, [0.1, 0.1], atol=1e-12)
        self.assertGreater(mean_cosine_alignment(observed, predicted), 0.99)

    def test_empty_and_missing_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            validate_trajectory_table(example_tracks().iloc[:0])
        for value in [None, "", "   "]:
            frame = example_tracks()
            frame.loc[0, "group_id"] = value
            with self.assertRaisesRegex(ValueError, "missing identifiers"):
                validate_trajectory_table(frame)

    def test_folds_populated_and_invariant_to_row_order(self):
        frame = example_tracks()
        first = assign_grouped_folds(frame, n_folds=5)
        second = assign_grouped_folds(frame.sample(frac=1, random_state=2), n_folds=5)
        keys = ["group_id", "bout_id"]
        a = first.groupby(keys).fold.first().sort_index()
        b = second.groupby(keys).fold.first().sort_index()
        pd.testing.assert_series_equal(a, b)
        self.assertEqual(set(a), set(range(5)))
        with self.assertRaisesRegex(ValueError, "already exists"):
            assign_grouped_folds(first)
        with self.assertRaisesRegex(ValueError, "distinct biological blocks"):
            assign_grouped_folds(frame, n_folds=7)

    def test_nonfinite_and_empty_metrics_rejected(self):
        for observed, predicted in [([], []), ([0], [np.nan]), ([np.inf], [0])]:
            for metric in [circular_absolute_error, mean_cosine_alignment]:
                with self.assertRaises(ValueError):
                    metric(observed, predicted)


if __name__ == "__main__":
    unittest.main()
