# Research integrity review, 2026-09-11

The research target remains the joint, held-out predictive value of individual
responsiveness and independently characterised social relationships. This review improves
software and evaluation infrastructure; it does not establish novelty or biological validity.

## Repaired failure modes

| Area | Finding | Change |
|---|---|---|
| Distributed metadata | The merger ignored `timestamp_utc` and `julia_threads`, but Julia writes `recorded_utc` and `threads`. Real shards with different timestamps were rejected. | Ignore actual runtime-only fields while retaining source and scientific-setting comparisons. Preserve complete source metadata in the merge report. |
| Replicate coverage | Correct total row counts could hide a missing replicate replaced by an unexpected ID. | Compare full condition and crossed replicate keys with the declared metadata grid, including control tables. |
| Output integrity | Main CSVs were written before supplemental validation, leaving partial output on failure. | Validate all inputs before staging and atomically publishing a fresh output directory. Reject existing destinations. Hash published CSVs. |
| Summary integrity | Stale means could pass as valid summaries. | Recompute heading means and available sample counts from replicate rows. Reject nonfinite values and inconsistent shard schemas. |
| Trajectory data | Empty tables and missing or blank biological IDs could pass validation. | Report missing identifiers and reject invalid inputs before downstream analysis. |
| Folds | Hash modulo allocation could produce empty test folds. Reassigning an existing fold column caused an opaque merge failure. | Deterministically distribute whole blocks across populated folds and explicitly reject an existing fold column or insufficient blocks. Freeze folds because adding blocks may change assignments. |
| Parameter recovery | A local optimizer omitted endpoints and could return a number for flat loss. | Profile the loss on 1,001 points, refine candidate minima, include endpoints, reject flat profiles and expose an ambiguity screen. |
| Numerical consistency | Python used a different cancellation tolerance from Julia. Products of large finite social weights could overflow. | Match the Julia tolerance and normalize Python neighbour weights in log space. |
| Prediction evaluation | The planned held-out model hierarchy had no matched block scoring utility. | Add strict same-observation comparisons, circular scores and equal-block paired bootstrap MAE differences. |
| CI coverage | Synthetic Python fixtures missed the real metadata incompatibility. Distribution smoke generation was absent. | Generate and merge actual two-shard Julia smoke outputs for production, finite-size and both control families. |

## Validation

- The expanded local Python suite passes 40 tests, including regression and synthetic
  parameter-recovery checks.
- The stored-data audit passes for nine source tables; historical production and finite-size
  summaries reproduce from replicate rows.
- Python compilation and whitespace checks pass.
- Julia is unavailable in the local editing environment. The pull request CI runs Julia
  model tests, trait-distribution tests, all four smoke shard/merge integrations and the
  benchmark smoke command. Consult its check status for the hosted execution result.

## Scientific work still required

1. Complete full corrected production, finite-size, algorithmic and distribution-control
   runs, inspect convergence per run and extend poorly mixed conditions. Smoke outputs
   are software tests only.
2. Historical approximate-search results remain historical. The audit still flags 323 of
   1,520 finite-size runs for drift above 0.02; these runs were not regenerated here.
3. Obtain suitable empirical sheep trajectories and independently measured or training-only
   social relationships. The repository contains no empirical trajectory dataset.
4. Fit the M0 to M3 hierarchy under frozen biological splits, include proximity, shuffled
   networks and appropriate alternative movement kernels, then score held-out predictions.
5. Treat numerical recovery as a prerequisite, not proof of statistical identifiability.
   The finite profile grid may miss extremely narrow minima, and the ambiguity screen is
   not a confidence interval. Free dyadic ties and outgoing influence retain their
   structural confounding.
6. Assess candidate novelty against the literature and actual empirical findings. Improved
   infrastructure alone is not a new scientific result.

No historical scientific outputs or Julia movement equations were changed by this review.
