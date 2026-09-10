using Statistics

"""Lag-k autocorrelation using the population autocovariance convention."""
function autocorrelation_at_lag(x::AbstractVector{<:Real}, lag::Integer)
    n = length(x)
    0 <= lag < n || throw(ArgumentError("lag must satisfy 0 <= lag < length(x)"))
    n >= 2 || throw(ArgumentError("at least two observations are required"))
    y = Float64.(x)
    all(isfinite, y) || throw(ArgumentError("finite observations are required"))
    μ = mean(y)
    centered = y .- μ
    γ0 = sum(abs2, centered) / n
    γ0 > 0 || return lag == 0 ? 1.0 : 0.0
    lag == 0 && return 1.0
    γk = sum(centered[1:(n-lag)] .* centered[(lag+1):n]) / (n - lag)
    return γk / γ0
end

"""Estimate integrated autocorrelation time by summing positive ACF terms.

This is a diagnostic, not a proof of convergence. The sum stops at the first
non-positive or non-finite lag correlation.
"""
function integrated_autocorrelation_time(x::AbstractVector{<:Real}; maxlag=nothing)
    n = length(x)
    n >= 4 || throw(ArgumentError("at least four observations are required"))
    ml = maxlag === nothing ? min(1000, n ÷ 4) : Int(maxlag)
    1 <= ml < n || throw(ArgumentError("maxlag must satisfy 1 <= maxlag < length(x)"))
    τ = 1.0
    for lag in 1:ml
        ρ = autocorrelation_at_lag(x, lag)
        (!isfinite(ρ) || ρ <= 0) && break
        τ += 2ρ
    end
    return max(1.0, τ)
end

function effective_sample_size(x::AbstractVector{<:Real}; maxlag=nothing)
    τ = integrated_autocorrelation_time(x; maxlag=maxlag)
    return min(Float64(length(x)), length(x) / τ)
end

"""Contiguous block means. Any remainder is distributed over the earliest blocks."""
function block_means(x::AbstractVector{<:Real}; nblocks::Integer=8)
    n = length(x)
    2 <= nblocks <= n || throw(ArgumentError("nblocks must satisfy 2 <= nblocks <= length(x)"))
    y = Float64.(x)
    all(isfinite, y) || throw(ArgumentError("finite observations are required"))
    q, r = divrem(n, nblocks)
    out = Float64[]
    start = 1
    for b in 1:nblocks
        len = q + (b <= r ? 1 : 0)
        stop = start + len - 1
        push!(out, mean(@view y[start:stop]))
        start = stop + 1
    end
    return out
end

"""Return conservative descriptive diagnostics for a post-warmup time series."""
function stationarity_diagnostics(x::AbstractVector{<:Real}; nblocks::Integer=8, maxlag=nothing)
    n = length(x)
    n >= max(8, nblocks) || throw(ArgumentError("measurement series is too short"))
    y = Float64.(x)
    all(isfinite, y) || throw(ArgumentError("finite observations are required"))
    half = n ÷ 2
    q = n ÷ 4
    blocks = block_means(y; nblocks=nblocks)
    τ = integrated_autocorrelation_time(y; maxlag=maxlag)
    return (
        ar1=autocorrelation_at_lag(y, 1),
        tau_int=τ,
        ess=min(Float64(n), n / τ),
        block_sd=std(blocks),
        half_drift=abs(mean(@view y[1:half]) - mean(@view y[(n-half+1):n])),
        late_quarter_drift=abs(mean(@view y[(n-2q+1):(n-q)]) - mean(@view y[(n-q+1):n])),
    )
end
