# fss_sweep_v2.jl
# Finite-size comparison at fixed density, with exact metric neighbours by default,
# crossed trait/dynamic random streams, and per-run convergence diagnostics.
# Run: julia --project=. --threads=auto src/fss_sweep_v2.jl

include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
include(joinpath(@__DIR__, "diagnostics.jl"))
include(joinpath(@__DIR__, "run_metadata.jl"))
using Statistics, DataFrames, CSV, Printf, Dates

const NEIGHBOR_SEARCH = Symbol(get(ENV, "ABM_NEIGHBOR_SEARCH", "exact"))
const UPDATE_MODE = Symbol(get(ENV, "ABM_UPDATE_MODE", "sequential"))
const SMOKE = get(ENV, "ABM_SMOKE", "0") == "1"
const SIGMA_MEAN = 0.7
const SIGMA_LIST = SMOKE ? [0.0, 0.3] : collect(0.0:0.025:0.45)
const NOISE = 0.5
const N_LIST = SMOKE ? [12, 24] : [100, 200, 400, 800, 1600]
const N_TRAIT_REPS = SMOKE ? 2 : 4
const N_DYNAMIC_REPS = SMOKE ? 1 : 4
const N_TOTAL = SMOKE ? 160 : 80000
const N_WARMUP = SMOKE ? 80 : 40000
const N_BLOCKS = SMOKE ? 4 : 8
const RHO = 200 / 20.0^2
const OUTDIR = get(ENV, "ABM_OUTPUT_DIR",
    joinpath(@__DIR__, "..", "results", SMOKE ? "smoke_fss" :
             string(NEIGHBOR_SEARCH, "_", UPDATE_MODE, "_fss")))

Lfor(N) = sqrt(N / RHO)
trait_seed(rep) = 110_000 + rep
init_seed(rep) = 120_000 + rep
dynamic_seed(rep) = 130_000 + rep

function run_one(; N, sigma_std, trait_rep, dynamic_rep)
    ts = trait_seed(trait_rep)
    is = init_seed(dynamic_rep)
    ds = dynamic_seed(dynamic_rep)
    model, sv = create_sheep_model(; N=N, L=Lfor(N), noise=NOISE,
        σ_mean=SIGMA_MEAN, σ_std=sigma_std, seed=0,
        trait_seed=ts, init_seed=is, dynamic_seed=ds,
        neighbor_search=NEIGHBOR_SEARCH, update_mode=UPDATE_MODE)

    for _ in 1:N_TOTAL
        step!(model)
    end
    meas = model.order_history[(N_WARMUP + 1):end]
    diag = stationarity_diagnostics(meas; nblocks=N_BLOCKS)
    m1 = mean(meas)
    m2 = mean(abs2, meas)
    m4 = mean(x -> x^4, meas)

    return (
        N=N,
        sigma_std=sigma_std,
        noise=NOISE,
        trait_rep=trait_rep,
        dynamic_rep=dynamic_rep,
        trait_seed=ts,
        init_seed=is,
        dynamic_seed=ds,
        phi=m1,
        phi2=m2,
        phi4=m4,
        ar1=diag.ar1,
        tau_int=diag.tau_int,
        ess=diag.ess,
        block_sd=diag.block_sd,
        half_drift=diag.half_drift,
        late_quarter_drift=diag.late_quarter_drift,
        real_mean=mean(sv),
        real_std=std(sv),
    )
end

jobs = [(n, s, tr, dr) for n in N_LIST for s in SIGMA_LIST
        for tr in 1:N_TRAIT_REPS for dr in 1:N_DYNAMIC_REPS]
sort!(jobs, by=j -> -j[1])
res = Vector{Any}(undef, length(jobs))

mkpath(OUTDIR)
const T0 = time()
println("FSS: $(length(jobs)) runs × $N_TOTAL steps, N ∈ $(N_LIST)")
println("search=$NEIGHBOR_SEARCH, update=$UPDATE_MODE, density=$RHO")
println("crossed design: $N_TRAIT_REPS trait × $N_DYNAMIC_REPS dynamic realizations")
println("started $(now())")
flush(stdout)

done = Threads.Atomic{Int}(0)
Threads.@threads :dynamic for i in eachindex(jobs)
    n, s, tr, dr = jobs[i]
    res[i] = run_one(; N=n, sigma_std=s, trait_rep=tr, dynamic_rep=dr)
    d = Threads.atomic_add!(done, 1) + 1
    if d % 25 == 0 || d == length(jobs)
        el = (time() - T0) / 60
        eta = el / d * (length(jobs) - d)
        @printf("  %4d / %d   elapsed %.1f min   rough eta %.1f min\n",
                d, length(jobs), el, eta)
        flush(stdout)
    end
end

raw = DataFrame(res)
write_run_metadata(OUTDIR;
    experiment="finite_size",
    N=N_LIST,
    density=RHO,
    noise=NOISE,
    sigma=SIGMA_LIST,
    trait_replicates=N_TRAIT_REPS,
    dynamic_replicates=N_DYNAMIC_REPS,
    total=N_TOTAL,
    warmup=N_WARMUP,
    diagnostic_blocks=N_BLOCKS,
    smoke=SMOKE,
    neighbor_search=string(NEIGHBOR_SEARCH),
    update_mode=string(UPDATE_MODE),
    seed_design="trait=110000+trait_rep; init=120000+dynamic_rep; dynamic=130000+dynamic_rep")
CSV.write(joinpath(OUTDIR, "fss_replicates.csv"), raw)

summ = combine(groupby(raw, [:N, :sigma_std])) do sub
    m1 = mean(sub.phi)
    m2 = mean(sub.phi2)
    m4 = mean(sub.phi4)
    Ni = first(sub.N)
    trait_means = [mean(g.phi) for g in groupby(sub, :trait_rep)]
    within_trait_vars = [nrow(g) > 1 ? var(g.phi) : 0.0 for g in groupby(sub, :trait_rep)]
    (
        phi_mean=m1,
        phi_sd=std(sub.phi),
        chi=Ni * (m2 - m1^2),
        binder=1 - m4 / (3 * m2^2),
        ar1=mean(sub.ar1),
        tau_int_median=median(sub.tau_int),
        ess_min=minimum(sub.ess),
        block_sd_max=maximum(sub.block_sd),
        half_drift_max=maximum(sub.half_drift),
        late_quarter_drift_max=maximum(sub.late_quarter_drift),
        between_trait_var=length(trait_means) > 1 ? var(trait_means) : 0.0,
        within_trait_var=mean(within_trait_vars),
        real_mean=mean(sub.real_mean),
        real_std=mean(sub.real_std),
        n=nrow(sub),
    )
end
sort!(summ, [:N, :sigma_std])
CSV.write(joinpath(OUTDIR, "fss_condition_means.csv"), summ)

println("\n  pooled fluctuation maxima by N, descriptive only:")
println("    N    | sigma@max | value   | min ESS | max late drift")
println("    " * "-"^61)
for Ni in N_LIST
    s = summ[summ.N .== Ni, :]
    j = argmax(s.chi)
    @printf("   %5d |   %.3f   | %.4f | %7.1f | %.4f\n",
        Ni, s.sigma_std[j], s.chi[j], minimum(s.ess_min),
        maximum(s.late_quarter_drift_max))
end
println("\n  wrote finite-size tables in $OUTDIR")
@printf("  total wall time: %.1f min\n", (time() - T0) / 60)
flush(stdout)
