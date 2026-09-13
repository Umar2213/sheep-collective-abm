# Reproducible analysis workflow

This workflow produces one-step heading predictions and a complete computational audit.
It does not automatically establish novelty, causality, biological validity or suitability
for a specific tracking device. Use independent observations before making such claims.

## What is executable

- Metric trajectory validation, or WGS84 GPS conversion to an explicitly selected projected
  metre CRS using pyproj. Longitude is passed first with `always_xy=True`; positions outside
  the target CRS area of use are rejected. See [pyproj Transformer documentation](https://pyproj4.github.io/pyproj/stable/api/transformer.html).
- Fixed speed, temporal-gap and optional positional-accuracy filters. Invalid fixes remain
  visible in the audit and invalidate adjacent intervals rather than creating bridges.
- Matched one-step predictions from M0 through M3 when independent social ties are supplied.
- Persistence, constant-turn, distance-decay and whole-network label-shuffle controls.
- Frozen biological splits, training-only fits, and uncertainty over a separately declared
  unit that can be coarser than the train/test split.
- Reproducible conditional paired bootstrap intervals, sensitivity scenarios and reports.
- Seeded synthetic demonstrations with known responsiveness parameters and social matrices.

## Minimal real-data input

CSV columns: `group_id,bout_id,individual_id,timestamp,x,y`. IDs are strings and leading
zeros are preserved. Times require explicit timezone information. `x,y` must be metres.
Set `crs` to a suitable projected CRS or `local_metres` for an already documented local
metric system. The latter is an explicit user declaration, not something the program can
verify. For GPS, replace x/y with `latitude,longitude`, set `coordinate_mode` to `gps`,
and choose a locally appropriate projected metre CRS. Do not use raw degrees as metres.

An optional `accuracy_m` column must have a finite nonnegative value for every observation.
Its interpretation must be checked against device documentation. The displacement screen
uses `displacement_sigma * hypot(accuracy_previous, accuracy_current)`; it is only a
quality heuristic unless those accuracy values have the assumed statistical meaning.
Missing accuracy values are not silently replaced with evidence of perfect accuracy.

No interpolation, smoothing or resampling is performed. Prediction features require
consecutive equal-duration intervals. Neighbours must have headings from the same past
interval as the focal animal. This may discard substantial asynchronous GPS data; obtain
a justified synchronisation protocol before fitting such data, rather than guessing.

## Configuration and study design

`AnalysisConfig` in `src/trajectory_pipeline.py` declares all settings. For example:

```json
{
  "data_kind": "observational",
  "coordinate_mode": "metric",
  "crs": "local_metres",
  "min_speed": 0.05,
  "max_speed": 15.0,
  "max_gap": 10.0,
  "max_accuracy": 10.0,
  "displacement_sigma": 2.0,
  "radius": 10.0,
  "n_folds": 3,
  "split_columns": ["group_id", "bout_id"],
  "uncertainty_columns": ["group_id"],
  "min_individual_train": 10,
  "n_bootstrap": 2000,
  "shuffle_seeds": [11, 29, 47],
  "seed": 42,
  "ties_independent": false
}
```

These numbers are demonstration settings, not validated biological defaults. Set them
from recording characteristics and the study design before examining test results.
Holding out sessions asks about unseen sessions of possibly familiar individuals.
Holding out groups asks about new groups; individual parameters then fall back to a
common training estimate when no training observations of those individuals exist.
These are different prediction questions and must not be conflated.

Group-level uncertainty can keep multiple sessions together. It still requires reasonable
independence between groups. With one uncertainty unit the software withholds intervals.
With fewer than five it explicitly flags weak uncertainty support. There is no universal
sample count that guarantees a valid interval.

To reuse exact folds, pass `--folds /previous/run/folds.csv`. Missing, duplicate or extra
blocks are rejected. Folds are assigned before heading-quality exclusions, and every fold
must retain eligible transitions. Do not rebuild folds from a selectively filtered set of
favourable observations. The configuration and original data must also be preserved.

## Model definitions

All fitted models predict the target interval's heading using the focal and neighbour
headings from the preceding interval, and positions at the predictor timestamp.
There are no periodic boundaries in observed-coordinate analysis.

| Label | Specification |
|---|---|
| persistence | Keep the last heading |
| constant_turn | Repeat the last angular turn; retain heading when prior history is unavailable |
| M0 | Common response, uniform radius-neighbour weights |
| M1 | Individual response, uniform radius-neighbour weights |
| distance | Common response, weights exp(-distance/radius) within the same radius |
| M2 | Common response, independently supplied directed social weights |
| M3 | Individual response, independently supplied directed social weights |
| shuffle_SEED | Individual response, relabelled directed social network |

The vector-blending rule and cancellation fallback use the existing tested implementation.
No neighbours, or zero total social weight, produce a retain-self prediction. These cases
are kept in the common evaluation set, rather than dropping observations selectively for
one model. The target timestamp in exported predictions is the target interval endpoint.

Fitting uses the existing 1,001-point loss profile, refinement of candidate minima and
explicit endpoint checks. This improves on a coarse interface grid but is not a proof of
finding every conceivable extremely narrow optimum. Flat loss produces a labelled
persistence fallback rather than an interpretable parameter estimate. Individual fits
with insufficient training observations use a labelled common-training fallback.

M2/M3 require a CSV with `group_id,focal_id,neighbour_id,weight`, covering exactly all
non-self ordered pairs in every group, with explicit zero weights. The focal receives
information from the neighbour. Set `ties_independent: true` only when social weights were
obtained independently of all analysed movement sessions. This assertion cannot be checked
by the software. Training-derived ties require an additional fold-specific estimator and
are not accepted as one supposedly independent global matrix.

Network controls relabel complete matrices with fixed seeds, preserving their structure
and weight distribution. Relabelling can have no effect for symmetric/uniform networks.
A few shuffled controls are not a permutation test or a calibrated significance level.
The distance-decay control remains an alignment kernel; constant-turn provides a
non-social alternative. Other biologically justified movement kernels may still be needed.

Outgoing influence is fixed at one. Jointly estimating free dyadic weights and outgoing
influence would retain the structural non-identifiability demonstrated elsewhere in the
repository. More controls do not remove that mathematical equivalence.

## Uncertainty and sensitivity

Scores use exactly matched observation keys and observed headings across models. Errors
are shortest circular differences. Within each declared uncertainty unit, the score is
mean absolute error. Units are weighted equally for comparisons. Bootstrap intervals
resample complete paired units, conditional on the fitted cross-validation predictions.
They do not refit training models, remove cross-validation dependence, or correct multiple
comparisons. Do not report them as full parameter uncertainty or automatic significance.

Predeclare a radius sensitivity set:

```bash
python src/run_analysis.py data.csv --config config.json --ties ties.csv \
  --folds previous/folds.csv --sensitivity-radii 5 10 20 --output new-run
```

All scenarios retain the same eligible target observations and frozen splits. Selecting
the best scenario using these held-out scores would leak test information. Hyperparameter
selection requires a separate inner validation design, which this command does not perform.

## Export and presentation

A fresh output directory contains:

- `audit.json`, `config.json`, `folds.csv`: decisions and exclusions;
- `features.csv`, `predictions.csv`, `parameters.csv`: numerical provenance and fit flags;
- `movement.csv`, `scores.csv`, `comparisons.csv`: results in metres, seconds and radians;
- SVG, PDF and PNG figures, with score figures labelled in degrees;
- `report.md` and `analysis_bundle.json`: generic report and browser-viewer handoff;
- `manifest.json`: original-input, source and output SHA-256 hashes plus software versions.

Output publication is staged and atomic. Existing results are never silently overwritten.
Sensitive positions remain in local input files and any exports you choose to retain.
Do not commit empirical trajectories or restricted relationship matrices to a public repo.

For a conference demonstration, run the synthetic generator and show the resulting audit,
frozen folds, matched models, controls and uncertainty. State that the generator uses the
same model family: favourable synthetic results are expected software checks, not newly
discovered animal behaviour. Actual measured data, design justification, external validation
and full corrected simulation experiments are still required for empirical claims.
