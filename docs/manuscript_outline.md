# Manuscript Outline

## Target journal: PLOS Computational Biology

## Title options (3, from most to least ambitious)

1. **Personality diversity drives a critical transition in flock cohesion: an agent-based model of collective sheep behaviour**

2. **When does personality matter for the flock? Threshold effects of social heterogeneity in a self-propelled agent model**

3. **Robust flocking under moderate personality variance, fragile under extreme diversity: a computational test of the mean–variance decoupling hypothesis**

---

## Abstract (150 word draft)

Collective animal movement is often modelled with identical agents, yet real groups contain individuals that differ consistently in behaviour. We built an agent-based model of 200 self-propelled agents (“sheep”) on a periodic arena, each assigned a social responsiveness trait drawn from a Beta distribution with fixed mean (0.7) and systematically varied standard deviation. Holding mean personality constant, we asked whether diversity in social weight alone alters flock cohesion, measured as the polar order parameter φ. Cohesion remained high (φ ≈ 0.97) for diversity σ ≤ 0.30, then collapsed nonlinearly between σ = 0.30 and 0.35 to φ ≈ 0.46 at σ = 0.45. One-way ANOVA confirmed strong effects of diversity (F = 130.5, p < 10⁻⁷⁰). Environmental noise lowered baseline cohesion and shifted the critical threshold leftward. Our results identify a robustness zone and a critical diversity threshold, suggesting that personality *variance*, not mean sociability alone, can determine whether a flock remains aligned.

---

## 1. Introduction

### Paragraph 1: Collective behaviour and the homogeneity assumption

Animal groups—from fish schools to bird flocks—often move as coherent units through simple local rules of alignment, attraction, and repulsion. Classic self-propelled particle models, notably the Vicsek model, demonstrate that order can emerge from purely local interactions without central control. A tacit assumption in many such models is that all individuals follow identical rules. Yet this homogeneity is a modelling convenience rather than a biological fact, and it limits our ability to predict how real groups—composed of distinct individuals—will respond to perturbation.

### Paragraph 2: Individual personality in animals

Across taxa, animals show repeatable differences in behaviour, termed personality or temperament, that are partly heritable and stable across contexts. In social species, traits such as boldness and sociability covary with how strongly individuals attend to neighbours. Réale et al. (2007) argued that such variation should be integrated into ecological and evolutionary theory rather than treated as noise around a population mean. For collective movement, the open question is not whether individuals differ, but whether the *distribution* of those differences matters for group-level outcomes.

### Paragraph 3: Sheep collective behaviour

Sheep are a particularly relevant system because they form dense, mobile groups under husbandry and in the wild, and their movement has been studied with GPS tracking and controlled experiments. Ginelli et al. (2015) showed that real sheep herds exhibit intermittent collective dynamics driven by conflicting pressures to graze and aggregate. Strömbom et al. (2014) modelled shepherding and herding with explicit sheep agents. These studies establish that sheep flocks are tractable, socially structured groups—but they do not systematically vary the *spread* of personality traits while holding the mean fixed.

### Paragraph 4: The gap in the literature

Most flocking models assign one parameter set to all agents. Where heterogeneity has been introduced, it is often binary (leaders vs followers) or tied to changing the mean trait value. No study, to our knowledge, has asked: if the average tendency to follow neighbours is held constant, does increasing the variance of that tendency across individuals change flock cohesion? This mean–variance decoupling is essential for separating “a group of moderately social sheep” from “a group with the same average sociability but a few loners and a few zealots.”

### Paragraph 5: This paper

We extend a Vicsek-type flocking model with agent-specific social weights drawn from Beta distributions. We sweep personality diversity at fixed mean sociability and replicate each condition across 15–20 random seeds. We report a robustness zone (cohesion insensitive to diversity up to σ ≈ 0.30), a sharp critical threshold near σ ≈ 0.33, and an interaction with environmental noise that makes flocks more fragile when diversity is high.

---

## 2. Methods

### 2.1 Model overview

We implemented an agent-based model in Julia 1.10.5 using Agents.jl v7.0.2, following the ODD (Overview, Design concepts, Details) protocol for transparent description of simulation models. The model is a continuous-space, fixed-speed flocking model with periodic boundaries, extended to allow heterogeneous social responsiveness among agents.

### 2.2 Agent definition

Each of N = 200 agents occupies position **x**ᵢ on a 20 × 20 torus and moves at constant speed v = 0.03 per time step. Agent i has heading θᵢ and a trait social weight σᵢ ∈ [0, 1], representing the proportion of its heading update drawn from neighbours versus its own previous heading. At initialization, σᵢ values are drawn independently from a Beta distribution parameterised to achieve target population mean μ = 0.7 and standard deviation s (varied across experiments). When s = 0, all agents receive σᵢ = μ.

### 2.3 Movement rules

Each step, agent i identifies all neighbours within interaction radius r = 1.0. If neighbours exist, the neighbour mean heading is computed via circular mean of {θⱼ}. Agent i blends this with its own heading: the updated direction uses weight σᵢ on the neighbour consensus and (1 − σᵢ) on its current heading. Environmental noise η perturbs the heading: θᵢ ← θ̄ᵢ + η(ξ − 0.5) with ξ ~ Uniform(0,1). The agent then moves at speed v. This rule reduces to standard Vicsek alignment when all σᵢ = 1 and η is small.

### 2.4 Order parameter

Flock cohesion is summarised by the polar order parameter φ = |⟨**v**⟩| / v, where ⟨**v**⟩ is the mean velocity vector across agents. φ = 1 indicates perfect alignment; φ ≈ 0 indicates disorder. For each simulation of 500 steps, we recorded φ at every step and defined steady-state cohesion as the mean φ over the final 100 steps, reducing transient effects.

### 2.5 Experimental design

**Experiment 1** varied s ∈ {0, 0.05, …, 0.25} at η = 0.5, μ = 0.7, with 15 seeds per condition. **Experiment 2** extended s ∈ {0.25, 0.30, …, 0.45} with 20 seeds. **Experiment 3** crossed s ∈ {0, 0.2, 0.35, 0.45} with η ∈ {0.3, 0.5, 0.7} (15 seeds each). A Vicsek baseline with identical agents validated implementation at η = 0.1 (flock) and η = 4.0 (disorder).

### 2.6 Statistical analysis

We tested differences in steady-state φ across diversity levels using one-way ANOVA on pooled per-seed values. Pairwise comparisons against the homogeneous baseline (s = 0) used Welch’s t-tests with Cohen’s d effect sizes. Uncertainty in condition means was quantified with 10,000 bootstrap resamples per (η, s) cell, reporting 95% confidence intervals. Threshold estimates in the phase diagram used linear interpolation between adjacent s levels where φ crossed 0.9.

---

## 3. Results

### 3.1 Baseline validation (Figure 1)

The Vicsek baseline with identical agents reproduced the expected noise-driven order–disorder transition. At low noise (η = 0.1), φ rose from ~0.1 to ~0.99 within approximately 80 steps and remained high. At high noise (η = 4.0), φ stayed below ~0.25, indicating sustained disorder. This confirms that the implementation, periodic boundaries, and order parameter behave as in the classical model before introducing personality heterogeneity.

### 3.2 Effect of personality diversity (Figure 2A)

At medium environmental noise (η = 0.5) and fixed mean sociability (μ = 0.7), cohesion remained near φ ≈ 0.97 for diversity s ≤ 0.30. Bootstrap 95% CIs overlapped across these conditions. Beginning near s = 0.30–0.35, mean φ fell sharply to 0.77 at s = 0.35 and 0.46 at s = 0.45. The relationship is nonlinear rather than gradual, indicating a threshold-like transition in collective alignment driven solely by increasing personality variance.

### 3.3 Critical threshold

Combining Experiments 1 and 2 (190 per-seed runs), one-way ANOVA detected a highly significant effect of diversity on φ (F = 130.5, p ≈ 5.3 × 10⁻⁷⁴). Welch t-tests against the homogeneous flock showed no significant decline until s ≥ 0.25 (p < 0.001), with large Cohen’s d at s = 0.35 (d ≈ 2.5) and s = 0.45 (d ≈ 4.0). The critical region lies between s = 0.30 and 0.35, where φ drops by roughly 0.15–0.20 within a narrow increment of diversity.

### 3.4 Noise × diversity interaction (Figure 2B, Figure 3)

Experiment 3 showed that environmental noise modulates both baseline cohesion and threshold position. At η = 0.3, homogeneous flocks reached φ ≈ 0.99 and remained cohesive until s = 0.35 (φ ≈ 0.85). At η = 0.7, baseline φ fell to ~0.94 even for s = 0, and collapse to φ ≈ 0.39 occurred by s = 0.45. The phase diagram (Figure 3) shows a green high-cohesion region at low s and low–medium η, separated by a boundary near φ = 0.9 from a red fragmented region. Interpolated critical diversity σ* decreases as η increases, indicating that noisy environments make flocks more vulnerable to personality heterogeneity.

---

## 4. Discussion

### 4.1 Main finding: robustness then collapse

The model reveals two regimes: a robustness zone in which the flock tolerates substantial personality spread without losing alignment, and a collapse zone in which a minority of weakly social agents disrupt global order. Mechanistically, low-σ agents fail to align with neighbours, injecting directional variance that propagates through the interaction network. Below a critical proportion of such agents, highly social individuals can “pull” the group back into alignment; above it, disorder dominates.

### 4.2 Comparison to Ginelli et al. 2015

Ginelli et al. documented intermittent switching between grazing and cohesive motion in real sheep herds, suggesting that collective state depends on local rules and context. Our model does not include foraging or resource heterogeneity, but the threshold in σ is conceptually parallel: collective cohesion is not lost gradually but can switch when individual-level tendencies cross a boundary. Future work could ask whether GPS-derived proxies for individual sociability in real flocks show variance comparable to our critical s range.

### 4.3 Biological implications

If management or breeding produces flocks with high variance in social responsiveness—e.g. mixing bold, independent individuals with highly gregarious ones—the model predicts disproportionate loss of cohesion relative to modest diversity. Under high environmental stress (wind, disturbance, predator cues modelled as noise), the safe diversity range shrinks. Uniformity in mean sociability is not sufficient; controlling variance may matter for herding efficiency and animal welfare during movement.

### 4.4 Limitations

The model uses a single personality axis, no explicit predator, no spatial memory or terrain, and no empirical calibration to GPS data. Agents are memoryless aside from their current heading. The Beta distribution is a convenient choice for bounded traits but may not match real sheep trait distributions. Results are specific to N = 200, box size 20, and interaction radius 1.0; sensitivity analyses are needed to test generality.

### 4.5 Future work

We plan to add a boldness trait affecting predator flight, validate order parameters against published sheep trajectories, and run two-dimensional sweeps of mean and variance (Experiment 4). Coupling this framework to empirical movement archives (e.g. Movebank) would test whether observed between-individual variance in sociability proxies predicts measured flock fragmentation in the field.

---

## 5. Conclusion

Personality variance can destabilise collective motion even when mean sociability is held constant. Flocks in our model remain cohesive across a wide robustness zone but undergo a sharp transition near a critical diversity threshold, exacerbated by environmental noise. Integrating individual heterogeneity into collective movement models is necessary to predict when groups stay together—and when they fall apart.

---

## ODD Protocol (Appendix)

### Overview

**Purpose:** Test how variance in agents’ social responsiveness affects flock cohesion under varying environmental noise.  
**Entities:** Mobile agents (sheep) on a 2D torus.  
**State variables:** Position, velocity, heading θ, social weight σ.  
**Process overview:** Initialise traits → repeat local alignment + noise + movement → record φ.

### Design concepts

**Emergence:** Global order parameter φ arises from local alignment rules.  
**Adaptation:** None (fixed traits per run).  
**Objectives:** None (no optimisation).  
**Learning:** None.  
**Prediction:** None.  
**Sensing:** Agents sense neighbours within radius r.  
**Interaction:** Vicsek-type alignment weighted by σᵢ.  
**Stochasticity:** Random initial headings, Beta-distributed σᵢ, uniform noise in updates, random seeds across replicates.  
**Collectives:** Flock is the full set of agents; no explicit sub-groups.

### Details: Initialization

N = 200 agents placed at random positions; random initial headings; σᵢ ~ Beta(α, β) from target μ and s, or σᵢ = μ if s = 0.

### Details: Input

No external time-varying input; experimental factors (μ, s, η, seed) set at run start.

### Details: Submodels

(1) Neighbour detection within r; (2) circular mean heading; (3) σ-weighted blend with own heading; (4) noise perturbation; (5) constant-speed displacement; (6) φ computed from mean velocity each step.
