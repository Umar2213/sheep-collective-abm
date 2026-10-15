# Pre-declared analysis protocol: public Merino sheep tracking data

Written 2026-10-09 before any model was fitted to these data. Only descriptive
checks (row counts, trial durations, 1-second displacement quantiles during drives)
were inspected before writing it. Any later change must be recorded below as a
versioned deviation.

## Source

- Jadhav V, Pasqua R, Zanon C, Roy M, Tredan G, Bon R, Guttal V, Theraulaz G (2024).
  Collective responses of flocking sheep (Ovis aries) to a herding dog (border collie).
  Communications Biology 7, 1543. doi:10.1038/s42003-024-07245-8
- Data and code: github.com/tee-lab/collective-responses-of-flocking-sheep-to-herding-dog
  (Zenodo archive doi:10.5281/zenodo.13982895, licence CC BY 4.0 on Zenodo; GPL-3.0 in the
  GitHub repository). File `main_text/sheepR.dat`. Commit and SHA-256 recorded by
  `prepare_sheep_data.py` in `provenance.json`.
- Content: 14 Merino ewes, one border collie (ID 15) and one handler (ID 16) tracked with
  ultra-wide-band tags in a pasture (80 m x 50 m in the published article); columns trial, ID, time (s), x (m), y (m),
  sixth column unused. Samples every 0.1 s in the published file. The article reports
  2 Hz localisation with typical error below 30 cm.

## Inclusion

1. Sheep IDs 1 to 14 only. The dog and handler are excluded from the movement table.
   Every model therefore ignores the dog equally; this is a stated limitation.
2. Analysed periods are the published active "drive" phases in `drivs_dat.m`, chosen by
   the original authors, not by us. Eight trials contain drives.
3. The trial that has no published drive (event 7 = file trial 8) is never analysed. It is
   reserved entirely for estimating social ties, so ties are independent of every
   analysed session.
4. Decimate to 1-second spacing by keeping samples whose time is a whole second. No
   interpolation, smoothing or resampling beyond this subsampling.

## Identifiers and time

- `group_id` = `flock1` (one flock).
- `session_id` = `trialNN` using the original trial number in `sheepR.dat`.
- `bout_id` = `trialNN_driveK`, one bout per published drive.
- `individual_id` = `S01` to `S14`.
- `timestamp`: the file gives seconds since each trial began, with no calendar date.
  Times are written on an arbitrary reference date, 2000-01-01T00:00:00+00:00, plus
  NN hours for trial NN, plus the within-trial seconds. Only time differences are used.
  The reference date is not the real recording date.

## Independent social ties (for M2, M3 and shuffle controls)

Directed k-nearest-neighbour frequency from the reserved trial: at every whole second of
trial 8, for each focal sheep i, find its k = 3 nearest other sheep. The weight A_ij is
the fraction of seconds in which j was one of i's three nearest neighbours. All 182
directed pairs are written, zeros included. These are spatial association ties from an
independent period, not affiliative relationships measured by behavioural observation.

## Configuration (website and command line)

data_kind observational; coordinate_mode metric; crs local_metres; min_speed 0.3 m/s
(1-s displacement comparable to the reported typical tag error); max_speed 8 m/s;
max_gap 1.5 s; sampling_interval_seconds 1.0; radius 5 m; n_folds 8 with
split_columns and uncertainty_columns [group_id, session_id] (leave-one-trial-out;
8 uncertainty units); min_individual_train 10; n_bootstrap 2000; shuffle_seeds
[11, 29, 47, 71, 97]; seed 42; ties_independent true; common_shuffle_controls true.
No accuracy column is supplied (unquantified-error analysis).

## Questions and contrasts

Prediction question: one-step (1 s) heading of familiar sheep in an unseen trial.
Primary contrasts, as produced by the pipeline: M1 vs M0; M2 vs M0 and vs distance;
M3 vs M1 and vs M2; M3 vs network-shuffled controls; M2 vs common-response shuffles;
all models vs persistence and constant-turn.

## Pre-declared sensitivity analyses (command line only; never used to choose settings)

- Interaction radius 3, 5 and 10 m on the same frozen folds.
- Sampling interval 0.5 s (native tag rate) and 2 s, as separate analyses.

## Interpretation rules

- Trials share the same 14 animals, so they are not independent groups. Intervals are
  conditional paired block-bootstrap intervals over 8 trials and are exploratory.
- A prediction gain is not a causal effect. Responsiveness describes a 1-s discrete step
  under herding pressure, not a fixed trait.
- A null or negative result is reported as such.

## Deviations and additions (recorded after the primary run)

1. Settings unchanged. `config.json` is now written as compact JSON with whole numbers as
   integers (for example `radius: 5` instead of `5.0`), exactly as the website stores an
   uploaded configuration. This changes no setting and no scientific output; it makes a
   website run and a command-line run byte-identical (verified: 19 of 19 output files).
2. Exploratory analyses added after seeing the primary results, and labelled as such:
   (a) stability of per-sheep responsiveness across disjoint halves of the trials
   (`exploratory/split_half.py`); (b) exact sign-flip tests and t-intervals over the 8
   trials for key contrasts (`exploratory/signflip.py`).
