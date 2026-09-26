"""Reproducible trajectory preparation and blocked predictive comparisons.

This is an empirical-analysis implementation, not evidence of empirical validity.
All preprocessing settings are supplied in advance; nothing is tuned on test scores.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib
import json

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from trajectory_validation import validate_trajectory_table, assign_grouped_folds, KEY_COLUMNS
from identifiability import blended_heading, fit_responsiveness, wrap_angle
from prediction_evaluation import score_predictions, compare_models


@dataclass(frozen=True)
class AnalysisConfig:
    data_kind: str = "unspecified"
    coordinate_mode: str = "metric"
    crs: str = "local_metres"
    min_speed: float = 0.05
    max_speed: float = 15.0
    max_gap: float = 10.0
    max_accuracy: float = 10.0
    displacement_sigma: float = 2.0
    radius: float = 10.0
    n_folds: int = 3
    split_columns: tuple = ("group_id", "bout_id")
    uncertainty_columns: tuple = ("group_id",)
    min_individual_train: int = 10
    n_bootstrap: int = 2000
    shuffle_seeds: tuple = (11, 29, 47)
    seed: int = 42
    ties_independent: bool = False

    def validate(self):
        if not isinstance(self.ties_independent, bool):
            raise ValueError("ties_independent must be a JSON boolean, not a string or number")
        if self.data_kind not in ("synthetic", "observational", "unspecified"):
            raise ValueError("data_kind must be synthetic, observational or unspecified")
        if self.coordinate_mode not in ("metric", "gps"):
            raise ValueError("coordinate_mode must be metric or gps")
        for name in ("max_speed", "max_gap", "max_accuracy", "radius"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v <= 0:
                raise ValueError(f"{name} must be finite and positive")
        for name in ("min_speed", "displacement_sigma"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.min_speed >= self.max_speed:
            raise ValueError("min_speed must be below max_speed")
        for name, minimum in (("n_folds", 2), ("min_individual_train", 3), ("n_bootstrap", 100)):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        if self.n_bootstrap > 100000:
            raise ValueError("n_bootstrap exceeds 100000")
        if not self.crs:
            raise ValueError("A coordinate reference system is required")
        allowed = {"group_id", "bout_id"}
        for columns in (self.split_columns, self.uncertainty_columns):
            if not columns or len(set(columns)) != len(columns) or not set(columns) <= allowed:
                raise ValueError("Unique group_id and/or bout_id blocking columns required")
        if "group_id" not in self.split_columns or "group_id" not in self.uncertainty_columns:
            raise ValueError("Blocking must include group_id to avoid collisions between sessions")
        if not set(self.uncertainty_columns) <= set(self.split_columns):
            raise ValueError("Uncertainty units must be at least as coarse as split units")
        if len(set(self.shuffle_seeds)) != len(self.shuffle_seeds) or len(self.shuffle_seeds) > 20:
            raise ValueError("Provide up to 20 unique shuffle seeds")
        if any(isinstance(s, bool) or not isinstance(s, int) or s < 0 for s in (*self.shuffle_seeds, self.seed)):
            raise ValueError("Seeds must be nonnegative integers")


def read_table(path):
    """Preserve literal identifiers, including leading zeros and the string NA."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _project(frame, config):
    data = frame.copy()
    if config.coordinate_mode == "gps":
        from pyproj import CRS, Transformer
        if not {"latitude", "longitude"} <= set(data):
            raise ValueError("GPS requires latitude and longitude columns")
        lat = pd.to_numeric(data.latitude, errors="coerce").to_numpy()
        lon = pd.to_numeric(data.longitude, errors="coerce").to_numpy()
        if not (np.isfinite(lat).all() and np.isfinite(lon).all()) or np.any(abs(lat) > 90) or np.any(abs(lon) > 180):
            raise ValueError("GPS coordinates must be finite WGS84 decimal degrees")
        target = CRS.from_user_input(config.crs)
        if not target.is_projected or any(abs(a.unit_conversion_factor - 1) > 1e-10 for a in target.axis_info[:2]):
            raise ValueError("GPS target CRS must be projected with metre units")
        area = target.area_of_use
        if area:
            lon_ok = ((lon >= area.west) & (lon <= area.east)) if area.west <= area.east else ((lon >= area.west) | (lon <= area.east))
            if not (lon_ok & (lat >= area.south) & (lat <= area.north)).all():
                raise ValueError("GPS positions lie outside the target CRS area of use")
        transformer = Transformer.from_crs("EPSG:4326", target, always_xy=True, allow_ballpark=False)
        data["x"], data["y"] = transformer.transform(lon, lat, errcheck=True)
    elif config.crs != "local_metres":
        from pyproj import CRS
        target = CRS.from_user_input(config.crs)
        if not target.is_projected or any(abs(a.unit_conversion_factor - 1) > 1e-10 for a in target.axis_info[:2]):
            raise ValueError("Metric coordinates require a projected CRS with metre units, or local_metres")
    return data


def prepare_trajectories(frame, config):
    config.validate()
    data = _project(frame, config)
    # Do not guess a timezone, even though the legacy audit can coerce naive times.
    if "timestamp" not in data or not data.timestamp.astype(str).str.match(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
    ).all():
        raise ValueError("Timestamps require ISO 8601 with explicit timezone")
    for col in KEY_COLUMNS[:3]:
        if col in data:
            data[col] = data[col].map(lambda v: v.strip() if isinstance(v, str) else v)
    data, audit = validate_trajectory_table(data)
    # The same fix cannot belong to different held-out bouts.
    if data.duplicated(["group_id", "individual_id", "timestamp"]).any():
        raise ValueError("Overlapping bouts reuse an individual timestamp; resolve session boundaries before splitting")
    accuracy_present = "accuracy_m" in data
    if accuracy_present:
        acc = pd.to_numeric(data.accuracy_m, errors="coerce")
        if not np.isfinite(acc).all() or (acc < 0).any():
            raise ValueError("accuracy_m must contain finite nonnegative values in every row")
        data["accuracy_m"] = acc
    else:
        data["accuracy_m"] = 0.0
    data["fix_usable"] = data.accuracy_m <= config.max_accuracy
    group = data.groupby(list(KEY_COLUMNS[:3]), sort=False)
    data["previous_time"] = group.timestamp.shift()
    data["dt"] = (data.timestamp - data.previous_time).dt.total_seconds()
    dx = data.x - group.x.shift()
    dy = data.y - group.y.shift()
    data["distance"] = np.hypot(dx, dy)
    data["speed"] = data.distance / data.dt
    good = (data.dt > 0) & (data.dt <= config.max_gap) & data.fix_usable & group.fix_usable.shift().eq(True) & (data.speed <= config.max_speed)
    data["interval_usable"] = good
    floor = config.displacement_sigma * np.hypot(data.accuracy_m, group.accuracy_m.shift())
    heading_good = good & (data.speed > config.min_speed) & (data.distance > floor)
    data["heading"] = np.where(heading_good, np.arctan2(dy, dx), np.nan)
    data["speed"] = data.speed.where(good)
    warnings = []
    if not accuracy_present:
        warnings.append("No accuracy_m supplied: GPS uncertainty was not quantified or removed.")
    warnings.append("No interpolation, resampling or smoothing. Speed and displacement thresholds were fixed before fitting.")
    flags = {"long_gaps": int((data.dt > config.max_gap).sum()),
             "poor_accuracy_fixes": int((~data.fix_usable).sum()),
             "overspeed_intervals": int(((data.distance / data.dt) > config.max_speed).sum()),
             "unusable_headings": int(data.heading.isna().sum()),
             "accuracy_supplied": accuracy_present}
    return data, {"structural": audit.to_dict(), "filters": flags, "warnings": warnings}


def individual_bout_summary(data):
    """Descriptive track summaries, not independent-frame inference or repeatability."""
    rows = []
    for keys, track in data.groupby(list(KEY_COLUMNS[:3]), sort=True):
        valid = track[track.interval_usable]
        duration = float(valid.dt.sum())
        distance = float(valid.distance.sum())
        rows.append(dict(zip(KEY_COLUMNS[:3], keys),
                         observations=len(track), usable_intervals=len(valid),
                         usable_headings=int(track.heading.notna().sum()),
                         observed_span_s=float((track.timestamp.max()-track.timestamp.min()).total_seconds()),
                         usable_duration_s=duration, path_length_m=distance,
                         time_weighted_speed_m_s=distance/duration if duration else np.nan))
    return pd.DataFrame(rows)


def movement_summary(data):
    rows = []
    for keys, frame in data.groupby(["group_id", "bout_id", "timestamp"], sort=True):
        available = frame[frame.fix_usable]
        moving = available[available.heading.notna()]
        eligible = len(moving) >= 2 and moving.previous_time.nunique() == 1
        phi = float(np.hypot(np.cos(moving.heading).mean(), np.sin(moving.heading).mean())) if eligible else np.nan
        spread = float(np.sqrt(((available.x - available.x.mean())**2 + (available.y - available.y.mean())**2).mean())) if len(available) >= 2 else np.nan
        rows.append(dict(zip(["group_id", "bout_id", "timestamp"], keys),
                         observed=len(available), moving=len(moving), alignment=phi,
                         spread_m=spread, mean_speed_m_s=available.speed.mean()))
    return pd.DataFrame(rows)


def validate_ties(ties, data, config):
    if ties is None:
        return None
    if config.ties_independent is not True:
        raise ValueError("Social ties must be declared independent of all analysed sessions")
    cols = ["group_id", "focal_id", "neighbour_id", "weight"]
    if not set(cols) <= set(ties) or ties.empty:
        raise ValueError("Nonempty social ties require group_id, focal_id, neighbour_id, weight")
    t = ties[cols].copy()
    for col in cols[:3]:
        if t[col].isna().any() or t[col].astype(str).str.strip().eq("").any():
            raise ValueError("Social tie identifiers must be complete")
        t[col] = t[col].astype(str).str.strip()
    t.weight = pd.to_numeric(t.weight, errors="coerce")
    if not np.isfinite(t.weight).all() or (t.weight < 0).any() or t.duplicated(cols[:3]).any():
        raise ValueError("Social weights must be finite, nonnegative and unique")
    if (t.focal_id == t.neighbour_id).any():
        raise ValueError("Self ties are not allowed")
    lookup = {(r.group_id, r.focal_id, r.neighbour_id): r.weight for r in t.itertuples()}
    expected = set()
    for g, frame in data.groupby("group_id"):
        ids = sorted(frame.individual_id.unique())
        expected |= {(g, i, j) for i in ids for j in ids if i != j}
    if set(lookup) != expected:
        raise ValueError("Supply exactly every directed non-self pair for every group, with explicit zero weights where needed")
    return lookup


def shuffled_ties(lookup, data, seed):
    """Relabel entire directed networks, preserving topology and weight distribution."""
    result = {}
    for g, frame in data.groupby("group_id", sort=True):
        ids = sorted(frame.individual_id.unique())
        digest = int.from_bytes(hashlib.sha256(str(g).encode()).digest()[:8], "big")
        rng = np.random.default_rng(np.random.SeedSequence([seed, digest]))
        permutation = rng.permutation(ids)
        # Exclude the identity relabelling; this remains a control, not a p-value.
        if list(permutation) == ids:
            permutation = np.roll(permutation, 1)
        mapping = dict(zip(ids, permutation))
        for i in ids:
            for j in ids:
                if i != j:
                    result[g, i, j] = lookup[g, mapping[i], mapping[j]]
    return result


def construct_features(data, config, ties=None):
    data = data.copy()
    track = data.groupby(list(KEY_COLUMNS[:3]), sort=False)
    data["target"] = track.heading.shift(-1)
    data["target_time"] = track.timestamp.shift(-1)
    data["target_dt"] = track.dt.shift(-1)
    data["past_heading"] = track.heading.shift(1)
    data["past_dt"] = track.dt.shift(1)
    networks = {"social": ties} if ties is not None else {}
    if ties is not None:
        networks.update({f"shuffle_{s}": shuffled_ties(ties, data, s) for s in config.shuffle_seeds})
    rows = []
    rejected = {"heading_or_target_missing": 0, "unequal_intervals": 0}
    for (g, b, time), frame in data.groupby(["group_id", "bout_id", "timestamp"], sort=True):
        available = frame[frame.heading.notna()]
        if len(available):
            tree = cKDTree(available[["x", "y"]].to_numpy())
        for r in frame.itertuples():
            if not np.isfinite(r.heading) or not np.isfinite(r.target):
                rejected["heading_or_target_missing"] += 1
                continue
            if not np.isclose(r.dt, r.target_dt, rtol=0, atol=1e-6):
                rejected["unequal_intervals"] += 1
                continue
            candidates = available.iloc[tree.query_ball_point([r.x, r.y], config.radius)]
            nb = candidates[(candidates.individual_id != r.individual_id) & (candidates.previous_time == r.previous_time)]
            distances = np.hypot(nb.x-r.x, nb.y-r.y).to_numpy()
            heading = nb.heading.to_numpy()
            vectors = {}
            for name, weights in [("uniform", np.ones(len(nb))), ("distance", np.exp(-distances/config.radius)), *[(name, np.array([lookup[g, r.individual_id, j] for j in nb.individual_id])) for name, lookup in networks.items()]]:
                if not len(weights) or not np.any(weights > 0):
                    # Exact no-neighbour fallback retains self for every r.
                    nx, ny = np.cos(r.heading), np.sin(r.heading)
                else:
                    weights = weights / weights.max()
                    nx, ny = np.average(np.cos(heading), weights=weights), np.average(np.sin(heading), weights=weights)
                vectors[name+"_x"], vectors[name+"_y"] = float(nx), float(ny)
            turn = float(wrap_angle(r.heading-r.past_heading)) if np.isfinite(r.past_heading) and np.isclose(r.past_dt, r.dt, atol=1e-6, rtol=0) else 0.0
            rows.append({"group_id": g, "bout_id": b, "individual_id": r.individual_id,
                         "timestamp": r.target_time, "predictor_timestamp": time,
                         "self_heading": r.heading, "observed_heading": r.target,
                         "turn_prediction": float(wrap_angle(r.heading+turn)),
                         "n_neighbours": len(nb), **vectors})
    if not rows:
        raise ValueError("No eligible heading transitions after fixed quality filters")
    return pd.DataFrame(rows), rejected


def make_folds(data, config, supplied=None):
    cols = list(config.split_columns)
    blocks = data[cols].drop_duplicates()
    if supplied is None:
        return assign_grouped_folds(blocks, block_columns=cols, n_folds=config.n_folds, salt=f"analysis-{config.seed}")
    if not set([*cols, "fold"]) <= set(supplied):
        raise ValueError("Frozen folds require split columns and fold")
    folds = supplied[[*cols, "fold"]].copy()
    if folds.duplicated(cols).any() or folds[cols].isna().any().any():
        raise ValueError("Frozen fold blocks must be complete and unique")
    n = pd.to_numeric(folds.fold, errors="coerce")
    if not np.isfinite(n).all() or (n != n.astype(int)).any() or set(n) != set(range(config.n_folds)):
        raise ValueError("Frozen folds must populate exactly 0 through n_folds-1")
    folds.fold = n.astype(int)
    if set(map(tuple, folds[cols].to_numpy())) != set(map(tuple, blocks.to_numpy())):
        raise ValueError("Frozen fold coverage must exactly match input blocks")
    return folds.sort_values(cols).reset_index(drop=True)


def _fit(train, vector):
    try:
        out = fit_responsiveness(train.self_heading.to_numpy(), train[vector+"_x"].to_numpy(), train[vector+"_y"].to_numpy(), train.observed_heading.to_numpy())
        return {**out, "status": "estimated"}
    except ValueError as e:
        if "flat loss" not in str(e):
            raise
        # Do not publish a made-up estimate. Use persistence as an explicit fallback.
        return {"responsiveness": 0.0, "n": len(train), "status": "flat_loss_persistence_fallback", "ambiguous_profile": True}


def fit_predict(features, folds, config, has_ties=False):
    f = features.merge(folds, on=list(config.split_columns), validate="many_to_one")
    if f.fold.isna().any() or set(f.fold) != set(range(config.n_folds)):
        raise ValueError("Every frozen fold must retain eligible transitions")
    definitions = [("M0", "uniform", False), ("M1", "uniform", True), ("distance", "distance", False)]
    if has_ties:
        definitions += [("M2", "social", False), ("M3", "social", True)]
        definitions += [(f"shuffle_{s}", f"shuffle_{s}", True) for s in config.shuffle_seeds]
    predictions, parameters = [], []
    for fold in range(config.n_folds):
        train, test = f[f.fold != fold], f[f.fold == fold]
        if len(train) < 3 or len(test) < 1:
            raise ValueError("Insufficient train or test observations")
        keys = test[list(KEY_COLUMNS)].copy()
        keys["observed_heading"] = test.observed_heading
        keys["fold"] = fold
        keys["predictor_timestamp"] = test.predictor_timestamp
        for label, angles in [("persistence", test.self_heading), ("constant_turn", test.turn_prediction)]:
            predictions.append(keys.assign(model=label, predicted_heading=np.asarray(angles)))
        for label, vector, individual in definitions:
            common = _fit(train, vector)
            parameters.append({"fold": fold, "model": label, "group_id": "", "individual_id": "", **common})
            pred = np.empty(len(test))
            for (g, i), indices in test.reset_index(drop=True).groupby(["group_id", "individual_id"]).groups.items():
                part = test.iloc[indices]
                estimate = common
                if individual:
                    own = train[(train.group_id == g) & (train.individual_id == i)]
                    if len(own) >= config.min_individual_train:
                        estimate = _fit(own, vector)
                    else:
                        estimate = {**common, "status": "insufficient_individual_training_common_fallback"}
                    parameters.append({"fold": fold, "model": label, "group_id": g, "individual_id": i, **estimate})
                pred[indices] = blended_heading(part.self_heading.to_numpy(), part[vector+"_x"].to_numpy(), part[vector+"_y"].to_numpy(), estimate["responsiveness"])
            predictions.append(keys.assign(model=label, predicted_heading=pred))
    result = pd.concat(predictions, ignore_index=True)
    score_predictions(result)  # strict matched-key and common-target assertion
    return result.sort_values(["model", *KEY_COLUMNS]).reset_index(drop=True), pd.DataFrame(parameters)


def evaluate(predictions, config):
    scores = score_predictions(predictions, block_columns=config.uncertainty_columns)
    models = sorted(scores.model.unique())
    pairs = [("M0", "M1"), ("persistence", "M0"), ("constant_turn", "M0"), ("distance", "M0")]
    if "M3" in models:
        pairs += [("M0", "M2"), ("distance", "M2")]
        pairs += [(ref, "M3") for ref in ("M0", "M1", "M2", "persistence", "constant_turn", "distance")]
        pairs += [(m, "M3") for m in models if m.startswith("shuffle_")]
    n_units = scores[list(config.uncertainty_columns)].drop_duplicates().shape[0]
    comparisons = []
    for reference, alternative in pairs:
        if n_units >= 2:
            comparison = compare_models(scores, reference, alternative, block_columns=config.uncertainty_columns, n_bootstrap=config.n_bootstrap, seed=config.seed)
            comparison["status"] = "conditional_paired_cluster_bootstrap"
        else:
            a = scores[scores.model == alternative].mean_absolute_error.mean()
            b = scores[scores.model == reference].mean_absolute_error.mean()
            comparison = dict(reference=reference, alternative=alternative, n_blocks=n_units,
                              mean_delta_mae=float(a-b), ci95_low=None, ci95_high=None,
                              status="interval_unavailable_fewer_than_two_units")
        comparisons.append(comparison)
    return scores, pd.DataFrame(comparisons)


def run_pipeline(frame, config, ties=None, folds=None):
    prepared, audit = prepare_trajectories(frame, config)
    network = validate_ties(ties, prepared, config)
    frozen = make_folds(prepared, config, folds)
    features, excluded = construct_features(prepared, config, network)
    predictions, parameters = fit_predict(features, frozen, config, network is not None)
    scores, comparisons = evaluate(predictions, config)
    audit["data_kind"] = config.data_kind
    audit["distinct_group_animal_ids"] = prepared[["group_id", "individual_id"]].drop_duplicates().shape[0]
    audit["excluded_transitions"] = excluded
    audit["eligible_transitions"] = len(features)
    audit["uncertainty_units"] = scores[list(config.uncertainty_columns)].drop_duplicates().shape[0]
    audit["warnings"] += [
        "Uncertainty intervals condition on fitted cross-validation predictions; they do not refit the full pipeline or correct multiple comparisons.",
        "Declare reasonably independent uncertainty units before analysis; a small unit count gives weak interval estimates.",
        "Network relabellings are negative controls, not a permutation significance test.",
        "Prediction gains do not establish causality, novelty or parameter identifiability.",
        "No free outgoing-influence parameter is estimated alongside unrestricted ties."]
    if audit["uncertainty_units"] < 5:
        audit["warnings"].append("Fewer than five uncertainty units: interpret uncertainty as exploratory.")
    return dict(prepared=prepared, audit=audit, features=features, folds=frozen,
                movement=movement_summary(prepared), individual_bouts=individual_bout_summary(prepared), predictions=predictions,
                parameters=parameters, scores=scores, comparisons=comparisons,
                config=asdict(config))
