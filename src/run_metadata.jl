using TOML, SHA, Dates

function _git_commit(root)
    if haskey(ENV, "GITHUB_SHA") && !isempty(ENV["GITHUB_SHA"])
        return ENV["GITHUB_SHA"]
    end
    try
        return strip(read(`git -C $root rev-parse HEAD`, String))
    catch
        return "unavailable"
    end
end

_toml_safe(x::Symbol) = string(x)
_toml_safe(x::Tuple) = [_toml_safe(v) for v in x]
_toml_safe(x::AbstractVector) = [_toml_safe(v) for v in x]
_toml_safe(x::AbstractDict) = Dict(string(k) => _toml_safe(v) for (k, v) in x)
_toml_safe(x) = x

"""Record source, environment and experimental identity for newly generated runs.

Historical outputs are never assigned provenance that was not actually recorded.
"""
function write_run_metadata(outdir; kwargs...)
    root = normpath(joinpath(@__DIR__, ".."))
    source_hashes = Dict(relpath(p, root) => bytes2hex(sha256(read(p)))
        for p in readdir(@__DIR__; join=true) if endswith(p, ".jl"))
    metadata = Dict{String, Any}(string(k) => _toml_safe(v) for (k, v) in kwargs)
    merge!(metadata, Dict(
        "recorded_utc" => string(now(UTC)),
        "git_commit" => _git_commit(root),
        "julia_version" => string(VERSION),
        "machine" => string(Sys.MACHINE),
        "kernel" => string(Sys.KERNEL),
        "threads" => Threads.nthreads(),
        "update_convention_default" => "sequential in-place, Schedulers.fastest",
        "trait_mean_target" => 0.7,
        "speed" => 0.03,
        "radius" => 1.0,
        "dt" => 1.0,
        "periodic" => true,
        "source_sha256" => source_hashes,
        "project_sha256" => bytes2hex(sha256(read(joinpath(root, "Project.toml")))),
        "manifest_sha256" => bytes2hex(sha256(read(joinpath(root, "Manifest.toml")))),
    ))
    mkpath(outdir)
    open(joinpath(outdir, "run_metadata.toml"), "w") do io
        TOML.print(io, metadata)
    end
end
