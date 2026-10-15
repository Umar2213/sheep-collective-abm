"""Prepare the public Jadhav et al. (2024) Merino sheep UWB data for the sheep analysis website.

Usage:
    git clone https://github.com/tee-lab/collective-responses-of-flocking-sheep-to-herding-dog.git
    python prepare_sheep_data.py collective-responses-of-flocking-sheep-to-herding-dog --interval 1 --output demo_1s

Writes trajectories.csv, ties.csv, config.json and provenance.json, following PROTOCOL.md.
Only the Python standard library, numpy and pandas are used.
"""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Published active-phase ("drive") windows in seconds, copied from main_text/drivs_dat.m.
# Keys are the MATLAB event numbers; event k is the k-th trial present in sheepR.dat.
DRIVES = {
    1: ([140, 453], [160, 465]),
    2: ([151, 196, 258, 700], [177, 232, 290, 730]),
    3: ([163], [193]),
    4: ([23, 50, 130, 191, 210, 272, 293], [35, 77, 170, 198, 240, 286, 298]),
    5: ([0.1, 48, 110, 207, 283], [24, 68, 128, 227, 288]),
    6: ([81], [89]),
    7: ([], []),
    8: ([0.1, 55, 170, 332, 438, 585], [33, 90, 220, 387, 530, 593]),
    9: ([0.1, 99, 303], [32, 210, 324]),
}
SHEEP_IDS = range(1, 15)          # 15 = dog, 16 = handler (figure_1b.m)
TIE_EVENT = 7                     # the only trial with no published drive
K_NEAREST = 3
REFERENCE = datetime(2000, 1, 1, tzinfo=timezone.utc)   # arbitrary; see PROTOCOL.md


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(repo):
    path = Path(repo) / "main_text" / "sheepR.dat"
    d = pd.read_csv(path, sep=r"\s+", header=None, names=["trial", "id", "t", "x", "y", "unused"])
    d["k"] = np.rint(d.t * 10).astype(int)            # 0.1-s sample index from trial start
    if not np.allclose(d.k / 10, d.t, atol=1e-6):
        raise ValueError("Times are not on a 0.1-s grid")
    trials = sorted(d.trial.unique())
    return path, d, {event: trial for event, trial in enumerate(trials, start=1)}


def build_trajectories(d, event_to_trial, step):
    rows = []
    for event, (starts, ends) in DRIVES.items():
        trial = event_to_trial[event]
        for n, (s, e) in enumerate(zip(starts, ends), start=1):
            # MATLAB uses 1-based index i = s/dt; sample index k = i - 1.
            k0, k1 = int(round(s / 0.1)) - 1, int(round(e / 0.1)) - 1
            part = d[(d.trial == trial) & d.id.isin(SHEEP_IDS) & d.k.between(k0, k1) & (d.k % step == 0)]
            for r in part.itertuples():
                when = REFERENCE + timedelta(hours=int(trial), seconds=r.k / 10)
                rows.append(dict(group_id="flock1", session_id=f"trial{trial:02d}",
                                 bout_id=f"trial{trial:02d}_drive{n}", individual_id=f"S{r.id:02d}",
                                 timestamp=when.isoformat(timespec="milliseconds"),
                                 x=round(r.x, 3), y=round(r.y, 3)))
    out = pd.DataFrame(rows).sort_values(["session_id", "bout_id", "individual_id", "timestamp"])
    return out.reset_index(drop=True)


def build_ties(d, event_to_trial, step):
    trial = event_to_trial[TIE_EVENT]
    part = d[(d.trial == trial) & d.id.isin(SHEEP_IDS) & (d.k % step == 0)]
    ids = list(SHEEP_IDS)
    counts = np.zeros((len(ids), len(ids)))
    n_times = 0
    for _, frame in part.groupby("k"):
        if len(frame) != len(ids):
            continue
        f = frame.set_index("id").loc[ids]
        xy = f[["x", "y"]].to_numpy()
        dist = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
        np.fill_diagonal(dist, np.inf)
        nearest = np.argsort(dist, axis=1)[:, :K_NEAREST]
        for i in range(len(ids)):
            counts[i, nearest[i]] += 1
        n_times += 1
    weights = counts / n_times
    rows = [dict(group_id="flock1", focal_id=f"S{a:02d}", neighbour_id=f"S{b:02d}", weight=round(weights[i, j], 6))
            for i, a in enumerate(ids) for j, b in enumerate(ids) if a != b]
    return pd.DataFrame(rows), trial, n_times


def _num(v):
    # Whole numbers are written as integers so the browser (JSON.stringify) and this
    # script produce byte-identical config files and therefore identical output hashes.
    return int(v) if float(v).is_integer() else v


def config(interval):
    return {k: (_num(v) if isinstance(v, float) else v) for k, v in _config(interval).items()}


def _config(interval):
    return {
        "data_kind": "observational", "coordinate_mode": "metric", "crs": "local_metres",
        "min_speed": 0.3, "max_speed": 8.0, "max_gap": round(1.5 * interval, 6),
        "sampling_interval_seconds": interval, "radius": 5.0, "n_folds": 8,
        "split_columns": ["group_id", "session_id"], "uncertainty_columns": ["group_id", "session_id"],
        "min_individual_train": 10, "n_bootstrap": 2000, "shuffle_seeds": [11, 29, 47, 71, 97],
        "seed": 42, "ties_independent": True, "common_shuffle_controls": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="Path to the cloned tee-lab repository")
    p.add_argument("--interval", type=float, default=1.0, choices=[0.5, 1.0, 2.0])
    p.add_argument("--output", required=True)
    a = p.parse_args()
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=False)
    step = int(round(a.interval * 10))
    source, d, event_to_trial = load(a.repo)
    traj = build_trajectories(d, event_to_trial, step)
    ties, tie_trial, n_tie_times = build_ties(d, event_to_trial, step)
    traj.to_csv(out / "trajectories.csv", index=False)
    ties.to_csv(out / "ties.csv", index=False)
    # Written exactly as the analysis service stores an uploaded configuration (compact JSON,
    # same key order), so a website run and a command-line run have identical input hashes.
    (out / "config.json").write_text(json.dumps(config(a.interval), allow_nan=False))
    try:
        commit = subprocess.check_output(["git", "-C", str(a.repo), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    prov = {
        "source_repository": "https://github.com/tee-lab/collective-responses-of-flocking-sheep-to-herding-dog",
        "source_commit": commit, "source_file": "main_text/sheepR.dat", "source_sha256": sha256(source),
        "article_doi": "10.1038/s42003-024-07245-8", "archive_doi": "10.5281/zenodo.13982895",
        "interval_seconds": a.interval, "sheep_ids": [int(i) for i in SHEEP_IDS], "excluded_ids": {"15": "dog", "16": "handler"},
        "analysed_trials": sorted(int(event_to_trial[e]) for e, (s, _) in DRIVES.items() if s),
        "tie_trial": int(tie_trial), "tie_definition": f"fraction of {n_tie_times} samples in which neighbour is among focal's {K_NEAREST} nearest sheep",
        "timestamp_reference": "2000-01-01T00:00:00+00:00 plus trial-number hours (arbitrary; real date not published)",
        "rows": int(len(traj)), "bouts": int(traj.bout_id.nunique()), "sessions": int(traj.session_id.nunique()),
        "outputs_sha256": {n: sha256(out / n) for n in ("trajectories.csv", "ties.csv", "config.json")},
    }
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    print(json.dumps({k: prov[k] for k in ("rows", "bouts", "sessions", "analysed_trials", "tie_trial")}))


if __name__ == "__main__":
    main()
