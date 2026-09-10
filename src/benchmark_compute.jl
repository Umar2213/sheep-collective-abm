# benchmark_compute.jl
# Lightweight timing helper for estimating full-run compute requirements on the
# actual workstation or cluster that will execute the scientific sweeps.
# Example:
#   ABM_BENCHMARK_N=1600 ABM_BENCHMARK_STEPS=1000 julia --project=. src/benchmark_compute.jl

include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
using Printf

function env_int(name, default; minimum=1)
    value = try
        parse(Int, get(ENV, name, string(default)))
    catch
        throw(ArgumentError("$name must be an integer"))
    end
    value >= minimum || throw(ArgumentError("$name must be >= $minimum"))
    return value
end

function env_float(name, default; minimum=0.0)
    value = try
        parse(Float64, get(ENV, name, string(default)))
    catch
        throw(ArgumentError("$name must be numeric"))
    end
    isfinite(value) && value >= minimum || throw(ArgumentError("$name must be finite and >= $minimum"))
    return value
end

N = env_int("ABM_BENCHMARK_N", 200)
STEPS = env_int("ABM_BENCHMARK_STEPS", 1000; minimum=10)
NOISE = env_float("ABM_BENCHMARK_NOISE", 0.5)
SIGMA_STD = env_float("ABM_BENCHMARK_SIGMA", 0.30)
UPDATE_MODE = Symbol(get(ENV, "ABM_UPDATE_MODE", "sequential"))
NEIGHBOR_SEARCH = Symbol(get(ENV, "ABM_NEIGHBOR_SEARCH", "exact"))
DENSITY = env_float("ABM_BENCHMARK_DENSITY", 0.5; minimum=eps())
L = sqrt(N / DENSITY)

model, _ = create_sheep_model(; N=N, L=L, noise=NOISE, σ_mean=0.7,
    σ_std=SIGMA_STD, seed=42, update_mode=UPDATE_MODE,
    neighbor_search=NEIGHBOR_SEARCH)

# Warm the compiled stepping path before timing.
for _ in 1:min(20, STEPS)
    step!(model)
end
empty!(model.order_history)

elapsed = @elapsed begin
    for _ in 1:STEPS
        step!(model)
    end
end

steps_per_second = STEPS / elapsed
agent_updates_per_second = N * steps_per_second
production_seconds = 60_000 / steps_per_second
fss_seconds = 80_000 / steps_per_second

println("Simulation benchmark")
println("  N                 = $N")
println("  L                 = $(round(L; digits=4))")
println("  density           = $DENSITY")
println("  sigma_std         = $SIGMA_STD")
println("  noise             = $NOISE")
println("  neighbour search  = $NEIGHBOR_SEARCH")
println("  update mode       = $UPDATE_MODE")
println("  timed steps       = $STEPS")
@printf("  elapsed           = %.3f s\n", elapsed)
@printf("  steps/s           = %.3f\n", steps_per_second)
@printf("  agent updates/s   = %.1f\n", agent_updates_per_second)
@printf("  est 60k-step run  = %.2f min\n", production_seconds / 60)
@printf("  est 80k-step run  = %.2f min\n", fss_seconds / 60)
println()
println("These are single-run wall-time estimates on this machine after compilation warmup.")
println("Parallel full-grid throughput depends on available cores, memory and scheduler overhead.")
