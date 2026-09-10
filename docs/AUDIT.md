# Repository audit, 10 September 2026

Baseline: commit `306d0b71233fd08e06c458ba80b05cadb88d7429`, default branch `master`.
Scope: all 11 original source files, project/manifest and citation/license files,
README, all nine simulation CSVs, four figure pairs and recent commit history.
The repository had no tests or Actions runs. Removed historical manuscript content
was not restored. The audit is of the current research software, not a manuscript review.

## Main findings and disposition

| Priority | Finding | Evidence | Disposition |
|---|---|---|---|
| Critical | Production script contains shell text and a duplicate body | `EOFcd /home/umar/...` and a shell heredoc in the Julia source | Removed corruption; added parse and smoke checks |
| Critical | Approximate neighbours confound nominal interaction radius and FSS | Pinned Agents.jl defaults to approximate search and spacing L/20 | Exact search now default; explicit legacy mode and separate output folders; full rerun still needed |
| High | Stored FSS does not establish stationarity | 323/1,520 runs have drift >0.02, maximum 0.181102 | Exported individual flagged runs; figures visibly flag affected conditions |
| High | Unsupported critical-point and exponent interpretation | Automatic first Binder crossing and log χ maximum versus log N interpreted as γ/ν | Removed transition certification and exponent fit; report all descriptive intersections |
| High | Most FSS maxima are not interior peaks | N=200,400,800,1600 have pooled maxima at σ=0.45 | Mark boundary maxima; no peak-scaling inference |
| High | Different variability measures were conflated | Production uses sample variance of run means; FSS pools temporal moments and realizations | Explicit labels and exact within/between decomposition |
| High | Lag-1 correlation labelled critical slowing down | No fitted relaxation-time scaling, full ACF or effective sample-size evidence | Labels now describe temporal persistence |
| High | Short-run bias sign reversed in README | At σ=0.35, long minus short order is +0.134356 | Corrected to underestimation by short runs |
| High | Claimed fixed mean was only distributional | Realized production means 0.642840 to 0.754645 | Documented sample-mean variation and distribution-tail confounding |
| Medium | README omitted existing size data | 95 FSS conditions, five N values | Updated inventory and limitations |
| Medium | Sequential update convention undocumented | Default StandardABM scheduler, immediate movement in agent step | Made existing convention explicit; synchronous comparison remains a control |
| Medium | φ called cohesion | Computation is mean velocity-vector magnitude divided by speed | Identified as heading order; spatial cohesion requires another metric |
| Medium | Input validation incomplete | Negative std squared; short windows indexed below one; invalid physical values accepted | Added validation and boundary tests |
| Medium | Hard-coded local output path | `/home/umar/sheep_collective/results` | Replaced with repository-relative pilot directory |
| Medium | Duplicate FSS implementations and unsupported performance promises | Two nearly identical files, unverified work-stealing/runtime statements | Single implementation with compatibility entry point; removed promises |
| Medium | Snapshot colours could clip wrapped headings | θ can exceed [-π,π] while colour scale uses that interval | Wrap heading before assigning colour |
| Medium | Missing software checks and data lineage | No tests/CI, unversioned Python requirements, no run metadata | Added regression checks, CI, direct dependency versions and new-run hashes |

The radius issue is independently supported by the pinned library's
[continuous-space implementation](https://github.com/JuliaDynamics/Agents.jl/blob/v7.0.2/src/spaces/continuous.jl).
Spacing changes from about 0.7071 at N=100 to 2.8284 at N=1600 at density 0.5.
The extra neighbours depend on cell geometry as well as distance; nominally fixed
radius 1 does not imply a fixed realized interaction rule under approximate search.

## Verified numerical checks

All 57 production and 95 FSS summary rows agree with every corresponding aggregate
field recomputed from their 1,140 and 1,520 replicate rows, respectively. All nine
source CSVs were inspected for missing/nonfinite values. Replicate keys, expected
seed sets, moment inequalities, order bounds and snapshot geometry passed checks.

| N | Maximum stored drift | Runs above 0.02 | σ of pooled fluctuation maximum |
|---:|---:|---:|---:|
| 100 | 0.165939 | 93/304 | 0.425 |
| 200 | 0.108327 | 65/304 | 0.450 |
| 400 | 0.113713 | 55/304 | 0.450 |
| 800 | 0.153881 | 58/304 | 0.450 |
| 1600 | 0.181102 | 52/304 | 0.450 |

Adjacent-size Binder intersections occur at approximately 0.3460 for N=400/800
and 0.4358 for N=800/1600; smaller adjacent pairs have none on the sampled grid.
They do not identify a common critical point. Uncertainty, interaction-range
confounding and stationarity must be resolved before using them scientifically.

The relaxation table's small `late_drift` values are absolute differences of
seed-averaged quarter means. Opposite drifts can cancel. It covers only η=0.5 and
five σ values. New relaxation runs additionally export per-seed quarter summaries;
no missing historical per-seed full-resolution statistics have been invented.

The regenerated main plots retain original measurements and change interpretation
and labels. Their thresholds and bootstrap intervals are in `results/audit/thresholds.csv`.
Original simulation CSVs were not replaced. `data_audit.json` records their hashes.

## Validation and limits

Completed locally: stored-data audit; three Python test cases covering variance
separation and crossing edge cases; execution of all four figure scripts; Python
compilation; review of the generated plots. This is reanalysis of existing data,
not newly executed simulations.

Julia is not installed in the audit environment. A network request to obtain it
was blocked before approval completed. The Julia unit, parse and smoke checks are
provided in CI but local execution was unavailable.

Subsequent GitHub validation **passed** for implementation commit
`533f5aa385c1a0710c171931904dfb7db215f88a`: Julia 1.10.5 environment
instantiation, all Julia parse/unit tests, both production and FSS smoke runs,
and the complete Python checks.
[Successful workflow](https://github.com/Umar2213/sheep-collective-abm/actions/runs/34454578947).
This documentation-only update records that result.

Full production/FSS reruns,
empirical model validation and definitive novelty assessment remain outstanding.
The manifest records Julia 1.10.5 and Agents.jl 7.0.2; it was parsed and checked for
direct dependency coverage but not regenerated or runtime-validated locally.

## Research conclusion

Relevant to ARC preparation: yes. All correct before the audit: no. Demonstrated
novel, sheep-validated contribution: no. The strongest route forward is a clear
mechanistic and predictive comparison using measured individual differences and
social ties. See [the research development plan](ARC_RESEARCH_PLAN.md).
