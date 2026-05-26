"""Figure 1: Vicsek baseline — order parameter over time."""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 9,
    "axes.labelsize": 10,
    "axes.titlesize": 10,
    "legend.fontsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

RESULTS = "/home/umar/sheep_collective/results"
FIGURES = "/home/umar/sheep_collective/figures"

low = pd.read_csv(os.path.join(RESULTS, "vicsek_N200_noise0.1.csv"))
high = pd.read_csv(os.path.join(RESULTS, "vicsek_N200_noise4.0.csv"))

fig, ax = plt.subplots(figsize=(5.5, 3.4))

ax.plot(
    low["step"].to_numpy(),
    low["order_parameter"].to_numpy(),
    color="#1976D2",
    linewidth=1.8,
    label="η = 0.1 — flock forms",
)
ax.plot(
    high["step"].to_numpy(),
    high["order_parameter"].to_numpy(),
    color="#C62828",
    linewidth=1.8,
    label="η = 4.0 — disorder",
)

ax.set_xlabel("Time step")
ax.set_ylabel("Flock cohesion (φ)")
ax.set_title("A   Vicsek baseline: order parameter over time")
ax.legend(loc="lower right", frameon=False)
ax.set_ylim(0, 1.05)

os.makedirs(FIGURES, exist_ok=True)
for ext in ("png", "pdf"):
    path = os.path.join(FIGURES, f"figure1.{ext}")
    fig.savefig(path, bbox_inches="tight", dpi=300)
    print(f"Saved -> {path}")

print("Done.")
