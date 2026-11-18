"""Research-only aspect profile completeness.

Profiles do not activate automatic sentiment corrections. When marketplace
coverage expands, this test must force deliberate mapping of each new category.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend/sentiment-analysis"))
from defaketive_sentiment import product_category  # noqa: E402


class AspectProfileCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "research/category_sentiment/category_aspect_profiles.json").read_text(encoding="utf-8"))

    def test_every_existing_category_has_a_profile(self):
        categories = set(product_category.CATEGORIES) - {"other"}
        self.assertEqual(len(categories), 49)
        self.assertEqual(set(self.data["profiles"]), categories)
        self.assertEqual(self.data["status"], "research_only_no_automatic_sentiment_override")

    def test_examples_are_nonempty_and_never_authorize_automatic_overrides(self):
        for category, profile in self.data["profiles"].items():
            with self.subTest(category=category):
                self.assertFalse(profile["qualified_for_sentiment_override"])
                for field in ("positive_example", "negative_example", "ambiguous_term"):
                    self.assertIsInstance(profile[field], str)
                    self.assertTrue(profile[field].strip())

    def test_other_fails_closed(self):
        self.assertNotIn("other", self.data["profiles"])
        self.assertIn("no category-aware corrections", self.data["other_policy"])


if __name__ == "__main__":
    unittest.main()
