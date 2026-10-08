# Simulation figures

The PNG and PDF files in this directory illustrate historical simulation analyses.
They are not evidence from measured sheep.

| Figure stem | Purpose |
|---|---|
| `fig_main_production` | Production-sweep summaries |
| `fig_main_v2` | Main historical production figure |
| `fig_fss` | Descriptive finite-size comparisons |
| `fig_snapshots` | Simulated movement snapshots |

Interpret these figures together with [the repository audit](../docs/AUDIT.md).
Historical approximate-search results must not be presented as corrected exact-radius
results. Directional alignment measures heading order, not spatial cohesion or causal
leadership. Finite-size plots do not establish a phase transition.

The scripts `src/analyze_production.py`, `src/make_main_figure.py`,
`src/analyze_fss.py` and `src/make_snapshots.py` regenerate the stored-data figures.
New trajectory-analysis runs export their figures alongside their own audit and manifest,
as described in [the analysis workflow](../docs/ANALYSIS_WORKFLOW.md).
