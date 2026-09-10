# Sheep collective ABM: heterogeneous alignment response

[![Model and stored-data checks](https://github.com/Umar2213/sheep-collective-abm/actions/workflows/checks.yml/badge.svg)](https://github.com/Umar2213/sheep-collective-abm/actions/workflows/checks.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Julia 1.10.5](https://img.shields.io/badge/Julia-1.10.5-9558B2.svg)](https://julialang.org/)

Research software for investigating how individual differences in alignment
response affect collective heading order in a sheep-inspired agent-based model.
The current model is computational and exploratory. It is not yet calibrated or
validated against measured sheep trajectories, and novelty has not been established.

**September 2026 audit:** the historical production script was corrupted by pasted
shell text. More substantially, historical neighbour searches used the library's
approximate radius, whose grid spacing increases with box size. New simulations
now use exact-radius searches. Stored results and the figures below describe the
**legacy approximate-search model**, and must not be presented as results of the
corrected model. See [the audit](docs/AUDIT.md), [model specification](docs/MODEL.md)
and [research plan](docs/RESEARCH_PLAN.md).

## What is implemented

- Agents have persistent individual response weights `w` drawn independently from
  a Beta distribution with target mean 0.7 and standard deviation σ.
- Each agent blends its own heading with the average heading vector of neighbours.
  Its `w` measures response to others, not the influence it exerts on others.
- Agents move at constant speed in a periodic 2D square with uniform angular noise.
- Updates are sequential and in place, using `Schedulers.fastest`, rather than
  synchronous classical Vicsek updates. Exact metric neighbours exclude the focal agent.
- φ measures heading alignment, not spatial cohesion, leadership or welfare.
- No empirically estimated social network or GPS calibration is implemented.

The Beta **distribution** mean is fixed. Realized group means fluctuate, ranging
from 0.6428 to 0.7546 in the stored production runs. Increasing σ changes the entire
bounded distribution, including its tail fractions, not variance alone.

## What the stored data support

There are 1,140 production runs (N=200, three noise levels, 19 dispersion levels,
20 seeds) and 1,520 exploratory size-comparison runs (N=100,200,400,800,1600;
η=0.5; 19 dispersion levels; 16 seeds). Their summary tables match the stored
replicate data. This consistency does not establish simulation provenance.

At N=200 the legacy data show decreasing average heading order with dispersion.
The following are descriptive crossings of the arbitrary φ=0.90 level, not
critical points or biological tolerance limits:

| Noise η | σ at φ=0.90 | 95% bootstrap interval |
|---|---:|---:|
| 0.3 | 0.3578 | 0.3543 to 0.3618 |
| 0.5 | 0.3233 | 0.3176 to 0.3284 |
| 0.7 | 0.2789 | 0.2732 to 0.2835 |

Intervals resample whole seed curves, 2,000 times. They quantify realization
uncertainty conditional on this model and grid, not model error or interpolation
bias. The φ=0.50 level is not reached in the stored mean curves.

![Legacy approximate-search production results](figures/fig_main_v2.png)

The size comparison cannot establish a phase transition: the interaction search
is confounded with size, 323/1,520 runs exceed the drift warning threshold of 0.02,
and four of five pooled fluctuation maxima occur at the largest sampled σ.
Lag-1 correlation alone does not demonstrate critical slowing down. The short-run
diagnostic **underestimates** order by 0.1344 at σ=0.35; earlier wording reversed
this sign. Small drift of seed-averaged curves does not establish per-run stationarity.

## Reproduce the stored-data analysis

Run from the repository root. Python 3.12 is the CI target; the Python environment
used during the audit is recorded in `requirements.txt`. The existing Julia
manifest records Julia 1.10.5 and Agents.jl 7.0.2. It was preserved, not regenerated.

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/audit_results.py
python src/analyze_production.py
python src/make_main_figure.py
python src/analyze_fss.py
python src/make_snapshots.py
```

The audit writes checksums, recomputed threshold intervals, decomposed fluctuation
statistics and a list of runs requiring stationarity review to `results/audit/`.
Original simulation CSVs are preserved. Plot scripts regenerate the tracked figures.

## Run the corrected simulations

```bash
julia --project=. -e 'using Pkg; Pkg.instantiate()'
julia --project=. tests/runtests.jl
ABM_SMOKE=1 julia --project=. --threads=2 src/production_sweep.jl
ABM_SMOKE=1 julia --project=. --threads=2 src/fss_sweep.jl
# Full runs are computational experiments, not completed by the audit:
julia --project=. --threads=auto src/production_sweep.jl
julia --project=. --threads=auto src/fss_sweep.jl
```

Smoke runs use tiny populations and 120 steps and provide no scientific evidence.
Full defaults retain the historical run lengths, which still require convergence
assessment. Exact-search results go to `results/exact_production/` and
`results/exact_fss/`; source hashes and parameters are recorded alongside them.
`ABM_OUTPUT_DIR` overrides the output folder. Repeated runs overwrite that folder.
`ABM_NEIGHBOR_SEARCH=approximate` explicitly selects the legacy search convention
and defaults to separate `results/approximate_*` folders.

To analyze a new production run without replacing the legacy figures:

```bash
ABM_DATA_LABEL="Exact-radius results" ABM_ANALYSIS_DIR=results/exact_production ABM_FIGURE_DIR=figures/exact python src/analyze_production.py
ABM_DATA_LABEL="Exact-radius results" ABM_ANALYSIS_DIR=results/exact_production ABM_FIGURE_DIR=figures/exact python src/make_main_figure.py
ABM_DATA_LABEL="Exact-radius results" ABM_ANALYSIS_DIR=results/exact_fss ABM_FIGURE_DIR=figures/exact ABM_AUDIT_DIR=results/exact_audit python src/analyze_fss.py
```

`diag_equilibration.jl`, `diag_relaxation.jl` and `snapshot_states.jl` now also use
exact searches and write separate `exact_diagnostics` or `exact_snapshots` folders.
The 500-step direct invocation of `heterogeneous_model_v2.jl` is only a pilot.

## Research direction and citation

The priority is a comparison of homogeneous response, heterogeneous response,
recognised social ties, and their combination, evaluated on held-out sheep
trajectories. A successful contribution would explain when measured social
relationships and individual states improve prediction beyond simpler baselines.
See the [specific hypotheses, controls and data requirements](docs/RESEARCH_PLAN.md).

Related work already studies heterogeneous social networks, individualistic motion
and differential leadership. See [prior research](docs/RESEARCH_PLAN.md#prior-research).
A Beta sweep by itself does not establish novelty.

See `CITATION.cff` for software citation and `LICENSE` for the MIT license.
