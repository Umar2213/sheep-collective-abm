# Model specification

## Purpose and scope

This repository is an exploratory collective-motion model motivated by sheep flocking.
It is not yet calibrated to measured sheep trajectories. The software is structured to
separate mechanisms that are often conflated: focal responsiveness, outgoing influence,
dyadic social relationships, metric interaction range, and update convention.

## State and units

Each agent i has position x_i, heading theta_i, responsiveness r_i and outgoing influence
q_i. The square has side L with periodic boundaries. Time, distance and speed remain
simulation units until empirical calibration is performed. Standard values are N=200,
L=20, speed=0.03, radius=1 and dt=1. Angular noise has full width eta radians and is
sampled uniformly from [-eta/2, eta/2].

## Interaction rule

Let u(theta)=(cos(theta), sin(theta)). For focal agent i, let J_i be metric neighbours
within the interaction radius, excluding i. Optional directed social ties A_ij and outgoing
influence q_j weight neighbour j. The neighbour vector is

    v_i = sum_{j in J_i} A_ij q_j u(theta_j) / sum_{j in J_i} A_ij q_j.

When no tie matrix is supplied, A_ij=1 for available neighbours. When all A_ij=1 and
all q_j=1, the implementation reduces exactly to the unweighted baseline, which is
covered by automated tests.

The focal deterministic direction is based on

    (1-r_i) u(theta_i) + r_i v_i.

Thus r_i controls how strongly i responds to neighbours. q_j controls how strongly j
contributes when observed by others. A_ij controls the pair-specific relationship from i
to j. These quantities are deliberately distinct because they need not be identifiable
from movement trajectories without additional constraints or independent measurements.
A zero total neighbour weight retains the focal direction. A numerically balanced
resultant also retains the focal direction rather than introducing atan(0,0) as an
arbitrary global direction.

## Neighbour search

New simulations use `search=:exact`, so interaction membership is determined by the
periodic Euclidean metric and the stated radius. Historical output used the library's
approximate search convention and is retained only as legacy data. Exact and approximate
searches can still be selected explicitly for matched algorithmic controls.

## Update conventions

Two update modes are implemented.

`sequential` retains the historical Agents.jl activation convention. Agents are activated
one at a time using `Schedulers.fastest`, and later agents can observe already updated
headings and positions.

`synchronous` is a scientific control. All deterministic headings and noise terms are
computed from the same pre-step state, headings are assigned together, then all agents
move. It is not silently substituted for the sequential model. Control experiments reuse
matched random streams across update modes.

## Responsiveness distribution

For target mean mu and standard deviation s, positive-s responsiveness is drawn from a
Beta distribution with

    k = mu(1-mu)/s^2 - 1,
    alpha = mu k,
    beta  = (1-mu) k.

For s=0, all agents have r_i=mu. Positive s requires s^2 < mu(1-mu). Independent draws
fix the population expectation, not the finite-flock sample mean. Responsiveness is
quenched within a run.

## Independent random streams

Trait values, initial positions/headings, and dynamical noise use separate
`MersenneTwister` streams. The public `seed` argument remains as a backward-compatible
base, while `trait_seed`, `init_seed` and `dynamic_seed` can be controlled independently.
Production and finite-size experiments use crossed trait and dynamic realizations.
Matched algorithmic controls reuse the same three seeds so differences are not driven
by unrelated initial conditions.

## Observables

Heading order is

    phi = norm(mean_i u(theta_i)),

which lies in [0,1]. It measures directional alignment, not spatial cohesion, leadership,
welfare or causal influence.

Production output records the run mean of phi, within-run temporal variance, lag-1
autocorrelation, an integrated-autocorrelation diagnostic, effective sample size, block
variation, half-window drift and late-quarter drift. Finite-size output additionally
records second and fourth moments for transparent descriptive fluctuation and Binder-like
statistics. No single diagnostic is treated as proof of stationarity or a phase transition.

## Convergence diagnostics

`src/diagnostics.jl` provides autocorrelation, integrated autocorrelation time, effective
sample size, block means and window-drift diagnostics. These are descriptive safeguards.
Publication-quality inference requires stability across longer windows, independent
initial conditions, adequate effective sample size and robust results across the explicit
algorithmic controls.

## Reproducibility boundary

Historical tables do not have complete per-run source and environment provenance, so
none is fabricated. New runs write `run_metadata.toml` with the Git commit when available,
Julia/platform information, experimental settings, seed design, project and manifest
hashes, and hashes of Julia source files.

The pinned environment currently uses Julia 1.10.5 and Agents.jl 7.0.2. Library-specific
behaviour should be rechecked if those versions are changed.
