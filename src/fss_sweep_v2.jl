# fss_sweep_v2.jl — finite-size-scaling sweep at FIXED DENSITY.
#
# Jobs are ordered by size. Dynamic scheduling does not guarantee per-job work
# stealing or a particular runtime. Measure performance on the target machine.
# Run: julia --project=. --threads=auto src/fss_sweep_v2.jl
include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
include(joinpath(@__DIR__, "run_metadata.jl"))
using Statistics, DataFrames, CSV, Printf, Dates

const NEIGHBOR_SEARCH = Symbol(get(ENV, "ABM_NEIGHBOR_SEARCH", "exact"))
const SMOKE = get(ENV, "ABM_SMOKE", "0") == "1"
const SIGMA_MEAN = 0.7
const SIGMA_LIST = SMOKE ? [0.0,0.3] : collect(0.0:0.025:0.45)        # same grid as production
const NOISE      = 0.5                             # headline noise level
const N_LIST     = SMOKE ? [12,24] : [100, 200, 400, 800, 1600]
const N_SEEDS    = SMOKE ? 2 : 16
const N_TOTAL    = SMOKE ? 120 : 80000
const N_WARMUP   = SMOKE ? 60 : 40000                            # provisional warmup; verify convergence
const RHO        = 200 / 20.0^2                     # = 0.5, the canonical density
const OUTDIR     = get(ENV, "ABM_OUTPUT_DIR", joinpath(@__DIR__, "..", "results", SMOKE ? "smoke_fss" : string(NEIGHBOR_SEARCH, "_fss")))

Lfor(N) = sqrt(N / RHO)                             # constant-density box side
lag1(x) = cor(@view(x[1:end-1]), @view(x[2:end]))

function run_one(; N, sigma_std, seed)
    model, sv = create_sheep_model(; N=N, L=Lfor(N), noise=NOISE,
        σ_mean=SIGMA_MEAN, σ_std=sigma_std, seed=seed, neighbor_search=NEIGHBOR_SEARCH)
    for _ in 1:N_TOTAL; step!(model); end
    meas = model.order_history[(N_WARMUP+1):end]
    m1 = mean(meas)
    m2 = mean(abs2, meas)
    m4 = mean(x -> x^4, meas)
    q  = length(meas) ÷ 4                           # Q3-vs-Q4 stationarity check
    drift = abs(mean(@view meas[2q+1:3q]) - mean(@view meas[3q+1:4q]))
    (N=N, sigma_std=sigma_std, noise=NOISE, seed=seed,
     phi=m1, phi2=m2, phi4=m4, ar1=lag1(meas), drift=drift, real_std=std(sv))
end

# LARGEST N first so the heavy runs launch first and the cheap ones backfill.
jobs = [(n, s, sd) for n in N_LIST for s in SIGMA_LIST for sd in 1:N_SEEDS]
sort!(jobs, by = j -> -j[1])                        # descending by N
res  = Vector{Any}(undef, length(jobs))

mkpath(OUTDIR)
const T0 = time()
println("FSS v2: $(length(jobs)) runs × $N_TOTAL steps, N ∈ $(N_LIST), on $(Threads.nthreads()) threads")
println("started $(now()) — largest-N-first, dynamic schedule")
flush(stdout)

done = Threads.Atomic{Int}(0)
Threads.@threads :dynamic for i in eachindex(jobs)
    n, s, sd = jobs[i]
    res[i] = run_one(; N=n, sigma_std=s, seed=sd)
    d = Threads.atomic_add!(done, 1) + 1
    if d % 25 == 0 || d == length(jobs)
        el  = (time() - T0) / 60
        eta = el / d * (length(jobs) - d)           # rough; skews high early (big-N first)
        @printf("  %4d / %d   elapsed %.1f min   eta ~%.1f min\n",
                d, length(jobs), el, eta)
        flush(stdout)
    end
end

raw = DataFrame(res)
write_run_metadata(OUTDIR; N=N_LIST, density=RHO, noise=NOISE, sigma=SIGMA_LIST, seeds=N_SEEDS, total=N_TOTAL, warmup=N_WARMUP, smoke=SMOKE, neighbor_search=string(NEIGHBOR_SEARCH))
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
println("\n  wrote FSS tables in $OUTDIR")
@printf("  total wall time: %.1f min\n", (time() - T0) / 60)
flush(stdout)
