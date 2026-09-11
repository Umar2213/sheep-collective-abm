import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from identifiability import (
    blended_heading,
    circular_error,
    equivalent_tie_influence_parameterization,
    fit_responsiveness,
    weighted_neighbour_vector,
    wrap_angle,
)


class IdentifiabilityTests(unittest.TestCase):
    def test_angle_wrapping_and_circular_error(self):
        values = wrap_angle(np.array([-3 * np.pi, -np.pi, 0.0, np.pi, 3 * np.pi]))
        self.assertTrue(np.all(values >= -np.pi))
        self.assertTrue(np.all(values < np.pi))
        self.assertAlmostEqual(float(circular_error(-np.pi + 0.1, np.pi - 0.1)), 0.2)

    def test_exact_responsiveness_recovery(self):
        rng = np.random.default_rng(7)
        n = 300
        self_heading = rng.uniform(-np.pi, np.pi, n)
        neighbour_heading = rng.uniform(-np.pi, np.pi, n)
        neighbour_strength = rng.uniform(0.35, 1.0, n)
        neighbour_x = neighbour_strength * np.cos(neighbour_heading)
        neighbour_y = neighbour_strength * np.sin(neighbour_heading)
        true_r = 0.63
        observed = blended_heading(self_heading, neighbour_x, neighbour_y, true_r)
        fit = fit_responsiveness(self_heading, neighbour_x, neighbour_y, observed)
        self.assertAlmostEqual(fit["responsiveness"], true_r, places=5)
        self.assertLess(fit["mean_squared_circular_error"], 1e-10)

    def test_recovery_is_reasonable_with_noise(self):
        rng = np.random.default_rng(8)
        n = 1000
        self_heading = rng.uniform(-np.pi, np.pi, n)
        neighbour_heading = rng.uniform(-np.pi, np.pi, n)
        neighbour_strength = rng.uniform(0.5, 1.0, n)
        nx = neighbour_strength * np.cos(neighbour_heading)
        ny = neighbour_strength * np.sin(neighbour_heading)
        true_r = 0.35
        deterministic = blended_heading(self_heading, nx, ny, true_r)
        observed = wrap_angle(deterministic + rng.uniform(-0.08, 0.08, n))
        fit = fit_responsiveness(self_heading, nx, ny, observed)
        self.assertLess(abs(fit["responsiveness"] - true_r), 0.03)

    def test_uniform_weighted_vector(self):
        headings = np.array([0.0, np.pi / 2])
        out = weighted_neighbour_vector(headings, [1, 1], [1, 1])
        self.assertTrue(np.allclose(out, [0.5, 0.5]))
        zero = weighted_neighbour_vector(headings, [0, 0], [1, 1])
        self.assertTrue(np.allclose(zero, [0.0, 0.0]))

    def test_tie_influence_column_scaling_is_structurally_equivalent(self):
        rng = np.random.default_rng(9)
        n = 6
        ties = rng.uniform(0.1, 2.0, size=(n, n))
        influence = rng.uniform(0.2, 2.0, size=n)
        scales = rng.uniform(0.3, 3.0, size=n)
        new_ties, new_influence = equivalent_tie_influence_parameterization(
            ties, influence, scales
        )
        self.assertTrue(
            np.allclose(ties * influence[np.newaxis, :],
                        new_ties * new_influence[np.newaxis, :])
        )
        headings = rng.uniform(-np.pi, np.pi, n)
        for i in range(n):
            original = weighted_neighbour_vector(headings, ties[i], influence)
            transformed = weighted_neighbour_vector(headings, new_ties[i], new_influence)
            self.assertTrue(np.allclose(original, transformed))

    def test_bad_shapes_and_weights_are_rejected(self):
        with self.assertRaises(ValueError):
            weighted_neighbour_vector([0, 1], [1], [1, 1])
        with self.assertRaises(ValueError):
            equivalent_tie_influence_parameterization(np.ones((2, 2)), [1, 1], [1, 0])
        with self.assertRaises(ValueError):
            fit_responsiveness([0, 1], [1, 0], [0, 1], [0, 1])

    def test_flat_loss_is_not_an_estimate(self):
        with self.assertRaisesRegex(ValueError, "not identifiable"):
            fit_responsiveness(np.zeros(5), np.ones(5), np.zeros(5), np.zeros(5))

    def test_boundary_optima_are_considered(self):
        headings = np.linspace(-1, 1, 20)
        nx, ny = np.cos(headings + 0.8), np.sin(headings + 0.8)
        for r in [0.0, 1.0]:
            observed = blended_heading(headings, nx, ny, r)
            fit = fit_responsiveness(headings, nx, ny, observed)
            self.assertEqual(fit["responsiveness"], r)
            self.assertTrue(fit["boundary_optimum"])

    def test_large_finite_weights_do_not_overflow(self):
        out = weighted_neighbour_vector([0, np.pi / 2], [1e300, 1e300], [1e300, 1e300])
        np.testing.assert_allclose(out, [0.5, 0.5])

    def test_zero_blend_matches_julia_tolerance(self):
        theta = 1.0
        nx, ny = -np.cos(theta) + 2e-15, -np.sin(theta)
        self.assertEqual(float(blended_heading(theta, nx, ny, 0.5)), theta)


if __name__ == "__main__":
    unittest.main()
