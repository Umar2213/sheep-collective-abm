"""Structural checks must behave the same for object and pandas string columns.

pandas 3 reads text as the string dtype by default; earlier versions do so on request.
"""
from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from trajectory_validation import audit_trajectory_table, validate_trajectory_table
from prediction_evaluation import score_predictions

TEXT = ["group_id", "bout_id", "individual_id", "timestamp"]


def tracks(dtype):
    rows = [dict(group_id="g", bout_id="b", individual_id=str(i),
                 timestamp=f"2026-01-01T00:00:0{t}Z", x=float(t), y=float(i))
            for i in range(2) for t in range(3)]
    frame = pd.DataFrame(rows)
    frame[TEXT] = frame[TEXT].astype(dtype)
    return frame


class StringDtypeTests(unittest.TestCase):
    def test_empty_table_reports_empty_for_every_text_dtype(self):
        for dtype in ("object", "string"):
            with self.subTest(dtype=dtype):
                empty = tracks(dtype).iloc[:0]
                audit = audit_trajectory_table(empty)
                self.assertEqual((audit.rows, audit.missing_identifiers, audit.timezone_missing_timestamps,
                                  audit.whitespace_identifiers), (0, 0, 0, 0))
                with self.assertRaisesRegex(ValueError, "empty"):
                    validate_trajectory_table(empty)

    def test_identifier_problems_detected_for_every_text_dtype(self):
        for dtype in ("object", "string"):
            for value, message in ((None, "missing identifiers"), ("", "missing identifiers"),
                                   ("  ", "missing identifiers"), (" 0", "whitespace")):
                with self.subTest(dtype=dtype, value=value):
                    frame = tracks(dtype)
                    frame.loc[0, "individual_id"] = value
                    with self.assertRaisesRegex(ValueError, message):
                        validate_trajectory_table(frame)

    def test_duplicate_index_labels_do_not_change_counts(self):
        frame = tracks("string")
        frame.index = [0] * len(frame)
        frame.iloc[0, frame.columns.get_loc("group_id")] = " g"
        self.assertEqual(audit_trajectory_table(frame).whitespace_identifiers, 1)

    def test_scoring_accepts_string_dtype_predictions(self):
        predictions = pd.concat([tracks("string").assign(model=name, observed_heading=0.0, predicted_heading=0.1)
                                 for name in ("M0", "M1")], ignore_index=True)
        predictions["model"] = predictions.model.astype("string")
        scores = score_predictions(predictions)
        self.assertEqual(len(scores), 2)
        self.assertTrue((scores.n_observations == 6).all())


if __name__ == "__main__":
    unittest.main()
