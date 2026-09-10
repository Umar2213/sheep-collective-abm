import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analysis_utils import (
    level_crossing,
    zero_crossings,
    variance_components,
    paired_effect_summary,
    convergence_flags,
)


class AnalysisTests(unittest.TestCase):
    def test_crossing_and_unbracketed_threshold(self):
        self.assertAlmostEqual(level_crossing([0, 1], [1, .8]), .5)
        self.assertTrue(np.isnan(level_crossing([0, 1], [.8, .7])))
        self.assertEqual(level_crossing([0, 1], [.9, .9]), 0)
        self.assertEqual(level_crossing([0, 1], [1, .9]), 1)

    def test_all_crossings_and_coincident_interval(self):
        self.assertEqual(zero_crossings([0, 1, 2], [-1, 1, -1]), [.5, 1.5])
        self.assertEqual(zero_crossings([0, 1, 2], [-1, 0, 1]), [1])
        with self.assertRaises(ValueError):
            zero_crossings([0, 1], [0, 0])

    def test_distinguish_disorder_from_temporal_variation(self):
        temporal, between, pooled = variance_components([.2, .8], [.04, .64], 10)
        self.assertAlmostEqual(temporal, 0)
        self.assertAlmostEqual(between, .9)
        self.assertAlmostEqual(pooled, .9)
        temporal, between, pooled = variance_components([.5, .5], [.3, .3], 10)
        self.assertAlmostEqual(temporal, .5)
        self.assertAlmostEqual(between, 0)
        with self.assertRaises(ValueError):
            variance_components([.8], [.1], 10)

    def test_paired_effect_summary(self):
        out = paired_effect_summary([.8, .7, .9], [.7, .65, .85])
        self.assertEqual(out["n"], 3)
        self.assertAlmostEqual(out["mean_delta"], (-.1 - .05 - .05) / 3)
        self.assertGreater(out["sd_delta"], 0)
        self.assertLess(out["ci95_low"], out["ci95_high"])
        with self.assertRaises(ValueError):
            paired_effect_summary([1.0], [0.9])

    def test_convergence_screening_is_explicit(self):
        flags = convergence_flags(
            ess=[50, 200],
            block_sd=[.01, .03],
            half_drift=[.03, .01],
            late_quarter_drift=[.01, .04],
        )
        self.assertEqual(flags["low_ess"].tolist(), [True, False])
        self.assertEqual(flags["high_block_sd"].tolist(), [False, True])
        self.assertEqual(flags["high_half_drift"].tolist(), [True, False])
        self.assertEqual(flags["high_late_drift"].tolist(), [False, True])
        with self.assertRaises(ValueError):
            convergence_flags([1, 2], [1], [1, 2], [1, 2])


if __name__ == "__main__":
    unittest.main()
