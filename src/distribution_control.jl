# distribution_control.jl
# Tests whether a heterogeneity effect depends on the Beta distribution shape.
# Beta and two-point responsiveness distributions have the same target population
# mean and variance, with matched latent quantile ranks from the same trait seed.
# Run: julia --project=. --threads=auto src/distribution_control.jl

include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
include(joinpath(@__DIR__, "diagnostics.jl"))
include(joinpath(@__DIR__, "run_metadata.jl"))
include(joinpath(@__DIR__, "sharding.jl"))
using Statistics, DataFrames, CSV, Printf

const SMOKE = get(ENV, "ABM_SMOKE", "0") == "1"
const SIGMA_MEAN = 0.7
const SIGMA_LIST = SMOKE ? [0.10, 0.30] : [0.10, 0.20, 0.30, 0.40]
const NOISE_LIST = SMOKE ? [0.5] : [0.3, 0.5, 0.7]
const TRAIT_FAMILIES = [:beta, :two_point]
const N_AGENTS = SMOKE ? 12 : 200
const N_TRAIT_REPS = SMOKE ? 2 : 4
const N_DYNAMIC_REPS = SMOKE ? 1 : 3
const N_TOTAL = SMOKE ? 160 : 60000
const N_WARMUP = SMOKE ? 80 : 30000
const N_BLOCKS = SMOKE ? 4 : 8
const SHARD = shard_spec()
const BASE_OUTDIR = get(ENV, "ABM_OUTPUT_DIR",
    joinpath(@__DIR__, "..", "results", SMOKE ? "smoke_distribution_controls" : "distribution_controls"))
const OUTDIR = shard_dir(BASE_OUTDIR, SHARD)

trait_seed(rep) = 310_000 + rep
init_seed(rep) = 320_000 + rep
dynamic_seed(rep) = 330_000 + rep

function run_distribution_control(; sigma_std, noise, family, trait_rep, dynamic_rep)
    ts = trait_seed(trait_rep)
    is = init_seed(dynamic_rep)
    ds = dynamic_seed(dynamic_rep)
    model, sv = create_sheep_model(; N=N_AGENTS, noise=noise,
        σ_mean=SIGMA_MEAN, σ_std=sigma_std, seed=0,
        trait_seed=ts, init_seed=is, dynamic_seed=ds,
        neighbor_search=:exact, update_mode=:sequential,
        trait_distribution=family)
    for _ in 1:N_TOTAL
        step!(model)
    end
    meas = model.order_history[(N_WARMUP + 1):end]
    diag = stationarity_diagnostics(meas; nblocks=N_BLOCKS)
    return (
        sigma_std=sigma_std,
        noise=noise,
        trait_distribution=string(family),
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

all_base_conditions = [(s, e) for s in SIGMA_LIST for e in NOISE_LIST]
base_conditions = select_shard(all_base_conditions, SHARD)
jobs = [(s, e, family, tr, dr)
        for (s, e) in base_conditions
        for family in TRAIT_FAMILIES
        for tr in 1:N_TRAIT_REPS for dr in 1:N_DYNAMIC_REPS]
res = Vector{Any}(undef, length(jobs))
println("distribution controls: $(length(jobs)) runs × $N_TOTAL steps")
println("families=$(TRAIT_FAMILIES), exact search, sequential update")
println("shard $(SHARD.index)/$(SHARD.count): $(length(base_conditions))/$(length(all_base_conditions)) base conditions")

done = Threads.Atomic{Int}(0)
Threads.@threads :dynamic for i in eachindex(jobs)
    s, e, family, tr, dr = jobs[i]
    res[i] = run_distribution_control(; sigma_std=s, noise=e, family=family,
        trait_rep=tr, dynamic_rep=dr)
    d = Threads.atomic_add!(done, 1) + 1
    (d % 25 == 0 || d == length(jobs)) && println("  $d / $(length(jobs))")
end

mkpath(OUTDIR)
raw = DataFrame(res)
CSV.write(joinpath(OUTDIR, "distribution_replicates.csv"), raw)
write_run_metadata(OUTDIR;
    experiment="distribution_controls",
    N=N_AGENTS,
    noise=NOISE_LIST,
    sigma=SIGMA_LIST,
    trait_families=string.(TRAIT_FAMILIES),
    trait_replicates=N_TRAIT_REPS,
    dynamic_replicates=N_DYNAMIC_REPS,
    total=N_TOTAL,
    warmup=N_WARMUP,
    diagnostic_blocks=N_BLOCKS,
    smoke=SMOKE,
    neighbor_search="exact",
    update_mode="sequential",
    shard_index=SHARD.index,
    shard_count=SHARD.count,
    full_condition_count=length(all_base_conditions),
    shard_condition_count=length(base_conditions),
    full_run_count=length(all_base_conditions) * length(TRAIT_FAMILIES) * N_TRAIT_REPS * N_DYNAMIC_REPS,
    shard_run_count=length(jobs),
    seed_design="quantile matched: trait=310000+trait_rep; init=320000+dynamic_rep; dynamic=330000+dynamic_rep")

summary = combine(groupby(raw, [:sigma_std, :noise, :trait_distribution])) do sub
    (
        phi_mean=mean(sub.phi),
        phi_sd=std(sub.phi),
        real_mean=mean(sub.real_mean),
        real_std=mean(sub.real_std),
        frac_lo=mean(sub.frac_lo),
        frac_hi=mean(sub.frac_hi),
        tau_int_median=median(sub.tau_int),
        ess_min=minimum(sub.ess),
        late_quarter_drift_max=maximum(sub.late_quarter_drift),
        n=nrow(sub),
    )
end
sort!(summary, [:noise, :sigma_std, :trait_distribution])
CSV.write(joinpath(OUTDIR, "distribution_condition_means.csv"), summary)

keys = [:sigma_std, :noise, :trait_rep, :dynamic_rep]
beta = select(raw[raw.trait_distribution .== "beta", :], keys..., :phi => :phi_beta)
point = select(raw[raw.trait_distribution .== "two_point", :], keys..., :phi => :phi_two_point)
pairs = innerjoin(beta, point, on=keys)
pairs.delta_phi = pairs.phi_two_point .- pairs.phi_beta
CSV.write(joinpath(OUTDIR, "paired_distribution_effects.csv"), pairs)

pair_summary = combine(groupby(pairs, [:sigma_std, :noise])) do sub
    (
        delta_phi_mean=mean(sub.delta_phi),
        delta_phi_sd=std(sub.delta_phi),
        delta_phi_min=minimum(sub.delta_phi),
        delta_phi_max=maximum(sub.delta_phi),
        n=nrow(sub),
    )
end
sort!(pair_summary, [:noise, :sigma_std])
CSV.write(joinpath(OUTDIR, "paired_distribution_summary.csv"), pair_summary)

println("\nTwo-point minus Beta paired effects:")
for row in eachrow(pair_summary)
    @printf("  eta=%.1f sigma=%.2f delta_phi=%+.4f +/- %.4f\n",
        row.noise, row.sigma_std, row.delta_phi_mean, row.delta_phi_sd)
end
println("\n  wrote distribution-control tables in $OUTDIR")
