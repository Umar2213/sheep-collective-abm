# Sheep Collective Behaviour — Agent-Based Model

**Author: Umar**

## Overview
An agent-based model investigating how individual personality variation
within a sheep flock affects collective behaviour. The central question:
if you hold mean personality constant but increase the variance of
personalities across individuals, does flock cohesion change?

The answer is yes — but only past a critical threshold.

## Key Findings
1. Robustness zone: Flock cohesion stays high (φ ≈ 0.97) when
   personality diversity σ ≤ 0.30, even with wide individual variation.
2. Critical threshold: Between σ = 0.30 and σ = 0.35, cohesion
   collapses nonlinearly from φ ≈ 0.92 to φ ≈ 0.77.
3. Noise interaction: Higher environmental noise lowers cohesion
   and shifts the collapse threshold to lower diversity values.

## Model
- Framework: Julia 1.10.5, Agents.jl v7.0.2
- N = 200 sheep on a 20x20 periodic box
- Personality trait: social weight per individual, drawn from Beta distribution
- Mean personality held fixed; variance varied systematically
- Order parameter φ: 1 = perfect flock, 0 = disorder
- Replication: 15-20 independent random seeds per condition

## Repository Structure
src/      — Julia simulation scripts and Python figure/analysis scripts
results/  — CSV outputs from all experiments
figures/  — Publication-quality figures
docs/     — Manuscript notes

## How to Run
julia --project=. -e 'using Pkg; Pkg.instantiate()'
julia --project=. src/vicsek_baseline.jl
julia --project=. src/heterogeneous_model_v2.jl
python3 src/figure2_cohesion.py

## Dependencies
Julia: Agents, Distributions, StatsBase, DataFrames, CSV, JLD2, ProgressMeter, ThreadsX
Python: pandas, matplotlib, scipy
