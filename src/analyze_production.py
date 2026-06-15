#!/usr/bin/env python3
# analyze_production.py — honest analysis of the canonical equilibrated sweep.
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROD = ROOT/"results"/"production"; FIGS = ROOT/"figures"; FIGS.mkdir(exist_ok=True)
rep  = pd.read_csv(PROD/"sweep_replicates.csv")
summ = pd.read_csv(PROD/"sweep_condition_means.csv")
noises = sorted(summ.noise.unique())

def boot_ci(x, n=2000, seed=0):
    rng = np.random.default_rng(seed); x = np.asarray(x)
    m = rng.choice(x, size=(n, len(x)), replace=True).mean(axis=1)
    return np.percentile(m, [2.5, 97.5])

ci = (rep.groupby(["noise","sigma_std"])["phi"]
        .apply(lambda s: pd.Series(dict(zip(["lo","hi"], boot_ci(s.values)))))
        .unstack().reset_index())
summ = summ.merge(ci, on=["noise","sigma_std"])
colors = {0.3:"#2c7fb8", 0.5:"#d95f0e", 0.7:"#756bb1"}

fig, ax = plt.subplots(2, 2, figsize=(11, 8.5))
for e in noises:
    d = summ[summ.noise==e].sort_values("sigma_std"); c = colors.get(e,"k")
    ax[0,0].plot(d.sigma_std, d.phi_mean, "-o", ms=3, color=c, label=f"η = {e}")
    ax[0,0].fill_between(d.sigma_std, d.lo, d.hi, color=c, alpha=0.18)
ax[0,0].set_xlabel("trait dispersion  σ"); ax[0,0].set_ylabel("order parameter  φ")
ax[0,0].set_title("(a) Order declines smoothly with dispersion"); ax[0,0].legend(frameon=False)

for e in noises:
    d = summ[summ.noise==e].sort_values("sigma_std")
    ax[0,1].plot(d.sigma_std, d.chi_seed, "-o", ms=3, color=colors.get(e,"k"), label=f"η = {e}")
ax[0,1].set_xlabel("trait dispersion  σ"); ax[0,1].set_ylabel("susceptibility  χ = N·Var(φ)")
ax[0,1].set_title("(b) Fluctuations peak in the transition region"); ax[0,1].legend(frameon=False)

for e in noises:
    d = summ[summ.noise==e].sort_values("sigma_std")
    ax[1,0].plot(d.sigma_std, d.ar1, "-o", ms=3, color=colors.get(e,"k"), label=f"η = {e}")
ax[1,0].set_xlabel("trait dispersion  σ"); ax[1,0].set_ylabel("lag-1 autocorrelation")
ax[1,0].set_title("(c) Critical slowing down approaching disorder"); ax[1,0].legend(frameon=False)

d5 = summ[summ.noise==0.5].sort_values("sigma_std")
ax[1,1].plot(d5.sigma_std, 100*d5.frac_lo, "-o", ms=3, color="#cb181d", label="weakly social (w<0.2)")
ax[1,1].plot(d5.sigma_std, 100*d5.frac_hi, "-s", ms=3, color="#238b45", label="strongly social (w>0.8)")
ax[1,1].set_xlabel("trait dispersion  σ"); ax[1,1].set_ylabel("% of population (η=0.5)")
ax[1,1].set_title("(d) Mechanism: dispersion grows the asocial tail"); ax[1,1].legend(frameon=False)

for a in ax.flat: a.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(FIGS/"fig_main_production.png", dpi=200); fig.savefig(FIGS/"fig_main_production.pdf")
print("  wrote figures/fig_main_production.png + .pdf")

def crossing(d, level):
    d = d.sort_values("sigma_std"); x, y = d.sigma_std.values, d.phi_mean.values
    for i in range(len(y)-1):
        if y[i] >= level >= y[i+1]:
            t = (y[i]-level)/(y[i]-y[i+1]); return x[i] + t*(x[i+1]-x[i])
    return np.nan

print("\n  noise | sigma@phi=0.90 | sigma@phi=0.50 | chi peak @ sigma | max chi")
print("  " + "-"*62)
for e in noises:
    d = summ[summ.noise==e]; s90 = crossing(d,0.90); s50 = crossing(d,0.50)
    pk = d.loc[d.chi_seed.idxmax()]
    print(f"   {e:.1f}  |     {s90:.3f}      |     {s50:.3f}      |      {pk.sigma_std:.3f}     | {pk.chi_seed:.3f}")
