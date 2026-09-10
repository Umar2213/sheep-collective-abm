#!/usr/bin/env python3
"""Merge complete-condition simulation shards after verifying coverage and uniqueness."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path

import pandas as pd


EXPERIMENTS = {
    "production": {
        "replicate_file": "sweep_replicates.csv",
        "summary_file": "sweep_condition_means.csv",
        "replicate_keys": ["sigma_std", "noise", "trait_rep", "dynamic_rep"],
        "condition_keys": ["sigma_std", "noise"],
    },
    "finite_size": {
        "replicate_file": "fss_replicates.csv",
        "summary_file": "fss_condition_means.csv",
        "replicate_keys": ["N", "sigma_std", "trait_rep", "dynamic_rep"],
        "condition_keys": ["N", "sigma_std"],
    },
    "algorithmic_controls": {
        "replicate_file": "control_replicates.csv",
        "summary_file": "control_condition_means.csv",
        "replicate_keys": [
            "sigma_std", "noise", "search_mode", "update_mode",
            "trait_rep", "dynamic_rep",
        ],
        "condition_keys": ["sigma_std", "noise", "search_mode", "update_mode"],
        "supplemental": [
            {
                "file": "paired_control_effects.csv",
                "keys": ["sigma_std", "noise", "trait_rep", "dynamic_rep", "control"],
                "rows": lambda m: int(m["full_condition_count"]) * int(m["trait_replicates"]) * int(m["dynamic_replicates"]) * 2,
            },
            {
                "file": "paired_control_summary.csv",
                "keys": ["sigma_std", "noise", "control"],
                "rows": lambda m: int(m["full_condition_count"]) * 2,
            },
        ],
    },
    "distribution_controls": {
        "replicate_file": "distribution_replicates.csv",
        "summary_file": "distribution_condition_means.csv",
        "replicate_keys": [
            "sigma_std", "noise", "trait_distribution", "trait_rep", "dynamic_rep",
        ],
        "condition_keys": ["sigma_std", "noise", "trait_distribution"],
        "supplemental": [
            {
                "file": "paired_distribution_effects.csv",
                "keys": ["sigma_std", "noise", "trait_rep", "dynamic_rep"],
                "rows": lambda m: int(m["full_condition_count"]) * int(m["trait_replicates"]) * int(m["dynamic_replicates"]),
            },
            {
                "file": "paired_distribution_summary.csv",
                "keys": ["sigma_std", "noise"],
                "rows": lambda m: int(m["full_condition_count"]),
            },
        ],
    },
}

SHARD_RE = re.compile(r"^shard_(\d+)_of_(\d+)$")


def _load_metadata(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _check_columns(frame: pd.DataFrame, required: list[str], source: Path) -> None:
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise ValueError(f"{source} is missing required columns: {missing}")


def _validate_metadata_consistency(metadata: list[dict]) -> None:
    """Reject shard sets produced from materially different experiment definitions."""
    ignored = {
        "shard_index", "shard_condition_count", "shard_run_count",
        "timestamp_utc", "hostname", "julia_threads",
    }
    reference = {k: v for k, v in metadata[0].items() if k not in ignored}
    for idx, meta in enumerate(metadata[1:], start=2):
        current = {k: v for k, v in meta.items() if k not in ignored}
        if current != reference:
            differing = sorted(k for k in set(reference) | set(current) if reference.get(k) != current.get(k))
            raise ValueError(f"Shard metadata are inconsistent, shard {idx} differs in: {differing}")


def _merge_supplemental(shard_dirs, metadata, specs, output: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    first_meta = metadata[0]
    for spec in specs:
        frames = []
        filename = spec["file"]
        for _, _, directory in shard_dirs:
            path = directory / filename
            if not path.exists():
                raise ValueError(f"Missing required shard file: {path}")
            frame = pd.read_csv(path)
            _check_columns(frame, spec["keys"], path)
            frames.append(frame)
        merged = pd.concat(frames, ignore_index=True)
        dup = merged.duplicated(spec["keys"], keep=False)
        if dup.any():
            examples = merged.loc[dup, spec["keys"]].head(5).to_dict("records")
            raise ValueError(f"Duplicate keys found in {filename}, examples: {examples}")
        expected = int(spec["rows"](first_meta))
        if len(merged) != expected:
            raise ValueError(f"Merged {len(merged)} rows in {filename}, expected {expected}")
        merged = merged.sort_values(spec["keys"]).reset_index(drop=True)
        merged.to_csv(output / filename, index=False)
        counts[filename] = len(merged)
    return counts


def merge_shards(root: Path, experiment: str, output: Path | None = None) -> dict:
    root = Path(root)
    if experiment not in EXPERIMENTS:
        raise ValueError(f"Unknown experiment {experiment!r}; choose from {sorted(EXPERIMENTS)}")
    cfg = EXPERIMENTS[experiment]

    shard_dirs = []
    for candidate in root.iterdir() if root.exists() else []:
        if not candidate.is_dir():
            continue
        match = SHARD_RE.match(candidate.name)
        if match:
            shard_dirs.append((int(match.group(1)), int(match.group(2)), candidate))
    if not shard_dirs:
        raise ValueError(f"No shard_###_of_### directories found under {root}")

    shard_dirs.sort(key=lambda x: x[0])
    declared_counts = {count for _, count, _ in shard_dirs}
    if len(declared_counts) != 1:
        raise ValueError(f"Inconsistent shard counts in directory names: {sorted(declared_counts)}")
    shard_count = declared_counts.pop()
    indices = [idx for idx, _, _ in shard_dirs]
    expected_indices = list(range(1, shard_count + 1))
    if indices != expected_indices:
        raise ValueError(f"Incomplete shard set: found {indices}, expected {expected_indices}")

    replicate_frames = []
    summary_frames = []
    metadata = []
    for idx, count, directory in shard_dirs:
        meta_path = directory / "run_metadata.toml"
        rep_path = directory / cfg["replicate_file"]
        summary_path = directory / cfg["summary_file"]
        for required_path in (meta_path, rep_path, summary_path):
            if not required_path.exists():
                raise ValueError(f"Missing required shard file: {required_path}")

        meta = _load_metadata(meta_path)
        if meta.get("experiment") != experiment:
            raise ValueError(
                f"{meta_path} says experiment={meta.get('experiment')!r}, expected {experiment!r}"
            )
        if int(meta.get("shard_index", -1)) != idx or int(meta.get("shard_count", -1)) != count:
            raise ValueError(f"Shard metadata disagrees with directory name: {directory}")
        metadata.append(meta)

        rep = pd.read_csv(rep_path)
        summ = pd.read_csv(summary_path)
        _check_columns(rep, cfg["replicate_keys"], rep_path)
        _check_columns(summ, cfg["condition_keys"], summary_path)
        replicate_frames.append(rep)
        summary_frames.append(summ)

    _validate_metadata_consistency(metadata)
    full_run_counts = {int(m["full_run_count"]) for m in metadata}
    full_condition_counts = {int(m["full_condition_count"]) for m in metadata}
    if len(full_run_counts) != 1 or len(full_condition_counts) != 1:
        raise ValueError("Shard metadata disagree on full expected run or condition counts")
    expected_runs = full_run_counts.pop()
    expected_base_conditions = full_condition_counts.pop()

    reps = pd.concat(replicate_frames, ignore_index=True)
    summaries = pd.concat(summary_frames, ignore_index=True)

    duplicate_runs = reps.duplicated(cfg["replicate_keys"], keep=False)
    if duplicate_runs.any():
        examples = reps.loc[duplicate_runs, cfg["replicate_keys"]].head(5).to_dict("records")
        raise ValueError(f"Duplicate replicate keys found, examples: {examples}")
    if len(reps) != expected_runs:
        raise ValueError(f"Merged {len(reps)} replicate rows, expected {expected_runs}")

    duplicate_conditions = summaries.duplicated(cfg["condition_keys"], keep=False)
    if duplicate_conditions.any():
        examples = summaries.loc[duplicate_conditions, cfg["condition_keys"]].head(5).to_dict("records")
        raise ValueError(f"Duplicate condition summaries found, examples: {examples}")

    expected_summary_rows = expected_base_conditions
    if experiment == "algorithmic_controls":
        expected_summary_rows *= len(metadata[0]["search_modes"]) * len(metadata[0]["update_modes"])
    elif experiment == "distribution_controls":
        expected_summary_rows *= len(metadata[0]["trait_families"])
    if len(summaries) != expected_summary_rows:
        raise ValueError(
            f"Merged {len(summaries)} condition-summary rows, expected {expected_summary_rows}"
        )

    reps = reps.sort_values(cfg["replicate_keys"]).reset_index(drop=True)
    summaries = summaries.sort_values(cfg["condition_keys"]).reset_index(drop=True)
    output = Path(output) if output is not None else root / "merged"
    output.mkdir(parents=True, exist_ok=True)
    rep_out = output / cfg["replicate_file"]
    summary_out = output / cfg["summary_file"]
    reps.to_csv(rep_out, index=False)
    summaries.to_csv(summary_out, index=False)

    supplemental_counts = _merge_supplemental(
        shard_dirs, metadata, cfg.get("supplemental", []), output
    )

    report = {
        "experiment": experiment,
        "source_root": str(root),
        "shard_count": shard_count,
        "replicate_rows": len(reps),
        "condition_summary_rows": len(summaries),
        "supplemental_rows": supplemental_counts,
        "replicate_keys": cfg["replicate_keys"],
        "condition_keys": cfg["condition_keys"],
        "source_directories": [str(d) for _, _, d in shard_dirs],
        "replicate_output": str(rep_out),
        "summary_output": str(summary_out),
    }
    with (output / "merge_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", required=True, choices=sorted(EXPERIMENTS))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = merge_shards(args.root, args.experiment, args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
