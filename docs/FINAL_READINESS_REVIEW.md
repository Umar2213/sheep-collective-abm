# Empirical starting readiness, 2026-09-26

## Decision

Ready to begin empirical study preparation and data auditing (WP0 to WP3), subject to
approved data access. This is a tested research foundation, not a completed empirical
empirical analysis or a guarantee of error-free software. No animal dataset was supplied for
this review. The website should expose the tested analysis workflow and its limitations.

Review base: `bd7ddf4c1ae6e25749234d01463cc516dbcfd20a`. Its
[hosted Python and Julia checks passed](https://github.com/Umar2213/sheep-collective-abm/actions/runs/36223431705).
The attached project-source copies predate this base; the current repository takes
precedence. This review adds input-integrity fixes on a separate branch for pull-request
review. Check that pull request's status before adopting its changes.

## Repairs and verification

| Finding | Change |
|---|---|
| Standalone validation and scoring assumed UTC for naive timestamps | Require explicit timezones; audit missing timezones separately; reject numeric epochs without a documented adapter |
| Surrounding whitespace could silently change or merge identifiers | Reject it in trajectories, social ties and predictions; preserve original identifiers |
| Missing sensor accuracy was exported as zero | Preserve missing accuracy and the audit flag; retain an explicitly unquantified-error analysis |
| CSV readers could silently rename duplicate headers | Reject duplicate or blank headers in the integrated input reader and retain failed-audit diagnostics |
| Score output had a check/write race | Open score files exclusively so a newly created file cannot be overwritten |
| Research wording overemphasized optional outgoing influence and called every contrast nested | Restore the primary empirical question and explain that fixed-network comparisons need not be statistically nested |

Local verification used Python 3.12.14 and the direct dependency pins in `requirements.txt`:
63 Python tests passed; synthetic generation, standalone audit, full analysis with social
ties and radius scenarios 5 and 10, and checksum verification of 20 output files passed.
The historical-data audit passed for nine source tables. Its 323/1520 finite-size drift
warnings persist and do not become validated results through this review. Julia source
was not changed or rerun locally; use hosted CI for the pull request's combined check.
No literature-priority verification, full simulation campaign or live Mserver test is
claimed. The synthetic output manifest correctly records the reviewed working tree as dirty.

## What remains before empirical conclusions

| Work package | Current position | Required next evidence |
|---|---|---|
| WP0 | Governance guidance and private inventory template available | Actual owner, access, ethics, publication permissions, sensor and sampling metadata |
| WP1 | Structural auditing available | An approved raw export, immutable checksums, device adapter and quality definitions |
| WP2 | Projection and fixed filtering available | Study-specific CRS, error estimates, thresholds and justified synchronization; no invented interpolation |
| WP3 | Supplied bout boundaries respected | Biological session/bout definitions and validated states; these are not automatically inferred |
| WP4 | Descriptive summaries and training-fold response fitting available | Repeated observations, within/among-individual variance modelling, uncertainty and realistic parameter recovery |
| WP5 | Independent ties and network-label controls supported | Independent relationship observations, stability/effort/uncertainty analysis, or a tested estimator inside each training fold |
| WP6 | Matched M0 to M3 predictions and block uncertainty available | Predeclared validation population, justified blocks, final holdout, and nested tuning only if settings are selected |
| WP7 | Versioned numerical exports and checksum verification available | Approved empirical release, sensor/recovery evidence, limitations and scientific review |

Responsiveness is currently group-specific and describes the analysed discrete time step.
Do not interpret differences across sampling intervals as persistent animal traits without
a justified common interval or time-dependent response model. Supplied accuracy values also
require device-specific interpretation. Passing a schema check does not validate either.

## Before the app or website

Use `analysis_bundle.json` schema version 1 as an initial viewer interface. Preserve the
synthetic/observational label, exclusion audit, units, fallback warnings, uncertainty-unit
counts and conditional-interval limitations. Review every empirical export before upload;
the bundle is not automatically anonymous. A public demonstration should use synthetic data.
The interface must not silently retune settings using held-out scores.

There is no need to add M4, more simulation grids, a complex dashboard or automatic
behavioural classifiers just to start the empirical study. Prioritize an approved pilot dataset and its
study inventory. Use `MSERVER_SETUP.md` to validate the environment on the actual server;
the pasted login banner is not a current quota or security assessment.

Existing issues #2 and #8 remain scientific work, not completed software fixes. PR #11 is
an older, separate documentation proposal; reconcile its overlapping guidance before any
merge. Do not assume it is already part of the default branch.
