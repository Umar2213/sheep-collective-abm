#!/usr/bin/env python3
"""Publication-quality flock heading snapshots."""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT/"results"/"snapshots"/"snapshot_states.csv")
FIGS = ROOT/"figures"; FIGS.mkdir(exist_ok=True)
sigmas = sorted(df.sigma.unique()); L = 20.0
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,
    "axes.titlesize":12,"axes.titleweight":"bold"})

fig, axes = plt.subplots(1, len(sigmas), figsize=(4*len(sigmas), 4.6))
for ax, s in zip(np.atleast_1d(axes), sigmas):
    d = df[df.sigma==s]; th = d.theta.values
    phi = np.hypot(np.cos(th).mean(), np.sin(th).mean())
    q = ax.quiver(d.x, d.y, np.cos(th), np.sin(th), th, cmap="twilight",
                  clim=(-np.pi, np.pi), scale=28, width=0.007,
                  pivot="mid", headwidth=3.5, headlength=4)
    ax.set_xlim(0,L); ax.set_ylim(0,L); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"σ = {s:.2f}    φ = {phi:.2f}")

fig.suptitle("Flock heading directions: order dissolves as trait dispersion rises  (η = 0.5)",
             fontsize=13, fontweight="bold", y=1.03)
cbar = fig.colorbar(q, ax=np.atleast_1d(axes), orientation="horizontal",
                    fraction=0.045, pad=0.07, ticks=[-np.pi,0,np.pi])
cbar.set_label("heading direction θ"); cbar.ax.set_xticklabels(["−π","0","π"])
fig.savefig(FIGS/"fig_snapshots.png", dpi=300, bbox_inches="tight")
fig.savefig(FIGS/"fig_snapshots.pdf", bbox_inches="tight")
print("wrote figures/fig_snapshots.png + .pdf")
