"""Opt-in relabelled-network controls with a common response, matched to M2."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from generate_demo import generate
from trajectory_pipeline import AnalysisConfig, run_pipeline


class CommonShuffleControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.ties, _ = generate(groups=2, sessions=2, animals=3, steps=20)
        cls.config = AnalysisConfig(n_folds=2, n_bootstrap=100, shuffle_seeds=(11, 29), ties_independent=True)
        cls.default = run_pipeline(cls.data, cls.config, cls.ties)
        cls.enabled = run_pipeline(cls.data, replace(cls.config, common_shuffle_controls=True), cls.ties)

    def test_default_model_set_is_unchanged(self):
        self.assertFalse(any(m.startswith("shuffle_common_") for m in self.default["predictions"].model))

    def test_controls_are_matched_and_compared_with_m2(self):
        predictions = self.enabled["predictions"]
        self.assertTrue({"shuffle_common_11", "shuffle_common_29", "shuffle_11", "shuffle_29"} <= set(predictions.model))
        self.assertEqual(predictions.groupby("model").size().nunique(), 1)
        pairs = set(zip(self.enabled["comparisons"].reference, self.enabled["comparisons"].alternative))
        self.assertTrue({("shuffle_common_11", "M2"), ("shuffle_common_29", "M2"),
                         ("shuffle_11", "M3"), ("shuffle_29", "M3")} <= pairs)
        self.assertFalse(any(ref.startswith("shuffle_common_") and alt != "M2" for ref, alt in pairs))
        # Existing models and their predictions are untouched by enabling the controls.
        keep = self.enabled["predictions"][~self.enabled["predictions"].model.str.startswith("shuffle_common_")]
        np.testing.assert_array_equal(keep.sort_values(["model", "group_id", "bout_id", "individual_id", "timestamp"]).predicted_heading,
                                      self.default["predictions"].sort_values(["model", "group_id", "bout_id", "individual_id", "timestamp"]).predicted_heading)

    def test_controls_fit_only_a_common_response(self):
        params = self.enabled["parameters"]
        common = params[params.model.str.startswith("shuffle_common_")]
        self.assertEqual(len(common), self.config.n_folds * len(self.config.shuffle_seeds))
        self.assertTrue((common.individual_id == "").all())

    def test_relabelling_an_exchangeable_network_reproduces_m2_exactly(self):
        uniform = self.ties.assign(weight=1.0)
        result = run_pipeline(self.data, replace(self.config, common_shuffle_controls=True), uniform)
        p = result["predictions"].set_index(["model", "group_id", "bout_id", "individual_id", "timestamp"]).predicted_heading
        np.testing.assert_array_equal(p.loc["shuffle_common_11"].sort_index(), p.loc["M2"].sort_index())

    def test_requires_boolean_and_warns_without_ties(self):
        for value in ("true", 1, None):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "common_shuffle_controls"):
                replace(self.config, common_shuffle_controls=value).validate()
        result = run_pipeline(self.data, replace(self.config, common_shuffle_controls=True))
        self.assertTrue(any("common_shuffle_controls" in w for w in result["audit"]["warnings"]))


if __name__ == "__main__":
    unittest.main()
