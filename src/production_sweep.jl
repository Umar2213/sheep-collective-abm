# production_sweep.jl — production dataset (stationarity must be assessed per run).
# Discards first 30k steps as transient; existing diagnostics cover a subset only,
# measures over final 30k. Records order, fluctuations (seed-susceptibility,
# temporal variance, lag-1 autocorrelation), and trait-distribution diagnostics.
# Run:  julia --project=. --threads=auto src/production_sweep.jl
include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
include(joinpath(@__DIR__, "run_metadata.jl"))
using Statistics, DataFrames, CSV, Printf

const SIGMA_MEAN=0.7
const NEIGHBOR_SEARCH = Symbol(get(ENV, "ABM_NEIGHBOR_SEARCH", "exact"))
const SMOKE = get(ENV, "ABM_SMOKE", "0") == "1"
const SIGMA_LIST=SMOKE ? [0.0,0.3] : collect(0.0:0.025:0.45)
const NOISE_LIST=SMOKE ? [0.5] : [0.3,0.5,0.7]
const N_AGENTS=SMOKE ? 12 : 200; const N_SEEDS=SMOKE ? 2 : 20
const N_TOTAL=SMOKE ? 120 : 60000; const N_WARMUP=SMOKE ? 60 : 30000
const OUTDIR=get(ENV, "ABM_OUTPUT_DIR", joinpath(@__DIR__,"..","results",SMOKE ? "smoke_production" : string(NEIGHBOR_SEARCH, "_production")))

lag1(x)=cor(@view(x[1:end-1]),@view(x[2:end]))

function run_one(; sigma_std, noise, seed)
    model, sv = create_sheep_model(; N=N_AGENTS, noise=noise,
        σ_mean=SIGMA_MEAN, σ_std=sigma_std, seed=seed, neighbor_search=NEIGHBOR_SEARCH)
    for _ in 1:N_TOTAL; step!(model); end
    meas = model.order_history[(N_WARMUP+1):end]
    (sigma_std=sigma_std, noise=noise, seed=seed,
     phi=mean(meas), phi_tempvar=var(meas), ar1=lag1(meas),
     real_mean=mean(sv), real_std=std(sv),
     frac_lo=count(<(0.2),sv)/length(sv), frac_hi=count(>(0.8),sv)/length(sv))
end

jobs=[(s,e,sd) for s in SIGMA_LIST for e in NOISE_LIST for sd in 1:N_SEEDS]
res=Vector{Any}(undef,length(jobs))
println("production: $(length(jobs)) runs × $N_TOTAL steps on $(Threads.nthreads()) threads")
done=Threads.Atomic{Int}(0)
Threads.@threads for i in eachindex(jobs)
    s,e,sd=jobs[i]; res[i]=run_one(; sigma_std=s, noise=e, seed=sd)
    d=Threads.atomic_add!(done,1)+1
    d % 100 == 0 && println("  $d / $(length(jobs))")
end
mkpath(OUTDIR)
raw=DataFrame(res)
write_run_metadata(OUTDIR; N=N_AGENTS, L=20.0, noise=NOISE_LIST, sigma=SIGMA_LIST, seeds=N_SEEDS, total=N_TOTAL, warmup=N_WARMUP, smoke=SMOKE, neighbor_search=string(NEIGHBOR_SEARCH))
CSV.write(joinpath(OUTDIR,"sweep_replicates.csv"),raw)
g=groupby(raw,[:noise,:sigma_std])
summ=combine(g, :phi=>mean=>:phi_mean, :phi=>std=>:phi_sd,
    :phi=>(x->N_AGENTS*var(x))=>:chi_seed, :phi_tempvar=>mean=>:tempvar,
    :ar1=>mean=>:ar1, :frac_lo=>mean=>:frac_lo, :frac_hi=>mean=>:frac_hi,
    :phi=>length=>:n)
sort!(summ,[:noise,:sigma_std]); CSV.write(joinpath(OUTDIR,"sweep_condition_means.csv"),summ)
println("\n  η=0.5 measured curve:")
println("  sigma | phi_mean |  sd   | chi_seed |  ar1  | %<0.2")
println("  "*"-"^56)
for row in eachrow(summ[summ.noise.==0.5,:])
    @printf("  %.3f | %.4f  | %.4f | %.4f  | %.4f | %4.1f%%\n",
        row.sigma_std,row.phi_mean,row.phi_sd,row.chi_seed,row.ar1,100*row.frac_lo)
end
println("\n  wrote production tables in $OUTDIR")
