# ============================================================
# vicsek_baseline.jl
#
# A "vanilla" Vicsek flocking model — our sanity-check baseline.
# Reference: Vicsek et al. (1995), Phys. Rev. Lett. 75(6):1226
#
# THE RULES (plain English):
#   - N agents move at constant speed in a 2D box
#   - Each agent looks at all neighbours within radius r
#   - It turns toward the AVERAGE direction of those neighbours
#   - A small random angle (noise η) is added to break perfect alignment
#
# THE KEY OBSERVABLE — Order Parameter φ (phi):
#   φ ≈ 1  →  all agents pointing the same way  (ordered flock)
#   φ ≈ 0  →  agents pointing in random ways     (disordered)
#
# SANITY CHECK: if we run with LOW noise, φ should rise toward 1.
#               If we run with HIGH noise, φ should stay near 0.
#               If that happens, the model is working correctly.
#
# WHY THIS IS OUR BASELINE:
#   All agents are IDENTICAL — no personality differences.
#   Phase 2 of our project will add individual variation on top of this.
# ============================================================

using Agents        # the agent-based modelling framework
using Statistics    # for mean()
using Random        # for MersenneTwister (reproducible random numbers)
using DataFrames    # for tidy result tables
using CSV           # for saving results to disk


# ─────────────────────────────────────────────────────────────
# 1. DEFINE THE AGENT TYPE
# ─────────────────────────────────────────────────────────────
# ContinuousAgent{2, Float64} is a built-in Agents.jl type.
# It automatically gives every agent:
#   id  :: Int                — unique integer ID (auto-assigned)
#   pos :: NTuple{2,Float64}  — (x, y) position in the 2D box
#   vel :: NTuple{2,Float64}  — (vx, vy) velocity vector
#
# We add ONE extra field of our own:
#   θ :: Float64  — the direction this agent is heading (radians, 0 to 2π)

@agent struct VicsekAgent(ContinuousAgent{2, Float64})
    θ :: Float64    # heading direction in radians
end


# ─────────────────────────────────────────────────────────────
# 2. MODEL PROPERTIES (the "knobs" we turn in experiments)
# ─────────────────────────────────────────────────────────────
# Storing parameters in a struct lets us access them cleanly as
# model.speed, model.noise, etc. inside the step functions.
# "mutable" is needed so we can append to order_history each step.

Base.@kwdef mutable struct VicsekProps
    speed         :: Float64         = 0.03    # v: movement speed per time step
    noise         :: Float64         = 0.5     # η: random angle range added each step
    radius        :: Float64         = 1.0     # r: how far each agent can "see"
    dt            :: Float64         = 1.0     # time step (1 = standard Vicsek)
    order_history :: Vector{Float64} = Float64[]  # φ recorded at every step
end


# ─────────────────────────────────────────────────────────────
# 3. AGENT STEP: the Vicsek update rule
#    Called once per agent per time step.
# ─────────────────────────────────────────────────────────────
function vicsek_agent_step!(agent::VicsekAgent, model)

    # --- find neighbours within interaction radius ---
    # nearby_agents() returns all OTHER agents within model.radius.
    # We collect them into a plain array so we can iterate twice if needed.
    neighbours = collect(nearby_agents(agent, model, model.radius))

    # Build a list of ALL angles to average: neighbours + self.
    # Including self is what Vicsek 1995 specifies.
    all_angles = [a.θ for a in neighbours]
    push!(all_angles, agent.θ)

    # --- circular mean of angles ---
    # WHY NOT just mean(all_angles)?
    # Angles wrap around at 2π. The naive mean of 350° and 10° gives 180°,
    # which is WRONG — the correct answer is 0°.
    # Fix: average sin and cos separately, then recover the angle with atan().
    avg_sin = mean(sin.(all_angles))
    avg_cos = mean(cos.(all_angles))
    avg_θ   = atan(avg_sin, avg_cos)    # result is in the range (-π, π)

    # --- add random noise ---
    # rand(abmrng(model)) returns a uniform number in [0, 1).
    # Shifting by -0.5 centres it at zero: range becomes [-0.5, 0.5).
    # Multiplying by noise (η) gives a random angle in [-η/2, η/2).
    noise_term = model.noise * (rand(abmrng(model)) - 0.5)
    new_θ      = avg_θ + noise_term

    # --- update this agent's heading and velocity ---
    agent.θ   = new_θ
    agent.vel = (model.speed * cos(new_θ),    # vx
                 model.speed * sin(new_θ))    # vy

    # --- move the agent ---
    # Agents.jl built-in: new_pos = old_pos + vel × dt
    # If the new position is outside the box, it wraps around (periodic boundary).
    move_agent!(agent, model, model.dt)
end


# ─────────────────────────────────────────────────────────────
# 4. MODEL STEP: runs AFTER all agents have stepped
#    We use this to compute and record the order parameter φ.
# ─────────────────────────────────────────────────────────────
function vicsek_model_step!(model)
    N = nagents(model)
    N == 0 && return    # nothing to do if the model is empty

    # φ = magnitude of mean velocity, divided by speed
    # If everyone moves in the same direction: mean velocity ≈ speed  →  φ ≈ 1
    # If directions cancel out:               mean velocity ≈ 0       →  φ ≈ 0
    vx_mean = mean(a.vel[1] for a in allagents(model))
    vy_mean = mean(a.vel[2] for a in allagents(model))
    φ       = sqrt(vx_mean^2 + vy_mean^2) / model.speed

    # Append to the running record stored in model properties
    push!(model.order_history, φ)
end


# ─────────────────────────────────────────────────────────────
# 5. CREATE (INITIALISE) THE MODEL
# ─────────────────────────────────────────────────────────────
function create_vicsek_model(;
    N      :: Int     = 200,     # number of agents
    L      :: Float64 = 20.0,    # box side length → density ρ = N / L²
    speed  :: Float64 = 0.03,    # Vicsek 1995 used v = 0.03
    noise  :: Float64 = 0.5,     # η: the main parameter we will vary
    radius :: Float64 = 1.0,     # r: interaction radius (= 1 in Vicsek 1995)
    dt     :: Float64 = 1.0,
    seed   :: Int     = 42       # fix seed → same initial conditions every run
)
    # 2D continuous box, size L × L, with wrap-around edges
    space = ContinuousSpace((L, L); periodic = true)

    props = VicsekProps(
        speed  = speed,
        noise  = noise,
        radius = radius,
        dt     = dt
    )

    model = StandardABM(
        VicsekAgent,          # what type of agents live in this model
        space;                # the space they live in
        properties  = props,
        agent_step! = vicsek_agent_step!,
        model_step! = vicsek_model_step!,
        rng         = MersenneTwister(seed)   # seeded RNG for reproducibility
    )

    # Place N agents at random positions with random initial headings
    for _ in 1:N
        θ_init = rand(abmrng(model)) * 2π        # random angle in [0, 2π)
        add_agent!(
            model;
            vel = (speed * cos(θ_init), speed * sin(θ_init)),
            θ   = θ_init
        )
    end

    return model
end


# ─────────────────────────────────────────────────────────────
# 6. RUN THE MODEL AND SAVE RESULTS
# ─────────────────────────────────────────────────────────────
function run_vicsek(;
    n_steps    :: Int     = 500,
    N          :: Int     = 200,
    L          :: Float64 = 20.0,
    speed      :: Float64 = 0.03,
    noise      :: Float64 = 0.5,
    radius     :: Float64 = 1.0,
    output_dir :: String  = "/home/umar/sheep_collective/results",
    seed       :: Int     = 42
)
    println("─────────────────────────────────────────────────────")
    println("N=$(N) agents | box=$(L)×$(L) | η=$(noise) | v=$(speed) | r=$(radius)")

    model = create_vicsek_model(;
        N = N, L = L, speed = speed, noise = noise,
        radius = radius, dt = 1.0, seed = seed
    )

    println("Running $(n_steps) steps...")
    for t in 1:n_steps
        step!(model)                          # one full time step
        if t % 100 == 0
            φ = model.order_history[end]
            println("  t = $(lpad(t, 4))   φ = $(round(φ; digits = 4))")
        end
    end

    φ_final = round(model.order_history[end]; digits = 4)
    println("Finished.  φ_final = $(φ_final)  (1 = perfect flock, 0 = disorder)")

    # Save the φ time series to a CSV file in results/
    mkpath(output_dir)
    fname = joinpath(output_dir, "vicsek_N$(N)_noise$(noise).csv")
    CSV.write(fname, DataFrame(
        step            = 1:n_steps,
        order_parameter = model.order_history
    ))
    println("Saved → $(fname)")

    return model
end


# ─────────────────────────────────────────────────────────────
# 7. ENTRY POINT: two sanity-check runs
#    Run this file with:
#      julia --project=/home/umar/sheep_collective src/vicsek_baseline.jl
# ─────────────────────────────────────────────────────────────
println("=" ^ 55)
println("  VICSEK BASELINE — SANITY CHECK")
println("  Agents.jl version: ", pkgversion(Agents))
println("=" ^ 55)

# Run 1: LOW noise — agents should align → φ rises toward 1
println("\n[Run 1] LOW noise  η = 0.1  →  expect φ → 1 (flock)")
run_vicsek(noise = 0.1, n_steps = 500)

# Run 2: HIGH noise — too random to align → φ stays near 0
println("\n[Run 2] HIGH noise η = 4.0  →  expect φ → 0 (disorder)")
run_vicsek(noise = 4.0, n_steps = 500)

println("\n", "=" ^ 55)
println("  ✓ Baseline complete.")
println("  Check /home/umar/sheep_collective/results/ for CSV files.")
println("=" ^ 55)
