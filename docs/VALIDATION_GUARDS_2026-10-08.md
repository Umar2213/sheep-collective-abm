# Empirical validation safeguards, 2026-10-08

Review base: `1d908562de74ea6d0cff993e513c1d3847b9e8cc`.
Scope: WP2, WP6 and WP7. The question is whether held-out prediction comparisons preserve
the intended biological units and describe one common prediction horizon. No empirical
animal data were used and no biological claims are added.

## Changes

- Reject mixed eligible prediction intervals before fitting. Export the common duration
  and optionally check a predeclared `sampling_interval_seconds`.
- Support explicit session and study-day blocks through preparation, features, frozen
  folds, predictions and scoring. Require complete metadata constant within each bout.
- Reject uncovered feature rows in direct fitter calls rather than dropping them in a join.
- Distinguish nearby usable positions from synchronized usable neighbour headings, and
  report missing recorded bout members. These are coverage diagnostics, not a flock census.
- Export per-prediction response status and neighbour fallback reason. Make common-response
  fallback visible in the audit and report, particularly for previously unseen groups.
- Document the implications for the modelling handoff and prediction population.

## Verification

The baseline passed 68 Python tests. The updated suite passed 77, including nine new
regression tests for time-step pooling, session/day propagation, held-out target isolation,
fold coverage, unseen-group reduction, missing neighbour observations and zero social weights.
The synthetic CLI workflow with radius scenarios 5 and 10 completed, and the manifest
verifier accepted all 20 output files. Whitespace checking passed.

Local validation used Python 3.12 with the direct scientific dependency versions in
`requirements.txt`. Source was materialized through the authenticated GitHub connector;
the temporary local Git snapshot is not the upstream commit. Its synthetic output manifest
records that local snapshot and a dirty working tree. The hosted pull-request checks provide
verification on the actual published commit. Julia was not installed locally; Julia code
and historical simulation outputs are unchanged. Check hosted CI for Julia results.

## Compatibility and remaining work

Uniform-interval inputs and existing group/bout configurations remain supported. Mixed
eligible intervals now fail intentionally. Direct users of `fit_predict` should regenerate
features with `construct_features`, including interval and neighbour-fallback fields.
New audit and prediction columns are additive; existing numerical score definitions remain.

Actual sensor characteristics, an approved pilot export, biological bout definitions and
independent social observations are still needed. Synchronization, behavioural-state
validation, hierarchical repeatability, training-fold network estimation, realistic recovery,
nested tuning and a final confirmatory holdout remain study-specific work. Session/day labels
and common time steps do not establish independence or parameter identifiability.

Only code, tests and documentation belong in this change. Keep completed inventories,
restricted trajectories, private relationship matrices and empirical outputs outside Git.
