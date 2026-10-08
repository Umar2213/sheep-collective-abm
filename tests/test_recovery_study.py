"""Responsiveness recovery through the production preprocessing and feature code."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from generate_demo import generate
from recovery_study import Scenario, observe, recover, run_study
from verify_analysis import verify_analysis


class ObservationModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.ties, cls.truth = generate(seed=3, groups=2, sessions=1, animals=3, steps=12)

    def test_exact_observation_and_no_mutation(self):
        before = self.data.copy()
        observed = observe(self.data, Scenario(), seed=1)
        pd.testing.assert_frame_equal(observed, self.data.reset_index(drop=True))
        pd.testing.assert_frame_equal(self.data, before)

    def test_noise_dropout_and_subsampling_are_seeded_and_shared(self):
        a = observe(self.data, Scenario(location_sd=0.2, dropout=0.25), seed=5)
        b = observe(self.data, Scenario(location_sd=0.2, dropout=0.25), seed=5)
        pd.testing.assert_frame_equal(a, b)
        self.assertLess(len(a), len(self.data))
        # Common random numbers: the same fixes survive and noise scales with the SD.
        c = observe(self.data, Scenario(location_sd=0.4, dropout=0.25), seed=5)
        exact = self.data.set_index(["group_id", "individual_id", "timestamp"]).loc[a.set_index(["group_id", "individual_id", "timestamp"]).index]
        np.testing.assert_allclose(c.x.to_numpy() - exact.x.to_numpy(), 2 * (a.x.to_numpy() - exact.x.to_numpy()))
        thinned = observe(self.data, Scenario(subsample=3), seed=5)
        seconds = pd.to_datetime(thinned.timestamp).dt.second
        self.assertTrue((seconds % 3 == 0).all())
        self.assertEqual(len(thinned), len(self.data) // 3)

    def test_declared_accuracy_and_invalid_scenarios(self):
        self.assertTrue((observe(self.data, Scenario(location_sd=0.3, declare_accuracy=True), 1).accuracy_m == 0.3).all())
        self.assertNotIn("accuracy_m", observe(self.data, Scenario(location_sd=0.3), 1))
        for bad in (Scenario(location_sd=-1), Scenario(dropout=1.0), Scenario(subsample=0), Scenario(subsample=True)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                bad.validate()

    def test_destroyed_observations_are_reported_not_fatal(self):
        rows = recover(self.data, self.ties, self.truth, Scenario(dropout=0.97), seed=2)
        self.assertEqual(len(rows), 2 * len(self.truth))
        self.assertFalse((rows.status == "estimated").any())
        self.assertTrue(rows.estimate.isna().all())


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.estimates, cls.summary = run_study([Scenario(), Scenario(location_sd=0.25)], replicates=1, seed=7)

    def row(self, sd, kernel):
        s = self.summary
        return s[(s.location_sd == sd) & (s.kernel == kernel)].iloc[0]

    def test_exact_observations_recover_known_individual_responsiveness(self):
        exact = self.row(0.0, "social")
        self.assertEqual(exact.estimated, 15)
        self.assertLess(exact.rmse, 0.06)
        self.assertGreater(exact.mean_spearman, 0.9)

    def test_location_error_degrades_and_biases_recovery(self):
        exact, noisy = self.row(0.0, "social"), self.row(0.25, "social")
        self.assertGreater(noisy.rmse, exact.rmse + 0.2)
        self.assertGreater(noisy.bias, 0.2)
        self.assertLess(noisy.mean_spearman, exact.mean_spearman - 0.3)

    def test_ignoring_generating_ties_is_worse_than_using_them(self):
        self.assertGreater(self.row(0.0, "uniform").rmse, self.row(0.0, "social").rmse)

    def test_study_is_reproducible(self):
        again, _ = run_study([Scenario()], replicates=1, seed=7)
        first = self.estimates[self.estimates.location_sd == 0].reset_index(drop=True)
        pd.testing.assert_frame_equal(first, again)


class CommandLineTests(unittest.TestCase):
    def test_publishes_verifiable_immutable_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "recovery"
            command = [sys.executable, str(ROOT / "src/recovery_study.py"), "--output", str(output),
                       "--location-sd", "0", "0.1", "--dropout", "0", "--subsample", "1", "--replicates", "1",
                       "--groups", "2", "--sessions", "1", "--animals", "3", "--steps", "20"]
            subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertEqual(verify_analysis(output)["verified_outputs"], 6)
            study = json.loads((output / "study.json").read_text())
            self.assertEqual(len(study["settings"]["scenarios"]), 2)
            self.assertEqual(len(pd.read_csv(output / "summary.csv")), 4)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
