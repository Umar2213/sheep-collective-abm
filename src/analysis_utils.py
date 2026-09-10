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
            return float(x[i] + (level-y[i])*(x[i+1]-x[i])/(y[i+1]-y[i]))
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
        values.append(x[i] - y[i]*(x[i+1]-x[i])/(y[i+1]-y[i]))
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
