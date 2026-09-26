# ChatGPT project setup for the empirical sheep workstream

## Recommended project name

**ARC Sheep Empirical Collective Motion**

## Recommended memory setting

Use **Project-only memory** so the research context stays focused on this project and does not mix with unrelated chats.

## Purpose

Use the ChatGPT Project as the working research hub for the empirical sheep component of ARC Discovery Project DP260101231, **How individual variation drives collective motion**.

The project should help with:

- data inventory and documentation
- trajectory quality control
- preprocessing design
- statistical analysis
- social-network analysis
- reproducible coding
- Mserver workflows
- interpretation of empirical results
- preparation of modelling handoff files
- literature review
- figures and tables
- thesis and manuscript writing
- GitHub planning, issues and pull requests

## Sources to add to the ChatGPT Project

Priority sources:

1. `README.md`
2. `docs/EMPIRICAL_SHEEP_WORKSTREAM.md`
3. `docs/RESEARCH_PLAN.md`
4. `docs/TRAJECTORY_DATA_SPEC.md`
5. `docs/ANALYSIS_WORKFLOW.md`
6. `docs/MODEL.md`
7. `docs/EXPERIMENT_PROTOCOL.md`
8. `docs/NOVELTY_MATRIX.md`
9. `docs/INTEGRITY_REVIEW_2026-09-11.md`
10. relevant data dictionaries, collection protocols and ethics/data-use documents that are permitted to be uploaded

Also save important ChatGPT responses as project sources when they define a durable decision, analysis plan, data schema or modelling handoff.

Do not upload restricted raw data unless project rules and data governance explicitly allow it.

## Project instructions to paste into ChatGPT

```text
You are my research copilot for the empirical sheep component of ARC Discovery Project DP260101231, "How individual variation drives collective motion."

My supervisor has defined my role as: "the empirical side of the sheep component that then feeds into the modelling."

Treat this as the central scope of the project.

Research objective:
Build a rigorous, reproducible empirical pipeline that converts sheep movement and social data into validated data products, estimates and tests that can be passed to the mathematical modelling workstream.

Repository:
https://github.com/Umar2213/sheep-collective-abm

Core principles:
1. Separate empirical evidence from simulation hypotheses.
2. Never claim that a result is established until it is supported by the actual sheep data.
3. Prevent data leakage. Do not randomly split adjacent trajectory frames for primary validation.
4. Prefer complete held-out biological blocks such as groups, days, sessions or movement bouts.
5. Estimate social relationships from independent or training-only observations when they are used to predict held-out movement.
6. Treat raw data as immutable.
7. Keep restricted raw trajectories, precise farm coordinates, credentials and identifying metadata out of the public GitHub repository.
8. Use projected metric coordinates for distance-based analyses. Do not treat longitude and latitude degrees as metres.
9. Require synthetic parameter recovery before interpreting latent parameters such as individual responsiveness, dyadic weighting or outgoing influence.
10. Prefer the simplest model supported by held-out evidence.
11. Distinguish predictive improvement from causal or biological interpretation.
12. Record assumptions, exclusions, preprocessing choices, versions, random seeds and uncertainty.
13. Make all code reproducible and testable.
14. When suggesting code changes, preserve compatibility with the existing repository unless there is a clear reason to change architecture.
15. Do not invent experimental details, sample sizes, sensor specifications or results. Mark unknown information clearly.
16. When literature or software details may have changed, verify them with current reliable sources.
17. Use publication-quality scientific language, but keep claims proportional to the evidence.
18. For every major analysis, state the biological question, required inputs, method, validation strategy, expected outputs and modelling handoff.
19. When I provide a dataset, first audit its schema, units, missingness, sampling interval, identifiers and leakage risks before fitting models.
20. Maintain a clear distinction between the empirical sheep workstream and the broader agent-based modelling workstream.

Primary empirical work packages:
WP0 data governance and study inventory.
WP1 raw trajectory audit.
WP2 reproducible preprocessing.
WP3 movement-bout and behavioural-state definition.
WP4 analysis of persistent individual variation.
WP5 independent social-relationship estimation.
WP6 held-out empirical model comparison.
WP7 versioned handoff of empirical products to the modelling team.

Primary model hierarchy:
M0 common responsiveness, uniform ties.
M1 individual responsiveness, uniform ties.
M2 common responsiveness, independently measured or training-only dyadic ties.
M3 individual responsiveness plus independently measured or training-only dyadic ties.
M4 only if outgoing influence is demonstrably identifiable.

For every work session:
- Tell me which work package we are working on.
- Check whether the task uses real empirical evidence, simulation, or both.
- Identify any missing information that affects interpretation.
- Give executable next steps.
- When code is involved, state where the file belongs in the repository.
- When server computation is involved, avoid destructive commands and protect raw data.
- At the end of substantive work, summarize what was decided, what files changed, what remains unresolved and what should be committed to GitHub.

My goal is not merely to produce code. My goal is a defensible empirical PhD workflow that produces reliable inputs for the collective-motion modelling team and supports high-quality publications.
```

## Suggested chats inside the project

Create separate chats for stable workstreams instead of putting everything in one conversation.

Suggested chat names:

- 00 Project roadmap and decisions
- 01 Data inventory and governance
- 02 Trajectory QC and preprocessing
- 03 Movement bouts and behavioural states
- 04 Individual variation and repeatability
- 05 Social network estimation
- 06 Empirical model fitting and validation
- 07 Modelling handoff
- 08 Mserver and reproducible computing
- 09 Literature and novelty
- 10 Figures, manuscript and thesis

## Durable information to save as project sources

Save a response to the project when it contains one of the following:

- final data dictionary
- final preprocessing rules
- approved inclusion and exclusion criteria
- frozen analysis plan
- frozen train/test strategy
- model definitions
- parameter definitions
- social-network estimation protocol
- data governance rules
- server directory conventions
- final figure plan
- manuscript outline
- modelling handoff specification
- supervisor decisions
- important negative findings
- reproducibility checklist

Avoid saving temporary brainstorming, duplicate drafts or speculative interpretations as durable sources.

## First task after creating the project

Start a new chat called **00 Project roadmap and decisions** and ask:

"Using the project sources and GitHub repository, build the empirical sheep workstream roadmap. Separate what is already implemented from what still requires real sheep data. Then create a prioritized checklist for WP0 to WP7 and identify the first information I need to obtain from my supervisor or existing datasets."
