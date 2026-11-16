"""Regression for a PowMr hybrid solar inverter mislabelled as Gaming.

This suite uses synthetic product metadata only. It does not change stored
analyses, scrape customers' reviews, or recalculate hazard results.
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))

import dashboard_utils as du  # noqa: E402
from defaketive_sentiment.product_category import classify_listing, group_of  # noqa: E402

INVERTER_TITLE = (
    "PowMr 4.5kw/6.5kw On-grid/Off-grid Hybrid Inverter 24Vdc/48Vdc "
    "230VAC Pure Sine Wave Solar Inverter Built in 120A MPPT Solar "
    "Controller Support Lifepo4 Battery RGB Light One-click Repair Function"
)


class SolarAndGamingRegression(unittest.TestCase):
    def test_powmr_actual_listing_is_battery_solar_not_gaming(self):
        self.assertEqual(classify_listing({"name": INVERTER_TITLE}), "battery_solar")
        self.assertEqual(group_of(classify_listing(INVERTER_TITLE)), "electronics")

    def test_solar_controllers_are_not_game_controllers(self):
        examples = (
            "MPPT Solar Charge Controller 100A for 12V 24V Off-grid Battery",
            "Solar Controller for LiFePO4 Battery",
            "PWM Solar Charging Controller 30A",
            "PowMr 5000W Hybrid Solar Inverter RGB Display",
        )
        for title in examples:
            with self.subTest(title=title):
                self.assertEqual(classify_listing(title), "battery_solar")

    def test_actual_gaming_devices_still_match_gaming(self):
        examples = (
            "PS5 DualSense Controller",
            "Xbox Wireless Controller",
            "Nintendo Switch Gamepad",
            "Gaming Controller Bluetooth Wireless for Android",
            "Game Controller USB for PC",
        )
        for title in examples:
            with self.subTest(title=title):
                self.assertEqual(classify_listing(title), "gaming")

    def test_other_inverter_products_are_unaffected(self):
        self.assertEqual(classify_listing("Samsung Refrigerator Inverter 2 Door"), "small_appliance")
        self.assertEqual(classify_listing("3KW Off Grid Solar Inverter 48V"), "battery_solar")

    @staticmethod
    def old_report():
        return {
            "name": INVERTER_TITLE,
            "link": "https://www.lazada.com.ph/products/fictional-inverter-i999999.html",
            "product_category": "gaming",
            "product_group": "electronics",
            "sentiment_summary": {"schema_version": "defaketive-summary-2.0"},
            "comments": [],
        }

    def test_old_report_is_not_silently_rewritten_and_requests_recheck(self):
        old = self.old_report()
        snapshot = copy.deepcopy(old)
        with mock.patch.object(du, "badge_view", return_value={"state": "no_warning_signs"}):
            shown = du.with_badge_view(old)
        self.assertEqual(old, snapshot, "Rendering a saved report must not change the original database record")
        self.assertEqual(shown["product_category"], "gaming", "Stored analysis category must remain auditable")
        self.assertEqual(shown["product_category_display"], "battery_solar")
        self.assertIs(shown["category_needs_recheck"], True)
        self.assertEqual(du.product_category_of(old), "battery_solar")
        with mock.patch.object(du, "sentiment_model_version", return_value="synthetic-current-version"):
            self.assertFalse(du.analysis_is_current([old]), "A mismatched saved category must require rechecking")

    def test_genuine_game_category_does_not_need_recheck(self):
        original = self.old_report()
        original["name"] = "Sony PS5 DualSense Controller"
        with mock.patch.object(du, "badge_view", return_value={"state": "no_warning_signs"}):
            shown = du.with_badge_view(original)
        self.assertNotIn("category_needs_recheck", shown)
        self.assertEqual(shown["product_category"], "gaming")

    def test_rechecked_solar_category_does_not_need_correction(self):
        fresh = self.old_report()
        fresh["product_category"] = "battery_solar"
        with mock.patch.object(du, "badge_view", return_value={"state": "no_warning_signs"}):
            shown = du.with_badge_view(fresh)
        self.assertNotIn("category_needs_recheck", shown)
        self.assertEqual(shown["product_category"], "battery_solar")


if __name__ == "__main__":
    unittest.main()
