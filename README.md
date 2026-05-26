# Sheep Collective Behaviour — Agent-Based Model

**Author: Umar**

## Overview
Agent-based model investigating how personality variance within a sheep
flock affects collective behaviour. Central question: if mean personality
is held constant but variance increases, does flock cohesion change?
Answer: yes — but only past a critical threshold.

## Key Findings
1. Flock cohesion stays high (φ ≈ 0.97) when diversity σ ≤ 0.30.
2. Cohesion collapses nonlinearly between σ = 0.30 and σ = 0.35.
3. Higher environmental noise lowers baseline cohesion and shifts
   the collapse threshold to lower diversity values.

## Model
- Framework: Julia 1.10.5, Agents.jl v7.0.2
- N=200 sheep, 20x20 periodic box, speed=0.03, radius=1.0
- Personality: social weight per agent, Beta distribution
- Mean personality fixed at 0.7; variance varied systematically
- Order parameter φ: 1=perfect flock, 0=disorder
- 15-20 independent seeds per condition

## Structure
src/      Julia + Python scripts
results/  CSV outputs
figures/  Publication figures
docs/     Manuscript

## How to Run
julia --project=. src/vicsek_baseline.jl
julia --project=. src/heterogeneous_model_v2.jl
python3 src/figure2_cohesion.py

## Dependencies
Julia: Agents, Distributions, StatsBase, DataFrames, CSV, JLD2, ProgressMeter, ThreadsX
Python: pandas, matplotlib, scipy
