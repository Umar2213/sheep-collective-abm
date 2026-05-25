# ============================================================
# heterogeneous_model.jl
#
# Extension of the Vicsek model with individual personality.
#
# THE NOVEL CONTRIBUTION:
#   Each sheep has its own "social weight" σ_i (sigma).
#   σ_i controls how strongly that sheep follows its neighbours:
#     σ_i = 1.0  →  fully copies neighbour direction (maximally social)
#     σ_i = 0.0  →  ignores all neighbours (fully independent)
#
# THE SCIENTIFIC QUESTION WE ARE ANSWERING:
#   If we hold the MEAN social weight constant but vary the VARIANCE,
#   does flock-level cohesion (φ) change?
#
#   Condition 1 — Homogeneous:    all sheep have exactly σ = 0.7
#   Condition 2 — Low variance:   σ ~ Normal(mean=0.7, std=0.1)
#   Condition 3 — High variance:  σ ~ Normal(mean=0.7, std=0.3)
#
#   Same average personality. Different spread. Different outcomes?
#   Nobody has answered this systematically for sheep. This is the paper.
#
# HOW σ IS ASSIGNED AT BIRTH:
#   σ_i ~ TruncatedNormal(μ_σ, s_σ, low=0, high=1)
#   TruncatedNormal is just Normal but clipped so values stay in [0,1]
#   μ_σ = mean social weight   (we hold this fixed)
#   s_σ = standard deviation   (THIS is our main variable)
# ============================================================

using Agents
using Distributions    # for Normal(), truncated()
using Statistics       # for mean(), std()
using Random           # for MersenneTwister
using DataFrames
using CSV


# ─────────────────────────────────────────────────────────────
# 1. AGENT TYPE
# ─────────────────────────────────────────────────────────────
# Compared to VicsekAgent in vicsek_baseline.jl, we add ONE new field:
#   social_weight :: Float64  — this sheep's personality (σ_i)
# This value is assigned at birth and never changes during the simulation.

@agent struct SheepAgent(ContinuousAgent{2, Float64})
    θ             :: Float64    # heading direction in radians
    social_weight :: Float64    # σ_i: personality trait (0=independent, 1=social)
end


# ─────────────────────────────────────────────────────────────
# 2. MODEL PROPERTIES
# ─────────────────────────────────────────────────────────────

Base.@kwdef mutable struct SheepProps
    speed         :: Float64         = 0.03   # movement speed
    noise         :: Float64         = 0.5    # η: random noise added each step
    radius        :: Float64         = 1.0    # interaction radius r
    dt            :: Float64         = 1.0    # time step
    σ_mean        :: Float64         = 0.7    # mean social weight of the population
    σ_std         :: Float64         = 0.1    # std dev of social weight (0 = all identical)
    order_history :: Vector{Float64} = Float64[]   # φ recorded at each step
end


# ─────────────────────────────────────────────────────────────
# 3. THE MODIFIED UPDATE RULE  ← this is where the science lives
# ─────────────────────────────────────────────────────────────
# KEY DIFFERENCE from vicsek_baseline.jl:
#
# In the Vicsek baseline, every agent gives equal weight to all neighbours.
# Here, each agent has its own σ_i that sets how much it "listens" to neighbours
# versus sticking to its own current heading.
#
# BLENDING FORMULA:
#   blend = σ_i × (neighbour average direction)
#         + (1 - σ_i) × (own current direction)
#
# When σ_i = 1.0: blend = neighbour average  → same as original Vicsek
# When σ_i = 0.0: blend = own direction      → ignores everyone else
# When σ_i = 0.5: halfway between the two

function sheep_agent_step!(agent::SheepAgent, model)

    neighbours = collect(nearby_agents(agent, model, model.radius))
    σ = agent.social_weight    # read this sheep's personality

    if isempty(neighbours)
        # No-one nearby: keep own heading (just add noise below)
        avg_θ = agent.θ
    else
        # Circular mean of neighbour headings
        nb_θ   = [a.θ for a in neighbours]
        nb_sin = mean(sin.(nb_θ))
        nb_cos = mean(cos.(nb_θ))

        # Blend: σ from neighbours, (1-σ) from self
        blend_sin = σ * nb_sin + (1.0 - σ) * sin(agent.θ)
        blend_cos = σ * nb_cos + (1.0 - σ) * cos(agent.θ)

        # Recover angle from blended sin/cos (handles wrap-around correctly)
        avg_θ = atan(blend_sin, blend_cos)
    end

    # Add random noise (same for all sheep — personality is in σ, not noise)
    noise_term = model.noise * (rand(abmrng(model)) - 0.5)
    new_θ      = avg_θ + noise_term

    # Update agent state
    agent.θ   = new_θ
    agent.vel = (model.speed * cos(new_θ), model.speed * sin(new_θ))
    move_agent!(agent, model, model.dt)
end


# ─────────────────────────────────────────────────────────────
# 4. MODEL STEP — record order parameter (same as baseline)
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
# 5. CREATE THE MODEL AND ASSIGN PERSONALITIES
# ─────────────────────────────────────────────────────────────

function create_sheep_model(;
    N      :: Int     = 200,
    L      :: Float64 = 20.0,
    speed  :: Float64 = 0.03,
    noise  :: Float64 = 0.5,
    radius :: Float64 = 1.0,
    dt     :: Float64 = 1.0,
    σ_mean :: Float64 = 0.7,
    σ_std  :: Float64 = 0.1,
    seed   :: Int     = 42
)
    space = ContinuousSpace((L, L); periodic = true)

    props = SheepProps(
        speed  = speed,
        noise  = noise,
        radius = radius,
        dt     = dt,
        σ_mean = σ_mean,
        σ_std  = σ_std
    )

    model = StandardABM(
        SheepAgent, space;
        properties  = props,
        agent_step! = sheep_agent_step!,
        model_step! = sheep_model_step!,
        rng         = MersenneTwister(seed)
    )

    # Build the personality distribution
    # truncated(Normal(μ, σ), 0, 1) clips values to stay inside [0, 1]
    # When σ_std = 0 we skip the distribution and assign σ_mean directly
    use_dist = σ_std > 0.0
    σ_dist   = use_dist ? truncated(Normal(σ_mean, σ_std), 0.0, 1.0) : nothing

    σ_values = Float64[]    # collect for reporting

    for _ in 1:N
        θ_init = rand(abmrng(model)) * 2π

        # Draw personality from distribution (or use fixed value if homogeneous)
        σ_i = use_dist ? rand(abmrng(model), σ_dist) : σ_mean
        push!(σ_values, σ_i)

        add_agent!(
            model;
            vel           = (speed * cos(θ_init), speed * sin(θ_init)),
            θ             = θ_init,
            social_weight = σ_i
        )
    end

    # Print a summary of the personality distribution we just created
    println("    Personality summary across $(N) sheep:")
    println("      mean σ = $(round(mean(σ_values); digits=3))")
    println("      std  σ = $(round(std(σ_values);  digits=3))")
    println("      min  σ = $(round(minimum(σ_values); digits=3))")
    println("      max  σ = $(round(maximum(σ_values); digits=3))")

    return model
end


# ─────────────────────────────────────────────────────────────
# 6. RUN THE MODEL AND SAVE RESULTS
# ─────────────────────────────────────────────────────────────

function run_sheep_model(;
    n_steps    :: Int     = 500,
    N          :: Int     = 200,
    L          :: Float64 = 20.0,
    speed      :: Float64 = 0.03,
    noise      :: Float64 = 0.5,
    radius     :: Float64 = 1.0,
    σ_mean     :: Float64 = 0.7,
    σ_std      :: Float64 = 0.1,
    output_dir :: String  = "/home/umar/sheep_collective/results",
    seed       :: Int     = 42
)
    label = σ_std == 0.0 ? "homogeneous (all σ=$(σ_mean))" :
                            "σ ~ Normal($(σ_mean), $(σ_std))"
    println("  Condition: $(label)")

    model = create_sheep_model(;
        N=N, L=L, speed=speed, noise=noise, radius=radius,
        σ_mean=σ_mean, σ_std=σ_std, seed=seed
    )

    println("    Running $(n_steps) steps...")
    for t in 1:n_steps
        step!(model)
        if t % 100 == 0
            φ = model.order_history[end]
            println("      t=$(lpad(t,4))   φ = $(round(φ; digits=4))")
        end
    end

    # Summarise the LAST 100 steps (once the model has settled)
    φ_steady = round(mean(model.order_history[end-99:end]); digits=4)
    println("    Mean φ over last 100 steps = $(φ_steady)")

    # Save full time series to CSV
    mkpath(output_dir)
    fname = joinpath(output_dir,
        "sheep_sigmean$(σ_mean)_sigstd$(σ_std)_noise$(noise).csv")
    CSV.write(fname, DataFrame(
        step            = 1:n_steps,
        order_parameter = model.order_history
    ))
    println("    Saved → $(fname)\n")

    return model, φ_steady
end


# ─────────────────────────────────────────────────────────────
# 7. RUN THE THREE CONDITIONS AND COMPARE
# ─────────────────────────────────────────────────────────────

println("=" ^ 62)
println("  HETEROGENEOUS SHEEP MODEL — CORE EXPERIMENT")
println()
println("  Fixed:   N=200, noise=0.5, σ_mean=0.7")
println("  Varying: σ_std (spread of personality distribution)")
println()
println("  Prediction: unknown. That is the point of the experiment.")
println("=" ^ 62)

println("\n[Condition 1] HOMOGENEOUS — all sheep identical, σ = 0.7")
_, φ1 = run_sheep_model(σ_mean=0.7, σ_std=0.0, n_steps=500)

println("[Condition 2] LOW VARIANCE — σ ~ Normal(0.7, 0.1)")
_, φ2 = run_sheep_model(σ_mean=0.7, σ_std=0.1, n_steps=500)

println("[Condition 3] HIGH VARIANCE — σ ~ Normal(0.7, 0.3)")
_, φ3 = run_sheep_model(σ_mean=0.7, σ_std=0.3, n_steps=500)

println("=" ^ 62)
println("  SUMMARY (mean φ over last 100 steps):")
println("  Condition 1 — Homogeneous:    φ = $(φ1)")
println("  Condition 2 — Low variance:   φ = $(φ2)")
println("  Condition 3 — High variance:  φ = $(φ3)")
println()
println("  Interpretation:")
if φ1 ≈ φ2 ≈ φ3
    println("  → Variance does NOT affect cohesion at this noise level.")
elseif φ3 < φ1
    println("  → Higher variance REDUCES cohesion.")
    println("    Independent sheep disrupt flock alignment.")
elseif φ3 > φ1
    println("  → Higher variance INCREASES cohesion.")
    println("    Highly social sheep pull others into alignment.")
else
    println("  → Mixed result. Run more noise levels to see the pattern.")
end
println("=" ^ 62)
