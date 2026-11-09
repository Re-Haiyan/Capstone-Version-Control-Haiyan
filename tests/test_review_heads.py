from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/sentiment-analysis'))
sys.path.insert(0, str(ROOT / 'scripts'))
from defaketive_sentiment import registry  # noqa: E402
from defaketive_sentiment.review_heads import feature_vector, is_template, star_conflict  # noqa: E402
from review_queue import kappa, priority  # noqa: E402


class ReviewHeadsTest(unittest.TestCase):
    def test_option_is_opt_in(self):
        self.assertIn(registry.XLMR_HEADS_SENTIMENT, registry.SENTIMENT_MODELS)
        self.assertEqual(registry.DEFAULT_SENTIMENT, registry.XLMR_SENTIMENT)

    def test_feature_vector_shape(self):
        vector = feature_vector(np.zeros(768, dtype=np.float32), np.array([0.2, 0.3, 0.5], dtype=np.float32))
        self.assertEqual(vector.shape, (771,))
        self.assertTrue(np.isfinite(vector).all())

    def test_template_and_star_conflict(self):
        self.assertTrue(is_template('Fast charging speed, Sleek design, Great value for money,'))
        self.assertFalse(is_template('ayaw gumana, sayang pera'))
        self.assertTrue(star_conflict('positive', 1))
        self.assertTrue(star_conflict('negative', '5'))
        self.assertFalse(star_conflict('negative', 1))
        self.assertFalse(star_conflict('positive', None))


class ReviewQueueTest(unittest.TestCase):
    def test_kappa(self):
        self.assertEqual(kappa([('a', 'a'), ('b', 'b')]), 1.0)
        self.assertLess(kappa([('a', 'b'), ('b', 'a'), ('a', 'a'), ('b', 'b')]), 0.01)

    def test_priority_puts_doubtful_rows_first(self):
        sure = {'ai_sentiment': 'positive', 'live_agrees': 'True', 'ai_confidence': 'high', 'star_text_mismatch': 'False'}
        doubt = {'ai_sentiment': 'unclear', 'live_agrees': 'False', 'ai_confidence': 'low', 'star_text_mismatch': 'True'}
        self.assertGreater(priority(doubt), priority(sure))


if __name__ == '__main__':
    unittest.main()
