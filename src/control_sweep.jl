# control_sweep.jl
# Matched controls for two implementation choices that can materially change the
# scientific interpretation: neighbour search and update convention.
# The same trait, initial-state and dynamic random seeds are reused across controls.
# Large grids can be split by complete (sigma, noise) base conditions.
# Run: julia --project=. --threads=auto src/control_sweep.jl

include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
include(joinpath(@__DIR__, "diagnostics.jl"))
include(joinpath(@__DIR__, "run_metadata.jl"))
include(joinpath(@__DIR__, "sharding.jl"))
using Statistics, DataFrames, CSV, Printf

const SMOKE = get(ENV, "ABM_SMOKE", "0") == "1"
const SIGMA_MEAN = 0.7
const SIGMA_LIST = SMOKE ? [0.0, 0.3] : [0.0, 0.15, 0.30, 0.45]
const NOISE_LIST = SMOKE ? [0.5] : [0.3, 0.5, 0.7]
const SEARCH_MODES = [:exact, :approximate]
const UPDATE_MODES = [:sequential, :synchronous]
const N_AGENTS = SMOKE ? 12 : 200
const N_TRAIT_REPS = SMOKE ? 2 : 4
const N_DYNAMIC_REPS = SMOKE ? 1 : 3
const N_TOTAL = SMOKE ? 160 : 60000
const N_WARMUP = SMOKE ? 80 : 30000
const N_BLOCKS = SMOKE ? 4 : 8
const SHARD = shard_spec()
const BASE_OUTDIR = get(ENV, "ABM_OUTPUT_DIR",
    joinpath(@__DIR__, "..", "results", SMOKE ? "smoke_controls" : "algorithmic_controls"))
const OUTDIR = shard_dir(BASE_OUTDIR, SHARD)

trait_seed(rep) = 210_000 + rep
init_seed(rep) = 220_000 + rep
dynamic_seed(rep) = 230_000 + rep

function run_control(; sigma_std, noise, search_mode, update_mode, trait_rep, dynamic_rep)
    ts = trait_seed(trait_rep)
    is = init_seed(dynamic_rep)
    ds = dynamic_seed(dynamic_rep)
    model, sv = create_sheep_model(; N=N_AGENTS, noise=noise,
        σ_mean=SIGMA_MEAN, σ_std=sigma_std, seed=0,
        trait_seed=ts, init_seed=is, dynamic_seed=ds,
        neighbor_search=search_mode, update_mode=update_mode)
    for _ in 1:N_TOTAL
        step!(model)
    end
    meas = model.order_history[(N_WARMUP + 1):end]
    diag = stationarity_diagnostics(meas; nblocks=N_BLOCKS)
    return (
        sigma_std=sigma_std,
        noise=noise,
        search_mode=string(search_mode),
        update_mode=string(update_mode),
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
    )
end

all_base_conditions = [(s, e) for s in SIGMA_LIST for e in NOISE_LIST]
base_conditions = select_shard(all_base_conditions, SHARD)
jobs = [(s, e, search, update, tr, dr)
        for (s, e) in base_conditions
        for search in SEARCH_MODES for update in UPDATE_MODES
        for tr in 1:N_TRAIT_REPS for dr in 1:N_DYNAMIC_REPS]
res = Vector{Any}(undef, length(jobs))
println("controls: $(length(jobs)) matched runs × $N_TOTAL steps")
println("search=$(SEARCH_MODES), update=$(UPDATE_MODES)")
println("shard $(SHARD.index)/$(SHARD.count): $(length(base_conditions))/$(length(all_base_conditions)) base conditions")

done = Threads.Atomic{Int}(0)
Threads.@threads :dynamic for i in eachindex(jobs)
    s, e, search, update, tr, dr = jobs[i]
    res[i] = run_control(; sigma_std=s, noise=e, search_mode=search,
        update_mode=update, trait_rep=tr, dynamic_rep=dr)
    d = Threads.atomic_add!(done, 1) + 1
    (d % 25 == 0 || d == length(jobs)) && println("  $d / $(length(jobs))")
end

mkpath(OUTDIR)
raw = DataFrame(res)
CSV.write(joinpath(OUTDIR, "control_replicates.csv"), raw)
write_run_metadata(OUTDIR;
    experiment="algorithmic_controls",
    N=N_AGENTS,
    noise=NOISE_LIST,
    sigma=SIGMA_LIST,
    search_modes=string.(SEARCH_MODES),
    update_modes=string.(UPDATE_MODES),
    trait_replicates=N_TRAIT_REPS,
    dynamic_replicates=N_DYNAMIC_REPS,
    total=N_TOTAL,
    warmup=N_WARMUP,
    diagnostic_blocks=N_BLOCKS,
    smoke=SMOKE,
    shard_index=SHARD.index,
    shard_count=SHARD.count,
    full_condition_count=length(all_base_conditions),
    shard_condition_count=length(base_conditions),
    full_run_count=length(all_base_conditions) * length(SEARCH_MODES) * length(UPDATE_MODES) * N_TRAIT_REPS * N_DYNAMIC_REPS,
    shard_run_count=length(jobs),
    seed_design="matched across controls: trait=210000+trait_rep; init=220000+dynamic_rep; dynamic=230000+dynamic_rep")

summary = combine(groupby(raw, [:sigma_std, :noise, :search_mode, :update_mode])) do sub
    (
        phi_mean=mean(sub.phi),
        phi_sd=std(sub.phi),
        tempvar=mean(sub.phi_tempvar),
        tau_int_median=median(sub.tau_int),
        ess_min=minimum(sub.ess),
        late_quarter_drift_max=maximum(sub.late_quarter_drift),
        n=nrow(sub),
    )
end
sort!(summary, [:noise, :sigma_std, :search_mode, :update_mode])
CSV.write(joinpath(OUTDIR, "control_condition_means.csv"), summary)

# Paired effects are calculated at the realization level so algorithmic controls
# are not compared using unrelated random initial conditions.
exact_seq = raw[(raw.search_mode .== "exact") .& (raw.update_mode .== "sequential"), :]
function paired_effect(reference, alternative, label)
    keys = [:sigma_std, :noise, :trait_rep, :dynamic_rep]
    alt = select(alternative, keys..., :phi => :phi_alt)
    pair = innerjoin(select(reference, keys..., :phi => :phi_ref), alt, on=keys)
    pair.delta_phi = pair.phi_alt .- pair.phi_ref
    pair.control = fill(label, nrow(pair))
    return pair
end

approx_seq = raw[(raw.search_mode .== "approximate") .& (raw.update_mode .== "sequential"), :]
exact_sync = raw[(raw.search_mode .== "exact") .& (raw.update_mode .== "synchronous"), :]
pairs = vcat(
    paired_effect(exact_seq, approx_seq, "approximate_minus_exact"),
    paired_effect(exact_seq, exact_sync, "synchronous_minus_sequential"),
)
CSV.write(joinpath(OUTDIR, "paired_control_effects.csv"), pairs)

pair_summary = combine(groupby(pairs, [:sigma_std, :noise, :control])) do sub
    (
        delta_phi_mean=mean(sub.delta_phi),
        delta_phi_sd=std(sub.delta_phi),
        delta_phi_min=minimum(sub.delta_phi),
        delta_phi_max=maximum(sub.delta_phi),
        n=nrow(sub),
    )
end
sort!(pair_summary, [:control, :noise, :sigma_std])
CSV.write(joinpath(OUTDIR, "paired_control_summary.csv"), pair_summary)

println("\npaired algorithmic effects relative to exact sequential baseline:")
for row in eachrow(pair_summary)
    @printf("  %-31s eta=%.1f sigma=%.2f delta_phi=%+.4f +/- %.4f\n",
        row.control, row.noise, row.sigma_std, row.delta_phi_mean, row.delta_phi_sd)
end
println("\n  wrote control tables in $OUTDIR")
