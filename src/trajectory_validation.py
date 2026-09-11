#!/usr/bin/env python3
"""Structural validation utilities for empirical sheep trajectory tables.

The functions here deliberately validate and report data problems rather than silently
interpolating, smoothing, resampling or imputing observations.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = (
    "group_id",
    "bout_id",
    "individual_id",
    "timestamp",
    "x",
    "y",
)
KEY_COLUMNS = ("group_id", "bout_id", "individual_id", "timestamp")


@dataclass(frozen=True)
class TrajectoryAudit:
    rows: int
    groups: int
    bouts: int
    individuals: int
    tracks: int
    missing_identifiers: int
    duplicate_keys: int
    nonfinite_coordinates: int
    unparseable_timestamps: int
    single_individual_bouts: int
    nonpositive_time_steps: int
    median_sampling_interval_seconds: float | None
    min_sampling_interval_seconds: float | None
    max_sampling_interval_seconds: float | None
    min_track_observations: int
    median_track_observations: float
    max_track_observations: int

    def to_dict(self) -> dict:
        return asdict(self)


def _require_columns(frame: pd.DataFrame, required: Sequence[str] = REQUIRED_COLUMNS) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required trajectory columns: {missing}")


def _missing_ids(frame, columns):
    return frame[list(columns)].isna().any(axis=1) | frame[list(columns)].apply(
        lambda col: col.map(lambda value: isinstance(value, str) and not value.strip())
    ).any(axis=1)


def _parsed_copy(frame: pd.DataFrame) -> pd.DataFrame:
    _require_columns(frame)
    data = frame.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce", utc=True, format="mixed")
    data["x"] = pd.to_numeric(data["x"], errors="coerce")
    data["y"] = pd.to_numeric(data["y"], errors="coerce")
    return data


def audit_trajectory_table(frame: pd.DataFrame) -> TrajectoryAudit:
    """Return a non-destructive structural audit of a trajectory table."""
    data = _parsed_copy(frame)
    duplicate_keys = int(data.duplicated(list(KEY_COLUMNS), keep=False).sum())
    unparseable_timestamps = int(data["timestamp"].isna().sum())
    finite_xy = np.isfinite(data["x"].to_numpy(dtype=float)) & np.isfinite(
        data["y"].to_numpy(dtype=float)
    )
    nonfinite_coordinates = int((~finite_xy).sum())

    bout_sizes = data.groupby(["group_id", "bout_id"], dropna=False)["individual_id"].nunique()
    single_individual_bouts = int((bout_sizes < 2).sum())

    track_keys = ["group_id", "bout_id", "individual_id"]
    track_sizes = data.groupby(track_keys, dropna=False).size()
    if len(track_sizes):
        min_track = int(track_sizes.min())
        median_track = float(track_sizes.median())
        max_track = int(track_sizes.max())
    else:
        min_track = 0
        median_track = 0.0
        max_track = 0

    valid_time = data.dropna(subset=["timestamp"]).sort_values(track_keys + ["timestamp"])
    deltas = (
        valid_time.groupby(track_keys, dropna=False)["timestamp"]
        .diff()
        .dt.total_seconds()
        .dropna()
    )
    nonpositive_time_steps = int((deltas <= 0).sum())
    positive_deltas = deltas[deltas > 0]
    if len(positive_deltas):
        median_dt = float(positive_deltas.median())
        min_dt = float(positive_deltas.min())
        max_dt = float(positive_deltas.max())
    else:
        median_dt = min_dt = max_dt = None

    return TrajectoryAudit(
        rows=int(len(data)),
        groups=int(data["group_id"].nunique(dropna=False)),
        bouts=int(data[["group_id", "bout_id"]].drop_duplicates().shape[0]),
        individuals=int(data["individual_id"].nunique(dropna=False)),
        tracks=int(len(track_sizes)),
        missing_identifiers=int(_missing_ids(data, KEY_COLUMNS[:3]).sum()),
        duplicate_keys=duplicate_keys,
        nonfinite_coordinates=nonfinite_coordinates,
        unparseable_timestamps=unparseable_timestamps,
        single_individual_bouts=single_individual_bouts,
        nonpositive_time_steps=nonpositive_time_steps,
        median_sampling_interval_seconds=median_dt,
        min_sampling_interval_seconds=min_dt,
        max_sampling_interval_seconds=max_dt,
        min_track_observations=min_track,
        median_track_observations=median_track,
        max_track_observations=max_track,
    )


def validate_trajectory_table(frame: pd.DataFrame) -> tuple[pd.DataFrame, TrajectoryAudit]:
    """Validate fatal structural conditions and return a sorted parsed copy plus audit.

    No interpolation, smoothing, imputation or resampling is performed.
    """
    data = _parsed_copy(frame)
    audit = audit_trajectory_table(data)
    failures = []
    if not len(data):
        failures.append("empty trajectory table")
    if audit.missing_identifiers:
        failures.append(f"{audit.missing_identifiers} rows with missing identifiers")
    if audit.unparseable_timestamps:
        failures.append(f"{audit.unparseable_timestamps} unparseable timestamps")
    if audit.nonfinite_coordinates:
        failures.append(f"{audit.nonfinite_coordinates} rows with nonfinite coordinates")
    if audit.duplicate_keys:
        failures.append(f"{audit.duplicate_keys} rows participating in duplicate observation keys")
    if audit.single_individual_bouts:
        failures.append(f"{audit.single_individual_bouts} bouts contain fewer than two individuals")
    if audit.nonpositive_time_steps:
        failures.append(f"{audit.nonpositive_time_steps} nonpositive within-track time steps")
    if failures:
        raise ValueError("Trajectory validation failed: " + "; ".join(failures))

    sort_columns = ["group_id", "bout_id", "individual_id", "timestamp"]
    return data.sort_values(sort_columns).reset_index(drop=True), audit


def _stable_fold_key(values: Iterable[object], salt: str = "sheep-collective-abm") -> int:
    raw = json.dumps([str(value) for value in values], ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256((salt + "\x1e" + raw).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def assign_grouped_folds(
    frame: pd.DataFrame,
    *,
    block_columns: Sequence[str] = ("group_id", "bout_id"),
    n_folds: int = 5,
    salt: str = "sheep-collective-abm",
    fold_column: str = "fold",
) -> pd.DataFrame:
    """Assign deterministic folds without splitting any complete biological block."""
    if isinstance(n_folds, bool) or not isinstance(n_folds, int) or n_folds < 2:
        raise ValueError("n_folds must be an integer >= 2")
    missing = [column for column in block_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing blocking columns: {missing}")
    if not block_columns:
        raise ValueError("block_columns must contain at least one column")

    if fold_column in frame.columns:
        raise ValueError(f"Fold column already exists: {fold_column}")
    if len(set(block_columns)) != len(block_columns):
        raise ValueError("Blocking columns must be unique")
    if _missing_ids(frame, block_columns).any():
        raise ValueError("Missing identifiers in blocking columns")
    if frame[list(block_columns)].drop_duplicates().shape[0] < n_folds:
        raise ValueError("At least n_folds distinct biological blocks are required")
    result = frame.copy()
    blocks = result[list(block_columns)].drop_duplicates().copy()
    hashes = [_stable_fold_key(values, salt=salt)
              for values in blocks.itertuples(index=False, name=None)]
    order = np.argsort(hashes, kind="stable")
    folds = np.empty(len(blocks), dtype=int)
    folds[order] = np.arange(len(blocks)) % n_folds
    blocks[fold_column] = folds
    result = result.merge(blocks, on=list(block_columns), how="left", validate="many_to_one")
    if result[fold_column].isna().any():
        raise RuntimeError("Fold assignment unexpectedly produced missing fold values")

    leakage = result.groupby(list(block_columns), dropna=False)[fold_column].nunique()
    if (leakage != 1).any():
        raise RuntimeError("A biological block was assigned to more than one fold")
    result[fold_column] = result[fold_column].astype(int)
    return result


def circular_absolute_error(observed_heading, predicted_heading) -> np.ndarray:
    """Absolute angular error in radians, wrapped to [0, pi]."""
    observed = np.asarray(observed_heading, dtype=float)
    predicted = np.asarray(predicted_heading, dtype=float)
    if observed.shape != predicted.shape:
        raise ValueError("Observed and predicted headings must have matching shapes")
    if observed.size == 0 or not (np.isfinite(observed).all() and np.isfinite(predicted).all()):
        raise ValueError("At least one finite heading pair is required")
    delta = np.arctan2(np.sin(predicted - observed), np.cos(predicted - observed))
    return np.abs(delta)


def mean_cosine_alignment(observed_heading, predicted_heading) -> float:
    """Mean cos(predicted-observed), 1 is perfect, 0 is orthogonal on average."""
    observed = np.asarray(observed_heading, dtype=float)
    predicted = np.asarray(predicted_heading, dtype=float)
    if observed.shape != predicted.shape:
        raise ValueError("Observed and predicted headings must have matching shapes")
    circular_absolute_error(observed, predicted)
    return float(np.mean(np.cos(predicted - observed)))
