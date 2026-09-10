# production_sweep.jl
# Corrected exact-radius production experiment with crossed trait and dynamic
# realizations, explicit random streams, and per-run convergence diagnostics.
# Run: julia --project=. --threads=auto src/production_sweep.jl

include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
include(joinpath(@__DIR__, "diagnostics.jl"))
include(joinpath(@__DIR__, "run_metadata.jl"))
using Statistics, DataFrames, CSV, Printf

const SIGMA_MEAN = 0.7
const NEIGHBOR_SEARCH = Symbol(get(ENV, "ABM_NEIGHBOR_SEARCH", "exact"))
const UPDATE_MODE = Symbol(get(ENV, "ABM_UPDATE_MODE", "sequential"))
const SMOKE = get(ENV, "ABM_SMOKE", "0") == "1"
const SIGMA_LIST = SMOKE ? [0.0, 0.3] : collect(0.0:0.025:0.45)
const NOISE_LIST = SMOKE ? [0.5] : [0.3, 0.5, 0.7]
const N_AGENTS = SMOKE ? 12 : 200
const N_TRAIT_REPS = SMOKE ? 2 : 5
const N_DYNAMIC_REPS = SMOKE ? 1 : 4
const N_TOTAL = SMOKE ? 160 : 60000
const N_WARMUP = SMOKE ? 80 : 30000
const N_BLOCKS = SMOKE ? 4 : 8
const OUTDIR = get(ENV, "ABM_OUTPUT_DIR",
    joinpath(@__DIR__, "..", "results", SMOKE ? "smoke_production" :
             string(NEIGHBOR_SEARCH, "_", UPDATE_MODE, "_production")))

trait_seed(rep) = 10_000 + rep
init_seed(rep) = 20_000 + rep
dynamic_seed(rep) = 30_000 + rep

function run_one(; sigma_std, noise, trait_rep, dynamic_rep)
    ts = trait_seed(trait_rep)
    is = init_seed(dynamic_rep)
    ds = dynamic_seed(dynamic_rep)
    model, sv = create_sheep_model(; N=N_AGENTS, noise=noise,
        σ_mean=SIGMA_MEAN, σ_std=sigma_std, seed=0,
        trait_seed=ts, init_seed=is, dynamic_seed=ds,
        neighbor_search=NEIGHBOR_SEARCH, update_mode=UPDATE_MODE)

    for _ in 1:N_TOTAL
        step!(model)
    end
    meas = model.order_history[(N_WARMUP + 1):end]
    diag = stationarity_diagnostics(meas; nblocks=N_BLOCKS)

    return (
        sigma_std=sigma_std,
        noise=noise,
        trait_rep=trait_rep,
        dynamic_rep=dynamic_rep,
        trait_seed=ts,
        init_seed=is,
        dynamic_seed=ds,
        phi=mean(meas),
        phi_tempvar=var(meas),
        ar1=diag.ar1,
        tau_int=diag.tau_int,
        ess=diag.ess,
        block_sd=diag.block_sd,
        half_drift=diag.half_drift,
        late_quarter_drift=diag.late_quarter_drift,
        real_mean=mean(sv),
        real_std=std(sv),
        frac_lo=count(<(0.2), sv) / length(sv),
        frac_hi=count(>(0.8), sv) / length(sv),
    )
end

jobs = [(s, e, tr, dr) for s in SIGMA_LIST for e in NOISE_LIST
        for tr in 1:N_TRAIT_REPS for dr in 1:N_DYNAMIC_REPS]
res = Vector{Any}(undef, length(jobs))
println("production: $(length(jobs)) runs × $N_TOTAL steps, search=$NEIGHBOR_SEARCH, update=$UPDATE_MODE")
println("crossed design: $N_TRAIT_REPS trait realizations × $N_DYNAMIC_REPS dynamic realizations")

done = Threads.Atomic{Int}(0)
Threads.@threads :dynamic for i in eachindex(jobs)
    s, e, tr, dr = jobs[i]
    res[i] = run_one(; sigma_std=s, noise=e, trait_rep=tr, dynamic_rep=dr)
    d = Threads.atomic_add!(done, 1) + 1
    (d % 100 == 0 || d == length(jobs)) && println("  $d / $(length(jobs))")
end

mkpath(OUTDIR)
raw = DataFrame(res)
write_run_metadata(OUTDIR;
    experiment="production",
    N=N_AGENTS,
    L=20.0,
    noise=NOISE_LIST,
    sigma=SIGMA_LIST,
    trait_replicates=N_TRAIT_REPS,
    dynamic_replicates=N_DYNAMIC_REPS,
    total=N_TOTAL,
    warmup=N_WARMUP,
    diagnostic_blocks=N_BLOCKS,
    smoke=SMOKE,
    neighbor_search=string(NEIGHBOR_SEARCH),
    update_mode=string(UPDATE_MODE),
    seed_design="trait=10000+trait_rep; init=20000+dynamic_rep; dynamic=30000+dynamic_rep")
CSV.write(joinpath(OUTDIR, "sweep_replicates.csv"), raw)

function summarize_condition(sub)
    trait_means = [mean(g.phi) for g in groupby(sub, :trait_rep)]
    within_trait_vars = [nrow(g) > 1 ? var(g.phi) : 0.0 for g in groupby(sub, :trait_rep)]
    return (
        phi_mean=mean(sub.phi),
        phi_sd=std(sub.phi),
        chi_seed=N_AGENTS * var(sub.phi),
        tempvar=mean(sub.phi_tempvar),
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
        frac_lo=mean(sub.frac_lo),
        frac_hi=mean(sub.frac_hi),
        n=nrow(sub),
    )
end

summ = combine(groupby(raw, [:noise, :sigma_std]), summarize_condition)
sort!(summ, [:noise, :sigma_std])
CSV.write(joinpath(OUTDIR, "sweep_condition_means.csv"), summ)

println("\n  η=0.5 summary:")
println("  sigma | phi_mean | sd     | median tau | min ESS | max late drift")
println("  " * "-"^72)
for row in eachrow(summ[summ.noise .== 0.5, :])
    @printf("  %.3f | %.4f   | %.4f | %10.2f | %7.1f | %.4f\n",
        row.sigma_std, row.phi_mean, row.phi_sd, row.tau_int_median,
        row.ess_min, row.late_quarter_drift_max)
end
println("\n  wrote production tables in $OUTDIR")
