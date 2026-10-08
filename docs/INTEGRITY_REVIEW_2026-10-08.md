# Reproducibility and recovery review, 2026-10-08

## Scope

Review base: `1cf4e41` (`master` after #20, validation guards). This work complements #20
and does not change its code paths: interval pooling, session/day blocks, fold coverage,
neighbour coverage and fallback reporting. One interaction with #20 was found and fixed in
the new recovery study. Two findings for the fallback behaviour are recorded below.

## Changes

| Finding | Change and evidence |
|---|---|
| Rerunning an identical analysis changed the hashes of four figure files (PDF/SVG creation dates, random SVG IDs), so a rerun could never be checked against a published manifest | Figures saved without dates and with a fixed SVG hash salt; regression test publishes the same result twice more than a second apart and requires identical `outputs_sha256` |
| A metric-coordinate analysis failed after all computation when pyproj, needed only for GPS or named CRS, was not installed | Manifest records `null` for an absent package; test |
| Under pandas 3 an empty table raised `invalid literal for int()` instead of the intended "empty trajectory table" error | Identifier and timezone flags built as explicit booleans (also used by #20's block checks); object and string dtype tests; weekly non-blocking latest-dependency workflow |
| Input hashes were recorded but never checked | `verify_analysis.py --input NAME=PATH`; unverified recorded inputs are listed; tests |
| Network-label controls existed only with individual response, matched to M3 | Opt-in `common_shuffle_controls` adds `shuffle_common_SEED`, compared with M2; off by default |
| No recovery check under location error, missingness or sampling interval (roadmap WP4, item 8; "realistic recovery" in the #20 remaining work) | `src/recovery_study.py` through the production preprocessing; see [RECOVERY_STUDY.md](RECOVERY_STUDY.md) |
| After #20's common-interval guard, every dropout scenario in the recovery study was silently rejected | Scenarios declare their interval and a 1.5-interval gap limit; regression test requires dropout scenarios to be fitted |

## Findings for the fallback behaviour

1. **Flat-loss individual fits use persistence, not the common estimate.** When an
   individual's own training transitions give a flat loss (for example, no neighbours in
   training), `_fit` returns responsiveness 0 with status `flat_loss_persistence_fallback`.
   #20 now makes this visible in `prediction_status_counts`, but M1/M3 still predict pure
   persistence for that animal even where its test transitions have neighbours, whereas
   insufficient training data falls back to the common estimate. Reproduced with one
   uninformative animal: common estimate 0.487, individual estimate 0. The two "no
   individual information" cases should probably share the common fallback.
2. **Group-only splits make M1 identical to M0.** Fits are group-specific, so holding out
   whole groups leaves no training rows for any test individual. #20 adds an audit warning
   for this case. M1 versus M0 is nevertheless still reported as a bootstrap contrast with
   a zero difference and zero-width interval. Marking contrasts whose alternative is
   entirely fallback as not estimable would prevent that row being read as evidence.

## Verification

Local environment: Python 3.13.16, numpy 2.5.3, pandas 3.0.5, scipy 1.18.1,
matplotlib 3.11.2. The pinned 3.12 environment could not be installed because this
environment's network policy blocks the package index, and pyproj is unavailable, so the
GPS projection test cannot run here. All other tests pass: the 76 tests on `master` that
do not need pyproj and 26 new tests. The synthetic demonstration with social ties and
radius scenarios 5 and 10 runs end to end, verifies with input checks, and reproduces
identical output hashes on a second run. Hosted CI on the pinned environment is the
authoritative result.

The recovery study, figure determinism and pandas behaviour depend on package versions;
confirm them in CI. Julia source was not changed or run.
