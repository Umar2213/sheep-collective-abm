# Simulation validation protocol

## Objective

This protocol defines the computational evidence required before the corrected model is
used for scientific claims. It is written before full corrected sweeps are interpreted so
that convergence and robustness criteria are not chosen after seeing the results.

## Stage 1, software verification

Required before any full experiment:

- all Julia and Python tests pass;
- exact periodic radius tests pass;
- uniform social ties with unit outgoing influence reduce exactly to the baseline;
- synchronous and sequential modes are each deterministic for fixed seeds;
- smoke production, finite-size and matched-control runs complete successfully;
- new run metadata identify source, environment and random-stream design.

## Stage 2, corrected production sweep

Default design:

- N = 200;
- density equivalent to L = 20;
- target responsiveness mean = 0.7;
- responsiveness SD = 0.000 to 0.450 in increments of 0.025;
- angular noise = 0.3, 0.5 and 0.7;
- exact metric neighbours;
- sequential update as the primary convention;
- 5 trait realizations crossed with 4 dynamic/initial-state realizations;
- 60,000 steps, first 30,000 discarded provisionally.

The crossed design is intentional. It allows trait-realization variability to be separated
descriptively from variability due to initial state and dynamics.

## Stage 3, finite-size comparison

Default design:

- N = 100, 200, 400, 800 and 1600;
- density fixed at 0.5 by L = sqrt(N / 0.5);
- angular noise = 0.5;
- same responsiveness grid as the production sweep;
- exact metric neighbours;
- sequential update;
- 4 trait realizations crossed with 4 dynamic/initial-state realizations;
- 80,000 steps, first 40,000 discarded provisionally.

Binder-like and pooled fluctuation statistics remain descriptive until convergence,
interior extrema and cross-size consistency are demonstrated.

## Stage 4, matched algorithmic controls

The same trait, initial-state and dynamic seeds are reused across the following controls:

- exact versus approximate neighbour search;
- sequential versus synchronous update.

The primary comparison is the paired change in mean heading order for each realization.
A qualitative scientific result should not depend solely on one undocumented algorithmic
convention.

## Convergence assessment

Each post-warmup run records:

- mean heading order;
- temporal variance;
- lag-1 autocorrelation;
- integrated-autocorrelation diagnostic;
- effective sample size;
- SD of contiguous block means;
- difference between first and second halves;
- difference between the final two quarters.

No single cutoff certifies stationarity. Conditions with poor effective sample size,
large block variation or persistent window drift must be rerun with longer warmup and
measurement windows. Stability should be checked by comparing estimates from nested
longer windows rather than treating a small final-quarter difference as sufficient.

## Decision rules

A result can move forward to interpretation only if:

1. software and smoke checks are green;
2. the primary estimate is stable when the measurement window is lengthened;
3. multiple independent trait and dynamic realizations agree within quantified uncertainty;
4. the qualitative effect persists under synchronous-update and exact-search controls;
5. finite-size claims do not depend on a fluctuation maximum at the sampled boundary;
6. any proposed transition location is supported by more than one finite-size diagnostic;
7. biological claims are deferred until empirical sheep data are fitted and held out.

## Empirical-validation gate

A later sheep-data study should evaluate nested models M0 to M4 defined in
`NOVELTY_MATRIX.md`. Train/test division should occur at the level of complete days,
groups or movement bouts. Social ties used for prediction should be estimated from
independent or pre-training data. Parameter recovery on simulated data is required before
interpreting latent responsiveness or influence parameters biologically.

## Reproducible commands

Software and smoke validation:

```bash
julia --project=. -e 'using Pkg; Pkg.instantiate()'
julia --project=. tests/runtests.jl
ABM_SMOKE=1 julia --project=. --threads=2 src/production_sweep.jl
ABM_SMOKE=1 julia --project=. --threads=2 src/fss_sweep.jl
ABM_SMOKE=1 julia --project=. --threads=2 src/control_sweep.jl
```

Full experiments:

```bash
julia --project=. --threads=auto src/production_sweep.jl
julia --project=. --threads=auto src/fss_sweep.jl
julia --project=. --threads=auto src/control_sweep.jl
```

## Compute boundary

The default full design contains thousands of long independent simulation runs, including
N up to 1600 in the finite-size experiment. GitHub Actions is intentionally restricted to
small smoke experiments because hosted CI is for software verification, not for consuming
large amounts of scientific compute. The full sweeps should be run on a workstation,
cluster or other compute resource where wall time, memory and job interruption can be
managed explicitly.

Before launching the complete grid, benchmark representative N=200 and N=1600 conditions.
Use those timings to choose a realistic parallelization strategy. If the design is split
over multiple jobs, every job must use unique output paths and metadata, and all parts must
be checked for duplicate or missing condition and replicate keys before aggregation.

A failed or interrupted large run must not be silently treated as complete. Scientific
summaries should be generated only after the expected condition and replicate keys have
been verified.
