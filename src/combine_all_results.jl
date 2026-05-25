# combine_all_results.jl
# Merges Exp1 + Exp2 + Exp3 into one master CSV for plotting / manuscript.

using DataFrames
using CSV

const ROOT = "/home/umar/sheep_collective/results"

function load_means(path, experiment, noise=0.5)
    df = CSV.read(path, DataFrame)
    if !hasproperty(df, :noise)
        df[!, :noise] .= noise
    end
    df[!, :experiment] .= experiment
    return df
end

# Exp1 (legacy filenames from first run)
exp1 = load_means(joinpath(ROOT, "experiment1_means.csv"), "exp1", 0.5)
if hasproperty(exp1, :σ_std_input) && !hasproperty(exp1, :noise)
    exp1[!, :noise] .= 0.5
end

# Exp2
exp2_path = joinpath(ROOT, "exp2", "experiment1_means.csv")
exp2 = isfile(exp2_path) ?
    load_means(exp2_path, "exp2", 0.5) :
    DataFrame(experiment=String[], noise=Float64[], σ_std_input=Float64[],
              φ_mean=Float64[], φ_sd=Float64[], n=Int[])

# Exp3 combined (if exists)
exp3_path = joinpath(ROOT, "exp3_all_means.csv")
exp3 = isfile(exp3_path) ?
    begin
        df = CSV.read(exp3_path, DataFrame)
        df[!, :experiment] .= "exp3"
        df
    end :
    DataFrame(experiment=String[], noise=Float64[], σ_std_input=Float64[],
              φ_mean=Float64[], φ_sd=Float64[], n=Int[])

master = vcat(exp1, exp2, exp3)
out = joinpath(ROOT, "MASTER_all_experiments.csv")
CSV.write(out, master)

println("=" ^ 60)
println("  MASTER RESULTS TABLE")
println("  Saved → $(out)")
println("=" ^ 60)
for sub in ["exp1", "exp2", "exp3"]
    subdf = filter(r -> r.experiment == sub, master)
    isempty(subdf) && continue
    println("\n  [$sub]  $(nrow(subdf)) rows")
    for row in eachrow(subdf)
        η = hasproperty(row, :noise) ? row.noise : 0.5
        println("    η=$(η)  σ_std=$(row.σ_std_input)  φ=$(round(row.φ_mean;digits=3)) ± $(round(row.φ_sd;digits=3))")
    end
end
println("\n" * "=" ^ 60)
