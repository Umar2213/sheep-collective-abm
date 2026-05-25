# ============================================================
# heterogeneous_model_v2.jl
#
# IMPROVED VERSION — fixes the confound and adds replication.
#
# CHANGES from heterogeneous_model.jl:
#
# 1. BETA DISTRIBUTION instead of truncated Normal.
#    The Beta distribution naturally lives in [0, 1] — no clipping,
#    no distortion of the mean. We can set mean and variance independently.
#    Given desired mean μ and variance v, the parameters are:
#       α = μ × (μ(1−μ)/v − 1)
#       β = (1−μ) × (μ(1−μ)/v − 1)
#    (Constraint: v must be < μ(1−μ), the maximum possible variance
#    of a distribution on [0,1] with mean μ.)
#
# 2. MULTIPLE SEEDS per condition (default 15).
#    Each random seed = one possible "world". One world tells us nothing.
#    Running many worlds and reporting mean ± standard deviation tells us
#    whether an effect is real signal or just noise. This is how we get
#    statistical evidence that a referee will accept.
#
# RUNTIME: with 6 conditions × 15 seeds = 90 runs, expect ~10–20 minutes.
# ============================================================

using Agents
using Distributions
using Statistics
using Random
using DataFrames
using CSV


# ─────────────────────────────────────────────────────────────
# 1. AGENT TYPE  (unchanged)
# ─────────────────────────────────────────────────────────────

@agent struct SheepAgent(ContinuousAgent{2, Float64})
    θ             :: Float64
    social_weight :: Float64
end


# ─────────────────────────────────────────────────────────────
# 2. MODEL PROPERTIES  (unchanged)
# ─────────────────────────────────────────────────────────────

Base.@kwdef mutable struct SheepProps
    speed         :: Float64         = 0.03
    noise         :: Float64         = 0.5
    radius        :: Float64         = 1.0
    dt            :: Float64         = 1.0
    σ_mean        :: Float64         = 0.7
    σ_std         :: Float64         = 0.1
    order_history :: Vector{Float64} = Float64[]
end


# ─────────────────────────────────────────────────────────────
# 3. AGENT STEP  (unchanged from v1)
# ─────────────────────────────────────────────────────────────

function sheep_agent_step!(agent::SheepAgent, model)
    neighbours = collect(nearby_agents(agent, model, model.radius))
    σ = agent.social_weight

    if isempty(neighbours)
        avg_θ = agent.θ
    else
        nb_θ   = [a.θ for a in neighbours]
        nb_sin = mean(sin.(nb_θ))
        nb_cos = mean(cos.(nb_θ))
        blend_sin = σ * nb_sin + (1.0 - σ) * sin(agent.θ)
        blend_cos = σ * nb_cos + (1.0 - σ) * cos(agent.θ)
        avg_θ = atan(blend_sin, blend_cos)
    end

    noise_term = model.noise * (rand(abmrng(model)) - 0.5)
    new_θ      = avg_θ + noise_term

    agent.θ   = new_θ
    agent.vel = (model.speed * cos(new_θ), model.speed * sin(new_θ))
    move_agent!(agent, model, model.dt)
end


# ─────────────────────────────────────────────────────────────
# 4. MODEL STEP  (unchanged)
# ─────────────────────────────────────────────────────────────

function sheep_model_step!(model)
    N = nagents(model)
    N == 0 && return
    vx_mean = mean(a.vel[1] for a in allagents(model))
    vy_mean = mean(a.vel[2] for a in allagents(model))
    φ = sqrt(vx_mean^2 + vy_mean^2) / model.speed
    push!(model.order_history, φ)
end


# ─────────────────────────────────────────────────────────────
# 5. NEW: Beta distribution from desired mean and std
# ─────────────────────────────────────────────────────────────

function beta_from_mean_std(μ::Float64, s::Float64)
    v = s^2
    if v <= 0.0
        return nothing       # caller treats this as "homogeneous"
    end
    max_v = μ * (1 - μ)
    if v >= max_v
        error("Requested variance $(round(v;digits=4)) exceeds max " *
              "possible $(round(max_v;digits=4)) for mean $(μ).")
    end
    common = μ * (1 - μ) / v - 1
    α = μ       * common
    β = (1 - μ) * common
    return Beta(α, β)
end


# ─────────────────────────────────────────────────────────────
# 6. CREATE THE MODEL  (now uses Beta)
# ─────────────────────────────────────────────────────────────

function create_sheep_model(; N=200, L=20.0, speed=0.03, noise=0.5,
                            radius=1.0, dt=1.0,
                            σ_mean=0.7, σ_std=0.1, seed=42)
    space = ContinuousSpace((L, L); periodic = true)
    props = SheepProps(speed=speed, noise=noise, radius=radius,
                       dt=dt, σ_mean=σ_mean, σ_std=σ_std)
    model = StandardABM(
        SheepAgent, space;
        properties  = props,
        agent_step! = sheep_agent_step!,
        model_step! = sheep_model_step!,
        rng         = MersenneTwister(seed)
    )

    σ_dist   = beta_from_mean_std(σ_mean, σ_std)
    σ_values = Float64[]

    for _ in 1:N
        θ_init = rand(abmrng(model)) * 2π
        σ_i    = σ_dist === nothing ? σ_mean : rand(abmrng(model), σ_dist)
        push!(σ_values, σ_i)
        add_agent!(model;
            vel           = (speed*cos(θ_init), speed*sin(θ_init)),
            θ             = θ_init,
            social_weight = σ_i
        )
    end

    return model, σ_values
end


# ─────────────────────────────────────────────────────────────
# 7. RUN ONE SEED → return summary stats
# ─────────────────────────────────────────────────────────────

function run_single_seed(; σ_mean, σ_std, seed, n_steps=500, N=200,
                         L=20.0, speed=0.03, noise=0.5, radius=1.0)
    model, σ_values = create_sheep_model(;
        N=N, L=L, speed=speed, noise=noise, radius=radius,
        σ_mean=σ_mean, σ_std=σ_std, seed=seed
    )
    for _ in 1:n_steps
        step!(model)
    end
    return (
        φ_steady      = mean(model.order_history[end-99:end]),
        actual_σ_mean = mean(σ_values),
        actual_σ_std  = std(σ_values),
    )
end


# ─────────────────────────────────────────────────────────────
# 8. RUN ONE CONDITION (multiple seeds)
# ─────────────────────────────────────────────────────────────

function run_condition(; σ_mean, σ_std, n_seeds=15, n_steps=500)
    φ_values   = Float64[]
    σmean_vals = Float64[]
    σstd_vals  = Float64[]

    print("  σ_std=$(rpad(σ_std,5)) : ")
    for seed in 1:n_seeds
        r = run_single_seed(; σ_mean=σ_mean, σ_std=σ_std,
                            seed=seed, n_steps=n_steps)
        push!(φ_values,   r.φ_steady)
        push!(σmean_vals, r.actual_σ_mean)
        push!(σstd_vals,  r.actual_σ_std)
        print(".")
    end
    println(" done")
    println("       φ        = $(round(mean(φ_values);   digits=4)) ± $(round(std(φ_values);   digits=4))")
    println("       actual σ̄ = $(round(mean(σmean_vals); digits=4)) ± $(round(std(σmean_vals); digits=4))")
    println("       actual s  = $(round(mean(σstd_vals);  digits=4)) ± $(round(std(σstd_vals);  digits=4))")
    return (φ_values, σmean_vals, σstd_vals)
end


# ─────────────────────────────────────────────────────────────
# 9. THE FULL EXPERIMENT
# ─────────────────────────────────────────────────────────────

function run_experiment(; σ_mean=0.7,
                        σ_std_list=[0.0, 0.05, 0.10, 0.15, 0.20, 0.25],
                        n_seeds=15, n_steps=500,
                        output_dir="/home/umar/sheep_collective/results")

    println("=" ^ 64)
    println("  EXPERIMENT 1 — effect of σ_std on flock cohesion φ")
    println()
    println("  Fixed:    σ_mean = $(σ_mean),  noise = 0.5,  N = 200")
    println("  Varying:  σ_std  = $(σ_std_list)")
    println("  Per cond: $(n_seeds) seeds, $(n_steps) steps each")
    println()
    println("  Beta distribution → no truncation, mean is preserved exactly.")
    println("=" ^ 64)
    println()

    raw = DataFrame(
        σ_mean        = Float64[],
        σ_std_input   = Float64[],
        seed          = Int[],
        actual_σ_mean = Float64[],
        actual_σ_std  = Float64[],
        φ_steady      = Float64[],
    )

    summary = DataFrame(
        σ_std_input  = Float64[],
        φ_mean       = Float64[],
        φ_sd         = Float64[],
        n            = Int[],
    )

    for σ_std in σ_std_list
        φ_vals, σm_vals, σs_vals =
            run_condition(; σ_mean=σ_mean, σ_std=σ_std,
                          n_seeds=n_seeds, n_steps=n_steps)
        for k in 1:n_seeds
            push!(raw, (
                σ_mean=σ_mean, σ_std_input=σ_std, seed=k,
                actual_σ_mean=σm_vals[k], actual_σ_std=σs_vals[k],
                φ_steady=φ_vals[k]
            ))
        end
        push!(summary, (
            σ_std_input = σ_std,
            φ_mean      = mean(φ_vals),
            φ_sd        = std(φ_vals),
            n           = n_seeds,
        ))
        println()
    end

    mkpath(output_dir)
    CSV.write(joinpath(output_dir, "experiment1_rawdata.csv"), raw)
    CSV.write(joinpath(output_dir, "experiment1_means.csv"),    summary)

    println("=" ^ 64)
    println("  RESULTS TABLE (φ = mean ± SD across $(n_seeds) seeds):")
    println("=" ^ 64)
    for row in eachrow(summary)
        bar = repeat("█", round(Int, row.φ_mean * 40))
        println("  σ_std=$(rpad(row.σ_std_input,5))  φ = $(rpad(round(row.φ_mean;digits=3),5)) ± $(rpad(round(row.φ_sd;digits=3),5))  $(bar)")
    end
    println("=" ^ 64)
    println("  Files saved to /home/umar/sheep_collective/results/:")
    println("    experiment1_rawdata.csv  (one row per seed × condition)")
    println("    experiment1_means.csv    (one row per condition)")
    println("=" ^ 64)

    return raw, summary
end


# ─────────────────────────────────────────────────────────────
# 10. RUN IT
# ─────────────────────────────────────────────────────────────

run_experiment(
    σ_mean      = 0.7,
    σ_std_list  = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25],
    n_seeds     = 15,
    n_steps     = 500,
)
