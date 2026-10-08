"""Verify a local analysis handoff against its recorded output SHA-256 manifest.

Optionally confirm that supplied input files are the exact files the analysis recorded,
for example that a handoff was produced from a particular approved raw export.
Integrity does not prove scientific validity or authenticate the manifest's author.
"""
import argparse
import json
from pathlib import Path
from run_analysis import digest


def verify_analysis(directory, inputs=None):
    root = Path(directory).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    entries = manifest.get("outputs_sha256")
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Manifest requires nonempty outputs_sha256")
    actual = {p.name for p in root.iterdir() if p.name != "manifest.json"}
    if actual != set(entries):
        raise ValueError("Output file coverage differs from manifest")
    for name, expected in entries.items():
        path = root / name
        if Path(name).name != name or path.is_symlink() or not path.is_file():
            raise ValueError(f"Unsafe or missing output: {name}")
        if digest(path) != expected:
            raise ValueError(f"Output checksum mismatch: {name}")
    result = {"verified_outputs": len(entries), "source_commit": manifest.get("source_commit"),
              "source_dirty": manifest.get("source_dirty")}
    if inputs:
        recorded = manifest.get("inputs")
        if not isinstance(recorded, dict) or not recorded:
            raise ValueError("Manifest records no input hashes to verify against")
        for name, path in inputs.items():
            if name not in recorded:
                raise ValueError(f"Manifest has no input named {name!r}; recorded inputs: {sorted(recorded)}")
            path = Path(path)
            if not path.is_file():
                raise ValueError(f"Input is not a readable file: {name}")
            if digest(path) != recorded[name]:
                raise ValueError(f"Input checksum mismatch: {name}")
        result["verified_inputs"] = sorted(inputs)
        # Recorded inputs that were not supplied are listed, never silently treated as checked.
        result["unverified_inputs"] = sorted(set(recorded) - set(inputs))
    return result


def parse_input(text):
    name, separator, path = text.partition("=")
    if not separator or not name or not path:
        raise argparse.ArgumentTypeError("Use NAME=PATH, for example trajectories=raw/tracks.csv")
    return name, Path(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--input", dest="inputs", action="append", type=parse_input, default=[],
                        metavar="NAME=PATH", help="Check an original input (trajectories, config, ties or folds) against the manifest")
    args = parser.parse_args()
    names = [name for name, _ in args.inputs]
    if len(set(names)) != len(names):
        parser.error("Supply each input name once")
    print(json.dumps(verify_analysis(args.directory, dict(args.inputs)), indent=2))


if __name__ == "__main__":
    main()
