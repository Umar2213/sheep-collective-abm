using Test
using Statistics

include(joinpath(@__DIR__, "..", "src", "heterogeneous_model_v2.jl"))

@testset "Two-point population moments" begin
    for s in (0.05, 0.20, 0.45)
        p = two_point_from_mean_std(0.7, s)
        mu = p.p_high * p.high + (1 - p.p_high) * p.low
        v = p.p_high * (p.high - mu)^2 + (1 - p.p_high) * (p.low - mu)^2
        @test mu ≈ 0.7 atol=1e-12
        @test sqrt(v) ≈ s atol=1e-12
        @test 0 <= p.low < 0.7 < p.high <= 1
        @test 0 < p.p_high < 1
    end
    @test two_point_from_mean_std(0.7, 0.0) === nothing
    @test_throws ArgumentError two_point_from_mean_std(0.7, 0.5)
end

@testset "Distribution family control" begin
    beta_model, beta_traits = create_sheep_model(
        N=50, σ_mean=0.7, σ_std=0.2,
        trait_seed=101, init_seed=202, dynamic_seed=303,
        trait_distribution=:beta,
    )
    point_model, point_traits = create_sheep_model(
        N=50, σ_mean=0.7, σ_std=0.2,
        trait_seed=101, init_seed=202, dynamic_seed=303,
        trait_distribution=:two_point,
    )
    @test beta_traits != point_traits
    @test beta_model.trait_distribution == :beta
    @test point_model.trait_distribution == :two_point
    @test [a.pos for a in allagents(beta_model)] == [a.pos for a in allagents(point_model)]
    @test [a.θ for a in allagents(beta_model)] == [a.θ for a in allagents(point_model)]
    @test length(unique(point_traits)) <= 2
    @test_throws ArgumentError create_sheep_model(trait_distribution=:unknown)
end
