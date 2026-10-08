# Responsiveness recovery under realistic observation conditions

## Purpose

The empirical roadmap requires recovery under realistic location error, missingness and
sampling intervals before fitted responsiveness is interpreted (WP4). The existing
identifiability tests use exact one-step headings. `src/recovery_study.py` instead runs
the production `prepare_trajectories`, `validate_ties` and `construct_features` code on
degraded synthetic observations with known individual responsiveness.

This is a software and design check. Simulation and fitting share one model family, so
good recovery is necessary but never sufficient, and poor recovery here would also be
expected in comparable real data. Nothing here is biological evidence.

## What is simulated

Each replicate uses the seeded synthetic generator: 3 groups, 2 sessions, 5 animals,
60 one-second steps, speed 0.65 m per step, uniform heading noise of ±0.04 rad, directed
social weights, and true responsiveness spread evenly from 0.15 to 0.85 within each group.
Each scenario then degrades the observed fixes:

| Setting | Meaning |
|---|---|
| `location_sd` | Independent Gaussian error per coordinate and fix, metres |
| `dropout` | Probability that each individual fix is missing |
| `subsample` | Keep every k-th sampling time; the one-step estimand changes for k > 1 |
| `accuracy` | `declared` supplies `accuracy_m = location_sd`, activating the displacement screen |

Within a replicate, all scenarios share one simulated trajectory set and one set of
random draws, so differences between scenarios are not sampling noise in the simulation.
Each individual is fitted on all of its eligible transitions with two kernels: `social`
uses the generating weights; `uniform` ignores them, as M1 does.

## Running it

```bash
python src/recovery_study.py --output /tmp/recovery --accuracy undeclared declared
python src/verify_analysis.py /tmp/recovery
```

Outputs: `estimates.csv` (one row per replicate, scenario, individual and kernel, with fit
status), `summary.csv` (bias, RMSE, slope on truth, mean per-replicate Spearman rank
correlation, boundary and ambiguity fractions, usable-heading fraction and fallback
counts), `study.json` (settings), `recovery.{png,svg,pdf}` and `manifest.json`. Scenarios
that leave no eligible transitions are recorded with status `no_eligible_transitions`
rather than aborting the study. Set the grid from the planned sensor, sampling rate and
animal speeds, not from these defaults.

## Default-grid results (seed 2026, 3 replicates, 45 individual fits per row)

Generating kernel, no dropout, every step, accuracy undeclared unless stated:

| Scenario | Bias | RMSE | Mean Spearman |
|---|---|---|---|
| Exact positions | +0.005 | 0.028 | 0.98 |
| Location SD 0.05 m | +0.28 | 0.32 | 0.79 |
| Location SD 0.10 m | +0.38 | 0.43 | 0.60 |
| Location SD 0.25 m | +0.41 | 0.48 | 0.06 |
| Exact positions, 10% dropout | -0.08 | 0.17 | 0.81 |
| Exact positions, every 2nd step | +0.17 | 0.18 | 0.97 |
| Exact positions, uniform kernel | -0.07 | 0.15 | 0.87 |

With accuracy declared at 0.25 m, the displacement screen removes about 46% of headings
(usable fraction 0.54) and recovery does not improve (RMSE 0.53).

## What this implies for empirical design

1. **The fitting code works when the data are good.** With exact positions the generating
   kernel recovers individual responsiveness closely and in the correct rank order.
2. **Location error inflates apparent responsiveness.** Error in the focal animal's own
   observed heading pushes the fit toward the neighbour average, giving a large positive
   bias. At 0.25 m error with 0.65 m steps, individual rank order is essentially lost.
   Displacement per sampling interval relative to location error is therefore a primary
   design quantity. Many GPS collars report errors of metres, far above this grid.
3. **Missing fixes distort neighbour sets.** A neighbour whose previous fix is missing is
   excluded, so 10% dropout alone degrades recovery substantially.
4. **The estimate depends on the sampling interval.** At every 2nd step, the one-step fit
   is systematically higher than the simulated per-second trait. Compare animals only at
   a justified common interval, as the readiness review states.
5. **Kernel misspecification costs accuracy and rank order** even with exact positions.
6. **Declaring accuracy does not rescue noisy data.** The displacement screen discards
   headings and can retain intervals in which error happened to enlarge displacement.

## Limits

Errors here are independent across fixes and animals; real GNSS error is often temporally
correlated and shared between nearby collars, which can behave differently. Missingness
here is completely at random. Speeds and step lengths are fixed. The study fits on all
transitions rather than in cross-validation, because it measures recoverability rather
than prediction. Repeat it with the actual device error model, sampling interval, speed
distribution, group size and missingness pattern of the pilot data before WP4 inference.
