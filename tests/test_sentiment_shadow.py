"""The opt-in sentiment calibrator in the pipeline: off by default, shadow changes nothing, 'on' says what it replaced."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from defaketive_sentiment import registry, sentiment_calibration as sc  # noqa: E402
from defaketive_sentiment.product_badges import ProductBadgeAggregator  # noqa: E402

ARTIFACT = ROOT / "research" / "artifacts" / "sentiment_calibrator_v1.joblib"
REVIEWS = ["Ang ganda ng product, sulit na sulit!", "Sira agad, hindi gumana, sayang ang pera", "Okay lang, may feature list: Moisturizes hair, Easy to use"]


@unittest.skipUnless(ARTIFACT.is_file(), "artifact not built")
class ShadowMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = registry.load_model()

    def setUp(self):
        for key in (sc.ENV, sc.MODE_ENV):
            os.environ.pop(key, None)

    tearDown = setUp

    def analyses(self):
        return self.model.analyze_batch(REVIEWS, [5, 1, 5], listing={"name": "Shampoo 340ml"})

    def test_off_by_default_adds_nothing(self):
        for a in self.analyses():
            self.assertNotIn("calibrated", a["sentiment"])
            self.assertNotIn("deployed_label", a["sentiment"])

    def test_shadow_records_the_calibrated_label_and_changes_no_label(self):
        base = [a["label"] for a in self.analyses()]
        os.environ[sc.ENV] = str(ARTIFACT)
        shadowed = self.analyses()
        self.assertEqual([a["label"] for a in shadowed], base)
        for a in shadowed:
            self.assertIn(a["sentiment"]["calibrated"]["label"], sc.CLASSES)
            self.assertNotIn("deployed_label", a["sentiment"])

    def test_on_replaces_the_label_and_keeps_the_deployed_one(self):
        base = [a["label"] for a in self.analyses()]
        os.environ[sc.ENV] = str(ARTIFACT); os.environ[sc.MODE_ENV] = "on"
        for a, deployed in zip(self.analyses(), base):
            self.assertEqual(a["label"], a["sentiment"]["calibrated"]["label"])
            self.assertEqual(a["sentiment"]["deployed_label"], deployed)

    def test_the_summary_carries_a_shadow_block_only_when_the_calibrator_ran(self):
        agg = ProductBadgeAggregator()
        plain = agg.summarize(self.analyses(), reviews_available=3, product_type="shampoo")
        self.assertNotIn("shadow_sentiment", plain)
        os.environ[sc.ENV] = str(ARTIFACT)
        shadowed = agg.summarize(self.analyses(), reviews_available=3, product_type="shampoo")
        block = shadowed["shadow_sentiment"]
        self.assertEqual(sum(block["sentiment_counts"].values()), 3)
        self.assertEqual(shadowed["sentiment_counts"], plain["sentiment_counts"])  # the real counts are untouched
        self.assertEqual(shadowed["positive_ratio_lower_bound"], plain["positive_ratio_lower_bound"])


if __name__ == "__main__":
    unittest.main()
