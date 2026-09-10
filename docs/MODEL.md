# Model specification

## State and units

Each persistent agent has position x_i, heading θ_i and response weight w_i.
The square has side L; positions wrap periodically. Time, distance and speed are
simulation units with no mapping to measured sheep movement yet. Standard values
are N=200, L=20, speed=0.03, radius=1 and dt=1. Angular noise has full width η in
radians, sampled uniformly from [-η/2,η/2].

## Heading and position update

Let u(θ)=(cos θ,sin θ). For agent i, let J_i be its neighbours excluding itself.
The new deterministic heading is the angle of

    (1-w_i) u(θ_i) + w_i mean_{j in J_i} u(θ_j).

If J_i is empty, retain θ_i before adding noise. Add uniform angular noise,
set velocity to speed times u(new θ_i), and move immediately by velocity times dt.
A zero resultant uses Julia's atan convention; the physical interpretation of
exactly opposed, balanced headings is not modelled separately.

Agents are activated sequentially using `Schedulers.fastest`. Later agents see
some already-updated headings and positions. This is a deliberate preservation
of the historical update convention, not the synchronous Vicsek rule. Scheduler
and synchronous-update sensitivity remain required scientific controls.

New default searches use `search=:exact`, respecting periodic Euclidean distance.
The historical code omitted this keyword. Agents.jl 7.0.2 defaults to approximate
searches with internal grid spacing L/20. This permits extra neighbours outside
the nominal radius and makes the historical size comparison confounded.

The direction vectors are averaged before blending, not normalized to unit
length first. Thus the effective strength of neighbour input also depends on
local alignment. With k neighbours, each neighbour receives coefficient w_i/k
and the focal agent receives 1-w_i. A fixed w does not recover equal self and
neighbour weights for every changing k. Use a separately specified classical
Vicsek baseline when comparing against that model.

## Trait distribution

For target mean μ and variance s², k=μ(1-μ)/s²-1, α=μk and β=(1-μ)k.
For s=0 use w_i=μ. For positive s, require s²<μ(1-μ); at μ=0.7,
s<sqrt(0.21), approximately 0.45826. Independent draws fix the population
expectation, not a finite flock's sample mean. The traits stay fixed during a run
(quenched variation). All random draws use the model's MersenneTwister, but a
shared seed across different parameter values is not identical random inputs:
Beta draws can consume different amounts of random state.

## Observables and uncertainty

Heading order φ=norm(mean_i u(θ_i)) lies in [0,1]. A finite random group usually
has positive φ, of order N^(-1/2); φ is not a spatial cohesion measure.

Production `chi_seed` is N times the sample variance of run-average φ across
seeds. It combines trait realizations, initial conditions, dynamical randomness
and finite-window error. `phi_tempvar` is a within-run sample temporal variance.
Do not label these interchangeably as a critical susceptibility.

The legacy FSS `chi` is N times (pooled second moment minus pooled mean squared).
The updated analysis splits it exactly into mean within-run temporal variance
and population variance of run means. Its Binder statistic retains the historical
factor 3 for transparency. A 2D isotropic Gaussian vector has this statistic 1/3,
not zero. Specify the convention when comparing theory or other models.

The stored FSS drift is the absolute difference of the final two quarters of the
measurement window. A 0.02 cutoff is a screening heuristic, not a convergence
test with calibrated error. Full autocorrelation functions, block estimates,
effective sample sizes, longer windows and independent initial states are needed.

## Reproducibility boundary

The legacy tables have no complete per-run source/environment provenance. The
current manifest changed after the FSS data commit. Its existence cannot identify
the precise environment that generated earlier results. New output metadata
records source and manifest hashes; historical hashes are not fabricated.

The audit compares the supplied implementation with the pinned library source:
[StandardABM defaults](https://github.com/JuliaDynamics/Agents.jl/blob/v7.0.2/src/core/model_standard.jl)
and [continuous space searches](https://github.com/JuliaDynamics/Agents.jl/blob/v7.0.2/src/spaces/continuous.jl).
