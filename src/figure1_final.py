import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RESULTS = "/home/umar/sheep_collective/results"
FIGURES = "/home/umar/sheep_collective/figures"

low = pd.read_csv(os.path.join(RESULTS, "vicsek_N200_noise0.1.csv"))
high = pd.read_csv(os.path.join(RESULTS, "vicsek_N200_noise4.0.csv"))

fig, ax = plt.subplots(figsize=(5.5, 3.6))

ax.axvspan(0, 80, alpha=0.15, color="grey", label="Transient")
ax.plot(
    low["step"].to_numpy(), low["order_parameter"].to_numpy(),
    color="#1976D2", linewidth=2, label="η = 0.1  (flock forms)",
)
ax.plot(
    high["step"].to_numpy(), high["order_parameter"].to_numpy(),
    color="#C62828", linewidth=2, label="η = 4.0  (disorder)",
)
ax.annotate(
    "Flock aligned by step ~80",
    xy=(90, 0.95), xytext=(200, 0.75),
    fontsize=8,
    arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
)

ax.set_xlabel("Time step")
ax.set_ylabel("Flock cohesion (φ)")
ax.set_title("Vicsek baseline: identical agents")
ax.set_ylim(0, 1.05)
ax.legend(loc="upper right", frameon=False)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

os.makedirs(FIGURES, exist_ok=True)
for ext in ("png", "pdf"):
    path = os.path.join(FIGURES, f"figure1_final.{ext}")
    fig.savefig(path, bbox_inches="tight", dpi=300)
    print(f"Saved -> {path}")
print("Done.")
