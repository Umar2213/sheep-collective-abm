"""Evaluate already held-out heading predictions on identical biological blocks.

This module does not fit models or certify training/test independence. Predictions
must be generated using training-only preprocessing, social ties and parameters.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from trajectory_validation import KEY_COLUMNS, circular_absolute_error, _missing_ids


def score_predictions(frame, *, block_columns=("group_id", "bout_id")):
    """Return per-model, per-block angular scores after enforcing matched coverage.

    Input has observation keys, model, observed_heading and predicted_heading.
    Every model must predict exactly the same observations, without duplicates.
    Angles are finite radians. Extra columns can identify a coarser block, e.g. day.
    """
    if not block_columns or len(set(block_columns)) != len(block_columns):
        raise ValueError("Provide unique, nonempty block_columns")
    if set(block_columns) & {"model", "observed_heading", "predicted_heading"}:
        raise ValueError("Block columns must identify biological units")
    required = list(dict.fromkeys([*KEY_COLUMNS, *block_columns, "model",
                                  "observed_heading", "predicted_heading"]))
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing prediction columns: {sorted(missing)}")
    data = frame.copy()
    if data.empty or _missing_ids(data, [*KEY_COLUMNS[:3], *block_columns, "model"]).any():
        raise ValueError("Nonempty predictions with complete identifiers required")
    data["timestamp"] = pd.to_datetime(data.timestamp, utc=True, errors="coerce", format="mixed")
    if data.timestamp.isna().any():
        raise ValueError("Unparseable prediction timestamps")
    keys = list(KEY_COLUMNS)
    if data.duplicated(["model", *keys]).any():
        raise ValueError("Duplicate model observation keys")
    models = list(data.model.unique())
    reference = data[data.model == models[0]].set_index(keys)
    for model in models[1:]:
        current = data[data.model == model].set_index(keys)
        if (len(current) != len(reference) or not current.index.isin(reference.index).all()):
            raise ValueError("Models must predict identical observation keys")
        current = current.reindex(reference.index)
        # Circularly equivalent observations are valid, including 0 versus 2*pi.
        if not np.allclose(circular_absolute_error(reference.observed_heading,
                                                   current.observed_heading), 0, atol=1e-12):
            raise ValueError("Observed headings disagree between models")
        for column in set(block_columns) - set(keys):
            if not current[column].equals(reference[column]):
                raise ValueError("Biological block assignments disagree between models")
    data["absolute_error"] = circular_absolute_error(data.observed_heading, data.predicted_heading)
    data["cosine_alignment"] = np.cos(data.absolute_error)
    return data.groupby(["model", *block_columns], as_index=False, sort=True).agg(
        n_observations=("absolute_error", "size"),
        mean_absolute_error=("absolute_error", "mean"),
        mean_cosine_alignment=("cosine_alignment", "mean"))


def compare_models(scores, reference, alternative, *, block_columns=("group_id", "bout_id"),
                   n_bootstrap=2000, seed=42):
    """Equal-block paired MAE difference, alternative minus reference, in radians.

    Percentile intervals resample complete paired blocks. Blocks must be reasonably
    independent for uncertainty interpretation. Bout blocks within the same flock
    may need coarsening. Negative differences favour the alternative model.
    """
    if reference == alternative:
        raise ValueError("Choose two distinct models")
    if isinstance(n_bootstrap, bool) or not isinstance(n_bootstrap, int) or n_bootstrap < 100:
        raise ValueError("n_bootstrap must be an integer >= 100")
    if not block_columns or len(set(block_columns)) != len(block_columns):
        raise ValueError("Provide unique, nonempty block_columns")
    keys = list(block_columns)
    if not set(["model", "mean_absolute_error", *keys]).issubset(scores.columns):
        raise ValueError("Missing block score columns")
    selected = scores[scores.model.isin([reference, alternative])]
    if _missing_ids(selected, keys).any() or selected.duplicated(["model", *keys]).any():
        raise ValueError("Complete unique model-block scores required")
    a = selected[selected.model == reference].set_index(keys).mean_absolute_error
    b = selected[selected.model == alternative].set_index(keys).mean_absolute_error
    if len(a) < 2 or len(a) != len(b) or not a.index.isin(b.index).all():
        raise ValueError("At least two identical biological blocks per model required")
    if not all(np.isfinite(v).all() and v.between(0, np.pi).all() for v in (a, b)):
        raise ValueError("Finite block angular errors in [0, pi] required")
    delta = (b.reindex(a.index) - a).to_numpy()
    rng = np.random.default_rng(seed)
    # One draw at a time keeps memory independent of bootstrap count.
    means = np.array([rng.choice(delta, size=len(delta), replace=True).mean()
                      for _ in range(n_bootstrap)])
    low, high = np.quantile(means, [0.025, 0.975])
    return {"reference": reference, "alternative": alternative, "n_blocks": len(delta),
            "mean_delta_mae": float(delta.mean()), "ci95_low": float(low),
            "ci95_high": float(high), "n_bootstrap": n_bootstrap, "seed": seed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--block-columns", nargs="+", default=["group_id", "bout_id"])
    args = parser.parse_args()
    scores = score_predictions(pd.read_csv(args.predictions), block_columns=args.block_columns)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(args.output, index=False)


if __name__ == "__main__":
    main()
