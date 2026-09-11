"""Small, explicit identifiability tools for the collective-motion model.

These functions operate on one-step heading updates. They are intentionally separate
from the ABM engine so parameter-recovery tests can be run before fitting animal data.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar


def wrap_angle(angle):
    """Wrap angles to [-pi, pi)."""
    angle = np.asarray(angle, dtype=float)
    return (angle + np.pi) % (2 * np.pi) - np.pi


def circular_error(observed, predicted):
    """Signed shortest angular difference, observed minus predicted."""
    return wrap_angle(np.asarray(observed, float) - np.asarray(predicted, float))


def blended_heading(self_heading, neighbour_x, neighbour_y, responsiveness):
    """Deterministic heading under the model's focal-responsiveness rule.

    neighbour_x and neighbour_y are the components of the already-normalized weighted
    neighbour vector. If the blend is numerically zero, the self heading is retained.
    """
    self_heading = np.asarray(self_heading, dtype=float)
    neighbour_x = np.asarray(neighbour_x, dtype=float)
    neighbour_y = np.asarray(neighbour_y, dtype=float)
    self_heading, neighbour_x, neighbour_y = np.broadcast_arrays(
        self_heading, neighbour_x, neighbour_y
    )
    r = float(responsiveness)
    if not np.isfinite(r) or not 0.0 <= r <= 1.0:
        raise ValueError("responsiveness must be finite and in [0,1]")
    if not (
        np.isfinite(self_heading).all()
        and np.isfinite(neighbour_x).all()
        and np.isfinite(neighbour_y).all()
    ):
        raise ValueError("finite headings and neighbour vectors required")

    x = (1.0 - r) * np.cos(self_heading) + r * neighbour_x
    y = (1.0 - r) * np.sin(self_heading) + r * neighbour_y
    out = np.arctan2(y, x)
    zero = np.hypot(x, y) <= 10 * np.finfo(float).eps
    return np.where(zero, self_heading, out)


def fit_responsiveness(self_heading, neighbour_x, neighbour_y, observed_heading):
    """Estimate one shared responsiveness from one-step heading observations.

    The criterion is mean squared circular error. This is a parameter-recovery tool,
    not a complete likelihood for sheep data. Observation error, temporal dependence,
    missingness and movement-state structure must be handled in an empirical model.
    """
    self_heading = np.asarray(self_heading, dtype=float)
    neighbour_x = np.asarray(neighbour_x, dtype=float)
    neighbour_y = np.asarray(neighbour_y, dtype=float)
    observed_heading = np.asarray(observed_heading, dtype=float)
    if not (
        self_heading.shape
        == neighbour_x.shape
        == neighbour_y.shape
        == observed_heading.shape
    ):
        raise ValueError("all arrays must have matching shapes")
    if self_heading.ndim != 1 or len(self_heading) < 3:
        raise ValueError("at least three one-dimensional observations are required")
    if not all(
        np.isfinite(a).all()
        for a in (self_heading, neighbour_x, neighbour_y, observed_heading)
    ):
        raise ValueError("finite observations required")

    def objective(r):
        pred = blended_heading(self_heading, neighbour_x, neighbour_y, r)
        err = circular_error(observed_heading, pred)
        return float(np.mean(err**2))

    # A bounded local optimizer assumes a unimodal objective. Circular residuals
    # can violate that assumption, so profile the interval and refine each basin.
    grid = np.linspace(0.0, 1.0, 1001)
    loss = np.array([objective(r) for r in grid])
    if np.ptp(loss) <= 1e-12:
        raise ValueError("Responsiveness is not identifiable from these observations: flat loss")
    candidates = [(float(loss[0]), 0.0), (float(loss[-1]), 1.0)]
    for i in range(1, len(grid) - 1):
        if loss[i] <= loss[i - 1] and loss[i] <= loss[i + 1]:
            result = minimize_scalar(objective, bounds=(grid[i - 1], grid[i + 1]),
                                     method="bounded", options={"xatol": 1e-10})
            if not result.success:
                raise RuntimeError(f"responsiveness optimization failed: {result.message}")
            candidates.append((float(result.fun), float(result.x)))
    value, estimate = min(candidates)
    near_optimal = grid[loss <= value + 1e-8]
    return {
        "responsiveness": estimate,
        "mean_squared_circular_error": value,
        "n": int(len(self_heading)),
        "boundary_optimum": estimate in (0.0, 1.0),
        "profile_loss_range": float(np.ptp(loss)),
        # A numerical ambiguity screen, not a confidence interval.
        "ambiguous_profile": bool(len(near_optimal) > 1 and np.ptp(near_optimal) > 0.01),
    }


def weighted_neighbour_vector(headings, tie_weights, influence_weights):
    """Return normalized weighted heading vector for one focal individual.

    This mirrors the product A_ij * q_j used by the ABM. Zero total weight returns
    a zero vector so the caller can apply the model's retain-self fallback.
    """
    headings = np.asarray(headings, dtype=float)
    ties = np.asarray(tie_weights, dtype=float)
    influence = np.asarray(influence_weights, dtype=float)
    if headings.ndim != 1 or ties.shape != headings.shape or influence.shape != headings.shape:
        raise ValueError("headings, tie weights and influence weights must be matching vectors")
    if not all(np.isfinite(a).all() for a in (headings, ties, influence)):
        raise ValueError("finite values required")
    if np.any(ties < 0) or np.any(influence < 0):
        raise ValueError("weights must be nonnegative")
    # Log weights avoid overflow/underflow in finite A*q products.
    positive = (ties > 0) & (influence > 0)
    if not positive.any():
        return np.array([0.0, 0.0])
    log_weights = np.log(ties[positive]) + np.log(influence[positive])
    weights = np.zeros_like(ties)
    weights[positive] = np.exp(log_weights - log_weights.max())
    total = float(weights.sum())
    if total <= 0:
        return np.array([0.0, 0.0])
    return np.array(
        [
            np.sum(weights * np.cos(headings)) / total,
            np.sum(weights * np.sin(headings)) / total,
        ],
        dtype=float,
    )


def equivalent_tie_influence_parameterization(tie_matrix, influence_weights, scales):
    """Construct an observationally equivalent A,q parameterization.

    For positive column scales c_j, A'_ij=A_ij*c_j and q'_j=q_j/c_j. Their product
    is unchanged for every i,j. This demonstrates a structural non-identifiability
    in the unconstrained model, rather than merely a numerical fitting problem.
    """
    ties = np.asarray(tie_matrix, dtype=float)
    influence = np.asarray(influence_weights, dtype=float)
    scales = np.asarray(scales, dtype=float)
    if (ties.ndim != 2 or influence.ndim != 1 or scales.ndim != 1
            or ties.shape[1] != influence.size or influence.size != scales.size):
        raise ValueError("tie matrix columns, influence weights and scales must agree")
    if not (
        np.isfinite(ties).all()
        and np.isfinite(influence).all()
        and np.isfinite(scales).all()
    ):
        raise ValueError("finite values required")
    if np.any(ties < 0) or np.any(influence < 0) or np.any(scales <= 0):
        raise ValueError("ties/influence must be nonnegative and scales strictly positive")
    return ties * scales[np.newaxis, :], influence / scales
