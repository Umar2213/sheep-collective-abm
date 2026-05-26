import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RESULTS = "/home/umar/sheep_collective/results"
FIGURES = "/home/umar/sheep_collective/figures"

df = pd.read_csv(os.path.join(RESULTS, "bootstrap_CIs.csv"))

fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.8))
fig.subplots_adjust(wspace=0.38)

# Panel A
ax = axes[0]
sub = df[np.isclose(df["noise"], 0.5)].sort_values("sigma_std")
yerr = np.vstack([
    sub["phi_mean"] - sub["ci_lower"],
    sub["ci_upper"] - sub["phi_mean"],
])
ax.errorbar(
    sub["sigma_std"], sub["phi_mean"], yerr=yerr,
    color="#1976D2", marker="o", markersize=6, linewidth=1.8,
    capsize=3, capthick=1.2, elinewidth=0.9, zorder=3,
)
ax.axvspan(0.30, 0.35, alpha=0.15, color="red")
ax.axhline(0.9, color="grey", linewidth=0.8, linestyle=":", alpha=0.6)
ax.annotate(
    "Critical\nthreshold",
    xy=(0.325, 0.88), xytext=(0.38, 0.72),
    fontsize=8, color="red", ha="center",
    arrowprops=dict(arrowstyle="->", color="red", lw=1.2),
)
ax.set_xlabel("Personality diversity (σ)")
ax.set_ylabel("Flock cohesion (φ)")
ax.set_title("A   Effect of personality diversity (η = 0.5)")
ax.set_ylim(0.25, 1.05)
ax.set_xlim(-0.01, 0.47)
ax.legend(loc="lower left", frameon=False)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# Panel B
ax = axes[1]
colors = {0.3: "#1976D2", 0.5: "#F57C00", 0.7: "#C62828"}
markers = {0.3: "o", 0.5: "s", 0.7: "^"}
labels = {0.3: "η = 0.3 (low)", 0.5: "η = 0.5 (medium)", 0.7: "η = 0.7 (high)"}

for eta in [0.3, 0.5, 0.7]:
    s = df[np.isclose(df["noise"], eta)].sort_values("sigma_std")
    yerr = np.vstack([
        s["phi_mean"] - s["ci_lower"],
        s["ci_upper"] - s["phi_mean"],
    ])
    ax.errorbar(
        s["sigma_std"], s["phi_mean"], yerr=yerr,
        color=colors[eta], marker=markers[eta], markersize=6,
        linewidth=1.8, capsize=3, capthick=1.2, elinewidth=0.9,
        label=labels[eta], zorder=3,
    )

ax.text(0.38, 0.80, "Higher noise → earlier collapse",
        fontsize=8, color="grey", style="italic")
ax.set_xlabel("Personality diversity (σ)")
ax.set_ylabel("Flock cohesion (φ)")
ax.set_title("B   Noise × diversity interaction")
ax.set_ylim(0.25, 1.05)
ax.set_xlim(-0.01, 0.47)
ax.legend(loc="lower left", frameon=False)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

fig.suptitle(
    "Personality diversity and environmental noise shape flock cohesion",
    fontsize=11, y=1.02,
)

os.makedirs(FIGURES, exist_ok=True)
for ext in ("png", "pdf"):
    path = os.path.join(FIGURES, f"figure2_final.{ext}")
    fig.savefig(path, bbox_inches="tight", dpi=300)
    print(f"Saved -> {path}")
print("Done.")
