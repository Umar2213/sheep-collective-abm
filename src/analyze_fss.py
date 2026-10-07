#!/usr/bin/env python3
"""Exploratory finite-size diagnostics, without automatic transition claims."""
from pathlib import Path
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analysis_utils import zero_crossings, variance_components

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("ABM_ANALYSIS_DIR", ROOT / "results/fss"))
FIGS = Path(os.environ.get("ABM_FIGURE_DIR", ROOT / "figures"))
FIGS.mkdir(parents=True, exist_ok=True)
raw = pd.read_csv(DATA / "fss_replicates.csv")
rows = []
for (n, noise, sigma), g in raw.groupby(["N", "noise", "sigma_std"]):
    temporal, between, pooled = variance_components(g.phi, g.phi2, n)
    rows.append(dict(N=n, noise=noise, sigma_std=sigma, phi_mean=g.phi.mean(),
                     chi_temporal=temporal, chi_between=between, chi_pooled=pooled,
                     binder=1-g.phi4.mean()/(3*g.phi2.mean()**2),
                     max_drift=g.drift.max(), failed_drift=int((g.drift > .02).sum()),
                     n=len(g)))
df = pd.DataFrame(rows)
if df.noise.nunique() != 1:
    raise ValueError("Plot each noise level separately")
out = Path(os.environ.get("ABM_AUDIT_DIR", ROOT / "results/audit"))
out.mkdir(parents=True, exist_ok=True)
df.to_csv(out / "fss_variance_components.csv", index=False)
ns = sorted(df.N.unique())
fig, axes = plt.subplots(2, 2, figsize=(11, 8.5))
colors = plt.cm.viridis(np.linspace(.1, .9, len(ns)))
for n, color in zip(ns, colors):
    d = df[df.N == n].sort_values("sigma_std")
    for ax, column in zip(axes.flat, ["phi_mean", "chi_temporal", "binder", "chi_between"]):
        ax.plot(d.sigma_std, d[column], "o-", ms=3, color=color, label=f"N={n}")
        bad = d.failed_drift > 0
        ax.scatter(d.loc[bad, "sigma_std"], d.loc[bad, column], marker="x", color="red", s=22)
        ax.set_xlabel("response dispersion σ")
for ax, title, label in zip(axes.flat,
        ["(a) Heading order", "(b) Within-run temporal fluctuations",
         "(c) Pooled Binder statistic (denominator 3)", "(d) Between-run fluctuations"],
        ["mean φ", "N · mean(temporal variance)", "1 - pooled φ⁴ / (3 pooled φ² squared)",
         "N · population variance(mean φ)"]):
    ax.set_title(title)
    ax.set_ylabel(label)
    ax.legend(fontsize=8)
    ax.grid(alpha=.2)
fig.suptitle(os.environ.get("ABM_DATA_LABEL", "Legacy approximate-search size comparison") + ", η=" + str(df.noise.iloc[0]) +
             "; red crosses mark conditions with drift > 0.02", fontsize=11)
fig.tight_layout()
for ext in ["png", "pdf"]:
    fig.savefig(FIGS / f"fig_fss.{ext}", dpi=220)
for n in ns:
    d = df[df.N == n].sort_values("sigma_std")
    peak = d.loc[d.chi_pooled.idxmax()]
    boundary = peak.sigma_std in (d.sigma_std.min(), d.sigma_std.max())
    print(f"N={n}: pooled maximum at σ={peak.sigma_std:.3f}, boundary={boundary}, "
          f"{d.failed_drift.sum()}/{d.n.sum()} runs exceed drift 0.02")
for a, b in zip(ns[:-1], ns[1:]):
    pair = df[df.N == a].merge(df[df.N == b], on="sigma_std", suffixes=("_a", "_b"))
    pair = pair.sort_values("sigma_std")
    print(f"N={a},{b}: descriptive Binder intersections: "
          f"{zero_crossings(pair.sigma_std, pair.binder_a-pair.binder_b)}")
print("No critical point or exponent inferred: drift, boundary maxima, disorder variation "
      "and uncertainty need resolution. A slope against N would correspond to γ/(dν), "
      "not γ/ν, only if the appropriate scaling assumptions held.")
