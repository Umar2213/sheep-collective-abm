"""WP1: non-destructive structural CSV audit, including failed validation reports."""
import argparse
import json
from pathlib import Path

from trajectory_pipeline import read_table
from trajectory_validation import audit_trajectory_table, validate_trajectory_table
from run_analysis import digest


def audit_file(path):
    before = digest(path)
    frame = read_table(path)
    report = {"schema_version": 1, "input_sha256": before, "valid_structure": False,
              "notice": "Structural audit only. CRS, timezone, sensor error, permissions and biological independence require separate review."}
    try:
        report["structural"] = audit_trajectory_table(frame).to_dict()
        validate_trajectory_table(frame)
        report["valid_structure"] = True
    except ValueError as error:
        report["error"] = str(error)
    if digest(path) != before:
        raise RuntimeError("Input changed during audit; freeze the source and rerun")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trajectories", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_file(args.trajectories)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"Audit saved: {args.output}")
    return 0 if report["valid_structure"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
