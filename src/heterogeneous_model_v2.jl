# Heterogeneous alignment-response model. See docs/MODEL.md for equations.
# Exact metric neighbours are the default. Sequential and synchronous updates are
# both implemented so update convention can be treated as an explicit control.
# No empirical sheep calibration is implied by this simulation model.

using Agents
using Distributions
using Statistics
using Random
using DataFrames
using CSV


# 1. AGENT TYPE

@agent struct SheepAgent(ContinuousAgent{2, Float64})
    θ                :: Float64
    social_weight    :: Float64   # focal individual's responsiveness to neighbours
    influence_weight :: Float64   # outgoing weight applied when others use this agent
end


# 2. MODEL PROPERTIES

Base.@kwdef mutable struct SheepProps
    speed              :: Float64 = 0.03
    noise              :: Float64 = 0.5
    radius             :: Float64 = 1.0
    dt                 :: Float64 = 1.0
    neighbor_search    :: Symbol = :exact
    update_mode        :: Symbol = :sequential
    trait_distribution :: Symbol = :beta
    σ_mean             :: Float64 = 0.7
    σ_std              :: Float64 = 0.1
    social_ties        :: Union{Nothing, Matrix{Float64}} = nothing
    order_history      :: Vector{Float64} = Float64[]
end


# 3. VALIDATION AND RANDOM STREAMS

function beta_from_mean_std(μ::Real, s::Real)
    isfinite(μ) && 0 <= μ <= 1 || throw(ArgumentError("mean must be finite and in [0,1]"))
    isfinite(s) && s >= 0 || throw(ArgumentError("std must be finite and nonnegative"))
    v = s^2
    if v <= 0.0
        return nothing
    end
    max_v = μ * (1 - μ)
    if v >= max_v
        throw(ArgumentError("Requested variance $(round(v; digits=4)) exceeds max " *
                            "possible $(round(max_v; digits=4)) for mean $(μ)."))
    end
    common = μ * (1 - μ) / v - 1
    return Beta(μ * common, (1 - μ) * common)
end

include(joinpath(@__DIR__, "trait_distributions.jl"))

function _checked_seed(name, value)
    value isa Integer || throw(ArgumentError("$name must be an integer"))
    value >= 0 || throw(ArgumentError("$name must be nonnegative"))
    return Int(value)
end

"""Resolve independent random streams while keeping `seed` as a backward-compatible base."""
function resolve_rng_seeds(seed::Integer; trait_seed=nothing, init_seed=nothing, dynamic_seed=nothing)
    base = _checked_seed("seed", seed)
    ts = trait_seed === nothing ? base : _checked_seed("trait_seed", trait_seed)
    is = init_seed === nothing ? base + 1_000_003 : _checked_seed("init_seed", init_seed)
    ds = dynamic_seed === nothing ? base + 2_000_003 : _checked_seed("dynamic_seed", dynamic_seed)
    return (trait_seed=ts, init_seed=is, dynamic_seed=ds)
end

function _validate_social_ties(social_ties, N)
    social_ties === nothing && return nothing
    size(social_ties) == (N, N) || throw(ArgumentError("social_ties must be an N by N matrix"))
    A = Matrix{Float64}(social_ties)
    all(isfinite, A) || throw(ArgumentError("social_ties must contain only finite values"))
    all(x -> x >= 0, A) || throw(ArgumentError("social_ties must be nonnegative"))
    for i in 1:N
        A[i, i] = 0.0
    end
    return A
end

function _validate_influence_weights(influence_weights, N)
    influence_weights === nothing && return ones(Float64, N)
    length(influence_weights) == N || throw(ArgumentError("influence_weights must have length N"))
    q = Float64.(influence_weights)
    all(isfinite, q) || throw(ArgumentError("influence_weights must contain only finite values"))
    all(x -> x >= 0, q) || throw(ArgumentError("influence_weights must be nonnegative"))
    return q
end


# 4. INTERACTION RULE

"""Return the deterministic heading for one focal agent.

`social_ties[i,j]` is the directed tie weight describing how strongly focal agent i
uses neighbour j. `influence_weight[j]` is an optional outgoing influence multiplier.
The focal response parameter remains `social_weight` for backward compatibility.
"""
function deterministic_heading(agent::SheepAgent, model)
    neighbours = collect(nearby_agents(agent, model, model.radius; search=model.neighbor_search))
    isempty(neighbours) && return agent.θ

    sin_sum = 0.0
    cos_sum = 0.0
    weight_sum = 0.0
    for nb in neighbours
        tie = model.social_ties === nothing ? 1.0 : model.social_ties[agent.id, nb.id]
        w = tie * nb.influence_weight
        if w > 0
            sin_sum += w * sin(nb.θ)
            cos_sum += w * cos(nb.θ)
            weight_sum += w
        end
    end
    weight_sum > 0 || return agent.θ

    nb_sin = sin_sum / weight_sum
    nb_cos = cos_sum / weight_sum
    r = agent.social_weight
    blend_sin = r * nb_sin + (1.0 - r) * sin(agent.θ)
    blend_cos = r * nb_cos + (1.0 - r) * cos(agent.θ)

    # Exactly balanced vectors have no defined direction. Retaining self direction
    # avoids an arbitrary global angle being introduced by atan(0,0).
    hypot(blend_sin, blend_cos) > 10eps(Float64) || return agent.θ
    return atan(blend_sin, blend_cos)
end

function _noisy_heading(base_heading, model)
    return base_heading + model.noise * (rand(abmrng(model)) - 0.5)
end

function _apply_heading!(agent::SheepAgent, model, new_θ)
    agent.θ = new_θ
    agent.vel = (model.speed * cos(new_θ), model.speed * sin(new_θ))
    move_agent!(agent, model, model.dt)
    return nothing
end


# 5. UPDATE CONVENTIONS

function sheep_agent_step!(agent::SheepAgent, model)
    _apply_heading!(agent, model, _noisy_heading(deterministic_heading(agent, model), model))
    return nothing
end

sheep_agent_noop!(agent::SheepAgent, model) = nothing

function record_order!(model)
    N = nagents(model)
    N == 0 && return nothing
    vx_mean = mean(a.vel[1] for a in allagents(model))
    vy_mean = mean(a.vel[2] for a in allagents(model))
    φ = sqrt(vx_mean^2 + vy_mean^2) / model.speed
    push!(model.order_history, φ)
    return nothing
end

function sheep_model_step_sequential!(model)
    record_order!(model)
    return nothing
end

"""Synchronous control: compute all headings from the same pre-step state, then move."""
function sheep_model_step_synchronous!(model)
    ids = [a.id for a in allagents(model)]
    new_headings = Dict{Int, Float64}()
    for id in ids
        agent = model[id]
        new_headings[id] = _noisy_heading(deterministic_heading(agent, model), model)
    end
    for id in ids
        agent = model[id]
        θ = new_headings[id]
        agent.θ = θ
        agent.vel = (model.speed * cos(θ), model.speed * sin(θ))
    end
    for id in ids
        move_agent!(model[id], model, model.dt)
    end
    record_order!(model)
    return nothing
end

# Historical public name retained for external scripts that may include this file.
sheep_model_step!(model) = sheep_model_step_sequential!(model)


# 6. CREATE THE MODEL

function create_sheep_model(; N=200, L=20.0, speed=0.03, noise=0.5,
                            radius=1.0, dt=1.0, neighbor_search=:exact,
                            update_mode=:sequential, trait_distribution=:beta,
                            σ_mean=0.7, σ_std=0.1,
                            seed=42, trait_seed=nothing, init_seed=nothing,
                            dynamic_seed=nothing, social_ties=nothing,
                            influence_weights=nothing)
    N isa Integer && N >= 1 || throw(ArgumentError("N must be a positive integer"))
    for (name, value) in ((:L, L), (:speed, speed), (:radius, radius), (:dt, dt))
        isfinite(value) && value > 0 || throw(ArgumentError("$name must be finite and positive"))
    end
    isfinite(noise) && noise >= 0 || throw(ArgumentError("noise must be finite and nonnegative"))
    neighbor_search in (:exact, :approximate) ||
        throw(ArgumentError("neighbor_search must be :exact or :approximate"))
    update_mode in (:sequential, :synchronous) ||
        throw(ArgumentError("update_mode must be :sequential or :synchronous"))
    trait_distribution in (:beta, :two_point) ||
        throw(ArgumentError("trait_distribution must be :beta or :two_point"))

    # Validate requested trait moments before allocating the model.
    beta_from_mean_std(σ_mean, σ_std)

    seeds = resolve_rng_seeds(seed; trait_seed=trait_seed, init_seed=init_seed,
                              dynamic_seed=dynamic_seed)
    A = _validate_social_ties(social_ties, N)
    q = _validate_influence_weights(influence_weights, N)

    space = ContinuousSpace((L, L); periodic=true)
    props = SheepProps(speed=speed, noise=noise, radius=radius, dt=dt,
                       neighbor_search=neighbor_search, update_mode=update_mode,
                       trait_distribution=trait_distribution,
                       σ_mean=σ_mean, σ_std=σ_std, social_ties=A)

    agent_step_fn = update_mode == :sequential ? sheep_agent_step! : sheep_agent_noop!
    model_step_fn = update_mode == :sequential ? sheep_model_step_sequential! : sheep_model_step_synchronous!
    model = StandardABM(
        SheepAgent, space;
        properties=props,
        scheduler=Schedulers.fastest,
        agents_first=true,
        agent_step! = agent_step_fn,
        model_step! = model_step_fn,
        rng=MersenneTwister(seeds.dynamic_seed)
    )

    trait_rng = MersenneTwister(seeds.trait_seed)
    init_rng = MersenneTwister(seeds.init_seed)
    σ_values = Float64[]

    for i in 1:N
        θ_init = rand(init_rng) * 2π
        pos_init = (rand(init_rng) * L, rand(init_rng) * L)
        σ_i = draw_responsiveness(trait_rng, trait_distribution, σ_mean, σ_std)
        push!(σ_values, σ_i)
        add_agent!(pos_init, model;
            vel=(speed * cos(θ_init), speed * sin(θ_init)),
            θ=θ_init,
            social_weight=σ_i,
            influence_weight=q[i]
        )
    end

    return model, σ_values
end


# 7. RUN ONE SEED

function run_single_seed(; σ_mean, σ_std, seed, n_steps=500, N=200,
                         L=20.0, speed=0.03, noise=0.5, radius=1.0,
                         neighbor_search=:exact, update_mode=:sequential,
                         trait_distribution=:beta,
                         trait_seed=nothing, init_seed=nothing, dynamic_seed=nothing,
                         social_ties=nothing, influence_weights=nothing)
    n_steps isa Integer && n_steps >= 100 ||
        throw(ArgumentError("n_steps must be an integer >= 100"))
    model, σ_values = create_sheep_model(;
        N=N, L=L, speed=speed, noise=noise, radius=radius,
        neighbor_search=neighbor_search, update_mode=update_mode,
        trait_distribution=trait_distribution,
        σ_mean=σ_mean, σ_std=σ_std, seed=seed,
        trait_seed=trait_seed, init_seed=init_seed, dynamic_seed=dynamic_seed,
        social_ties=social_ties, influence_weights=influence_weights
    )
    for _ in 1:n_steps
        step!(model)
    end
    return (
        φ_steady=mean(model.order_history[end-99:end]),
        actual_σ_mean=mean(σ_values),
        actual_σ_std=std(σ_values),
    )
end


# 8. RUN ONE CONDITION, BACKWARD-COMPATIBLE PILOT API

function run_condition(; σ_mean, σ_std, n_seeds=15, n_steps=500, noise=0.5,
                       neighbor_search=:exact, update_mode=:sequential,
                       trait_distribution=:beta)
    n_seeds isa Integer && n_seeds >= 2 ||
        throw(ArgumentError("n_seeds must be an integer >= 2"))
    φ_values = Float64[]
    σmean_vals = Float64[]
    σstd_vals = Float64[]

    print("  σ_std=$(rpad(σ_std, 5)) : ")
    for seed in 1:n_seeds
        r = run_single_seed(; σ_mean=σ_mean, σ_std=σ_std, seed=seed,
                            n_steps=n_steps, noise=noise,
                            neighbor_search=neighbor_search, update_mode=update_mode,
                            trait_distribution=trait_distribution)
        push!(φ_values, r.φ_steady)
        push!(σmean_vals, r.actual_σ_mean)
        push!(σstd_vals, r.actual_σ_std)
        print(".")
    end
    println(" done")
    println("       φ        = $(round(mean(φ_values); digits=4)) ± $(round(std(φ_values); digits=4))")
    println("       actual σ̄ = $(round(mean(σmean_vals); digits=4)) ± $(round(std(σmean_vals); digits=4))")
    println("       actual s  = $(round(mean(σstd_vals); digits=4)) ± $(round(std(σstd_vals); digits=4))")
    return (φ_values, σmean_vals, σstd_vals)
end


# 9. SMALL INTERACTIVE EXPERIMENT

function run_experiment(; σ_mean=0.7,
                        σ_std_list=[0.0, 0.05, 0.10, 0.15, 0.20, 0.25],
                        n_seeds=15, n_steps=500, noise=0.5,
                        neighbor_search=:exact, update_mode=:sequential,
                        trait_distribution=:beta,
                        output_dir=joinpath(@__DIR__, "..", "results", "pilot"),
                        label="experiment")
    println("=" ^ 64)
    println("  $(label): effect of σ_std on heading order φ")
    println("  search=$(neighbor_search), update=$(update_mode), traits=$(trait_distribution)")
    println("  fixed σ_mean=$(σ_mean), noise=$(noise), N=200")
    println("  $(n_seeds) seeds, $(n_steps) steps per condition")
    println("=" ^ 64)

    raw = DataFrame(σ_mean=Float64[], noise=Float64[], σ_std_input=Float64[],
                    seed=Int[], actual_σ_mean=Float64[], actual_σ_std=Float64[],
                    φ_steady=Float64[])
    summary = DataFrame(noise=Float64[], σ_std_input=Float64[], φ_mean=Float64[],
                        φ_sd=Float64[], n=Int[])

    for σ_std in σ_std_list
        φ_vals, σm_vals, σs_vals = run_condition(;
            σ_mean=σ_mean, σ_std=σ_std, n_seeds=n_seeds, n_steps=n_steps,
            noise=noise, neighbor_search=neighbor_search, update_mode=update_mode,
            trait_distribution=trait_distribution)
        for k in 1:n_seeds
            push!(raw, (σ_mean=σ_mean, noise=noise, σ_std_input=σ_std, seed=k,
                        actual_σ_mean=σm_vals[k], actual_σ_std=σs_vals[k],
                        φ_steady=φ_vals[k]))
        end
        push!(summary, (noise=noise, σ_std_input=σ_std, φ_mean=mean(φ_vals),
                        φ_sd=std(φ_vals), n=n_seeds))
    end

    mkpath(output_dir)
    CSV.write(joinpath(output_dir, "$(label)_rawdata.csv"), raw)
    CSV.write(joinpath(output_dir, "$(label)_means.csv"), summary)
    return raw, summary
end


if abspath(PROGRAM_FILE) == abspath(@__FILE__)
    @warn "500-step pilot only: these outputs do not establish stationarity."
    run_experiment(label="experiment1")
end
