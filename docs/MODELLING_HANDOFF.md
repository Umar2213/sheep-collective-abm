# WP7 modelling handoff

Transfer via an approved private channel. Public GitHub contains software, templates and
synthetic demonstrations, not restricted empirical outputs.

| Product | Interpretation and required metadata |
|---|---|
| `prepared.csv` | Parsed/projected observations plus quality flags, speed and heading; unusable rows retained, not silently repaired |
| `audit.json` | Structural checks, exclusions, warnings and counts |
| `individual_bouts.csv` | Per-animal/per-bout descriptive duration, usable path length and duration-weighted speed; not repeatability estimates |
| `movement.csv` | Available-animal alignment and spatial spread; dependent on observation coverage |
| `config.json`, `folds.csv` | Frozen settings and exact block assignments |
| `features.csv`, `predictions.csv` | Auditable predictor/target times and matched one-step predictions |
| `parameters.csv` | Training-fold response fits, common/persistence fallback and numerical ambiguity flags |
| `scores.csv`, `comparisons.csv` | Radian angular errors and paired uncertainty conditional on the fitted predictions |
| `manifest.json` | Input/output/source hashes, Git commit, dirty-tree indicator, software versions and units |
| `report.md`, figures, `analysis_bundle.json` | Presentation outputs; still subject to privacy and scientific review |

Coordinates and path length are metres, duration is seconds, speed is metres/second and
angles are radians. Score figures use degrees. The CRS is in `config.json`; for `local_metres`,
retain the private definition, origin and projection/translation method with the inventory.
A speed average uses total usable distance divided by total usable interval duration, so
irregular intervals do not each receive equal weight. It describes observed usable coverage,
not the animal's complete time budget. No path length is inferred across excluded gaps.
When accuracy was not supplied, `prepared.csv` retains missing `accuracy_m` values and
the audit records this omission. Do not replace these values with zero measurement error.

The independently observed tie matrix, observation effort, collection window, direction
convention, uncertainty and animal crosswalk must accompany an empirical handoff separately.
These cannot be reconstructed from predictions. The current pipeline does not estimate tie
uncertainty or validate behavioural states.

The audit now records the common prediction interval, eligible-transition coverage counts,
and prediction-weighted response and neighbour fallback counts. The same diagnostics appear
in the report and browser bundle. Features retain explicit blocking metadata and neighbour
availability counts; predictions retain interval, response status and neighbour fallback
reason. These counts are not independent sample sizes. Bout rosters include only recorded
animals and cannot establish complete flock coverage. Whole-group holdout uses common
responses for previously unseen group/animal pairs and does not test stable individual traits.

Verify a completed output folder:

```bash
python src/verify_analysis.py /approved/private/analysis-run
```

The verifier rejects altered, missing, extra and symbolic-link outputs. A successful check
means consistency with the supplied manifest, not scientific validity or authentication.
Keep a trusted manifest copy and original-input checksums in the approved study record.
Reproduction requires the original inputs and recorded source/dependencies. Source hashes
capture local edits; a dirty Git commit must not be described as the exact executed source.

Before biological use, include the data version, analysis version, study design, uncertainty
unit rationale, sample coverage, exclusions, sensor error, parameter-recovery evidence,
validation population, limitations and reviewer decision. Successful synthetic tests and
negative empirical findings must remain clearly distinguished.

