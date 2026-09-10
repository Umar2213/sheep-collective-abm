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
| Sheep collective motion with alternating leadership | Gómez-Nava, Bon & Peruani, 2022, Nature Physics, DOI: 10.1038/s41567-022-01769-8 | Sheep can show intermittent motion with temporal leaders and strongly directed interaction structure, so leadership itself is not a new claim. |
| High-resolution sheep tracking for leadership and social networks | Maroto-Molina et al., 2021, Sensors, PMID: 33573163 | RTK/GNSS data can quantify sheep movement leaders and association networks. |
| Directional information flow in sheep under herding pressure | Communications Biology, 2024, DOI: 10.1038/s42003-024-07245-8 | Position-dependent directional influence and data-driven ABMs have already been applied to sheep. |
| Sheep movement initiation and following | Earlier experimental work on collective departures and spontaneous movements | Social context, recruitment and leader/follower behaviour have already been quantified experimentally. |

## Candidate contribution that remains worth testing

The strongest defensible direction is not "heterogeneity affects flocking". A stronger
candidate is a mechanistic and predictive decomposition of three distinct interaction
components in the same model and data-analysis framework:

1. focal responsiveness r_i, how strongly individual i changes its own direction in
   response to others;
2. outgoing influence q_j, how strongly neighbour j contributes to others' updates;
3. directed dyadic relationship A_ij, how strongly focal i uses information from j.

The central empirical question is whether estimating these components separately improves
held-out prediction of sheep movement compared with simpler nested baselines, and whether
the components are identifiable from the available data.

## Required nested comparisons

| Model | Responsiveness | Dyadic ties | Outgoing influence | Purpose |
|---|---|---|---|---|
| M0 | common | uniform | fixed 1 | minimal local-alignment baseline |
| M1 | individual | uniform | fixed 1 | isolates heterogeneous responsiveness |
| M2 | common | measured/estimated | fixed 1 | isolates dyadic social structure |
| M3 | individual | measured/estimated | fixed 1 | tests their joint predictive value |
| M4 | individual | measured/estimated | estimated | only if parameter recovery supports identifiability |

M4 must not be used merely because it is more complex. If q_j and A_ij cannot be
recovered separately, q_j should remain fixed.

## Evidence required before claiming a contribution

A strong paper should demonstrate all of the following:

- exact-radius and update-rule controls do not qualitatively overturn the result;
- simulation estimates are stable across longer windows and independent initial states;
- parameter-recovery experiments show which latent quantities can actually be identified;
- model comparisons use complete held-out sheep groups, days or movement bouts rather
  than randomly split adjacent frames;
- measured social relationships are estimated independently of the test trajectory to
  avoid circularity;
- predictive gains are reported against homogeneous, proximity-only and shuffled-network
  baselines;
- uncertainty is calculated at the independent animal-group/day/bout level;
- biological interpretation is separated from purely computational effects.

## Claims to avoid

Until the above evidence exists, do not claim that the repository has discovered a new
phase transition, a universal critical exponent, a novel sheep leadership mechanism, or
that a fixed-mean Beta dispersion sweep is itself biologically novel.

## Working gap statement

A potentially publishable gap is the lack of a validated framework that explicitly
separates individual responsiveness, partner-specific social weighting and outgoing
influence, then tests their identifiable and out-of-sample predictive contributions in
sheep movement data under matched computational controls.

This remains a hypothesis about the literature gap. It must be re-evaluated before
manuscript submission with a focused systematic search.
