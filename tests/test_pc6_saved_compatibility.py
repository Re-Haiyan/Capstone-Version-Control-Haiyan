"""Non-destructive pc4 -> pc6 transition for historical reports.

Only accept a pc4 report when its backend-chosen category is unchanged under
pc6 AND the rest of the exact model version is identical. Otherwise preserve
the saved report as historical and require an explicit recheck.
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "backend" / "sentiment-analysis")]
import dashboard_utils  # noqa: E402
import webapp  # noqa: E402
from defaketive_sentiment.product_category import classify_listing  # noqa: E402

OLD = "defaketive+engine-same+pc4+xlmr-same+hazards-same+params-same"
NEW = "defaketive+engine-same+pc6+xlmr-same+hazards-same+params-same"


def report(name: str, category: str | None, version: str = OLD) -> dict:
    product = {
        "name": name,
        "sentiment_summary": {"schema_version": "defaketive-summary-2.0"},
        "comments": [{
            "rating": 1,
            "content": "Sobrang init at sira yung product.",
            "sentiment_analysis": {"model_version": version, "review_tags": ["safety"], "label": "negative"}
        }],
        "product_category": category,
    }
    return product


class SafeCategoryUpgrade(unittest.TestCase):
    def current(self, product):
        with patch.object(dashboard_utils, "sentiment_model_version", return_value=NEW):
            return dashboard_utils.analysis_is_current([product])

    def test_unchanged_category_preserves_original_checker_output(self):
        product = report("Samsung Galaxy A15 Smartphone 128GB", "phone")
        original = copy.deepcopy(product)
        self.assertEqual(classify_listing({"name": product["name"]}), "phone")
        self.assertTrue(self.current(product))
        self.assertEqual(product, original, "compatibility must be read-only, not update stored versions")

    def test_changed_solar_controller_category_is_stale_and_not_falsely_endorsed(self):
        name = "PowMr Off-grid Hybrid Solar Inverter MPPT Solar Controller 24V"
        self.assertEqual(classify_listing({"name": name}), "battery_solar")
        self.assertFalse(self.current(report(name, "gaming")))

    def test_unknown_legacy_category_stays_stale_and_requires_rescan(self):
        self.assertFalse(self.current(report("Samsung Galaxy A15 Smartphone 128GB", None)))
        self.assertTrue(self.current(report("Random Seller Item 123", "other")))

    def test_unrelated_old_model_or_threshold_change_is_not_accepted(self):
        item = report("Samsung Galaxy A15 Smartphone 128GB", "phone", "defaketive+pc3+older-xlmr")
        self.assertFalse(self.current(item))
        item["comments"][0]["sentiment_analysis"]["model_version"] = (
            "defaketive+engine-other+pc4+xlmr-same+hazards-same+params-same"
        )
        self.assertFalse(self.current(item))

    def test_new_pc6_scans_are_current(self):
        name = "PowMr Off-grid Hybrid Solar Inverter MPPT Solar Controller 24V"
        self.assertTrue(self.current(report(name, "battery_solar", NEW)))

    def test_saved_catalog_does_not_trigger_automatic_recheck_or_modify_reports(self):
        item = report("PowMr MPPT Solar Charge Controller 24V", "gaming")
        expected = copy.deepcopy(item)
        key = ("pc6-save-preservation-test", "only", NEW)
        try:
            with patch.object(webapp, "analysis_is_current", return_value=False), patch.object(
                webapp, "analyze_products", side_effect=AssertionError("unexpected auto recheck")
            ):
                result = webapp._analysed(key, lambda: [item], preserve_saved_reports=True)
            self.assertEqual(result, [expected])
            self.assertEqual(item, expected)
        finally:
            webapp._analysed_files.pop(key, None)


if __name__ == "__main__":
    unittest.main()
