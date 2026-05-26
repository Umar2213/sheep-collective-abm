"""Statistical analysis: ANOVA and t-tests on raw simulation data."""

import os
from io import StringIO

import pandas as pd
from scipy import stats

RESULTS = "/home/umar/sheep_collective/results"
OUT = os.path.join(RESULTS, "stats_summary.txt")

EXP1_RAW = os.path.join(RESULTS, "experiment1_rawdata.csv")
EXP2_RAW = os.path.join(RESULTS, "exp2", "experiment1_rawdata.csv")

EXP3_RAW = {
    0.3: os.path.join(RESULTS, "exp3_noise0.3", "exp3_noise0.3_rawdata.csv"),
    0.5: os.path.join(RESULTS, "exp3_noise0.5", "exp3_noise0.5_rawdata.csv"),
    0.7: os.path.join(RESULTS, "exp3_noise0.7", "exp3_noise0.7_rawdata.csv"),
}

COLS_EXP12 = [
    "sigma_mean",
    "sigma_std_input",
    "seed",
    "actual_sigma_mean",
    "actual_sigma_std",
    "phi_steady",
]

COLS_EXP3 = [
    "sigma_mean",
    "noise",
    "sigma_std_input",
    "seed",
    "actual_sigma_mean",
    "actual_sigma_std",
    "phi_steady",
]


def load_exp12(path):
    df = pd.read_csv(path, encoding="utf-8")
    df.columns = COLS_EXP12
    return df


def load_exp3(path):
    df = pd.read_csv(path, encoding="utf-8")
    df.columns = COLS_EXP3
    return df


def one_way_anova(df, group_col="sigma_std_input", value_col="phi_steady"):
    groups = [
        g[value_col].values
        for _, g in df.groupby(group_col)
        if len(g) > 0
    ]
    if len(groups) < 2:
        return None, None
    f_stat, p_val = stats.f_oneway(*groups)
    return f_stat, p_val


def ttests_vs_baseline(df, baseline=0.0, group_col="sigma_std_input", value_col="phi_steady"):
    baseline_vals = df.loc[df[group_col] == baseline, value_col]
    rows = []
    for level in sorted(df[group_col].unique()):
        if level == baseline:
            continue
        other = df.loc[df[group_col] == level, value_col]
        t_stat, p_val = stats.ttest_ind(baseline_vals, other, equal_var=False)
        rows.append({
            "sigma_std": level,
            "n_baseline": len(baseline_vals),
            "n_other": len(other),
            "mean_baseline": baseline_vals.mean(),
            "mean_other": other.mean(),
            "t": t_stat,
            "p": p_val,
        })
    return pd.DataFrame(rows)


def section_header(title):
    return "\n" + "=" * 60 + "\n" + title + "\n" + "=" * 60 + "\n"


def main():
    lines = []
    lines.append("STATISTICAL ANALYSIS — sheep collective ABM")
    lines.append(f"Generated from raw per-seed CSVs in {RESULTS}\n")

    # --- Exp1 + Exp2 combined (η = 0.5) ---
    df1 = load_exp12(EXP1_RAW)
    df2 = load_exp12(EXP2_RAW)
    combined = pd.concat([df1, df2], ignore_index=True)

    lines.append(section_header("COMBINED Exp1 + Exp2  (η = 0.5)"))
    lines.append(f"Total rows: {len(combined)}")
    lines.append(f"σ_std levels: {sorted(combined['sigma_std_input'].unique())}\n")

    f_stat, p_val = one_way_anova(combined)
    lines.append("One-way ANOVA: phi_steady ~ sigma_std_input")
    lines.append(f"  F = {f_stat:.4f},  p = {p_val:.4e}\n")

    tt = ttests_vs_baseline(combined, baseline=0.0)
    lines.append("Welch t-tests: sigma_std = 0.0 vs each other level")
    lines.append(tt.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    lines.append("")

    # --- Exp3: one ANOVA per noise level ---
    for eta, path in EXP3_RAW.items():
        if not os.path.isfile(path):
            lines.append(f"\n[SKIP] Missing: {path}\n")
            continue
        df3 = load_exp3(path)
        lines.append(section_header(f"Exp3  η = {eta}"))
        lines.append(f"File: {path}")
        lines.append(f"Rows: {len(df3)}")
        lines.append(f"σ_std levels: {sorted(df3['sigma_std_input'].unique())}\n")

        f_stat, p_val = one_way_anova(df3)
        lines.append("One-way ANOVA: phi_steady ~ sigma_std_input")
        lines.append(f"  F = {f_stat:.4f},  p = {p_val:.4e}\n")

        tt = ttests_vs_baseline(df3, baseline=0.0)
        lines.append("Welch t-tests: sigma_std = 0.0 vs each other level")
        lines.append(tt.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
        lines.append("")

    text = "\n".join(lines)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"\nSaved -> {OUT}")


if __name__ == "__main__":
    main()
