# Novelty matrix

## Purpose

This document defines what would and would not constitute a defensible contribution for
this repository. It is a working literature matrix, not a claim of priority. The project
should only make a novelty claim after the relevant literature has been expanded and the
proposed mechanism has been tested against empirical sheep trajectories.

## What is already established

| Area | Representative work | What it means for this project |
|---|---|---|
| Individual heterogeneity in collective behaviour | Jolles, King & Killen, 2020, Trends in Ecology & Evolution, DOI: 10.1016/j.tree.2019.11.001 | The general statement that individual differences matter for collective behaviour is established and cannot be the novelty claim. |
| Heterogeneous interaction structure in flocking models | Miguel, Parley & Pastor-Satorras, 2018, Physical Review Letters, DOI: 10.1103/PhysRevLett.120.068303 | Heterogeneous social interactions in Vicsek-type systems are established prior art. |
| Individual-specific interaction rules | Schaerf, Herbert-Read & Ward, 2021, Journal of the Royal Society Interface, DOI: 10.1098/rsif.2020.0925 | Statistical differences among individuals' movement interaction rules have already been tested, so individual-specific response rules alone are not a sufficient novelty claim. |
| Dyadic movement influence and hierarchy inference | Milner et al., 2021, Methods in Ecology and Evolution, DOI: 10.1111/2041-210X.13468 | Directed dyadic influence structures can already be inferred from interacting-animal movement data. |
| Time-varying social influence | Sridhar et al., 2023, Philosophical Transactions B, DOI: 10.1098/rstb.2022.0062 | Social influence can depend on the timescale of analysis, so any fitted influence parameter should not automatically be treated as a timeless trait. |
| Sheep decision rules during collective departures | Pillot et al., 2011, PLOS ONE, DOI: 10.1371/journal.pone.0014487 | Sheep stimulus-response rules and their scaling with group size have already been quantified experimentally, so a sheep-specific individual response rule is not novel by itself. |
| Data-driven individual-level interaction modelling in small sheep flocks | Welch, Alzubaidi & Schaerf, 2023, MODSIM2023, "Modelling collective states and individual-level interactions in small sheep flocks" | High-resolution sheep trajectories have already been used to infer pairwise movement interactions and construct an agent-based model, so combining sheep tracking with an ABM is not itself a novelty claim. |
| Sheep collective motion with alternating leadership | Gómez-Nava, Bon & Peruani, 2022, Nature Physics, DOI: 10.1038/s41567-022-01769-8 | Sheep can show intermittent motion with temporal leaders and strongly directed interaction structure, so leadership itself is not a new claim. |
| High-resolution sheep tracking for leadership and social networks | Maroto-Molina et al., 2021, Sensors, PMID: 33573163 | RTK/GNSS data can quantify sheep movement leaders and association networks. |
| Directional information flow in sheep under herding pressure | Communications Biology, 2024, DOI: 10.1038/s42003-024-07245-8 | Position-dependent directional influence and data-driven ABMs have already been applied to sheep. |
| Standardized trajectory-level collective-motion analysis | Papadopoulou, Garnier & King, 2025, Methods in Ecology and Evolution, DOI: 10.1111/2041-210X.14460 | Modern software already provides standardized event-level and trajectory-level collective-motion metrics, including a sheep case study. Empirical validation should use or benchmark against established trajectory metrics rather than inventing ad hoc summaries without justification. |
| Collective motion without an explicit alignment rule | Allocentric flocking, Nature Communications, 2025, DOI: 10.1038/s41467-025-64676-5 | Explicit heading alignment is not the only plausible mechanism. Empirical work should compare the proposed interaction rule against simpler or alternative behavioural kernels. |

## Candidate contribution that remains worth testing

The strongest defensible direction is not "heterogeneity affects flocking", "individuals
use different interaction rules", "some sheep influence others", "we inferred a sheep
interaction rule", or "we built a sheep ABM". All of those broad ideas have substantial
prior art.

A narrower candidate is a sheep-specific, preregistered-style model-comparison framework
that asks whether distinct biological information sources add non-redundant predictive
value under strict identifiability and held-out validation:

1. focal responsiveness r_i, how strongly individual i changes its own direction in
   response to neighbours;
2. directed dyadic relationship A_ij, how strongly focal i uses information from j,
   characterized independently of the test trajectory wherever possible;
3. outgoing influence q_j, how strongly neighbour j contributes to others' updates,
   included only if separate identifiability can be demonstrated.

The potential contribution would come from the combination of mechanism separation,
parameter-recovery analysis, independent social-tie characterization, matched
computational controls, alternative behavioural kernels, and out-of-sample sheep
prediction. Merely naming or fitting these components is not enough.

## Required nested comparisons

| Model | Responsiveness | Dyadic ties | Outgoing influence | Purpose |
|---|---|---|---|---|
| M0 | common | uniform | fixed 1 | minimal local-alignment baseline |
| M1 | individual | uniform | fixed 1 | isolates heterogeneous responsiveness |
| M2 | common | measured/estimated | fixed 1 | isolates dyadic social structure |
| M3 | individual | measured/estimated | fixed 1 | tests their joint predictive value |
| M4 | individual | measured/estimated | estimated | only if parameter recovery supports identifiability |

M4 must not be used merely because it is more complex. Since q_j and A_ij enter the
current neighbour weighting multiplicatively, they can be confounded. Free q_j should be
used only when independent constraints or recovery experiments demonstrate that the data
can distinguish it from A_ij.

A later empirical comparison should also include at least one plausible movement kernel
that does not assume explicit velocity alignment when the data can distinguish the
mechanisms. This guards against attributing predictive improvement to a flexible but
biologically incorrect interaction rule.

## Evidence required before claiming a contribution

A strong paper should demonstrate all of the following:

- exact-radius and update-rule controls do not qualitatively overturn the result;
- simulation estimates are stable across longer windows and independent initial states;
- the main heterogeneity effect is not an artifact of choosing one trait-distribution shape;
- parameter-recovery experiments show which latent quantities can actually be identified;
- model comparisons use complete held-out sheep groups, days or movement bouts rather
  than randomly split adjacent frames;
- measured social relationships are estimated independently of the test trajectory to
  avoid circularity;
- predictive gains are reported against homogeneous, proximity-only and shuffled-network
  baselines;
- at least one plausible alternative movement kernel is tested where data permit;
- time-varying influence is considered rather than assuming every inferred influence score
  is a permanent individual characteristic;
- established trajectory-level metrics are used or explicitly benchmarked where relevant;
- uncertainty is calculated at the independent animal-group/day/bout level;
- biological interpretation is separated from purely computational effects.

## Claims to avoid

Until the above evidence exists, do not claim that the repository has discovered a new
phase transition, a universal critical exponent, a novel sheep leadership mechanism, a
new general theory of individual heterogeneity, the first data-driven sheep ABM, the first
individual-level sheep interaction model, or that a fixed-mean Beta dispersion sweep is
itself biologically novel.

## Working gap statement

A potentially publishable gap is whether, in sheep, independently characterized dyadic
relationships and individual responsiveness provide non-redundant, identifiable and
out-of-sample predictive information when evaluated together against simpler baselines,
algorithmic controls, distribution-shape controls, and alternative movement kernels.

This is deliberately phrased as an open question rather than a claim that no prior study
has addressed it. The gap must be re-evaluated before manuscript submission with a focused
systematic search, including forward and backward citation tracing from the closest
sheep-specific interaction-modelling studies.
