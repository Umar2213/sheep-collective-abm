# experiment3_noise_sweep.jl
# Tests whether the personality-variance threshold shifts with environmental noise.

include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))

using DataFrames
using CSV

const OUTPUT_ROOT = "/home/umar/sheep_collective/results"

function run_experiment3()
    println("=" ^ 64)
    println("  EXPERIMENT 3 — noise sensitivity of personality threshold")
    println("  noise levels: [0.3, 0.5, 0.7]")
    println("  σ_std:        [0.0, 0.2, 0.35, 0.45]")
    println("  15 seeds × 500 steps per condition")
    println("=" ^ 64)
    println()

    all_means = DataFrame[]

    for η in [0.3, 0.5, 0.7]
        label = "exp3_noise$(η)"
        out   = joinpath(OUTPUT_ROOT, label)
        _, summary = run_experiment(;
            σ_mean      = 0.7,
            σ_std_list  = [0.0, 0.2, 0.35, 0.45],
            n_seeds     = 15,
            n_steps     = 500,
            noise       = η,
            output_dir  = out,
            label       = label,
        )
        push!(all_means, summary)
        println()
    end

    combined = vcat(all_means...)
    combined_path = joinpath(OUTPUT_ROOT, "exp3_all_means.csv")
    CSV.write(combined_path, combined)

    println("=" ^ 64)
    println("  EXPERIMENT 3 COMPLETE")
    println("  Combined summary → $(combined_path)")
    println("=" ^ 64)

    return combined
end

run_experiment3()
