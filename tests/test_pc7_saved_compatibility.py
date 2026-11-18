"""pc6 -> pc7 is a title-category-only release, never a silent backfill."""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"backend"),str(ROOT/"backend/sentiment-analysis")]
import dashboard_utils  # noqa: E402
from defaketive_sentiment.product_category import classify_listing, PRODUCT_CATEGORY_REVISION  # noqa: E402

BASE="hazard-same+pc6+xlmr-same+params-same"
NEW="hazard-same+pc7+xlmr-same+params-same"


def report(title,category,version=BASE,group=None):
    return {
        "name":title,"product_category":category,
        **({"product_group":group} if group is not None else {}),
        "sentiment_summary":{"schema_version":"defaketive-summary-2.0"},
        "comments":[{"sentiment_analysis":{"model_version":version,"label":"neutral","review_tags":[]}}],
    }


class TestPc7Compatibility(unittest.TestCase):
    def current(self,product):
        with patch.object(dashboard_utils,"sentiment_model_version",return_value=NEW):
            return dashboard_utils.analysis_is_current([product])

    def test_hair_and_air_conditioners_are_not_conflated(self):
        self.assertEqual(PRODUCT_CATEGORY_REVISION,"pc7")
        self.assertEqual(classify_listing("Window Air Conditioner 1HP"),"small_appliance")
        self.assertEqual(classify_listing("Portable Air Conditioner 12000BTU"),"small_appliance")
        self.assertEqual(classify_listing("Hair Conditioner With Keratin 200mL"),"haircare")
        self.assertEqual(classify_listing("Shampoo Conditioner Set"),"haircare")

    def test_old_matching_pc6_remains_current_without_writes(self):
        original=report("20000mAh Power Bank","powerbank",group="electronics")
        clone=copy.deepcopy(original)
        self.assertTrue(self.current(original))
        self.assertEqual(original,clone)
        self.assertTrue(self.current(report("Shampoo Conditioner Set","haircare",group="beauty_health")))

    def test_air_conditioner_old_haircare_is_stale(self):
        stale=report("Window Air Conditioner 1HP","haircare",group="beauty_health")
        self.assertFalse(self.current(stale))
        self.assertEqual(stale["product_category"],"haircare")
        self.assertTrue(self.current(report("Window Air Conditioner 1HP","small_appliance",NEW,group="home_living")))

    def test_pc4_legacy_preserved_only_with_identical_category(self):
        self.assertTrue(self.current(report("20000mAh Power Bank","powerbank",BASE.replace("+pc6+","+pc4+"))))
        self.assertFalse(self.current(report("Window Air Conditioner 1HP","haircare",BASE.replace("+pc6+","+pc4+"))))

    def test_unrelated_model_changes_are_not_accepted(self):
        self.assertFalse(self.current(report("20000mAh Power Bank","powerbank","other-model+pc6+different")))
        self.assertFalse(self.current(report("20000mAh Power Bank","powerbank",BASE.replace("+xlmr-same","+xlmr-old"))))
        self.assertFalse(self.current(report("20000mAh Power Bank",None)))
        self.assertFalse(self.current(report("20000mAh Power Bank","powerbank",group="fashion")))


if __name__=="__main__":
    unittest.main()
