"""Product-category context for sentiment: opt-in SHADOW ONLY.

Regression gates:
* no input changes to the shipped XLM-R / sentiment model;
* no effect on hazard tags, warnings or aggregate sentiment;
* category derived only from listing title;
* category ambiguities and negations fail closed;
* findings are research candidates, never independent ground truth.
"""
from __future__ import annotations

import copy
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))

from defaketive_sentiment import category_sentiment as cs  # noqa: E402
from defaketive_sentiment.hazard_model import HazardBadgeModel, LexiconHazardTagger  # noqa: E402


class CategoryShadowRules(unittest.TestCase):
    def setUp(self) -> None:
        self.mode = mock.patch.dict(os.environ, {cs.ENV: "shadow"})
        self.mode.start()
        self.addCleanup(self.mode.stop)

    def get(self, title: str, review: str, label: str = "neutral"):
        return cs.suggest(review, {"name": title}, label)

    def test_positive_phone_thin_is_not_clothes_quality(self):
        a = self.get("Samsung Galaxy A15 Smartphone", "Ang manipis, maganda tingnan")
        self.assertEqual(a["product_category"], "phone")
        self.assertEqual(a["candidate_label"], "positive")
        self.assertTrue(a["disagrees"])
        self.assertFalse(a["used_for_decision"])
        self.assertEqual(a["mode"], "shadow")
        self.assertIn("manipis", a["matched_text"])

    def test_explicit_clothing_material_complaint(self):
        a = self.get("Cotton T-shirt Oversized", "Sobrang nipis ng tela, see through")
        self.assertEqual(a["product_category"], "apparel")
        self.assertEqual(a["candidate_label"], "negative")
        self.assertEqual(a["deployed_label"], "neutral")

    def test_solar_power_and_powerbank_heat_reports(self):
        for title in ("Solar Inverter 3000W MPPT", "Xiaomi 20000mAh Power Bank"):
            with self.subTest(title=title):
                a = self.get(title, "Sobrang init after 15 minutes")
                self.assertEqual(a["candidate_label"], "negative")
                self.assertEqual(a["rule"], "battery_heat_complaint")

    def test_negated_and_comparison_ambiguous_cases_do_not_trigger(self):
        self.assertIsNone(self.get("Oversized Cotton Shirt", "Fabric is not too thin"))
        self.assertIsNone(self.get("Solar Inverter 3000W", "No overheating detected"))
        self.assertIsNone(self.get("Samsung Galaxy Smartphone", "Hindi manipis ang phone, maganda"))
        self.assertIsNone(self.get("Lipstick Loose Powder Makeup", "Loose powder gives a perfect finish"))
        self.assertIsNone(self.get("Bag with phone case", "Nice thin material"))

    def test_other_categories_and_unrecognised_titles_fail_closed(self):
        self.assertIsNone(self.get("Random Marketplace Product 999", "Sobrang init"))
        self.assertIsNone(self.get("Stainless Steel Cooking Pan", "Pantay ang init kapag nagluluto"))
        self.assertIsNone(self.get("Samsung Refrigerator Inverter Two Door", "Sobrang init"))

    def test_title_not_review_or_user_supplied_field_determines_category(self):
        self.assertIsNone(cs.suggest(
            "Sobrang init", {"name": "Gaming Controller PS5", "product_category": "battery_solar"},
            "neutral",
        ))
        self.assertIsNone(cs.suggest(
            "Sobrang init", {"name": "Random Listing", "description": "Solar Inverter 5000W"}, "neutral",
        ))

    def test_off_by_default_and_invalid_or_long_input(self):
        with mock.patch.dict(os.environ, {cs.ENV: ""}):
            self.assertIsNone(self.get("Solar Inverter", "sobrang init"))
        self.assertIsNone(cs.suggest("sobrang init", None, "neutral"))
        self.assertIsNone(self.get("Solar Inverter", "sobrang init", "unknown"))
        self.assertIsNone(self.get("Solar Inverter", "x" * 6000))


class FakeSentiment:
    model_version = "synthetic-neutral-sentiment"

    def fingerprint(self, text):
        return str(text).lower()

    def analyze(self, review, rating=None):
        return {
            "model_version": self.model_version,
            "label": "neutral",
            "label_source": "synthetic_test_only",
            "classifier": {"probabilities": {}},
            "sentiment_evidence": [],
            "risk": {"detected": False, "categories": [], "evidence": []},
            "scores": {},
        }


class PipelineShadowWiring(unittest.TestCase):
    def test_opt_in_shadow_never_changes_hazard_or_sentiment(self):
        model = HazardBadgeModel(
            allow_unqualified=True,
            tagger=LexiconHazardTagger(rules="0.4", counterfeit_rules="c2"),
            sentiment_model=FakeSentiment(),
        )
        review = "Sobrang nipis ng tela, see through"
        listing = {"name": "Cotton T-shirt Oversized"}
        with mock.patch.dict(os.environ, {cs.ENV: ""}):
            baseline = model.analyze(review, 2, listing=listing)
        with mock.patch.dict(os.environ, {cs.ENV: "shadow"}):
            candidate = model.analyze(review, 2, listing=listing)
        self.assertNotIn("category_shadow", baseline["sentiment"])
        block = candidate["sentiment"]["category_shadow"]
        self.assertEqual(block["candidate_label"], "negative")
        self.assertEqual(block["deployed_label"], "neutral")
        self.assertFalse(block["used_for_decision"])
        without_shadow = copy.deepcopy(candidate)
        del without_shadow["sentiment"]["category_shadow"]
        self.assertEqual(without_shadow, baseline)

    def test_empty_or_ambiguous_product_does_not_change_existing_schema(self):
        model = HazardBadgeModel(
            allow_unqualified=True,
            tagger=LexiconHazardTagger(rules="0.4", counterfeit_rules="c2"),
            sentiment_model=FakeSentiment(),
        )
        with mock.patch.dict(os.environ, {cs.ENV: "shadow"}):
            result = model.analyze("Seems fine", 5, listing={"name": "Random Unknown Item"})
        self.assertNotIn("category_shadow", result["sentiment"])
        self.assertEqual(result["label"], "neutral")


if __name__ == "__main__":
    unittest.main()
