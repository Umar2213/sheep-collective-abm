# fss_sweep.jl — finite-size-scaling sweep at FIXED DENSITY.
#
# Holds density ρ = N/L² constant (ρ = 0.5, matching the canonical N=200, L=20),
# so each agent sees the same expected number of neighbours regardless of N.
# This is the correct FSS protocol: only the system size changes.
#
# One noise level (η = 0.5, the headline). For each run we record the
# time-series moments ⟨φ⟩, ⟨φ²⟩, ⟨φ⁴⟩ over the stationary window, which give:
#   order parameter            φ        = ⟨φ⟩
#   connected susceptibility   χ        = N·(⟨φ²⟩ − ⟨φ⟩²)
#   Binder cumulant            U        = 1 − ⟨φ⁴⟩ / (3⟨φ²⟩²)
# Binder curves for different N CROSS at a true critical point and do not cross
# for a pure crossover — that crossing test is the core deliverable.
#
# Run (survives SSH disconnect):
#   nohup julia --project=. --threads=auto src/fss_sweep.jl > fss_run.log 2>&1 &
include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
using Statistics, DataFrames, CSV, Printf

const SIGMA_MEAN = 0.7
const SIGMA_LIST = collect(0.0:0.025:0.45)        # same grid as production, comparable
const NOISE      = 0.5                             # headline noise level
const N_LIST     = [100, 200, 400, 800, 1600]      # drop 1600 to ~halve runtime
const N_SEEDS    = 16                              # lower for big N if you want speed
const N_TOTAL    = 80000                           # extra headroom vs production (60k)
const N_WARMUP   = 40000                           # critical slowing down grows with N
const RHO        = 200 / 20.0^2                    # = 0.5, the canonical density
const OUTDIR     = joinpath(@__DIR__, "..", "results", "fss")

Lfor(N) = sqrt(N / RHO)                            # constant-density box side
lag1(x) = cor(@view(x[1:end-1]), @view(x[2:end]))

function run_one(; N, sigma_std, seed)
    model, sv = create_sheep_model(; N=N, L=Lfor(N), noise=NOISE,
        σ_mean=SIGMA_MEAN, σ_std=sigma_std, seed=seed)
    for _ in 1:N_TOTAL; step!(model); end
    meas = model.order_history[(N_WARMUP+1):end]
    m1 = mean(meas)
    m2 = mean(abs2, meas)
    m4 = mean(x -> x^4, meas)
    q  = length(meas) ÷ 4                          # Q3-vs-Q4 stationarity check
    drift = abs(mean(@view meas[2q+1:3q]) - mean(@view meas[3q+1:4q]))
    (N=N, sigma_std=sigma_std, noise=NOISE, seed=seed,
     phi=m1, phi2=m2, phi4=m4, ar1=lag1(meas), drift=drift, real_std=std(sv))
end

jobs = [(n, s, sd) for n in N_LIST for s in SIGMA_LIST for sd in 1:N_SEEDS]
res  = Vector{Any}(undef, length(jobs))
println("FSS: $(length(jobs)) runs × $N_TOTAL steps, N ∈ $(N_LIST), on $(Threads.nthreads()) threads")
done = Threads.Atomic{Int}(0)
Threads.@threads for i in eachindex(jobs)
    n, s, sd = jobs[i]
    res[i] = run_one(; N=n, sigma_std=s, seed=sd)
    d = Threads.atomic_add!(done, 1) + 1
    d % 50 == 0 && println("  $d / $(length(jobs))")
end

mkpath(OUTDIR)
raw = DataFrame(res)
CSV.write(joinpath(OUTDIR, "fss_replicates.csv"), raw)

summ = combine(groupby(raw, [:N, :sigma_std])) do sub
    m1 = mean(sub.phi); m2 = mean(sub.phi2); m4 = mean(sub.phi4)
    Ni = first(sub.N)
    (phi_mean = m1,
     phi_sd   = std(sub.phi),
     chi      = Ni * (m2 - m1^2),
     binder   = 1 - m4 / (3 * m2^2),
     ar1      = mean(sub.ar1),
     drift    = maximum(sub.drift),
     real_std = mean(sub.real_std),
     n        = nrow(sub))
end
sort!(summ, [:N, :sigma_std])
CSV.write(joinpath(OUTDIR, "fss_condition_means.csv"), summ)

println("\n  χ peak location and height by N (η = $NOISE):")
println("    N    | σ@χmax |  χmax  | max drift")
println("    " * "-"^40)
for Ni in N_LIST
    s = summ[summ.N .== Ni, :]
    j = argmax(s.chi)
    @printf("   %5d |  %.3f | %.4f |  %.4f\n",
        Ni, s.sigma_std[j], s.chi[j], maximum(s.drift))
end
println("\n  wrote results/fss/fss_replicates.csv + fss_condition_means.csv")
println("  (any 'max drift' ≳ 0.02 → bump N_WARMUP for that size and rerun)")
