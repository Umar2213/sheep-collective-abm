# Empirical PhD workflow: WP0 to WP7

## Scope and question

The PhD contribution is the empirical sheep component feeding the modelling of ARC
Discovery Project DP260101231, “How individual variation drives collective motion”.
The repository supports this work; it does not establish results about real sheep.

Do persistent individual differences and stable social relationships explain held-out
movement beyond common responsiveness and spatial proximity, and which quantities are
robust enough to transfer to the modelling team?

## Work packages and current boundaries

| WP | Required work | Available software | Decision or missing input |
|---|---|---|---|
| WP0 | Study inventory, ethics, access, ownership, animal and sensor metadata | Private inventory template and storage guidance | Actual datasets, permissions, sensors, sampling design and collection dates unknown |
| WP1 | Immutable raw checksums, IDs, time, coordinates, duplicates, sampling gaps | `src/audit_trajectories.py`, `src/trajectory_validation.py` | Raw adapter and device quality semantics depend on actual files |
| WP2 | Projection, fixed quality rules, synchronized trajectories, recorded exclusions | `src/trajectory_pipeline.py`, flagged `prepared.csv` | No automatic interpolation, smoothing or resampling; justify these before adding them |
| WP3 | Biologically defensible sessions, movement bouts and states | Existing bout IDs respected; gaps and low-displacement headings flagged | No validated bout detector or behavioural classifier implemented |
| WP4 | Within versus among-individual variation, repeatability, responsiveness, group position and initiation | `individual_bouts.csv` and training-only response fits | Summaries are descriptive; hierarchical repeatability and initiation/following require repeated independent observations and defined events |
| WP5 | Stable dyadic relationships, observation effort and network uncertainty | Independent directed tie input, proximity and network-label controls | No fold-specific social estimator or stability inference implemented |
| WP6 | M0 to M3 comparisons on complete held-out blocks | Frozen folds, matched scores, conditional cluster bootstrap, sensitivity | Final confirmatory holdout, nested tuning and alternative biological kernels depend on design |
| WP7 | Versioned, uncertainty-aware empirical handoff | Manifest, units, source hashes, verifier and handoff checklist | Scientific review and approved access required before release |

## Required design decisions before real-data fitting

1. Complete the private study inventory. Keep anonymization keys and original coordinates restricted.
2. Audit the raw export before adapting it. Document time zones, device quality flags,
   metric CRS, sensor error and every exclusion. Do not alter the original export.
3. Define sessions and bouts biologically. A recording session and a movement bout are
   different concepts. Do not relabel frames to manufacture independent replicates.
4. Specify the prediction population: future sessions of familiar sheep, new sheep, or
   new groups. The current fitter estimates responses within `(group_id, individual_id)`;
   an animal moving groups receives a separate group-specific fit. Stable study-wide
   animal IDs should still be retained. This is not a cross-context repeatability model.
5. Choose splits and uncertainty units before looking at results. Current integrated
   blocking supports group and group/bout only. For day/session splits, add explicit
   support with tests; do not disguise them as arbitrary bout labels. Nonoverlapping
   bouts from the same session can still be dependent.
6. Predeclare preprocessing and radius settings. Supplied social ties must be independent
   of all analysed sessions. Training-derived ties need an estimator inside each fold;
   a global matrix with `ties_independent: true` is not a substitute.
7. Use complete biological blocks. With few independent groups, report exploratory
   estimates and limitations. Do not manufacture precision from frame counts.
8. Run recovery under realistic location error, missingness and sampling intervals before
   interpreting fitted responsiveness. The existing noiseless one-step tests are insufficient
   to establish empirical identifiability, interval coverage or stable animal traits.

## Primary model contrasts

| Question | Contrast |
|---|---|
| Individual responsiveness adds prediction | M1 versus M0 |
| Social relationships add prediction | M2 versus M0 and distance control |
| Relationships add beyond individual response | M3 versus M1 |
| Individual response adds beyond relationships | M3 versus M2 |
| Combined predictive performance | M3 versus M0, persistence, constant turn and distance |
| Network labels matter | M3 versus network-shuffled individual-response controls |

The existing shuffle controls have individual responsiveness, so they are matched to M3,
not a pure M2 social-only permutation test. A few seeds do not yield a permutation p-value.
Additional matched common-response shuffles should be added if required by the final WP5
protocol. M4 is conditional on separately identifying outgoing influence; it is not a primary
PhD requirement. Prediction gains are not causal effects.

## Completion criteria

A negative or imprecise result is valid. An empirical package is complete when its inputs,
exclusions, units, provenance, uncertainty, validation population and limitations are
reviewable, regardless of whether M1, M2 or M3 improves prediction. Full simulation sweeps
are supporting modelling tasks, not prerequisites for starting WP0 to WP3.

The app and website should consume versioned outputs from tested analysis code. They must
not tune settings using held-out scores or make private exports public by default.
