#!/usr/bin/env python3
"""Merge complete-condition simulation shards after verifying coverage and uniqueness."""

from __future__ import annotations

import argparse
import json
import hashlib
import itertools
import shutil
import tempfile

import numpy as np
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
        "recorded_utc", "threads",
    }
    reference = {k: v for k, v in metadata[0].items() if k not in ignored}
    for idx, meta in enumerate(metadata[1:], start=2):
        current = {k: v for k, v in meta.items() if k not in ignored}
        if current != reference:
            differing = sorted(k for k in set(reference) | set(current) if reference.get(k) != current.get(k))
            raise ValueError(f"Shard metadata are inconsistent, shard {idx} differs in: {differing}")


def _key_set(frame, keys):
    if frame[keys].isna().any().any():
        raise ValueError("Missing values in scientific keys")
    # Julia ranges and CSV parsers can differ in their final floating-point bit.
    return {tuple(round(v, 12) if isinstance(v, (float, np.floating)) else v
                  for v in row)
            for row in frame[keys].itertuples(index=False, name=None)}


def _expected_design(meta, cfg):
    axes = {"sigma_std": meta["sigma"], "noise": meta["noise"],
            "N": meta.get("N"), "search_mode": meta.get("search_modes"),
            "update_mode": meta.get("update_modes"),
            "trait_distribution": meta.get("trait_families"),
            "control": ["approximate_minus_exact", "synchronous_minus_sequential"]}
    for name in ("trait", "dynamic"):
        count = meta[f"{name}_replicates"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError(f"{name}_replicates must be a positive integer")
        axes[f"{name}_rep"] = list(range(1, count + 1))
    return axes


def _check_design(frame, keys, axes, filename):
    expected = pd.DataFrame(itertools.product(*(axes[k] for k in keys)), columns=keys)
    actual_keys, expected_keys = _key_set(frame, keys), _key_set(expected, keys)
    if actual_keys != expected_keys or len(frame) != len(expected_keys):
        raise ValueError(f"Incomplete or unexpected design keys in {filename}: "
                         f"{len(expected_keys - actual_keys)} missing, "
                         f"{len(actual_keys - expected_keys)} unexpected")


def _check_values(frame, filename):
    numeric = frame.select_dtypes(include="number")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all() or frame.isna().any().any():
        raise ValueError(f"Missing or nonfinite values in {filename}")


def _merge_supplemental(shard_dirs, metadata, specs, axes):
    tables = {}
    for spec in specs:
        frames = []
        filename = spec["file"]
        for _, _, directory in shard_dirs:
            path = directory / filename
            if not path.exists():
                raise ValueError(f"Missing required shard file: {path}")
            frame = pd.read_csv(path)
            _check_columns(frame, spec["keys"], path)
            _check_values(frame, path)
            if frames and list(frame.columns) != list(frames[0].columns):
                raise ValueError(f"Inconsistent columns in {filename}")
            frames.append(frame)
        merged = pd.concat(frames, ignore_index=True)
        if merged.duplicated(spec["keys"], keep=False).any():
            raise ValueError(f"Duplicate keys found in {filename}")
        _check_design(merged, spec["keys"], axes, filename)
        if len(merged) != int(spec["rows"](metadata[0])):
            raise ValueError(f"Unexpected row count in {filename}")
        tables[filename] = merged.sort_values(spec["keys"]).reset_index(drop=True)
    return tables


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
        _check_values(rep, rep_path)
        _check_values(summ, summary_path)
        if replicate_frames and list(rep.columns) != list(replicate_frames[0].columns):
            raise ValueError("Inconsistent replicate columns across shards")
        if summary_frames and list(summ.columns) != list(summary_frames[0].columns):
            raise ValueError("Inconsistent summary columns across shards")
        if "shard_run_count" in meta and len(rep) != meta["shard_run_count"]:
            raise ValueError(f"Incorrect shard run count in {directory}")
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

    axes = _expected_design(metadata[0], cfg)
    _check_design(reps, cfg["replicate_keys"], axes, cfg["replicate_file"])
    _check_design(summaries, cfg["condition_keys"], axes, cfg["summary_file"])
    # Detect stale summaries, not just their presence.
    if "phi" in reps and "phi_mean" in summaries:
        computed = reps.groupby(cfg["condition_keys"], as_index=False).agg(
            computed_mean=("phi", "mean"), computed_n=("phi", "size"))
        checked = summaries.merge(computed, on=cfg["condition_keys"], validate="one_to_one")
        if not np.allclose(checked.phi_mean, checked.computed_mean, rtol=1e-10, atol=1e-12):
            raise ValueError("Condition phi_mean does not reproduce from replicate rows")
        if "n" in checked and not (checked.n == checked.computed_n).all():
            raise ValueError("Condition n does not match replicate count")

    reps = reps.sort_values(cfg["replicate_keys"]).reset_index(drop=True)
    summaries = summaries.sort_values(cfg["condition_keys"]).reset_index(drop=True)
    supplemental = _merge_supplemental(
        shard_dirs, metadata, cfg.get("supplemental", []), axes)
    supplemental_counts = {name: len(table) for name, table in supplemental.items()}
    output = Path(output) if output is not None else root / "merged"
    if output.exists():
        raise ValueError(f"Output already exists; choose a fresh --output directory: {output}")
    rep_out = output / cfg["replicate_file"]
    summary_out = output / cfg["summary_file"]

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
    # Validate everything before publishing a complete directory. A bad supplemental
    # table must never leave a plausible-looking partial merged dataset behind.
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".merge-", dir=output.parent))
    try:
        tables = {cfg["replicate_file"]: reps, cfg["summary_file"]: summaries, **supplemental}
        for name, table in tables.items():
            table.to_csv(staging / name, index=False)
        report["output_sha256"] = {
            name: hashlib.sha256((staging / name).read_bytes()).hexdigest() for name in tables}
        report["source_metadata"] = metadata
        (staging / "merge_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
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
