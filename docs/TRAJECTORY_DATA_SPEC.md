# Sheep trajectory data specification

## Purpose

This specification defines the minimum structure required for empirical validation of the
collective-motion models. It is intentionally strict because trajectory data are easy to
leak across training and test sets when adjacent time points from the same movement bout
are split independently.

The repository does not include empirical sheep trajectories. This document defines how
future data should be prepared without committing identifiable farm locations or other
restricted information to the public repository.

## Required columns

| Column | Meaning |
|---|---|
| `group_id` | Stable identifier for the social group or flock |
| `bout_id` | Stable identifier for one continuous movement bout or observation session |
| `individual_id` | Anonymized animal identifier, stable within the study |
| `timestamp` | Observation time, preferably ISO-8601 with timezone information |
| `x` | Planar x coordinate in a documented metric coordinate system |
| `y` | Planar y coordinate in the same coordinate system as `x` |

Coordinates should be expressed in metres in a local projected coordinate reference
system when metric distances are used. Raw latitude and longitude should not be treated as
Cartesian metres.

## Recommended optional columns

Useful fields include `date`, `sampling_quality`, `fix_quality`, `speed`, `heading`,
`behavioural_state`, `treatment`, `environment_id`, `pasture_id`, `sex`, `age_class`, and
other study covariates that are justified by the experimental design. Sensitive or
identifying metadata should remain outside the public repository unless their release is
explicitly permitted.

## Required integrity checks

Before fitting any model, the data pipeline should verify:

1. the table is nonempty, all required columns exist, and identifiers are nonmissing and nonblank;
2. timestamps are parseable and coordinates are finite;
3. each `(group_id, bout_id, individual_id, timestamp)` key is unique;
4. timestamps are strictly increasing within each individual track after sorting;
5. each analysed bout contains at least two individuals;
6. sampling intervals and track lengths are reported rather than silently assumed;
7. coordinate units and the coordinate reference system are documented;
8. missing observations are reported explicitly;
9. interpolation, smoothing and resampling decisions are recorded and performed only after
   the raw-data audit;
10. any social relationship used as a predictor is estimated without using the held-out
    test trajectory that it is later asked to predict.

The repository utility `src/trajectory_validation.py` performs the structural checks that
can be evaluated from a tabular trajectory file. It does not silently interpolate or
repair tracks.

## Train/test splitting

Randomly splitting adjacent frames is not an acceptable primary validation strategy,
because observations from the same animal and movement event are strongly dependent.

The primary evaluation unit should be a complete biological block, for example a group,
day, recording session, or movement bout. The precise blocking level must be chosen before
model comparison and should match the independence structure of the experiment. The helper
`assign_grouped_folds` creates deterministic folds from complete blocks and verifies that a
block never appears in more than one fold. It balances the number of blocks, not frames,
across folds after deterministic hash ordering. At least `n_folds` blocks are required,
and every fold is populated. Assignments are invariant to row order but can change when
the set of blocks changes. Save and reuse a frozen fold table for a fixed study dataset.
This allocation replaces the earlier hash-modulo rule, so regenerate older folds only as
an explicitly versioned analysis change.

At minimum, report prediction performance for every held-out block and the distribution of
performance across independent blocks. Model selection and hyperparameter tuning must use
training data only.

## Social relationships and circularity

If dyadic relationships are used in M2 or M3, they should preferably be estimated from an
independent observation period or from training-period data only. Constructing a network
from the test movement bout and then using that network to predict the same bout creates
circular evidence.

Shuffled-network and proximity-only baselines should be included. If outgoing influence is
estimated separately from directed dyadic ties, parameter-recovery experiments or external
constraints must demonstrate that the two components are identifiable.

## Privacy and data governance

Use anonymized animal identifiers. Do not commit precise farm coordinates, owner names,
access credentials, or restricted raw data to this public repository. Keep the raw-data
license, ethics/animal-use approval information, collection protocol and consent or access
conditions with the study records. Only publish data or derived coordinates when the
relevant permissions allow it.

## Minimum empirical deliverable

A defensible empirical validation package should contain:

- a data dictionary and provenance record;
- an immutable raw-data checksum manifest stored in the permitted data environment;
- a reproducible preprocessing script;
- a trajectory integrity report;
- predefined grouped train/test folds;
- nested M0 to M3 model comparisons, with M4 only if identifiable;
- proximity-only, shuffled-network and alternative-movement-kernel baselines;
- block-level prediction metrics and uncertainty;
- a clear separation between predictive evidence and biological interpretation.

## Scoring held-out predictions

Supply one row per model and observation with the fields below plus any extra
columns used to define a coarser biological block:

| Fields | Requirement |
|---|---|
| `group_id`, `bout_id`, `individual_id`, `timestamp` | Same observation keys for every model |
| `model` | Model name, such as M0, M1, M2, M3, proximity or shuffled |
| `observed_heading`, `predicted_heading` | Finite angles in radians |

The table contains seven columns in total. Coordinates are not required for scoring.
Generate predictions with training-only parameters, preprocessing and social relationships.
The scorer cannot infer whether the upstream fitting procedure leaked test information.

```bash
python src/prediction_evaluation.py /path/to/held_out_predictions.csv \
  --output /path/to/block_scores.csv --block-columns group_id bout_id
```

For paired uncertainty, from Python with `src` on the import path:

```python
from prediction_evaluation import score_predictions, compare_models
scores = score_predictions(predictions, block_columns=("group_id",))
comparison = compare_models(scores, "M0", "M3", block_columns=("group_id",), seed=42)
```

The comparison averages the MAE difference equally across complete blocks and bootstraps
paired blocks, preserving model pairing. Its interval requires reasonably independent
blocks; choosing individual bouts does not make bouts from the same flock independent.
Choose the blocking level from the study design, before inspecting model differences.
At least two matched blocks are required, but very few blocks yield weak uncertainty
estimates. These utilities supply evaluation infrastructure, not empirical validation.
