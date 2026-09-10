# Simulation validation protocol

## Objective

This protocol defines the computational evidence required before the corrected model is
used for scientific claims. It is written before full corrected sweeps are interpreted so
that convergence and robustness criteria are not chosen after seeing the results.

## Current status

The software-verification stage has been exercised in GitHub Actions, including Julia and
Python tests plus smoke production, finite-size and matched-control experiments. Full
scientific sweeps have not yet been run and no corrected scientific result is inferred from
the smoke data.

A 1,000-step exact-radius, sequential-update calibration benchmark was also run on a
GitHub-hosted Ubuntu runner after compilation warmup. At N=200 it measured about 5,066
steps/s, corresponding to about 0.20 min for one 60,000-step run. At N=1600 it measured
about 581 steps/s, corresponding to about 2.30 min for one 80,000-step run. These are
planning measurements from hosted hardware, not biological or scientific evidence, and
full-grid throughput will depend on the actual compute resource and parallel scheduler.

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

## Stage 5, trait-distribution robustness

The primary Beta responsiveness distribution is compared with a moment-matched two-point
distribution having the same target mean and variance. Shared trait ranks and matched
initial/dynamic seeds are used so the distribution-shape contrast is paired as closely as
possible. A claimed heterogeneity effect should not be attributed to variance alone if it
changes qualitatively when the distribution shape changes.

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
5. the main heterogeneity result is not solely a consequence of one trait-distribution shape;
6. finite-size claims do not depend on a fluctuation maximum at the sampled boundary;
7. any proposed transition location is supported by more than one finite-size diagnostic;
8. biological claims are deferred until empirical sheep data are fitted and held out.

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
julia --project=. tests/trait_distributions.jl
ABM_SMOKE=1 julia --project=. --threads=2 src/production_sweep.jl
ABM_SMOKE=1 julia --project=. --threads=2 src/fss_sweep.jl
ABM_SMOKE=1 julia --project=. --threads=2 src/control_sweep.jl
```

Full experiments:

```bash
julia --project=. --threads=auto src/production_sweep.jl
julia --project=. --threads=auto src/fss_sweep.jl
julia --project=. --threads=auto src/control_sweep.jl
julia --project=. --threads=auto src/distribution_control.jl
```

## Compute boundary

The default full design contains thousands of long independent simulation runs, including
N up to 1600 in the finite-size experiment. GitHub Actions is intentionally used for
software verification, lightweight benchmarks and controlled automation rather than as an
unbounded scientific-compute service. The full sweeps should be run on a workstation,
cluster or other compute resource where wall time, memory, job interruption and resource
allocation can be managed explicitly.

The hosted benchmark provides an order-of-magnitude planning estimate only. Before a full
campaign on a different machine, rerun `src/benchmark_compute.jl` there. If the design is
split over multiple jobs, use complete-condition sharding, unique output paths and the
repository's shard merger. Every expected condition and replicate key must be present once
and only once before aggregation.

A failed or interrupted large run must not be silently treated as complete. Scientific
summaries should be generated only after the expected condition and replicate keys have
been verified.
