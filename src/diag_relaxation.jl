# diag_relaxation.jl — convergence + bistability check near the transition.
include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
using Statistics, DataFrames, CSV, Printf

const NOISE=0.5; const SIGMA_MEAN=0.7
const SIGMA_LIST=[0.25,0.30,0.33,0.35,0.40]
const N_AGENTS=200; const N_SEEDS=12; const N_STEPS=60000; const DECIMATE=50
const OUTDIR=joinpath(@__DIR__,"..","results","diagnostics")

function run_one(; sigma_std, seed)
    model, sv = create_sheep_model(; N=N_AGENTS, noise=NOISE,
        σ_mean=SIGMA_MEAN, σ_std=sigma_std, seed=seed)
    for _ in 1:N_STEPS; step!(model); end
    h = model.order_history; q = length(h) ÷ 4
    qm = [mean(h[(k*q+1):((k+1)*q)]) for k in 0:3]
    (sigma=sigma_std, seed=seed, q1=qm[1], q2=qm[2], q3=qm[3], q4=qm[4], hist=h)
end

jobs=[(s,sd) for s in SIGMA_LIST for sd in 1:N_SEEDS]
res=Vector{Any}(undef,length(jobs))
println("relax: $(length(jobs)) runs × $N_STEPS steps on $(Threads.nthreads()) threads")
Threads.@threads for i in eachindex(jobs)
    s,sd=jobs[i]; res[i]=run_one(; sigma_std=s, seed=sd)
end
mkpath(OUTDIR)
summ=DataFrame(sigma=Float64[],phi_Q3=Float64[],phi_Q4=Float64[],
               late_drift=Float64[],seed_sd_Q4=Float64[],min_Q4=Float64[],max_Q4=Float64[])
for s in SIGMA_LIST
    rs=[r for r in res if r.sigma==s]
    q3=mean(getfield.(rs,:q3)); q4=mean(getfield.(rs,:q4)); q4v=getfield.(rs,:q4)
    push!(summ,(s,q3,q4,abs(q4-q3),std(q4v),minimum(q4v),maximum(q4v)))
end
CSV.write(joinpath(OUTDIR,"relaxation_summary.csv"),summ)
ts=DataFrame(sigma=Float64[],seed=Int[],step=Int[],phi=Float64[])
for s in SIGMA_LIST, sd in 1:3
    r=first(r for r in res if r.sigma==s && r.seed==sd)
    for t in 1:DECIMATE:length(r.hist); push!(ts,(s,sd,t,r.hist[t])); end
end
CSV.write(joinpath(OUTDIR,"relaxation_timeseries.csv"),ts)
println("\n  sigma | phi_Q3 | phi_Q4 | late_drift | seed_sd | min_Q4 | max_Q4")
println("  "*"-"^66)
for row in eachrow(summ)
    @printf("  %.2f  | %.4f | %.4f |  %.4f    | %.4f  | %.4f | %.4f\n",
        row.sigma,row.phi_Q3,row.phi_Q4,row.late_drift,row.seed_sd_Q4,row.min_Q4,row.max_Q4)
end
println("\n  wrote relaxation_summary.csv + relaxation_timeseries.csv")
