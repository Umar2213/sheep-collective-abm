"""Responsiveness recovery under location error, missing fixes and coarser sampling.

WP4 gate: before interpreting fitted responsiveness, check whether the production
preprocessing and feature code can recover known values under realistic observation
conditions. This simulates groups with known individual responsiveness (the seeded
synthetic generator), degrades the observations, runs prepare_trajectories,
validate_ties and construct_features unchanged, then fits each individual's
responsiveness on all of its eligible transitions.

Two kernels are fitted: "social" uses the generating directed weights, "uniform"
ignores them, as M1 does. The simulation and fitting share one model family, so good
recovery here is a necessary software and design check, never biological validation.
Simulated responsiveness applies to one native time step. With subsample > 1 the
one-step estimand changes, so deviations then measure interval dependence of the
estimate rather than estimator error alone.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import itertools
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from generate_demo import generate
from identifiability import fit_responsiveness
from run_analysis import FIGURE_METADATA, digest, package_versions, write_json
from trajectory_pipeline import AnalysisConfig, construct_features, prepare_trajectories, validate_ties

KERNELS = ("social", "uniform")


@dataclass(frozen=True)
class Scenario:
    location_sd: float = 0.0          # metres; independent Gaussian error per coordinate and fix
    dropout: float = 0.0              # probability that an individual fix is missing
    subsample: int = 1                # keep every k-th sampling time within each bout
    declare_accuracy: bool = False    # supply accuracy_m = location_sd to the quality filters

    def validate(self):
        if not np.isfinite(self.location_sd) or self.location_sd < 0:
            raise ValueError("location_sd must be finite and nonnegative")
        if not 0 <= self.dropout < 1:
            raise ValueError("dropout must be in [0, 1)")
        if isinstance(self.subsample, bool) or not isinstance(self.subsample, int) or self.subsample < 1:
            raise ValueError("subsample must be an integer >= 1")
        if not isinstance(self.declare_accuracy, bool):
            raise ValueError("declare_accuracy must be a boolean")

    @property
    def label(self):
        accuracy = "declared" if self.declare_accuracy else "undeclared"
        return f"sd={self.location_sd:g}|dropout={self.dropout:g}|subsample={self.subsample}|accuracy={accuracy}"


def observe(trajectories, scenario, seed):
    """Degrade simulated fixes. Draws are scenario-independent (common random numbers)."""
    scenario.validate()
    data = trajectories.copy()
    rng = np.random.default_rng(seed)
    # Always draw both arrays for the full table so scenarios share the same realization.
    noise = rng.standard_normal((len(data), 2))
    missing = rng.random(len(data)) < scenario.dropout
    data["x"] = data.x.astype(float) + scenario.location_sd * noise[:, 0]
    data["y"] = data.y.astype(float) + scenario.location_sd * noise[:, 1]
    times = pd.to_datetime(data.timestamp, utc=True, format="mixed")
    step = times.groupby([data.group_id, data.bout_id]).rank(method="dense").astype(int) - 1
    keep = (step % scenario.subsample == 0).to_numpy() & ~missing
    data = data.loc[keep].reset_index(drop=True)
    if scenario.declare_accuracy:
        data["accuracy_m"] = float(scenario.location_sd)
    return data


def _replicate_seeds(seed, replicate):
    simulation, observation = np.random.SeedSequence([seed, replicate]).generate_state(2)
    return int(simulation), int(observation)


def recover(trajectories, ties, truth, scenario, *, seed=0, radius=10.0, min_transitions=10):
    """Fit every simulated individual under one scenario; returns per-individual rows."""
    observed = observe(trajectories, scenario, seed)
    max_gap = max(10.0, 2.0 * scenario.subsample)
    config = AnalysisConfig(data_kind="synthetic", radius=radius, max_gap=max_gap,
                            shuffle_seeds=(), ties_independent=True)
    base = truth[["group_id", "individual_id", "responsiveness"]].rename(columns={"responsiveness": "true_responsiveness"})
    try:
        prepared, _ = prepare_trajectories(observed, config)
        lookup = validate_ties(ties, prepared, config)
        features, _ = construct_features(prepared, config, lookup)
        usable = float(prepared.heading.notna().mean())
    except ValueError as error:
        # A scenario can destroy every usable heading; record it rather than abort the study.
        rows = [dict(row, kernel=k, status="no_eligible_transitions", n_transitions=0, estimate=np.nan,
                     boundary_optimum=False, ambiguous_profile=False, usable_heading_fraction=0.0,
                     scenario_error=str(error)[:200])
                for row in base.to_dict("records") for k in KERNELS]
        return pd.DataFrame(rows)
    rows = []
    for row in base.to_dict("records"):
        own = features[(features.group_id == row["group_id"]) & (features.individual_id == row["individual_id"])]
        for kernel in KERNELS:
            entry = dict(row, kernel=kernel, n_transitions=len(own), estimate=np.nan, boundary_optimum=False,
                         ambiguous_profile=False, usable_heading_fraction=usable, scenario_error="")
            if len(own) < min_transitions:
                entry["status"] = "insufficient_transitions"
            else:
                try:
                    fit = fit_responsiveness(own.self_heading.to_numpy(), own[kernel + "_x"].to_numpy(),
                                             own[kernel + "_y"].to_numpy(), own.observed_heading.to_numpy())
                    entry.update(status="estimated", estimate=fit["responsiveness"],
                                 boundary_optimum=fit["boundary_optimum"], ambiguous_profile=fit["ambiguous_profile"])
                except ValueError as error:
                    if "flat loss" not in str(error):
                        raise
                    entry["status"] = "flat_loss"
            rows.append(entry)
    return pd.DataFrame(rows)


def summarize(estimates):
    """Aggregate per scenario and kernel. Spearman is per replicate, then averaged."""
    keys = ["location_sd", "dropout", "subsample", "declare_accuracy", "kernel"]
    out = []
    for values, frame in estimates.groupby(keys, sort=True):
        fitted = frame[frame.status == "estimated"]
        error = fitted.estimate - fitted.true_responsiveness
        correlations = []
        for _, rep in fitted.groupby("replicate"):
            if len(rep) >= 3 and rep.estimate.nunique() > 1 and rep.true_responsiveness.nunique() > 1:
                correlations.append(spearmanr(rep.true_responsiveness, rep.estimate).statistic)
        slope = (float(np.polyfit(fitted.true_responsiveness, fitted.estimate, 1)[0])
                 if len(fitted) >= 3 and fitted.true_responsiveness.nunique() > 1 else np.nan)
        out.append(dict(zip(keys, values),
                        replicates=int(frame.replicate.nunique()), individuals=len(frame),
                        estimated=len(fitted),
                        insufficient_transitions=int((frame.status == "insufficient_transitions").sum()),
                        flat_loss=int((frame.status == "flat_loss").sum()),
                        no_eligible_transitions=int((frame.status == "no_eligible_transitions").sum()),
                        usable_heading_fraction=float(frame.groupby("replicate").usable_heading_fraction.first().mean()),
                        median_transitions=float(frame.n_transitions.median()),
                        bias=float(error.mean()) if len(fitted) else np.nan,
                        rmse=float(np.sqrt((error ** 2).mean())) if len(fitted) else np.nan,
                        mean_abs_error=float(error.abs().mean()) if len(fitted) else np.nan,
                        slope_on_truth=slope,
                        mean_spearman=float(np.mean(correlations)) if correlations else np.nan,
                        boundary_fraction=float(fitted.boundary_optimum.mean()) if len(fitted) else np.nan,
                        ambiguous_fraction=float(fitted.ambiguous_profile.mean()) if len(fitted) else np.nan))
    return pd.DataFrame(out)


def run_study(scenarios, *, replicates=3, seed=2026, simulation=None, radius=10.0, min_transitions=10):
    simulation = dict(simulation or {})
    for scenario in scenarios:
        scenario.validate()
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates < 1:
        raise ValueError("replicates must be an integer >= 1")
    frames = []
    for replicate in range(replicates):
        simulation_seed, observation_seed = _replicate_seeds(seed, replicate)
        trajectories, ties, truth = generate(seed=simulation_seed, radius=radius, **simulation)
        for scenario in scenarios:
            rows = recover(trajectories, ties, truth, scenario, seed=observation_seed,
                           radius=radius, min_transitions=min_transitions)
            frames.append(rows.assign(replicate=replicate, **asdict(scenario)))
    estimates = pd.concat(frames, ignore_index=True)
    return estimates, summarize(estimates)


def figure(summary, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "svg.fonttype": "none", "svg.hashsalt": "sheep-collective-abm",
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), layout="constrained")
    groups = summary.groupby(["dropout", "subsample", "declare_accuracy"], sort=True)
    for (dropout, subsample, declared), frame in groups:
        label = f"dropout {dropout:g}, every {subsample} step(s)" + (", accuracy declared" if declared else "")
        for ax, kernel in zip(axes[:2], KERNELS):
            part = frame[frame.kernel == kernel].sort_values("location_sd")
            ax.plot(part.location_sd, part.rmse, marker="o", label=label)
        social = frame[frame.kernel == "social"].sort_values("location_sd")
        axes[2].plot(social.location_sd, social.usable_heading_fraction, marker="o", label=label)
    axes[0].set(title="Generating (social) kernel", xlabel="Location error SD (m)", ylabel="Responsiveness RMSE")
    axes[1].set(title="Uniform kernel (as M1)", xlabel="Location error SD (m)", ylabel="Responsiveness RMSE")
    axes[2].set(title="Fixes with a usable heading", xlabel="Location error SD (m)", ylabel="Fraction", ylim=(-.02, 1.02))
    axes[2].legend(fontsize=7, frameon=False)
    for suffix, metadata in FIGURE_METADATA.items():
        fig.savefig(output / f"recovery.{suffix}", dpi=200, metadata=metadata)
    plt.close(fig)


def publish(estimates, summary, output, *, settings):
    output = Path(output)
    if output.exists():
        raise FileExistsError("Output exists; choose a fresh directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".recovery-", dir=output.parent))
    try:
        estimates.to_csv(stage / "estimates.csv", index=False)
        summary.to_csv(stage / "summary.csv", index=False)
        write_json(stage / "study.json", {
            "schema_version": 1, "kind": "responsiveness_recovery_study", "settings": settings,
            "notice": ("Synthetic recovery study. Simulation and fitting share one model family; results are "
                       "software and design checks under the stated observation conditions, not biological evidence.")})
        figure(summary, stage)
        try:
            sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent,
                                          text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            sha = None
        write_json(stage / "manifest.json", {
            "schema_version": 1, "source_commit": sha, "packages": package_versions(),
            "python": platform.python_version(), "inputs": {},
            "source_sha256": {p.name: digest(p) for p in Path(__file__).parent.glob("*.py")},
            "outputs_sha256": {p.name: digest(p) for p in sorted(stage.iterdir())}})
        stage.rename(output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--location-sd", nargs="+", type=float, default=[0.0, 0.05, 0.1, 0.25])
    parser.add_argument("--dropout", nargs="+", type=float, default=[0.0, 0.1])
    parser.add_argument("--subsample", nargs="+", type=int, default=[1, 2])
    parser.add_argument("--accuracy", nargs="+", choices=["undeclared", "declared"], default=["undeclared"],
                        help="Whether accuracy_m = location SD is supplied to the quality filters")
    parser.add_argument("--replicates", type=int, default=3)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--groups", type=int, default=3)
    parser.add_argument("--sessions", type=int, default=2)
    parser.add_argument("--animals", type=int, default=5)
    parser.add_argument("--steps", type=int, default=60)
    parser.add_argument("--radius", type=float, default=10.0)
    parser.add_argument("--min-transitions", type=int, default=10)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output directory already exists")
    scenarios = [Scenario(sd, dropout, k, mode == "declared")
                 for sd, dropout, k, mode in itertools.product(args.location_sd, args.dropout, args.subsample, args.accuracy)]
    simulation = dict(groups=args.groups, sessions=args.sessions, animals=args.animals, steps=args.steps)
    estimates, summary = run_study(scenarios, replicates=args.replicates, seed=args.seed, simulation=simulation,
                                   radius=args.radius, min_transitions=args.min_transitions)
    settings = dict(scenarios=[asdict(s) for s in scenarios], replicates=args.replicates, seed=args.seed,
                    simulation=simulation, radius=args.radius, min_transitions=args.min_transitions,
                    kernels=list(KERNELS))
    publish(estimates, summary, args.output, settings=settings)
    columns = ["location_sd", "dropout", "subsample", "declare_accuracy", "kernel", "estimated",
               "usable_heading_fraction", "bias", "rmse", "mean_spearman"]
    print(summary[columns].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"Recovery study saved: {args.output}")


if __name__ == "__main__":
    main()
