# Contributing

Keep the empirical sheep contribution central. Start with `docs/EMPIRICAL_ROADMAP.md`.
Use a branch and pull request for substantial changes. Preserve the existing Python empirical
pipeline and Julia simulation components unless an architectural change is justified.

Run `python -m unittest discover -s tests -v`, the synthetic demonstration, and
`python src/verify_analysis.py OUTPUT` before proposing analysis changes. Julia changes also
require the pinned Julia tests and all four smoke/shard integrations in CI. Add regression
tests for important defects. Record validation that was not run rather than calling it passed.

Never commit restricted trajectories, original coordinates, confidential metadata or
credentials. Review `git diff --cached` and untracked files. Preserve historical simulation
tables and their labels. Never overwrite raw data or silently revise frozen folds.
Document methods, exclusions, units, random seeds and scientific limits. Report negative
findings honestly. Repository readiness is not completed empirical validation.
