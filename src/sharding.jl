"""Utilities for splitting deterministic simulation job lists across compute tasks."""

function shard_spec()
    count = try
        parse(Int, get(ENV, "ABM_SHARD_COUNT", "1"))
    catch
        throw(ArgumentError("ABM_SHARD_COUNT must be an integer"))
    end
    index = try
        parse(Int, get(ENV, "ABM_SHARD_INDEX", "1"))
    catch
        throw(ArgumentError("ABM_SHARD_INDEX must be an integer"))
    end
    count >= 1 || throw(ArgumentError("ABM_SHARD_COUNT must be >= 1"))
    1 <= index <= count || throw(ArgumentError("ABM_SHARD_INDEX must be between 1 and ABM_SHARD_COUNT"))
    return (index=index, count=count)
end

function select_shard(jobs, spec=shard_spec())
    selected = [jobs[k] for k in eachindex(jobs) if mod(k - 1, spec.count) + 1 == spec.index]
    isempty(selected) && throw(ArgumentError("Selected shard contains no jobs; reduce ABM_SHARD_COUNT"))
    return selected
end

function shard_dir(base, spec=shard_spec())
    spec.count == 1 && return base
    tag = "shard_" * lpad(string(spec.index), 3, '0') * "_of_" * lpad(string(spec.count), 3, '0')
    return joinpath(base, tag)
end
