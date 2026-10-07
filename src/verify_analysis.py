"""Verify a local analysis handoff against its recorded output SHA-256 manifest.

Integrity does not prove scientific validity or authenticate the manifest's author.
"""
import argparse
import json
from pathlib import Path
from run_analysis import digest


def verify_analysis(directory):
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
    return {"verified_outputs": len(entries), "source_commit": manifest.get("source_commit"),
            "source_dirty": manifest.get("source_dirty")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_analysis(args.directory), indent=2))


if __name__ == "__main__":
    main()
