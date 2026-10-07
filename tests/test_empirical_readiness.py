from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from trajectory_pipeline import AnalysisConfig, prepare_trajectories, individual_bout_summary, read_table, validate_ties
from trajectory_validation import audit_trajectory_table, validate_trajectory_table
from prediction_evaluation import score_predictions
from audit_trajectories import audit_file
from verify_analysis import verify_analysis
from run_analysis import digest


class ReadinessTests(unittest.TestCase):
    def test_false_string_cannot_assert_independence(self):
        for value in ('false', 'true', 1, None):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'boolean'):
                replace(AnalysisConfig(), ties_independent=value).validate()

    def test_invalid_numeric_config_is_rejected(self):
        for value in (True, '10', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                replace(AnalysisConfig(), radius=value).validate()

    def track(self):
        return pd.DataFrame([dict(group_id='g', bout_id='b', individual_id=str(i),
            timestamp=f'2026-01-01T00:00:0{t}Z', x=t, y=i) for i in range(2) for t in (0, 1, 3)])

    def test_overlapping_bouts_cannot_cross_validation_folds(self):
        data = self.track()
        data = pd.concat([data, data.assign(bout_id='another')])
        with self.assertRaisesRegex(ValueError, 'Overlapping bouts'):
            prepare_trajectories(data, AnalysisConfig())

    def test_naive_time_cannot_pass_standalone_audit_or_scoring(self):
        data = self.track()
        data['timestamp'] = data.timestamp.str.removesuffix('Z')
        self.assertEqual(audit_trajectory_table(data).timezone_missing_timestamps, len(data))
        with self.assertRaisesRegex(ValueError, 'timezone'):
            validate_trajectory_table(data)
        predictions = data.assign(model='M0', observed_heading=0., predicted_heading=0.)
        with self.assertRaisesRegex(ValueError, 'timezone'):
            score_predictions(predictions)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'naive.csv'
            data.to_csv(path, index=False)
            self.assertFalse(audit_file(path)['valid_structure'])

    def test_explicit_offsets_preserve_instants_and_numeric_epochs_are_rejected(self):
        data = self.track()
        data['timestamp'] = data.timestamp.str.replace('T00:', 'T08:', regex=False).str.replace('Z', '+08:00', regex=False)
        clean, _ = validate_trajectory_table(data)
        expected, _ = validate_trajectory_table(self.track())
        pd.testing.assert_series_equal(clean.timestamp, expected.timestamp)
        with self.assertRaisesRegex(ValueError, 'timezone'):
            validate_trajectory_table(self.track().assign(timestamp=1234567890))

    def test_identifiers_are_not_silently_trimmed(self):
        data = self.track()
        data.loc[0, 'individual_id'] = ' 0'
        with self.assertRaisesRegex(ValueError, 'whitespace'):
            prepare_trajectories(data, AnalysisConfig())
        ties = pd.DataFrame([dict(group_id='g', focal_id=' 0', neighbour_id='1', weight=1)])
        with self.assertRaisesRegex(ValueError, 'whitespace'):
            validate_ties(ties, self.track(), AnalysisConfig(ties_independent=True))

    def test_unknown_accuracy_is_not_exported_as_perfect_accuracy(self):
        prepared, audit = prepare_trajectories(self.track(), AnalysisConfig())
        self.assertTrue(prepared.accuracy_m.isna().all())
        self.assertFalse(audit['filters']['accuracy_supplied'])
        self.assertEqual(int(prepared.interval_usable.sum()), 4)
        measured, audit = prepare_trajectories(self.track().assign(accuracy_m=0.), AnalysisConfig())
        self.assertTrue(measured.accuracy_m.eq(0).all())
        self.assertTrue(audit['filters']['accuracy_supplied'])

    def test_duplicate_csv_headers_cannot_be_silently_renamed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'bad.csv'
            for header in ('x,x', 'x,', ''):
                path.write_text(header+'\n1,2\n')
                with self.subTest(header=header), self.assertRaisesRegex(ValueError, 'column names'):
                    read_table(path)
                report = audit_file(path)
                self.assertFalse(report['valid_structure'])
                self.assertIn('column names', report['error'])

    def test_individual_summary_uses_duration_and_excludes_bad_intervals(self):
        data, _ = prepare_trajectories(self.track(), AnalysisConfig(max_gap=1.5))
        summary = individual_bout_summary(data)
        self.assertTrue((summary.usable_duration_s == 1).all())
        self.assertTrue((summary.path_length_m == 1).all())
        self.assertTrue((summary.time_weighted_speed_m_s == 1).all())
        self.assertTrue((summary.observed_span_s == 3).all())

    def test_failed_audit_retains_diagnostics_and_raw_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'raw.csv'
            self.track().assign(x='invalid').to_csv(path, index=False)
            sha = digest(path)
            report = audit_file(path)
            self.assertFalse(report['valid_structure'])
            self.assertEqual(report['structural']['nonfinite_coordinates'], 6)
            self.assertEqual(digest(path), sha)
            self.assertEqual(report['input_sha256'], sha)

    def test_verifier_rejects_tampering_and_extra_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root/'scores.csv'
            data.write_text('original')
            (root/'manifest.json').write_text(json.dumps({'outputs_sha256': {'scores.csv': digest(data)}}))
            self.assertEqual(verify_analysis(root)['verified_outputs'], 1)
            data.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                verify_analysis(root)
            data.write_text('original')
            (root/'extra.csv').write_text('extra')
            with self.assertRaisesRegex(ValueError, 'coverage'):
                verify_analysis(root)

    def test_scoring_cli_preserves_literal_ids_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = self.track().rename(columns={'x':'observed_heading','y':'predicted_heading'})
            data['group_id'] = 'NA'
            data['individual_id'] = data.individual_id.map({'0':'001','1':'002'})
            data['model'] = 'M0'
            data.to_csv(root/'input.csv', index=False)
            command = [sys.executable, str(Path(__file__).resolve().parents[1]/'src/prediction_evaluation.py'), str(root/'input.csv'), '--output', str(root/'scores.csv')]
            subprocess.run(command, check=True, capture_output=True)
            result = pd.read_csv(root/'scores.csv', keep_default_na=False, dtype=str)
            self.assertEqual(result.group_id.iloc[0], 'NA')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
