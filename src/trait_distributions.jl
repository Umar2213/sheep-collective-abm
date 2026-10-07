# Responsiveness-distribution controls.
# The primary model uses Beta heterogeneity. A two-point alternative matches the
# same population mean and variance while having deliberately different shape/tails.

"""Parameters of a two-point distribution on {low, 1} with target mean and std."""
function two_point_from_mean_std(μ::Real, s::Real)
    isfinite(μ) && 0 <= μ <= 1 || throw(ArgumentError("mean must be finite and in [0,1]"))
    isfinite(s) && s >= 0 || throw(ArgumentError("std must be finite and nonnegative"))
    v = s^2
    v == 0 && return nothing
    max_v = μ * (1 - μ)
    v < max_v || throw(ArgumentError("variance must be smaller than μ(1-μ) for the interior control"))
    0 < μ < 1 || throw(ArgumentError("positive variance requires mean strictly inside (0,1)"))

    # For a two-point variable supported on a < μ < b, variance=(μ-a)(b-μ).
    # Setting b=1 gives an exact population-moment match throughout the admissible
    # variance range, with low approaching 0 as variance approaches its maximum.
    low = μ - v / (1 - μ)
    p_high = (μ - low) / (1 - low)
    return (low=Float64(low), high=1.0, p_high=Float64(p_high))
end

"""Draw one responsiveness value using a single Uniform(0,1) variate.

Using one base uniform per agent makes distribution-family controls quantile-matched:
the same trait seed gives the same latent rank across Beta and two-point families.
"""
function draw_responsiveness(rng::AbstractRNG, family::Symbol, μ::Real, s::Real)
    family in (:beta, :two_point) ||
        throw(ArgumentError("trait_distribution must be :beta or :two_point"))
    s == 0 && return Float64(μ)
    u = rand(rng)
    if family == :beta
        d = beta_from_mean_std(μ, s)
        return Float64(quantile(d, u))
    end
    pars = two_point_from_mean_std(μ, s)
    return u < pars.p_high ? pars.high : pars.low
end
