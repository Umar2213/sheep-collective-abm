# Research development plan

## Scope

The primary PhD scope is the empirical sheep component feeding the mathematical modelling
of ARC Discovery Project DP260101231. Build a reproducible empirical pipeline and deliver
validated data, biological measurements, statistical estimates, social-network information
and model-validation evidence. The agent-based model supports this scope.

The operational plan is [WP0 to WP7](EMPIRICAL_ROADMAP.md). Begin with data governance and
the study inventory, raw trajectory audit, preprocessing and defensible behavioural units.
Simulation sweeps are supporting work and must not displace empirical study preparation.
No empirical sheep findings are currently established by this repository.

The project deliberately separates three quantities that are easy to conflate:

- focal responsiveness `r_i`, how strongly individual i changes its own direction in
  response to others;
- outgoing influence `q_j`, how strongly neighbour j contributes to other individuals;
- directed dyadic weighting `A_ij`, how strongly individual i uses information from j.

This distinction is central to the research design. More parameters are not automatically
better, and outgoing influence should only be estimated if parameter-recovery experiments
show that it can be separated from dyadic relationship weights.

## Research question

**Are individual movement differences repeatable, are social relationships stable, and
do individual responsiveness and independently characterized dyadic relationships provide
non-redundant prediction of sheep movement beyond common response and spatial proximity?**

Outgoing influence is an optional modelling extension only after separate identifiability
is established. It is not a primary empirical PhD objective.

This is a candidate research contribution, not a novelty claim. `NOVELTY_MATRIX.md`
records representative prior work and the evidence needed before a novelty statement is
made.

## Model comparison hierarchy

All models should use the same movement kernel, boundary treatment, observation model,
training/test split and scoring rules.

| Model | Individual responsiveness | Partner-specific ties | Outgoing influence |
|---|---|---|---|
| M0 | common | uniform | fixed 1 |
| M1 | individual | uniform | fixed 1 |
| M2 | common | measured/estimated | fixed 1 |
| M3 | individual | measured/estimated | fixed 1 |
| M4 | individual | measured/estimated | estimated only if identifiable |

M0 to M3 are the primary hierarchy. M4 is conditional on parameter recovery and should be
dropped if `q_j` and `A_ij` cannot be separately identified.
With externally fixed nonuniform ties, M0 and M2 are not generally nested statistical
models. Use the specified matched held-out comparisons, not a likelihood-ratio test that
assumes every pair in the hierarchy is nested.

## Testable hypotheses

H1. M1 improves held-out directional or displacement prediction over M0 when persistent
individual responsiveness differences are present in the empirical data.

H2. M2 improves held-out prediction over M0 and over proximity-only or shuffled-tie
controls when independently measured relationship structure contains predictive
information beyond local geometry.

H3. M3 improves held-out prediction over both M1 and M2 if individual responsiveness and
partner-specific weighting contribute non-redundant information.

H4. Estimated latent parameters remain stable enough across training subsets and
parameter-recovery experiments to support biological interpretation. Failure of this
hypothesis means the model can still be predictive, but the latent parameters should not
be interpreted as measured causal influence.

H5. The main qualitative simulation result remains under exact metric neighbour search and
is not created by the sequential update convention.

These hypotheses may be rejected. No result is assumed in advance.

## Computational work before animal data

For supporting simulation claims, follow `EXPERIMENT_PROTOCOL.md`. These experiments
are not prerequisites for starting empirical WP0 to WP3.

1. Verify the corrected exact-radius implementation with automated tests and smoke runs.
2. Use independent random streams for traits, initial state and dynamical noise.
3. Cross multiple dynamic realizations with each trait realization to distinguish major
   sources of simulation variability.
4. Run the corrected N=200 production grid and quantify per-run convergence diagnostics.
5. Repeat the fixed-density size comparison only after the corrected interaction rule is
   established.
6. Compare exact versus approximate neighbour search on matched random realizations.
7. Compare sequential versus synchronous updating on the same matched realizations.
8. Compare Beta responsiveness distributions with alternative bounded distributions or
   moment-matched finite populations to determine whether any apparent effect is driven by
   tail mass rather than dispersion itself.
9. Add parameter-recovery experiments for synthetic `r_i`, `A_ij` and, only when justified,
   `q_j` before fitting these quantities to animal data.

Full trajectories or adequately sampled trajectories should be retained for the experiments
used to study mechanisms, not only condition averages.

## Distributional robustness

A fixed Beta mean with changing standard deviation changes more than one mathematical
feature of the population. It changes tail probabilities and finite-sample composition.
Therefore a strong mechanistic analysis should include at least one of the following:

- moment-matched alternative bounded distributions;
- finite populations constructed to have tightly controlled sample mean and variance;
- analyses that condition on realized mean, variance and low/high-response tail fractions.

The aim is to separate an effect of heterogeneity from an effect of a particular Beta tail.

## Empirical data requirements

Minimum movement data should include:

`group_id`, `bout_id`, `individual_id`, `timestamp`, projected `x` and `y` in metres.
Use stable anonymized IDs. Record quality information and the observation interval when
available; do not invent missing sensor metadata.

Useful accompanying data include repeated behavioural measurements, group composition,
movement state, environmental conditions, body or physiological measurements relevant to
the biological question, and independent observations from which social relationships can
be estimated.

Longitude and latitude degrees must not be treated as Euclidean metres. Movement direction
should only be estimated when displacement is sufficiently larger than location error, or
an explicit observation-error model should be fitted.

## Social relationships and leakage control

Social ties used to predict a test movement should be estimated from independent or
pre-training observations. Constructing a network from the same movement bout being
predicted risks circularity.

The primary empirical comparison should include:

- uniform-neighbour baseline;
- proximity-only weighting;
- independently estimated social ties;
- shuffled traits;
- shuffled ties that preserve relevant network structure;
- individual responsiveness alone;
- social ties alone;
- their joint model.

## Train/test design

Do not randomly split adjacent GPS frames. Such frames are strongly dependent and can make
prediction accuracy look unrealistically high.

Prefer held-out units such as complete days, movement bouts or groups. If enough independent
groups are available, a particularly strong design is leave-one-group-out evaluation.
Model selection should occur without touching the final test units.

## Evaluation

Potential predictive outcomes include heading or turning-angle error, displacement forecast
error and predictive log score when a probabilistic observation model is used. Group-level
outcomes may include spatial cohesion, fragmentation, initiation/following latency and
leadership turnover when these are defined independently of the fitted model.

Uncertainty should be calculated at the level of independent groups, days or bouts, not by
treating thousands of adjacent GPS frames as independent observations.

## Parameter recovery

Before interpreting `r_i`, `A_ij` or `q_j`, generate synthetic data from known parameters,
fit the intended inference procedure, and measure recovery error, bias, interval coverage
and confounding between parameter classes.

Important tests include:

- whether heterogeneous `r_i` can be recovered when all ties are uniform;
- whether directed `A_ij` can be recovered when responsiveness is common;
- whether joint `r_i` and `A_ij` are distinguishable;
- whether free `q_j` can be distinguished from rescaling columns of `A_ij`;
- sensitivity to location error, missing observations and sampling interval;
- sensitivity to unmodelled stop/start behaviour.

If recovery fails, reduce model complexity before biological interpretation.

## Decision gates

**Software gate:** Julia tests and all four smoke experiments pass in the pinned
environment.

**Simulation gate:** corrected exact-radius results are reproducible, per-run convergence is
acceptable after any required extensions, and the principal effect survives matched
algorithmic controls.

**Distribution gate:** the main conclusion is not solely a consequence of the chosen Beta
distribution tail or uncontrolled realized sample means.

**Identifiability gate:** synthetic parameter recovery establishes which latent quantities
can be estimated reliably.

**Empirical gate:** evaluate held-out sheep trajectories against simpler baselines with
uncertainty assessed at independent biological units. No improvement, weak individual
differences and unidentifiable parameters are valid outcomes, not failed research.

**Novelty gate:** a focused literature review shows that the final combination of mechanism,
identifiability analysis and empirical predictive test makes a specific contribution beyond
published work.

A publication claim should follow these gates. Additional phase diagrams or a more complex
model are not substitutes for robust mechanism, identifiability and held-out validation.
