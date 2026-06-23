#!/usr/bin/env python3
# analyze_fss.py — finite-size-scaling analysis and figure.
#
# Reads results/fss/fss_condition_means.csv and produces:
#   (a) order parameter φ(σ) for each N        -> does the decline sharpen with N?
#   (b) connected susceptibility χ(σ) for each N -> does the peak GROW with N?
#   (c) Binder cumulant U(σ) for each N          -> do curves CROSS (=> transition)?
#   (d) χ_max vs N (log-log)                      -> effective exponent γ/ν
# Prints the Binder-crossing estimate and the χ_max scaling slope.
# Run:  python3 src/analyze_fss.py
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
CSV  = os.path.join(HERE, "..", "results", "fss", "fss_condition_means.csv")
FIGD = os.path.join(HERE, "..", "figures")
os.makedirs(FIGD, exist_ok=True)

df = pd.read_csv(CSV)
Ns = sorted(df["N"].unique())
cmap = plt.cm.viridis(np.linspace(0.15, 0.9, len(Ns)))

fig, ax = plt.subplots(2, 2, figsize=(11, 8.5))

# (a) order parameter
for c, N in zip(cmap, Ns):
    d = df[df.N == N].sort_values("sigma_std")
    ax[0, 0].plot(d.sigma_std, d.phi_mean, "o-", ms=3, lw=1.4, color=c, label=f"N={N}")
ax[0, 0].axhline(0.90, ls=":", c="grey", lw=1)
ax[0, 0].set_xlabel("trait dispersion  σ"); ax[0, 0].set_ylabel("order parameter  φ")
ax[0, 0].set_title("(a) Does order sharpen with N?"); ax[0, 0].legend(fontsize=8)

# (b) susceptibility
for c, N in zip(cmap, Ns):
    d = df[df.N == N].sort_values("sigma_std")
    ax[0, 1].plot(d.sigma_std, d.chi, "o-", ms=3, lw=1.4, color=c, label=f"N={N}")
ax[0, 1].set_xlabel("trait dispersion  σ"); ax[0, 1].set_ylabel("susceptibility  χ = N·Var(φ)")
ax[0, 1].set_title("(b) Does the peak grow with N?"); ax[0, 1].legend(fontsize=8)

# (c) Binder cumulant
for c, N in zip(cmap, Ns):
    d = df[df.N == N].sort_values("sigma_std")
    ax[1, 0].plot(d.sigma_std, d.binder, "o-", ms=3, lw=1.4, color=c, label=f"N={N}")
ax[1, 0].set_xlabel("trait dispersion  σ"); ax[1, 0].set_ylabel("Binder cumulant  U")
ax[1, 0].set_title("(c) Do the curves cross? (crossing = σc)"); ax[1, 0].legend(fontsize=8)

# Binder crossing of the two largest N (linear interpolation of the difference)
def crossing(Na, Nb):
    a = df[df.N == Na].sort_values("sigma_std")
    b = df[df.N == Nb].sort_values("sigma_std")
    s = a.sigma_std.values
    diff = np.interp(s, b.sigma_std.values, b.binder.values) - a.binder.values
    sign = np.sign(diff)
    idx = np.where(np.diff(sign) != 0)[0]
    if len(idx) == 0:
        return None
    i = idx[0]
    # linear interp where diff crosses zero
    return s[i] - diff[i] * (s[i+1] - s[i]) / (diff[i+1] - diff[i])

sc = crossing(Ns[-2], Ns[-1]) if len(Ns) >= 2 else None

# (d) chi_max scaling
chimax = np.array([df[df.N == N].chi.max() for N in Ns])
Na = np.array(Ns, float)
ax[1, 1].loglog(Na, chimax, "ks-", ms=6)
ax[1, 1].set_xlabel("system size  N"); ax[1, 1].set_ylabel("χ_max")
slope = np.polyfit(np.log(Na), np.log(chimax), 1)[0]
ax[1, 1].set_title(f"(d) χ_max ∝ N^{slope:.2f}  (effective γ/ν)")

fig.suptitle(f"Finite-size scaling at η = {df.noise.iloc[0] if 'noise' in df else 0.5}",
             fontsize=13, fontweight="bold")
fig.tight_layout(rect=[0, 0, 1, 0.97])
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(FIGD, f"fig_fss.{ext}"), dpi=300, bbox_inches="tight")

print("=" * 60)
print("FINITE-SIZE-SCALING SUMMARY")
print("=" * 60)
print(f"system sizes: {Ns}")
print(f"χ_max by N:   {dict(zip(Ns, np.round(chimax,4)))}")
print(f"χ_max scaling slope (log-log)  γ/ν ≈ {slope:.3f}")
if sc is not None:
    print(f"Binder crossing (N={Ns[-2]} vs {Ns[-1]})  σc ≈ {sc:.3f}")
else:
    print("Binder curves do NOT cross in this range -> consistent with a CROSSOVER,")
    print("not a sharp transition (still a clean, honest, publishable finding).")
print("\nInterpretation guide:")
print("  χ_max grows with N AND Binder curves cross  -> genuine transition (aim PRE/Interface)")
print("  χ_max saturates AND no Binder crossing       -> finite-size crossover (still an upgrade)")
print("\nwrote figures/fig_fss.png + fig_fss.pdf")
