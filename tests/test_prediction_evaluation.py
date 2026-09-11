import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from prediction_evaluation import score_predictions, compare_models


def predictions():
    rows = []
    for bout, count in [('short', 2), ('long', 20)]:
        for i in range(count):
            for model, error in [('M0', 0.5), ('M3', 0.2 if bout == 'short' else 0.6)]:
                rows.append(dict(group_id='g1', bout_id=bout, individual_id='a',
                                 timestamp=f'2026-01-01T00:00:{i:02d}Z', model=model,
                                 observed_heading=np.pi - 0.01,
                                 predicted_heading=-np.pi - 0.01 + error))
    return pd.DataFrame(rows)


class PredictionTests(unittest.TestCase):
    def test_equal_block_paired_comparison(self):
        scores = score_predictions(predictions())
        result = compare_models(scores, 'M0', 'M3')
        self.assertAlmostEqual(result['mean_delta_mae'], -0.1)
        self.assertEqual(result['n_blocks'], 2)
        self.assertEqual(result, compare_models(scores, 'M0', 'M3'))
        self.assertLessEqual(result['ci95_low'], result['mean_delta_mae'])
        self.assertGreaterEqual(result['ci95_high'], result['mean_delta_mae'])

    def test_missing_prediction_rejected(self):
        with self.assertRaisesRegex(ValueError, 'identical observation'):
            score_predictions(predictions().iloc[1:])

    def test_disagreeing_observations_rejected(self):
        frame = predictions()
        frame.loc[1, 'observed_heading'] = 0
        with self.assertRaisesRegex(ValueError, 'disagree'):
            score_predictions(frame)

    def test_duplicate_and_nonfinite_rejected(self):
        frame = predictions()
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            score_predictions(pd.concat([frame, frame.iloc[[0]]]))
        frame.loc[0, 'predicted_heading'] = np.nan
        with self.assertRaisesRegex(ValueError, 'finite'):
            score_predictions(frame)

    def test_missing_model_and_single_block_rejected(self):
        scores = score_predictions(predictions())
        with self.assertRaisesRegex(ValueError, 'identical biological blocks'):
            compare_models(scores, 'M0', 'absent')
        with self.assertRaisesRegex(ValueError, 'identical biological blocks'):
            compare_models(scores[scores.bout_id == 'short'], 'M0', 'M3')
