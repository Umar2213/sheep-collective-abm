"""Command-line analysis with immutable outputs and generic, exportable reports."""
from __future__ import annotations
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

import numpy as np
import pandas as pd

from trajectory_pipeline import AnalysisConfig, read_table, run_pipeline


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False, default=str)+"\n")


def figures(result, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "svg.fonttype": "none", "axes.spines.top": False, "axes.spines.right": False})
    scores = result["scores"]
    data_label = result["config"].get("data_kind", "unspecified").capitalize()
    fig, ax = plt.subplots(figsize=(8, 4.8), layout="constrained")
    names = sorted(scores.model.unique())
    for i, name in enumerate(names):
        vals = np.degrees(scores[scores.model == name].mean_absolute_error)
        ax.scatter(np.repeat(i, len(vals)), vals, color="#16857e", alpha=.65)
        ax.scatter(i, vals.mean(), marker="_", s=400, color="#132c43", linewidths=3)
    ax.set(xticks=range(len(names)), xticklabels=names, ylabel="Held-out mean absolute error (degrees)", title=f"{data_label} data: scores by uncertainty unit")
    ax.tick_params(axis="x", rotation=35)
    for suffix in ("svg", "png", "pdf"):
        fig.savefig(output/f"model_scores.{suffix}", dpi=200)
    plt.close(fig)
    # Stable first session, full data remain available in CSV outputs.
    data = result["prepared"]
    g, b = data[["group_id", "bout_id"]].iloc[0]
    frame = data[(data.group_id == g) & (data.bout_id == b)]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    for _, track in frame.groupby("individual_id"):
        # Draw individual segments only when their interval passed all filters.
        x, y = track.x.to_numpy(), track.y.to_numpy()
        color = axes[0]._get_lines.get_next_color()
        for i in range(1, len(track)):
            if track.interval_usable.iloc[i]:
                axes[0].plot(x[i-1:i+1], y[i-1:i+1], color=color, linewidth=1)
    axes[0].set(xlabel="x (m)", ylabel="y (m)", title=f"{data_label} data: example session")
    axes[0].set_aspect("equal", adjustable="datalim")
    movement = result["movement"]
    movement = movement[(movement.group_id == g) & (movement.bout_id == b)]
    axes[1].plot((movement.timestamp-movement.timestamp.min()).dt.total_seconds(), movement.alignment, color="#16857e")
    axes[1].set(xlabel="Time since session start (s)", ylabel="Directional alignment", ylim=(-.02, 1.02))
    for suffix in ("svg", "png", "pdf"):
        fig.savefig(output/f"movement.{suffix}", dpi=200)
    plt.close(fig)


def publish_result(result, output, *, inputs=None, sensitivity=None):
    output = Path(output)
    if output.exists():
        raise FileExistsError("Output exists; choose a fresh directory to preserve the prior analysis")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".analysis-", dir=output.parent))
    try:
        for name in ("folds", "movement", "features", "predictions", "parameters", "scores", "comparisons"):
            result[name].to_csv(stage/f"{name}.csv", index=False)
        if sensitivity is not None:
            sensitivity.to_csv(stage/"sensitivity.csv", index=False)
        write_json(stage/"config.json", result["config"])
        write_json(stage/"audit.json", result["audit"])
        # Generic, compact handoff to the web viewer. No raw trajectories or identifying title.
        def records(frame):
            return json.loads(frame.to_json(orient="records", date_format="iso"))
        write_json(stage/"analysis_bundle.json", {
            "schema_version": 1, "kind": "blocked_trajectory_analysis",
            "config": result["config"], "audit": result["audit"],
            "scores": records(result["scores"]), "comparisons": records(result["comparisons"]),
            "parameter_status_counts": result["parameters"].status.value_counts().to_dict(),
            "input_sha256": inputs or {},
            "notice": "Computational results only. Scientific interpretation requires independent data and a justified study design."
        })
        figures(result, stage)
        table = result["comparisons"].copy()
        lines = ["# Analysis report", "", "Status: computational analysis, not independently validated biological findings.", "",
                 f"Declared data kind: {result['config'].get('data_kind', 'unspecified')}",
                 f"Eligible transitions: {result['audit']['eligible_transitions']}",
                 f"Uncertainty units: {result['audit']['uncertainty_units']}", "",
                 "## Paired comparisons", "", "Differences are alternative minus reference in radians; negative favours the alternative.", "",
                 "```", table.to_string(index=False), "```", "", "## Interpretation limits", ""]
        lines += ["- "+w for w in result["audit"]["warnings"]]
        lines += ["", "## Reproducibility", "", "Use config.json, folds.csv and original inputs to repeat this run. Input and output hashes are in manifest.json.",
                  "Parameter fallback and ambiguity flags are in parameters.csv. Confidence intervals are conditional on the fitted predictions, not full refitting uncertainty.",
                  "Only fixed settings were used. Any sensitivity scenarios are descriptive checks, not settings selected to optimise these held-out scores."]
        (stage/"report.md").write_text("\n".join(lines)+"\n")
        try:
            sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent, text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            sha = None
        manifest = {"schema_version": 1, "source_commit": sha,
                    "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                    "inputs": inputs or {}, "source_sha256": {p.name: digest(p) for p in Path(__file__).parent.glob("*.py")},
                    "outputs_sha256": {p.name: digest(p) for p in sorted(stage.iterdir())}}
        write_json(stage/"manifest.json", manifest)
        stage.rename(output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trajectories", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--ties", type=Path)
    parser.add_argument("--folds", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sensitivity-radii", nargs="+", type=float, help="Predeclared radius scenarios; no test-set selection")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output directory already exists")
    options = json.loads(args.config.read_text())
    for key in ("split_columns", "uncertainty_columns", "shuffle_seeds"):
        if key in options:
            options[key] = tuple(options[key])
    config = AnalysisConfig(**options)
    data, ties = read_table(args.trajectories), read_table(args.ties) if args.ties else None
    folds = read_table(args.folds) if args.folds else None
    result = run_pipeline(data, config, ties, folds)
    sensitivity = []
    if args.sensitivity_radii:
        for radius in args.sensitivity_radii:
            trial = result if radius == config.radius else run_pipeline(data, replace(config, radius=radius), ties, result["folds"])
            # Filters and folds are frozen, so radius comparisons must have identical targets.
            original = result["predictions"][list(KEYS)].drop_duplicates().sort_values(list(KEYS)).reset_index(drop=True)
            current = trial["predictions"][list(KEYS)].drop_duplicates().sort_values(list(KEYS)).reset_index(drop=True)
            if not original.equals(current):
                raise RuntimeError("Sensitivity scenarios lost matched observation coverage")
            sensitivity.append(trial["comparisons"].assign(radius=radius))
    hashes = {name: digest(path) for name, path in (("trajectories", args.trajectories), ("config", args.config), ("ties", args.ties), ("folds", args.folds)) if path}
    publish_result(result, args.output, inputs=hashes, sensitivity=pd.concat(sensitivity, ignore_index=True) if sensitivity else None)
    print(f"Analysis complete: {args.output}")


KEYS = ("group_id", "bout_id", "individual_id", "timestamp")
if __name__ == "__main__":
    main()
