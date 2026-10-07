"""Statistics for simulations; independent realizations are sampling units."""
import numpy as np


def level_crossing(x, y, level=0.9):
    """First downward crossing, NaN when the sampled range does not bracket it."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) != len(y) or len(x) < 2 or np.any(np.diff(x) <= 0):
        raise ValueError("Matching arrays and strictly increasing x required")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Finite values required")
    for i in range(len(x) - 1):
        if y[i] == level:
            return float(x[i])
        if y[i] > level >= y[i + 1]:
            return float(x[i] + (level - y[i]) * (x[i + 1] - x[i]) / (y[i + 1] - y[i]))
    return float(x[-1]) if y[-1] == level else np.nan


def zero_crossings(x, y):
    """All bracketed zeros, without a critical-point interpretation."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) != len(y) or np.any(np.diff(x) <= 0):
        raise ValueError("Matching arrays and strictly increasing x required")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Finite values required")
    if np.any((y[:-1] == 0) & (y[1:] == 0)):
        raise ValueError("Coincident interval has no isolated crossing")
    values = list(x[y == 0])
    for i in np.flatnonzero(y[:-1] * y[1:] < 0):
        values.append(x[i] - y[i] * (x[i + 1] - x[i]) / (y[i + 1] - y[i]))
    return sorted(set(float(v) for v in values))


def variance_components(phi, phi2, size):
    """Exact pooled decomposition, using population variance across realizations.

    This is not an unbiased disorder estimator. Stored phi2 is a temporal raw
    moment. Production chi_seed instead uses sample variance (ddof=1).
    """
    phi, phi2 = np.asarray(phi, float), np.asarray(phi2, float)
    within = phi2 - phi**2
    if np.any(within < -1e-10):
        raise ValueError("Second moment is smaller than squared mean")
    temporal = size * np.mean(np.maximum(within, 0))
    between = size * np.var(phi, ddof=0)
    return temporal, between, temporal + between


def paired_effect_summary(reference, alternative):
    """Summarize a matched control using one value from each paired realization.

    Returns mean difference, sample SD, standard error and a normal-approximation
    95% interval. The interval is descriptive for simulation replicates, not a
    substitute for biological replication.
    """
    reference = np.asarray(reference, float)
    alternative = np.asarray(alternative, float)
    if reference.shape != alternative.shape or reference.ndim != 1 or len(reference) < 2:
        raise ValueError("Matching one-dimensional arrays with at least two pairs required")
    if not np.isfinite(reference).all() or not np.isfinite(alternative).all():
        raise ValueError("Finite values required")
    delta = alternative - reference
    mean = float(np.mean(delta))
    sd = float(np.std(delta, ddof=1))
    se = sd / np.sqrt(len(delta))
    return {
        "n": int(len(delta)),
        "mean_delta": mean,
        "sd_delta": sd,
        "se_delta": float(se),
        "ci95_low": float(mean - 1.96 * se),
        "ci95_high": float(mean + 1.96 * se),
    }


def convergence_flags(ess, block_sd, half_drift, late_quarter_drift,
                      *, min_ess=100.0, max_block_sd=0.02,
                      max_half_drift=0.02, max_late_drift=0.02):
    """Return transparent screening flags, not a convergence certificate.

    Thresholds are explicit arguments so analyses cannot silently change them.
    A flagged run requires inspection or a longer simulation. Passing all flags
    does not by itself prove stationarity.
    """
    arrays = [np.asarray(v, float) for v in (ess, block_sd, half_drift, late_quarter_drift)]
    if len({a.shape for a in arrays}) != 1:
        raise ValueError("Diagnostic arrays must have matching shapes")
    if not all(np.isfinite(a).all() for a in arrays):
        raise ValueError("Finite diagnostic values required")
    ess_a, block_a, half_a, late_a = arrays
    return {
        "low_ess": ess_a < min_ess,
        "high_block_sd": block_a > max_block_sd,
        "high_half_drift": half_a > max_half_drift,
        "high_late_drift": late_a > max_late_drift,
    }
