# production_sweep.jl — canonical equilibrated dataset.
# Discards first 30k steps as transient (Q3≈Q4 confirmed by diag_relaxation),
# measures over final 30k. Records order, fluctuations (seed-susceptibility,
# temporal variance, lag-1 autocorrelation), and trait-distribution diagnostics.
# Run:  julia --project=. --threads=auto src/production_sweep.jl
include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
using Statistics, DataFrames, CSV, Printf

const SIGMA_MEAN=0.7
const SIGMA_LIST=collect(0.0:0.025:0.45)
const NOISE_LIST=[0.3,0.5,0.7]
const N_AGENTS=200; const N_SEEDS=20
const N_TOTAL=60000; const N_WARMUP=30000
const OUTDIR=joinpath(@__DIR__,"..","results","production")

lag1(x)=cor(@view(x[1:end-1]),@view(x[2:end]))

function run_one(; sigma_std, noise, seed)
    model, sv = create_sheep_model(; N=N_AGENTS, noise=noise,
        σ_mean=SIGMA_MEAN, σ_std=sigma_std, seed=seed)
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
raw=DataFrame(res); CSV.write(joinpath(OUTDIR,"sweep_replicates.csv"),raw)
g=groupby(raw,[:noise,:sigma_std])
summ=combine(g, :phi=>mean=>:phi_mean, :phi=>std=>:phi_sd,
    :phi=>(x->N_AGENTS*var(x))=>:chi_seed, :phi_tempvar=>mean=>:tempvar,
    :ar1=>mean=>:ar1, :frac_lo=>mean=>:frac_lo, :frac_hi=>mean=>:frac_hi,
    :phi=>length=>:n)
sort!(summ,[:noise,:sigma_std]); CSV.write(joinpath(OUTDIR,"sweep_condition_means.csv"),summ)
println("\n  η=0.5 equilibrated curve:")
println("  sigma | phi_mean |  sd   | chi_seed |  ar1  | %<0.2")
println("  "*"-"^56)
for row in eachrow(summ[summ.noise.==0.5,:])
    @printf("  %.3f | %.4f  | %.4f | %.4f  | %.4f | %4.1f%%\n",
        row.sigma_std,row.phi_mean,row.phi_sd,row.chi_seed,row.ar1,100*row.frac_lo)
end
println("\n  wrote results/production/sweep_replicates.csv + sweep_condition_means.csv")
EOFcd /home/umar/sheep_collective
cat > src/production_sweep.jl << 'EOF'
# production_sweep.jl — canonical equilibrated dataset.
# Discards first 30k steps as transient (Q3≈Q4 confirmed by diag_relaxation),
# measures over final 30k. Records order, fluctuations (seed-susceptibility,
# temporal variance, lag-1 autocorrelation), and trait-distribution diagnostics.
# Run:  julia --project=. --threads=auto src/production_sweep.jl
include(joinpath(@__DIR__, "heterogeneous_model_v2.jl"))
using Statistics, DataFrames, CSV, Printf

const SIGMA_MEAN=0.7
const SIGMA_LIST=collect(0.0:0.025:0.45)
const NOISE_LIST=[0.3,0.5,0.7]
const N_AGENTS=200; const N_SEEDS=20
const N_TOTAL=60000; const N_WARMUP=30000
const OUTDIR=joinpath(@__DIR__,"..","results","production")

lag1(x)=cor(@view(x[1:end-1]),@view(x[2:end]))

function run_one(; sigma_std, noise, seed)
    model, sv = create_sheep_model(; N=N_AGENTS, noise=noise,
        σ_mean=SIGMA_MEAN, σ_std=sigma_std, seed=seed)
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
raw=DataFrame(res); CSV.write(joinpath(OUTDIR,"sweep_replicates.csv"),raw)
g=groupby(raw,[:noise,:sigma_std])
summ=combine(g, :phi=>mean=>:phi_mean, :phi=>std=>:phi_sd,
    :phi=>(x->N_AGENTS*var(x))=>:chi_seed, :phi_tempvar=>mean=>:tempvar,
    :ar1=>mean=>:ar1, :frac_lo=>mean=>:frac_lo, :frac_hi=>mean=>:frac_hi,
    :phi=>length=>:n)
sort!(summ,[:noise,:sigma_std]); CSV.write(joinpath(OUTDIR,"sweep_condition_means.csv"),summ)
println("\n  η=0.5 equilibrated curve:")
println("  sigma | phi_mean |  sd   | chi_seed |  ar1  | %<0.2")
println("  "*"-"^56)
for row in eachrow(summ[summ.noise.==0.5,:])
    @printf("  %.3f | %.4f  | %.4f | %.4f  | %.4f | %4.1f%%\n",
        row.sigma_std,row.phi_mean,row.phi_sd,row.chi_seed,row.ar1,100*row.frac_lo)
end
println("\n  wrote results/production/sweep_replicates.csv + sweep_condition_means.csv")
