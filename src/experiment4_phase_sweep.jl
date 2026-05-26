include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
using CSV, DataFrames, Statistics

function run_phase_sweep(;
    sigma_mean_list = [0.3, 0.5, 0.7, 0.9],
    sigma_std_list  = [0.0, 0.1, 0.2, 0.3, 0.35, 0.4],
    noise = 0.5, n_seeds = 10, n_steps = 500,
    output_dir = "/home/umar/sheep_collective/results"
)
    rows = []
    total = length(sigma_mean_list) * length(sigma_std_list)
    done = 0
    for sm in sigma_mean_list
        for ss in sigma_std_list
            max_var = sm * (1 - sm)
            if ss^2 >= max_var
                println("Skip sigma_mean=$(sm) sigma_std=$(ss) — violates Beta constraint")
                continue
            end
            phi_vals = Float64[]
            for seed in 1:n_seeds
                r = run_single_seed(; σ_mean=sm, σ_std=ss,
                                     seed=seed, n_steps=n_steps, noise=noise)
                push!(phi_vals, r.φ_steady)
            end
            done += 1
            println("[$done/$total] sigma_mean=$(sm) sigma_std=$(ss) phi=$(round(mean(phi_vals),digits=3))")
            push!(rows, (sigma_mean=sm, sigma_std=ss, phi_mean=mean(phi_vals),
                          phi_sd=std(phi_vals), n=n_seeds, noise=noise))
        end
    end
    mkpath(output_dir)
    CSV.write(joinpath(output_dir, "experiment4_phase_sweep.csv"), DataFrame(rows))
    println("Saved experiment4_phase_sweep.csv")
end

if abspath(PROGRAM_FILE) == @__FILE__
    run_phase_sweep()
end
