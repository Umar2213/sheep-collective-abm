using TOML, SHA, Dates

"Record the environment and source identity for future runs; never backfill legacy provenance."
function write_run_metadata(outdir; kwargs...)
    root = normpath(joinpath(@__DIR__, ".."))
    source_hashes = Dict(basename(p) => bytes2hex(sha256(read(p)))
        for p in readdir(@__DIR__; join=true) if endswith(p, ".jl"))
    metadata = Dict{String,Any}(string(k) => v for (k,v) in kwargs)
    merge!(metadata, Dict("julia_version" => string(VERSION),
        "recorded_utc" => string(now(UTC)), "threads" => Threads.nthreads(),
        "update_convention" => "sequential in-place, Schedulers.fastest",
        "trait_mean_target" => 0.7, "speed" => 0.03, "radius" => 1.0,
        "dt" => 1.0, "periodic" => true, "source_sha256" => source_hashes,
        "manifest_sha256" => bytes2hex(sha256(read(joinpath(root,"Manifest.toml"))))))
    open(joinpath(outdir, "run_metadata.toml"), "w") do io
        TOML.print(io, metadata)
    end
end
