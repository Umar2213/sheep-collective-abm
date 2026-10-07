# Empirical readiness review, 2026-09-26

## Scope

Audit base: `793bc22dbfb0e774227277975af4652c2b5328fb`. This review covers the current
repository and the empirical research requirements supplied by the researcher. It does not
certify all possible inputs, completed empirical analyses, animal-study approvals or live Mserver
configuration. Existing architecture and historical scientific outputs are preserved.

## Changes

| Finding | Repair and evidence |
|---|---|
| Research plan prioritized simulation rather than empirical contribution | WP0 to WP7 roadmap, revised scope, private study inventory, governance, server setup and modelling-handoff guidance |
| String `"false"` could satisfy the social-independence flag | Require a boolean and test invalid types |
| Overlapping named bouts could reuse one animal fix in different folds | Reject repeated group/animal/time across bouts; regression test |
| Social-only hypothesis lacked explicit comparison | Add M2 versus M0 and distance, and M3 versus M0; contrast coverage test |
| Scoring CLI inferred and altered literal IDs | Read strings without automatic NA conversion; CLI test |
| Scoring CLI and simulation sweeps could replace existing outputs | Refuse existing score files and exclusively reserve fresh simulation directories before computation |
| Julia finite tie/influence products could overflow or underflow | Normalize positive products in log space, with extreme-scale invariance tests |
| No standalone failed-input structural report | Add immutable-input audit command with checksums and failure diagnostics |
| Handoff omitted flagged trajectories and individual bout summaries | Export prepared rows and duration-weighted descriptive summaries, tested on excluded gaps |
| Handoff hashes had no verification command | Add coverage/checksum verifier with tampering regression tests and CI integration |
| Environment provenance was incomplete | Record all direct package versions, units and dirty-tree state; stream file hashes; reject inputs changed during analysis |

## Validation record

Local Python 3.12 environment installs the exact direct dependencies from `requirements.txt`.
The 58-test Python suite passes. End-to-end synthetic analysis, sensitivity runs, standalone
audit and manifest verification are exercised separately. Nine historical source tables
pass the existing stored-data audit; the existing 323/1520 finite-size drift warnings remain.
Julia is not installed in the local editing environment. The pull request's GitHub Actions
runs pinned Julia tests plus the four actual smoke/shard/merge integrations. Its check status
is the authoritative hosted validation result; do not infer success from this document.

## Outstanding empirical gates

Dataset access, ethics/permissions, sensors, measurement error, sampling design and actual
animal metadata remain unknown. Validated bout/state definitions, hierarchical repeatability,
training-only social estimation, realistic recovery/coverage studies, nested model selection
and independent final validation remain study work. Full corrected simulation campaigns
have not been executed here. No novelty search or empirical biological finding is claimed.

Current individual response fits are group-specific, even if stable animal IDs occur across
groups. Current integrated splits support groups or group/bout, not arbitrary day/session
columns. Descriptive summaries do not separate within- and among-individual variance. Bootstrap
intervals condition on fitted cross-validation predictions. Additional independent biological
units, not additional adjacent frames, are needed when uncertainty support is weak.

No review can guarantee that a repository has no remaining mistakes. This record identifies
what was changed and what evidence supports readiness for the next empirical stage.
