"""The model version stamp must change when the rules change, so that saved reports made by earlier rules are shown as such."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
import dashboard_utils  # noqa: E402
from defaketive_sentiment import product_category  # noqa: E402

OLD_STAMP = "defaketive-hazard-lexicon-0.3.0+rules0.4g1n1f1f2f3f4f5f6f7f8af9f10s1f11f12f13f14o1q1s2s3s5+hazard-learned-6.0.0-safety-defect-34a2ad69+r1b+c2r8+extra-labels-1.0.0-quality-not_as_described-f8d08961+lc1+lc2+lc3+pc3+defaketive-xlmr-firecs-v1-onnx-int8-e04da4c2+reference-baselines-2.0.0+hazard-parameters-1.1.0"


def product(version):
    return {"sentiment_summary": {"schema_version": "defaketive-summary-2.0"}, "comments": [{"sentiment_analysis": {"model_version": version}}]}


class VersionStamp(unittest.TestCase):
    def test_the_rule_revision_is_in_the_model_version(self):
        version = dashboard_utils.sentiment_model_version()
        self.assertIn(f"+{product_category.PRODUCT_CATEGORY_REVISION}+", version)
        self.assertNotEqual(version, OLD_STAMP)  # the stamp of the production release before this one

    def test_a_report_made_with_the_old_rules_is_not_current_and_one_made_now_is(self):
        self.assertFalse(dashboard_utils.analysis_is_current([product(OLD_STAMP)]))

    def test_the_revision_is_bumped_past_pc3(self):
        self.assertNotEqual(product_category.PRODUCT_CATEGORY_REVISION, "pc3")


if __name__ == "__main__":
    unittest.main()
