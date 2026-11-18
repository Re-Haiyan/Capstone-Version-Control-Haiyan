"""Shopper-facing concern headings stay broad across all product groups.

No hazard taxonomy, rule, model version, counts, or severity is modified.
Specific group helpers retain examples relevant to the kind of product.
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "backend"))

import category_copy  # noqa: E402
from dashboard_utils import BADGE_COPY, BADGE_LABELS, INFORMS_ONLY, _badge_copy, _labels  # noqa: E402

HEADINGS = {
    "safety": "Safety concerns",
    "defect": "Functionality or damage concerns",
    "quality": "Quality concerns",
    "counterfeit": "Authenticity concerns",
    "not_as_described": "Listing differences",
}


class GeneralizedConcernWording(unittest.TestCase):
    def test_exactly_five_concern_categories_have_broad_advisory_names(self):
        self.assertEqual(set(BADGE_COPY), set(HEADINGS))
        self.assertEqual({slug: spec["label"] for slug,spec in BADGE_COPY.items()}, HEADINGS)
        self.assertEqual({item["category"]: item["label"] for item in BADGE_LABELS}, HEADINGS)

    def test_every_product_group_keeps_specific_context_without_changing_headings(self):
        groups = ("electronics", *category_copy.PROFILES)
        for group in set(groups):
            profile=category_copy.profile(group)
            with self.subTest(group=group):
                self.assertEqual({item["category"]: item["label"] for item in _labels(profile)}, HEADINGS)
                for name in HEADINGS:
                    self.assertTrue(_badge_copy(name, profile)["helper"].strip())
                    self.assertTrue(_badge_copy(name, profile)["none"].strip())

    def test_only_quality_and_listing_differences_are_informational(self):
        self.assertEqual(set(INFORMS_ONLY), {"quality", "not_as_described"})
        for item in BADGE_LABELS:
            self.assertEqual(item["informs_only"], item["category"] in INFORMS_ONLY)


if __name__ == "__main__":
    unittest.main()
