# snapshot_states.jl — save final agent states for representative conditions.
include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
using DataFrames, CSV

const NOISE   = 0.5
const CONDS   = [0.00, 0.30, 0.40, 0.45]   # σ: ordered -> fragmented
const N       = 200
const N_STEPS = 30000
const SEED    = 1
const OUT     = joinpath(@__DIR__, "..", "results", "snapshots")

rows = DataFrame(sigma=Float64[], x=Float64[], y=Float64[], theta=Float64[], w=Float64[])
for s in CONDS
    model, sv = create_sheep_model(; N=N, noise=NOISE, σ_mean=0.7, σ_std=s, seed=SEED)
    for _ in 1:N_STEPS; step!(model); end
    for a in allagents(model)
        push!(rows, (s, a.pos[1], a.pos[2], a.θ, a.social_weight))
    end
    println("  σ=$s done, final φ = $(round(model.order_history[end]; digits=3))")
end
mkpath(OUT)
CSV.write(joinpath(OUT, "snapshot_states.csv"), rows)
println("  wrote results/snapshots/snapshot_states.csv  ($(nrow(rows)) rows)")
