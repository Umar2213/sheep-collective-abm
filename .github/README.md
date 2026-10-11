# Automated repository checks

| Workflow | Purpose |
|---|---|
| [checks.yml](workflows/checks.yml) | Python and Julia tests, synthetic analysis, output verification, stored-data auditing, and simulation smoke/shard checks |
| [benchmark.yml](workflows/benchmark.yml) | Controlled simulation compute benchmarks |
| [scientific-shard.yml](workflows/scientific-shard.yml) | Configured simulation-shard execution |

A successful check verifies the software paths covered by that run. Synthetic
demonstrations, benchmarks and smoke experiments do not establish empirical validity,
parameter identifiability or a new biological result.

Use branches and pull requests for substantial changes. Consult
[the contribution guide](../CONTRIBUTING.md) and
[the simulation protocol](../docs/EXPERIMENT_PROTOCOL.md) before running full experiments.
Do not upload restricted empirical data or credentials as workflow inputs or artifacts.
