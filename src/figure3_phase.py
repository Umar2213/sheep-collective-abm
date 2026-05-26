import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RESULTS = "/home/umar/sheep_collective/results"
FIGURES = "/home/umar/sheep_collective/figures"

master = pd.read_csv(
    os.path.join(RESULTS, "MASTER_all_experiments.csv"), encoding="utf-8"
)
master.columns = ["sigma_std", "phi_mean", "phi_sd", "n", "noise", "experiment"]

exp3 = master[master["experiment"] == "exp3"].copy()
noise_levels = [0.3, 0.5, 0.7]
sigma_levels = [0.0, 0.2, 0.35, 0.45]

matrix = np.zeros((3, 4))
for i, eta in enumerate(noise_levels):
    for j, sig in enumerate(sigma_levels):
        row = exp3[np.isclose(exp3["noise"], eta) & np.isclose(exp3["sigma_std"], sig)]
        matrix[i, j] = row["phi_mean"].iloc[0] if len(row) else np.nan


def estimate_threshold(sub, phi_target=0.9):
    sub = sub.sort_values("sigma_std")
    sigs = sub["sigma_std"].values
    phis = sub["phi_mean"].values
    for k in range(len(sigs) - 1):
        if phis[k] >= phi_target and phis[k + 1] < phi_target:
            frac = (phi_target - phis[k]) / (phis[k + 1] - phis[k])
            return sigs[k] + frac * (sigs[k + 1] - sigs[k])
    if np.all(phis >= phi_target):
        return sigs[-1]
    return sigs[0]


def bound_threshold(sub, phi_hi=0.92, phi_lo=0.85):
    sub = sub.sort_values("sigma_std")
    upper = estimate_threshold(sub, phi_hi)
    lower = estimate_threshold(sub, phi_lo)
    return lower, upper


fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.4))
fig.subplots_adjust(wspace=0.45)

# Panel A — heatmap
ax = axes[0]
im = ax.imshow(matrix, aspect="auto", cmap="RdYlGn", vmin=0.3, vmax=1.0, origin="upper")
for i in range(3):
    for j in range(4):
        ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=10)
ax.set_xticks(range(4))
ax.set_xticklabels([str(s) for s in sigma_levels])
ax.set_yticks(range(3))
ax.set_yticklabels([str(n) for n in noise_levels])
ax.set_xlabel("Personality diversity (σ)")
ax.set_ylabel("Environmental noise (η)")
ax.set_title("A   Phase diagram: cohesion landscape")
cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("Flock cohesion (φ)")

# White dashed boundary between phi>0.9 and phi<0.9
for i in range(3):
    for j in range(3):
        if (matrix[i, j] > 0.9) != (matrix[i, j + 1] > 0.9):
            x = j + 0.5
            ax.plot([x, x], [i - 0.5, i + 0.5], "w--", linewidth=1.5)

# Panel B — threshold vs noise
ax = axes[1]
thresholds = []
lo_bounds = []
hi_bounds = []
for eta in noise_levels:
    sub = exp3[np.isclose(exp3["noise"], eta)]
    thresholds.append(estimate_threshold(sub))
    lo, hi = bound_threshold(sub)
    lo_bounds.append(lo)
    hi_bounds.append(hi)

thresholds = np.array(thresholds)
lo_bounds = np.array(lo_bounds)
hi_bounds = np.array(hi_bounds)

ax.fill_between(noise_levels, lo_bounds, hi_bounds, alpha=0.2, color="#C62828")
ax.plot(noise_levels, thresholds, color="#C62828", marker="^", markersize=8, linewidth=2)
ax.set_xlabel("Environmental noise (η)")
ax.set_ylabel("Critical diversity threshold (σ*)")
ax.set_title("B   Threshold shifts with noise")
ax.text(0.32, thresholds.max() + 0.04, "Fragile\n(high diversity)", fontsize=8, ha="center")
ax.text(0.32, thresholds.min() - 0.06, "Robust\n(low diversity)", fontsize=8, ha="center")
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

os.makedirs(FIGURES, exist_ok=True)
for ext in ("png", "pdf"):
    path = os.path.join(FIGURES, f"figure3_phase.{ext}")
    fig.savefig(path, bbox_inches="tight", dpi=300)
    print(f"Saved -> {path}")
print("Done.")
