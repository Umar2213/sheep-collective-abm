"""Generate a seeded mechanistic software-test fixture, not empirical observations."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
from identifiability import blended_heading


def generate(seed=42, groups=3, sessions=2, animals=5, steps=60, radius=10.0):
    rng = np.random.default_rng(seed)
    rows, ties, truth = [], [], []
    for g in range(groups):
        group = f"group_{g+1:02d}"
        response = np.linspace(.15, .85, animals)
        network = rng.uniform(.1, 1, (animals, animals))
        np.fill_diagonal(network, 0)
        for i in range(animals):
            truth.append(dict(group_id=group, individual_id=f"animal_{i+1:02d}", responsiveness=response[i]))
            for j in range(animals):
                if i != j:
                    ties.append(dict(group_id=group, focal_id=f"animal_{i+1:02d}", neighbour_id=f"animal_{j+1:02d}", weight=network[i,j]))
        for b in range(sessions):
            pos = rng.uniform(-3, 3, (animals, 2))
            heading = rng.uniform(-np.pi, np.pi, animals)
            for t in range(steps):
                for i in range(animals):
                    rows.append(dict(group_id=group, bout_id=f"session_{b+1:02d}", individual_id=f"animal_{i+1:02d}", timestamp=(pd.Timestamp("2026-01-01T09:00:00Z")+pd.Timedelta(days=b, seconds=t)).isoformat(), x=pos[i,0], y=pos[i,1]))
                new = heading.copy()
                for i in range(animals):
                    near = (np.linalg.norm(pos-pos[i], axis=1) <= radius) & (np.arange(animals) != i)
                    w = network[i,near]
                    if len(w) and w.sum():
                        nx, ny = np.average(np.cos(heading[near]), weights=w), np.average(np.sin(heading[near]), weights=w)
                        new[i] = blended_heading(heading[i], nx, ny, response[i])
                heading = new + rng.uniform(-.04, .04, animals)
                pos += .65*np.column_stack((np.cos(heading), np.sin(heading)))
    return pd.DataFrame(rows), pd.DataFrame(ties), pd.DataFrame(truth)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    data, ties, truth = generate(args.seed)
    for name, frame in (("trajectories", data), ("ties", ties), ("synthetic_truth", truth)):
        frame.to_csv(args.output/f"{name}.csv", index=False)
    (args.output/"NOTICE.txt").write_text("SYNTHETIC TEST DATA. No animal observations or real locations. Seeded synchronous open-plane vector-blending simulation, fixed speed, uniform angular noise. The same rule is used for fitting, so recovery here is a software check, not biological validation.\n")
    (args.output/"config.json").write_text(json.dumps(dict(data_kind="synthetic", crs="local_metres", n_folds=2, split_columns=["group_id", "bout_id"], uncertainty_columns=["group_id"], ties_independent=True, radius=10, shuffle_seeds=[11,29,47], seed=args.seed), indent=2)+"\n")


if __name__ == "__main__":
    main()
