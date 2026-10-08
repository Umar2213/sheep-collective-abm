"""Optional verification that a handoff was produced from specific input files."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from run_analysis import digest
from verify_analysis import verify_analysis


class InputVerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.output = base / "output"
        self.output.mkdir()
        (self.output / "scores.csv").write_text("model,mae\nM0,0.1\n")
        self.raw = base / "tracks.csv"
        self.raw.write_text("group_id,bout_id\ng,b\n")
        self.config = base / "config.json"
        self.config.write_text("{}\n")
        manifest = {"outputs_sha256": {"scores.csv": digest(self.output / "scores.csv")},
                    "inputs": {"trajectories": digest(self.raw), "config": digest(self.config)}}
        (self.output / "manifest.json").write_text(json.dumps(manifest))

    def tearDown(self):
        self.tmp.cleanup()

    def test_outputs_only_behaviour_is_unchanged(self):
        self.assertEqual(verify_analysis(self.output),
                         {"verified_outputs": 1, "source_commit": None, "source_dirty": None})

    def test_matching_inputs_verified_and_omitted_inputs_listed(self):
        result = verify_analysis(self.output, {"trajectories": self.raw})
        self.assertEqual(result["verified_inputs"], ["trajectories"])
        self.assertEqual(result["unverified_inputs"], ["config"])
        result = verify_analysis(self.output, {"trajectories": self.raw, "config": self.config})
        self.assertEqual(result["unverified_inputs"], [])

    def test_changed_unknown_or_missing_inputs_rejected(self):
        self.raw.write_text("group_id,bout_id\ng,b2\n")
        with self.assertRaisesRegex(ValueError, "Input checksum mismatch: trajectories"):
            verify_analysis(self.output, {"trajectories": self.raw})
        with self.assertRaisesRegex(ValueError, "no input named 'ties'"):
            verify_analysis(self.output, {"ties": self.config})
        with self.assertRaisesRegex(ValueError, "readable file"):
            verify_analysis(self.output, {"config": self.output / "absent.json"})

    def test_manifest_without_input_hashes_cannot_confirm_inputs(self):
        manifest = json.loads((self.output / "manifest.json").read_text())
        manifest["inputs"] = {}
        (self.output / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "no input hashes"):
            verify_analysis(self.output, {"config": self.config})

    def test_command_line(self):
        command = [sys.executable, str(ROOT / "src/verify_analysis.py"), str(self.output)]
        done = subprocess.run(command + ["--input", f"config={self.config}"], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(done.stdout)["verified_inputs"], ["config"])
        for bad in (["--input", "config"], ["--input", f"config={self.config}", "--input", f"config={self.config}"]):
            with self.subTest(arguments=bad):
                self.assertNotEqual(subprocess.run(command + bad, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
