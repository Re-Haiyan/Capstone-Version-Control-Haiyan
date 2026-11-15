"""Regression tests for multi-mention hazard reports (safety s5b).

Synthetic, policy-derived examples: not part of the historical labelled set.
A benign first mention must not mask a later real one in the same sentence.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "sentiment-analysis"))

from defaketive_sentiment.safety_lookalikes import s3_adds, s3_removes  # noqa: E402
from defaketive_sentiment.hazard_model import LexiconHazardTagger  # noqa: E402


class MultipleSafetyMentions(unittest.TestCase):
    def test_negated_first_but_second_is_a_report(self) -> None:
        for review in (
            "It did not become hot at first, then the charger became hot",
            "Not over heated yesterday but the cable over heated today",
        ):
            with self.subTest(review=review):
                self.assertIsNotNone(s3_adds(review))

    def test_other_device_first_but_purchased_item_is_hot(self) -> None:
        text = "My phone became hot but this charger became hot"
        self.assertIsNotNone(s3_adds(text))

    def test_only_negated_or_other_device_is_not_a_report(self) -> None:
        for review in (
            "It did not become hot at first and it did not become hot later",
            "My phone became hot but the charger did not become hot",
            "My phone became hot, and the power bank works perfectly",
        ):
            with self.subTest(review=review):
                self.assertIsNone(s3_adds(review))

    def test_other_device_and_denied_item_are_both_accounted_for(self) -> None:
        reasons = s3_removes("My phone became hot but the charger did not become hot")
        self.assertIn("other_device", reasons)
        self.assertIn("denial", reasons)

    def test_integration_preserves_safety_tag(self) -> None:
        tagger = LexiconHazardTagger(rules="0.4", counterfeit_rules="c2")
        review = "My phone became hot but this charger became hot"
        self.assertIn("safety", tagger.tag_sentence(review)["tags"])

    def test_integration_does_not_turn_denial_into_a_hazard(self) -> None:
        tagger = LexiconHazardTagger(rules="0.4", counterfeit_rules="c2")
        review = "My phone became hot but the charger did not become hot"
        self.assertNotIn("safety", tagger.tag_sentence(review)["tags"])


if __name__ == "__main__":
    unittest.main()
