# Reviewer-data guide

Anticipated reviewer questions and exactly where the answer lives. Keep this handy when
you write the response-to-reviewers letter — every line below is already defensible from
the data in this folder.

---

**Q1. "A single system size can't establish a transition — is this real or a finite-size artifact?"**
→ This is now answered by the FSS analysis (Section 3.6, Fig. 3, Table 3).
   `results/fss/fss_condition_means.csv`. The susceptibility maximum grows as χ_max ∝ N^0.91
   across N = 100–1600 at fixed density. Because χ = N·Var(φ), an exponent near 1 means
   Var(φ) is nearly N-independent → fluctuations are **collective**, not independent per-agent
   noise (which would give size-independent χ and Var(φ) ∝ 1/N). This is the headline upgrade.

**Q2. "Then give me the critical point and the exponents."**
→ Declined honestly in-text. The susceptibility peak sits at σ = 0.45 for all N ≥ 200
   (Table 3) — the peak is not bracketed. σ = 0.45 ≈ the hard variance ceiling of a
   Beta(mean 0.7) distribution (σ_max = √(0.7·0.3) ≈ 0.458, Section 2.3). The transition is
   structurally pinned to the edge, so we report the *approach* to a transition and do NOT
   present 0.91 as a critical γ/ν. This pre-empts the "you over-claimed exponents" rejection.

**Q3. "How do you know the runs are equilibrated?"**
→ Section 2.5 + `results/diagnostics/`. Two diagnostics: (a) short (500-step) runs overstate
   φ by up to 0.13 near the transition vs long runs; (b) Q3-vs-Q4 drift ≤ 0.01 everywhere
   (max 0.010 at σ=0.33). FSS runs use 80k steps, 40k discarded — even more conservative.

**Q4. "Isn't the effect just lowering mean responsiveness?"**
→ No. Mean is fixed at μ = 0.7 for **every** condition (Section 2.3). Only the variance
   changes. Mechanism is the growth of the weak-responder tail (Fig. 1e,f): w<0.2 fraction
   0→0.30, w>0.8 fraction 0→0.68. This is the central decoupling of the design.

**Q5. "Did you control density in the FSS sweep? Larger N could just mean denser/sparser."**
→ Yes. ρ = N/L² held constant at 0.5 (the canonical N=200, L=20 value), L = √(N/ρ)
   (Section 2.7, Table 1). Each agent sees the same expected neighbour count at every N —
   only system size changes. Implemented in `src/fss_sweep_v2.jl`.

**Q6. "Show me the Binder cumulant crossing."**
→ Table 4 + Fig. 3c. Curves stay near the ordered value 2/3 at low σ and converge/tangle in
   the σ ≈ 0.43–0.45 region. Reported honestly as *consistent with an approaching crossing
   near the edge*, not a resolved single crossing point. Don't over-claim this in the rebuttal.

**Q7. "Can I see the raw per-replicate data, not just means?"**
→ `results/fss/fss_replicates.csv` (1,520 runs, all 16 seeds × 95 conditions) and the
   single-size per-seed file in `results/production/`. Nothing is hidden behind the means.

**Q8. "Is this reproducible?"**
→ Full source in `src/`, pinned environment in `env/` (Project.toml, Manifest.toml,
   requirements.txt), public repo, and a Zenodo DOI on acceptance. Reproduction commands in
   README_PACKAGE.md.

**Q9. "Why only one noise level in the FSS sweep?"**
→ Acknowledged as a limitation (Section 4.2): FSS done at η = 0.5 only. The single-size
   sweep covers η = 0.3/0.5/0.7; mapping the size-dependence of the noise–dispersion
   interaction is named future work (Section 4.3).

**Q10. "Why not push σ higher to capture the peak?"**
→ You can't with mean 0.7 — 0.458 is the mathematical ceiling. The clean fix (named in
   Section 4.3) is to lower the trait mean (e.g. 0.5) or sweep η, which moves the transition
   into the interior. This is the obvious next paper, not a flaw in this one.

---

## Suggested submission targets (sound-science fit, given the honest framing)
Royal Society Open Science · PLOS ONE · Journal of Theoretical Biology · Scientific Reports.
The FSS collective-fluctuation result strengthens the case versus the original single-size
draft; the edge-pinned transition keeps it out of "measured-exponents PRE" territory, and
the manuscript says so plainly so a referee cannot catch you on it.
