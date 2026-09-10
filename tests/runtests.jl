using Test
# Parse every Julia entry point before running anything expensive.
@testset "Julia entry points parse" begin
    for file in filter(p -> endswith(p, ".jl"), readdir(joinpath(@__DIR__, "..", "src"); join=true))
        tree = Meta.parseall(read(file, String))
        has_parse_error(x) = x isa Expr && (x.head in (:error, :incomplete) || any(has_parse_error, x.args))
        @test !has_parse_error(tree)
    end
end
include(joinpath(@__DIR__, "..", "src", "heterogeneous_model_v2.jl"))

@testset "Trait distribution and input validation" begin
    d = beta_from_mean_std(0.7, 0.2)
    @test mean(d) ≈ 0.7
    @test std(d) ≈ 0.2
    @test beta_from_mean_std(0, 0) === nothing
    @test beta_from_mean_std(1, 0) === nothing
    for (mu,s) in [(0.7,-0.1), (1.1,0.0), (0.7,0.5), (NaN,0.1), (0.7,Inf)]
        @test_throws ArgumentError beta_from_mean_std(mu,s)
    end
    @test_throws ArgumentError create_sheep_model(N=0)
    @test_throws ArgumentError create_sheep_model(speed=0.0)
    @test_throws ArgumentError create_sheep_model(noise=-1.0)
    @test_throws ArgumentError run_single_seed(σ_mean=0.7,σ_std=0.1,seed=1,n_steps=10)
end

@testset "Determinism and physical invariants" begin
    a,wa = create_sheep_model(N=12, seed=9)
    b,wb = create_sheep_model(N=12, seed=9)
    @test wa == wb
    for _ in 1:30
        step!(a); step!(b)
    end
    @test a.order_history == b.order_history
    @test length(a.order_history) == 30
    @test all(x -> isfinite(x) && 0 <= x <= 1+1e-12, a.order_history)
    for agent in allagents(a)
        @test all(x -> 0 <= x < 20, agent.pos)
        @test hypot(agent.vel...) ≈ a.speed
    end
end

@testset "Isolated zero-noise motion and homogeneous traits" begin
    m,w = create_sheep_model(N=1, noise=0.0, σ_std=0.0)
    agent = first(allagents(m)); theta = agent.θ
    for _ in 1:10; step!(m); end
    @test w == [0.7]
    @test agent.θ ≈ theta
    @test all(x -> isapprox(x,1.0), m.order_history)
end

@testset "Exact periodic interaction radius" begin
    m,_ = create_sheep_model(N=3, L=20.0, radius=1.0)
    move_agent!(m[1], (0.1, 0.1), m)
    move_agent!(m[2], (19.6, 0.1), m) # periodic distance 0.5
    move_agent!(m[3], (1.2, 0.1), m)  # distance 1.1, outside radius
    ids = Set(a.id for a in nearby_agents(m[1],m,m.radius; search=m.neighbor_search))
    @test m.neighbor_search == :exact
    @test 2 in ids
    @test !(3 in ids)
    @test !(1 in ids)
    old,_ = create_sheep_model(N=3, neighbor_search=:approximate)
    @test old.neighbor_search == :approximate
    @test_throws ArgumentError create_sheep_model(neighbor_search=:unknown)
end
