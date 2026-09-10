import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analysis_utils import level_crossing, zero_crossings, variance_components


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


if __name__ == "__main__":
    unittest.main()
