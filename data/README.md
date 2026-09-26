# Data directory policy

This directory is a documentation placeholder only.

The public repository must not contain restricted raw sheep trajectories, precise farm coordinates, identifying information, credentials or other protected study data.

## Recommended server-side data layout

The actual approved research environment can use a structure such as:

```text
data/
  raw/          # immutable source files
  external/     # external reference data, subject to licence
  interim/      # auditable intermediate products
  processed/    # analysis-ready versioned tables
  metadata/     # dictionaries, manifests, provenance
```

Do not edit files in `raw/` in place.

Each processed dataset should be reproducible from permitted source data using version-controlled code.

## Public GitHub content

Only commit:

- schemas
- synthetic examples
- explicitly releasable example data
- dictionaries without restricted information
- checksums or manifests that do not expose sensitive paths or identifiers
- approved derived summary data

See `docs/EMPIRICAL_SHEEP_WORKSTREAM.md` and `docs/TRAJECTORY_DATA_SPEC.md`.
