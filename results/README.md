# Simulation results and audit tables

These folders retain historical simulation outputs for reproducibility. They do not
contain measured sheep trajectories or establish biological validation.

| Folder | Contents |
|---|---|
| `production/` | Historical production replicates and condition summaries |
| `fss/` | Historical finite-size replicates and condition summaries |
| `diagnostics/` | Equilibration and relaxation summaries and time series |
| `snapshots/` | Simulated states used for snapshot figures |
| `audit/` | Data checks, variance decomposition and stationarity-review flags |

The historical production and finite-size tables used the legacy approximate neighbour
search. They are not outputs of the corrected exact-radius model. The audit flags
323 of 1,520 historical finite-size runs for drift; these tables do not establish a
phase transition.

See [the numerical audit](../docs/AUDIT.md) and
[the simulation protocol](../docs/EXPERIMENT_PROTOCOL.md) for interpretation and rerun
requirements. Keep new corrected runs in separate output directories and preserve their
configuration, seeds, source version and checksums.

Restricted empirical datasets and derived identifying coordinates belong in an approved
private data environment, not this directory.
