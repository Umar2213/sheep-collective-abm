"""Bootstrap CIs, ANOVA, Welch t-tests, and Cohen's d."""

import os
from io import StringIO

import numpy as np
import pandas as pd
from scipy import stats

RESULTS = "/home/umar/sheep_collective/results"
BOOTSTRAP_N = 10_000
RNG = np.random.default_rng(42)

EXP12_PATHS = [
    os.path.join(RESULTS, "experiment1_rawdata.csv"),
    os.path.join(RESULTS, "exp2", "experiment1_rawdata.csv"),
]
EXP12_COLS = [
    "sigma_mean", "sigma_std_input", "seed",
    "actual_sigma_mean", "actual_sigma_std", "phi_steady",
]

EXP3_PATHS = {
    0.3: os.path.join(RESULTS, "exp3_noise0.3", "exp3_noise0.3_rawdata.csv"),
    0.5: os.path.join(RESULTS, "exp3_noise0.5", "exp3_noise0.5_rawdata.csv"),
    0.7: os.path.join(RESULTS, "exp3_noise0.7", "exp3_noise0.7_rawdata.csv"),
}
EXP3_COLS = [
    "sigma_mean", "noise", "sigma_std_input", "seed",
    "actual_sigma_mean", "actual_sigma_std", "phi_steady",
]


def load_exp12():
    frames = []
    for path in EXP12_PATHS:
        df = pd.read_csv(path, encoding="utf-8")
        df.columns = EXP12_COLS
        df["noise"] = 0.5
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def load_exp3():
    frames = []
    for eta, path in EXP3_PATHS.items():
        df = pd.read_csv(path, encoding="utf-8")
        df.columns = EXP3_COLS
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def cohens_d(x, y):
    n1, n2 = len(x), len(y)
    if n1 < 2 or n2 < 2:
        return np.nan
    s1, s2 = x.std(ddof=1), y.std(ddof=1)
    pooled = np.sqrt((s1**2 + s2**2) / 2)
    if pooled == 0:
        return 0.0
    return (x.mean() - y.mean()) / pooled


def bootstrap_ci(values, n_boot=BOOTSTRAP_N):
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n == 0:
        return np.nan, np.nan, np.nan
    means = np.array([
        RNG.choice(values, size=n, replace=True).mean()
        for _ in range(n_boot)
    ])
    return values.mean(), np.percentile(means, 2.5), np.percentile(means, 97.5)


def anova_and_ttests(df, group_col="sigma_std_input", value_col="phi_steady", baseline=0.0):
    lines = []
    groups = [g[value_col].values for _, g in df.groupby(group_col)]
    f_stat, p_val = stats.f_oneway(*groups)
    lines.append(f"One-way ANOVA ({value_col} ~ {group_col}):")
    lines.append(f"  F = {f_stat:.4f},  p = {p_val:.4e}\n")
    lines.append(f"Welch t-tests vs baseline ({group_col}={baseline}):")
    lines.append(
        f"{'sigma_std':>10} {'n_base':>7} {'n_other':>7} "
        f"{'mean_base':>10} {'mean_other':>10} {'t':>8} {'p':>10} {'cohens_d':>10}"
    )
    base = df.loc[df[group_col] == baseline, value_col]
    rows = []
    for level in sorted(df[group_col].unique()):
        if level == baseline:
            continue
        other = df.loc[df[group_col] == level, value_col]
        t_stat, p_val = stats.ttest_ind(base, other, equal_var=False)
        d = cohens_d(base.values, other.values)
        lines.append(
            f"{level:10.4f} {len(base):7d} {len(other):7d} "
            f"{base.mean():10.4f} {other.mean():10.4f} "
            f"{t_stat:8.4f} {p_val:10.4e} {d:10.4f}"
        )
        rows.append({
            "sigma_std": level, "t": t_stat, "p": p_val, "cohens_d": d,
        })
    lines.append("")
    return lines, f_stat, p_val


def build_bootstrap_table(df):
    rows = []
    for (noise, sigma_std), g in df.groupby(["noise", "sigma_std_input"]):
        phi = g["phi_steady"].values
        mean, lo, hi = bootstrap_ci(phi)
        rows.append({
            "noise": noise,
            "sigma_std": sigma_std,
            "n": len(phi),
            "phi_mean": mean,
            "ci_lower": lo,
            "ci_upper": hi,
        })
    return pd.DataFrame(rows).sort_values(["noise", "sigma_std"])


def main():
    exp12 = load_exp12()
    exp3 = load_exp3()
    all_data = pd.concat([exp12, exp3], ignore_index=True)

    lines = []
    lines.append("=" * 60)
    lines.append("STATISTICAL ANALYSIS — stats_final.py")
    lines.append("=" * 60 + "\n")

    lines.append("--- Exp1 + Exp2 combined (noise = 0.5) ---\n")
    sec, f, p = anova_and_ttests(exp12)
    lines.extend(sec)

    for eta in [0.3, 0.5, 0.7]:
        sub = exp3[np.isclose(exp3["noise"], eta)]
        lines.append(f"--- Exp3 noise = {eta} ---\n")
        sec, _, _ = anova_and_ttests(sub)
        lines.extend(sec)

    boot = build_bootstrap_table(all_data)
    boot_path = os.path.join(RESULTS, "bootstrap_CIs.csv")
    boot.to_csv(boot_path, index=False)
    lines.append(f"Bootstrap CIs saved -> {boot_path}")
    lines.append(f"  {len(boot)} conditions, {BOOTSTRAP_N} resamples each\n")

    text = "\n".join(lines)
    out_path = os.path.join(RESULTS, "stats_final.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(text)
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
