# diag_equilibration.jl — decisive checks, reuses the real model unchanged.
# Run:  julia --project=. --threads=auto src/diag_equilibration.jl
include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
using Statistics, DataFrames, CSV, Printf

const NOISE=0.5; const SIGMA_MEAN=0.7
const SIGMA_LIST=[0.0,0.20,0.30,0.33,0.35,0.40]
const N_AGENTS=200; const N_SEEDS=8; const N_STEPS=15000
const SHORT_CUT=500; const SHORT_WIN=100; const MEAS_FROM=7501; const DECIMATE=25
const OUTDIR=joinpath(@__DIR__, "..", "results", "diagnostics")

function run_one(; sigma_std, seed)
    model, sv = create_sheep_model(; N=N_AGENTS, noise=NOISE,
                                   σ_mean=SIGMA_MEAN, σ_std=sigma_std, seed=seed)
    for _ in 1:N_STEPS; step!(model); end
    h = model.order_history
    phi_short = mean(h[(SHORT_CUT-SHORT_WIN+1):SHORT_CUT])   # old method
    meas = h[MEAS_FROM:end]; phi_long = mean(meas)
    half = length(meas) ÷ 2
    drift = abs(mean(meas[1:half]) - mean(meas[half+1:end]))
    (sigma=sigma_std, seed=seed, phi_short=phi_short, phi_long=phi_long,
     bias=phi_long-phi_short, drift=drift, real_mean=mean(sv), real_std=std(sv),
     frac_lo=count(<(0.2),sv)/length(sv), frac_hi=count(>(0.8),sv)/length(sv), hist=h)
end

jobs=[(s,sd) for s in SIGMA_LIST for sd in 1:N_SEEDS]
res=Vector{Any}(undef,length(jobs))
println("diag: $(length(jobs)) runs × $N_STEPS steps on $(Threads.nthreads()) threads")
Threads.@threads for i in eachindex(jobs)
    s,sd=jobs[i]; res[i]=run_one(; sigma_std=s, seed=sd)
end
mkpath(OUTDIR)
summ=DataFrame(sigma=Float64[],phi_short=Float64[],phi_long=Float64[],bias=Float64[],
               max_drift=Float64[],real_mean=Float64[],real_std=Float64[],
               frac_lo=Float64[],frac_hi=Float64[])
for s in SIGMA_LIST
    rs=[r for r in res if r.sigma==s]
    push!(summ,(s,mean(getfield.(rs,:phi_short)),mean(getfield.(rs,:phi_long)),
        mean(getfield.(rs,:bias)),maximum(getfield.(rs,:drift)),
        mean(getfield.(rs,:real_mean)),mean(getfield.(rs,:real_std)),
        mean(getfield.(rs,:frac_lo)),mean(getfield.(rs,:frac_hi))))
end
CSV.write(joinpath(OUTDIR,"equilibration_summary.csv"),summ)
ts=DataFrame(sigma=Float64[],step=Int[],phi=Float64[])
for s in SIGMA_LIST
    r=first(r for r in res if r.sigma==s && r.seed==1)
    for t in 1:DECIMATE:length(r.hist); push!(ts,(s,t,r.hist[t])); end
end
CSV.write(joinpath(OUTDIR,"equilibration_timeseries.csv"),ts)
println("\n  sigma | phi_short | phi_long |  bias   | maxdrift | real_s | %<0.2 | %>0.8")
println("  "*"-"^74)
for row in eachrow(summ)
    @printf("  %.2f  |  %.4f   | %.4f  | %+.4f | %.4f   | %.3f  | %4.1f%% | %4.1f%%\n",
        row.sigma,row.phi_short,row.phi_long,row.bias,row.max_drift,
        row.real_std,100*row.frac_lo,100*row.frac_hi)
end
println("\n  wrote results/diagnostics/equilibration_summary.csv + _timeseries.csv")
