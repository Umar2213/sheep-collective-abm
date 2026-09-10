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
include(joinpath(@__DIR__, "..", "src", "diagnostics.jl"))
include(joinpath(@__DIR__, "..", "src", "sharding.jl"))

@testset "Trait distribution and input validation" begin
    d = beta_from_mean_std(0.7, 0.2)
    @test mean(d) ≈ 0.7
    @test std(d) ≈ 0.2
    @test beta_from_mean_std(0, 0) === nothing
    @test beta_from_mean_std(1, 0) === nothing
    for (mu, s) in [(0.7, -0.1), (1.1, 0.0), (0.7, 0.5), (NaN, 0.1), (0.7, Inf)]
        @test_throws ArgumentError beta_from_mean_std(mu, s)
    end
    @test_throws ArgumentError create_sheep_model(N=0)
    @test_throws ArgumentError create_sheep_model(speed=0.0)
    @test_throws ArgumentError create_sheep_model(noise=-1.0)
    @test_throws ArgumentError create_sheep_model(update_mode=:unknown)
    @test_throws ArgumentError run_single_seed(σ_mean=0.7, σ_std=0.1, seed=1, n_steps=10)
end

@testset "Determinism and physical invariants" begin
    a, wa = create_sheep_model(N=12, seed=9)
    b, wb = create_sheep_model(N=12, seed=9)
    @test wa == wb
    for _ in 1:30
        step!(a)
        step!(b)
    end
    @test a.order_history == b.order_history
    @test length(a.order_history) == 30
    @test all(x -> isfinite(x) && 0 <= x <= 1 + 1e-12, a.order_history)
    for agent in allagents(a)
        @test all(x -> 0 <= x < 20, agent.pos)
        @test hypot(agent.vel...) ≈ a.speed
    end
end

@testset "Independent random streams" begin
    a, wa = create_sheep_model(N=16, σ_std=0.2, seed=1,
        trait_seed=101, init_seed=202, dynamic_seed=303)
    b, wb = create_sheep_model(N=16, σ_std=0.2, seed=999,
        trait_seed=102, init_seed=202, dynamic_seed=303)
    @test wa != wb
    @test [x.pos for x in allagents(a)] == [x.pos for x in allagents(b)]
    @test [x.θ for x in allagents(a)] == [x.θ for x in allagents(b)]

    c, wc = create_sheep_model(N=16, σ_std=0.2, seed=999,
        trait_seed=101, init_seed=203, dynamic_seed=303)
    @test wa == wc
    @test [x.pos for x in allagents(a)] != [x.pos for x in allagents(c)]
end

@testset "Isolated zero-noise motion and homogeneous traits" begin
    m, w = create_sheep_model(N=1, noise=0.0, σ_std=0.0)
    agent = first(allagents(m))
    theta = agent.θ
    for _ in 1:10
        step!(m)
    end
    @test w == [0.7]
    @test agent.θ ≈ theta
    @test all(x -> isapprox(x, 1.0), m.order_history)
end

@testset "Exact periodic interaction radius" begin
    m, _ = create_sheep_model(N=3, L=20.0, radius=1.0)
    move_agent!(m[1], (0.1, 0.1), m)
    move_agent!(m[2], (19.6, 0.1), m) # periodic distance 0.5
    move_agent!(m[3], (1.2, 0.1), m)  # distance 1.1, outside radius
    ids = Set(a.id for a in nearby_agents(m[1], m, m.radius; search=m.neighbor_search))
    @test m.neighbor_search == :exact
    @test 2 in ids
    @test !(3 in ids)
    @test !(1 in ids)
    old, _ = create_sheep_model(N=3, neighbor_search=:approximate)
    @test old.neighbor_search == :approximate
    @test_throws ArgumentError create_sheep_model(neighbor_search=:unknown)
end

@testset "Uniform social ties reduce exactly to the baseline" begin
    N = 10
    A = ones(N, N)
    for i in 1:N
        A[i, i] = 0.0
    end
    base, wb = create_sheep_model(N=N, seed=77, σ_std=0.15,
        trait_seed=11, init_seed=22, dynamic_seed=33)
    tied, wt = create_sheep_model(N=N, seed=77, σ_std=0.15,
        trait_seed=11, init_seed=22, dynamic_seed=33, social_ties=A,
        influence_weights=ones(N))
    @test wb == wt
    for _ in 1:25
        step!(base)
        step!(tied)
    end
    @test base.order_history == tied.order_history
    @test [x.θ for x in allagents(base)] == [x.θ for x in allagents(tied)]
    @test [x.pos for x in allagents(base)] == [x.pos for x in allagents(tied)]
end

@testset "Directed ties and outgoing influence are validated" begin
    N = 5
    @test_throws ArgumentError create_sheep_model(N=N, social_ties=ones(N - 1, N - 1))
    bad = ones(N, N)
    bad[1, 2] = -1
    @test_throws ArgumentError create_sheep_model(N=N, social_ties=bad)
    @test_throws ArgumentError create_sheep_model(N=N, influence_weights=ones(N - 1))

    A = ones(N, N)
    A[1, 2] = 0.0
    m, _ = create_sheep_model(N=N, social_ties=A, influence_weights=collect(1.0:N))
    @test m.social_ties[1, 1] == 0.0
    @test m.social_ties[1, 2] == 0.0
    @test m[5].influence_weight == 5.0
end

@testset "Synchronous update is reproducible and distinct control" begin
    a, _ = create_sheep_model(N=20, seed=5, update_mode=:synchronous)
    b, _ = create_sheep_model(N=20, seed=5, update_mode=:synchronous)
    for _ in 1:20
        step!(a)
        step!(b)
    end
    @test a.order_history == b.order_history
    @test length(a.order_history) == 20

    seq, _ = create_sheep_model(N=20, seed=5, update_mode=:sequential)
    for _ in 1:20
        step!(seq)
    end
    @test seq.order_history != a.order_history
end

@testset "Time-series diagnostics" begin
    x = collect(1.0:16.0)
    bm = block_means(x; nblocks=4)
    @test bm == [2.5, 6.5, 10.5, 14.5]
    @test autocorrelation_at_lag(fill(2.0, 8), 1) == 0.0
    @test integrated_autocorrelation_time([1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0]) == 1.0
    d = stationarity_diagnostics(x; nblocks=4, maxlag=3)
    @test d.ess > 0
    @test d.tau_int >= 1
    @test d.block_sd > 0
    @test d.half_drift > 0
    @test d.late_quarter_drift > 0
end

@testset "Deterministic condition sharding" begin
    old_count = get(ENV, "ABM_SHARD_COUNT", nothing)
    old_index = get(ENV, "ABM_SHARD_INDEX", nothing)
    try
        ENV["ABM_SHARD_COUNT"] = "3"
        ENV["ABM_SHARD_INDEX"] = "2"
        spec = shard_spec()
        @test spec == (index=2, count=3)
        @test select_shard(collect(1:8), spec) == [2, 5, 8]
        @test endswith(shard_dir("results", spec), "shard_002_of_003")
        ENV["ABM_SHARD_INDEX"] = "4"
        @test_throws ArgumentError shard_spec()
        ENV["ABM_SHARD_COUNT"] = "20"
        ENV["ABM_SHARD_INDEX"] = "20"
        @test_throws ArgumentError select_shard([1, 2], shard_spec())
    finally
        old_count === nothing ? pop!(ENV, "ABM_SHARD_COUNT", nothing) : (ENV["ABM_SHARD_COUNT"] = old_count)
        old_index === nothing ? pop!(ENV, "ABM_SHARD_INDEX", nothing) : (ENV["ABM_SHARD_INDEX"] = old_index)
    end
end
