# Research development plan

## Scope

This repository develops an exploratory sheep-inspired collective-motion model focused
on how persistent individual differences in responsiveness can affect group-level
movement. The current implementation is computational rather than empirically
calibrated. The next stage is to test whether individual response differences and
measured social relationships improve prediction of observed sheep movement.

| Research need | Repository status | Necessary next step |
|---|---|---|
| Individual differences | Persistent response weights | Relate response to measured traits and state |
| Heterogeneous influence | Indirect effects possible, influence not parameterised or measured | Separate responsiveness from outgoing influence |
| Recognised social partners | Absent | Introduce independently estimated dyadic tie weights |
| Sheep biology | Generic constant-speed movement | Test stop/start states, spatial attraction, repulsion and arena effects |
| Empirical prediction | No animal data or calibration | Fit training trajectories and test held-out groups/days |

## Novelty judgement

Novelty is **not established**. The broad proposition that heterogeneity affects
collective motion is already well studied. A fixed-mean Beta response sweep could
be a specific numerical contribution only after demonstrating a distinct mechanism,
robustness and predictive value beyond existing work. This targeted literature
check is not an exhaustive systematic review and cannot certify priority for the
exact rule.

### Prior research

| Primary source | Relevant contribution | Consequence for this repository |
|---|---|---|
| [Miguel, Parley & Pastor-Satorras (2018), Effects of heterogeneous social interactions on flocking dynamics](https://arxiv.org/abs/1801.03371), [PRL DOI](https://doi.org/10.1103/PhysRevLett.120.068303) | Heterogeneous social-network topology in a Vicsek variant affects collective order | Network heterogeneity is established prior art; its mechanism differs from individual response dispersion |
| [Baglietto, Albano & Candia (2013), Gregarious vs Individualistic Behavior in Vicsek Swarms](https://arxiv.org/abs/1303.6315) | Individualistic movement can destroy ordered motion in a model variant | Low-response or individualistic minorities affecting order is not a new broad claim |
| [Toulet et al. (2015 preprint), Imitation Combined with a Characteristic Stimulus Duration Results in Robust Collective Decision-making in Sheep](https://arxiv.org/abs/1512.07307) | Sheep experiments and a model link imitation and stimulus duration to departure/following consensus | Sheep-specific behaviour and quantitative experiment/model comparison provide a benchmark |
| [Garland et al. (2018 preprint), Anatomy of Leadership in Collective Behaviour](https://arxiv.org/abs/1802.01194) | Distinguishes components of leadership and supplies inference test models | Position, response, information flow and causal influence require separate definitions |

Network topology, response weights and independent direction choices are distinct
mechanisms, so apparently different effects should not be treated as contradictions
without matched model comparisons.

## Proposed research question

**Do measured individual response differences and recognised social ties jointly
improve out-of-sample predictions of sheep movement, beyond either mechanism alone?**

This is an untested candidate contribution, not a novelty claim. Its exact scope
should be defined against the literature and agreed with the relevant supervisor or
research collaborators before being presented as a thesis or publication contribution.

## Model comparison and hypotheses

Use the same movement kernel, boundaries, observation model and fitting protocol
for all four nested models:

| Model | Individual response | Partner-specific ties |
|---|---|---|
| M0 | Common response | Equal weights among local neighbours |
| M1 | Individual response | Equal weights among local neighbours |
| M2 | Common response | Measured tie weights |
| M3 | Individual response | Measured tie weights |

For a moving agent i, a candidate weighted neighbour vector is

    sum_j A_ij(t) q_j u_j / sum_j A_ij(t) q_j,

restricted to visible/local neighbours. A_ij expresses i's relationship to j;
q_j is outgoing influence, and a separate r_i controls i's responsiveness.
Their product can be non-identifiable. Start with q_j=1 and measured, normalized
A_ij. Add free outgoing influence only if parameter-recovery experiments and
independent data support it. Handle an empty/zero-weight neighbour set by retaining
self direction. Predictive performance alone does not prove causal influence.

H1: M1 improves held-out direction predictions over M0.
H2: M2 improves predictions over spatial proximity alone and shuffled ties.
H3: M3 improves predictions over both M1 and M2.
H4: social ties buffer or amplify the effect of physiological state on initiation
and following, if repeated state measurements and sufficient independent groups
are available. These hypotheses may be rejected; no outcome is presumed.

## Work that can precede animal data

1. Run the supplied Julia tests and smoke experiments, then benchmark exact versus
   legacy search on matched parameter grids. Keep outputs and metadata separate.
2. Establish exact-search baselines at μ=0.7 and σ=0 before larger sweeps. Test
   sequential versus synchronous updates, density, speed/radius ratio and noise.
3. Separate trait, initial-state and dynamical RNG streams. Cross multiple dynamic
   seeds with each trait realization to distinguish sources of variability.
4. Compare Beta distributions against other bounded distributions and moment-matched
   finite populations. Quantify tail-fraction and realized-mean effects. Do not
   remove or clip low weights while claiming the same mean and variance.
5. Save full or adequately sampled trajectories, agent identities, traits, block
   moments and per-run diagnostics. Require stable estimates across successively
   longer windows and initial conditions. Use block resampling for time dependence.
6. Implement the nested social-tie models in a versioned experimental module and
   verify exact reduction to M0 under uniform weights. Do not silently change the
   legacy model or attach synthetic output to an empirical claim.

The audit implements repairs and analysis foundations. It does not imply these
future model experiments have already been performed.

## Data and validation protocol

Minimum trajectory fields: group_id, animal_id, timestamp_utc, x_m, y_m, position
quality/uncertainty and observation interval. Use a documented projected coordinate
system; never treat longitude/latitude degrees as Euclidean metres. Retain missing
observations and specify interpolation limits. Estimate directions only where
movement exceeds the GPS error scale, with an explicit observation model.

Record repeated behavioural assays, observed movement state, relevant physiological
state, group composition, encounter opportunity and arena/environmental conditions.
The specific measurements and animal procedures require appropriate research design
and ethics approval. No empirical measurements are supplied in this repository.

Estimate social ties in independent/pre-training observation windows and control
for spatial opportunity. Ties calculated from the same test movement being predicted
create circularity. Split by complete days, bouts and groups before fitting or
normalization, never randomly split adjacent GPS frames. Keep final test groups or
days untouched during model selection.

Use held-out heading/turn errors, displacement forecast error and predictive
log scores where a probabilistic observation model is specified. Also compare
spatial cohesion, initiation/following latency, fragmentation and leadership
turnover, with predefined measures. Report uncertainty resampled at the independent
group/day level, not thousands of correlated GPS frames. Compare shuffled traits,
shuffled networks preserving relevant structure, and proximity-only baselines.
Perform parameter recovery on simulated data before interpreting fitted mechanisms.

## Decision gates

- Software gate: Julia tests and both smoke entry points pass on the pinned environment.
- Simulation gate: exact-radius, update-rule and stationarity controls yield reproducible estimates.
- Empirical gate: verified trajectory data, independent social ties, identifiable parameters,
  and held-out predictive improvement support the biological question.
- Novelty gate: a focused literature matrix and supervisor comparison identify the precise
  contribution beyond existing mechanisms.

A publication claim should follow these gates. More phase diagrams or a more complex
model alone are not a substitute for a well-defined biological mechanism and test.
