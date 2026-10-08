"""Reproducibility of published analysis outputs and their provenance record."""
from importlib.metadata import PackageNotFoundError, version as installed_version
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from generate_demo import generate
from run_analysis import publish_result
from trajectory_pipeline import AnalysisConfig, run_pipeline


class ReproducibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data, ties, _ = generate(groups=2, sessions=2, animals=3, steps=20)
        config = AnalysisConfig(n_folds=2, n_bootstrap=100, shuffle_seeds=(11,), ties_independent=True)
        cls.result = run_pipeline(data, config, ties)

    def test_absent_optional_package_is_recorded_not_fatal(self):
        def version(name):
            if name == "pyproj":
                raise PackageNotFoundError(name)
            return installed_version(name)

        with patch("run_analysis.version", side_effect=version), patch("run_analysis.figures"), \
                tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            publish_result(self.result, root)
            packages = json.loads((root / "manifest.json").read_text())["packages"]
        self.assertIsNone(packages["pyproj"])
        self.assertEqual(packages["numpy"], installed_version("numpy"))
        self.assertEqual(set(packages), {"numpy", "pandas", "scipy", "pyproj", "matplotlib"})

    def test_identical_analyses_publish_identical_output_hashes(self):
        # Real figures are rendered; the second run starts at least one second later so
        # an embedded wall-clock date would change the PDF and SVG bytes.
        with tempfile.TemporaryDirectory() as tmp:
            manifests = []
            for name in ("first", "second"):
                if manifests:
                    time.sleep(1.1)
                root = Path(tmp) / name
                publish_result(self.result, root)
                manifests.append(json.loads((root / "manifest.json").read_text())["outputs_sha256"])
        self.assertTrue({"model_scores.pdf", "model_scores.svg", "movement.pdf", "movement.png"} <= set(manifests[0]))
        differing = sorted(n for n in manifests[0] if manifests[0][n] != manifests[1].get(n))
        self.assertEqual(differing, [])


if __name__ == "__main__":
    unittest.main()
