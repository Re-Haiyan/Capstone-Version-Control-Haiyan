"""The buying conclusion ("Based on the reviews of this product ...") follows the verdict and the reviewers' mood."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from dashboard_utils import _conclusion, _sentiment_shares  # noqa: E402


def summary(positive: int, uncertain: int, negative: int, bound: float | None = None) -> dict:
    total = positive + uncertain + negative
    return {
        "sentiment_counts": {"positive": positive, "uncertain": uncertain, "negative": negative},
        "positive_ratio_lower_bound": bound if bound is not None else (positive / total if total else 0),
    }


def badges(safety: int = 0, counterfeit: int = 0, defect: int = 0) -> list[dict]:
    return [{"category": "safety", "mentions": safety}, {"category": "counterfeit", "mentions": counterfeit}, {"category": "defect", "mentions": defect}]


def decide(state: str, data: dict, found: list[dict] | None = None, usable: int = 100) -> dict | None:
    return _conclusion(data, state, found or badges(), usable)


class ConclusionTests(unittest.TestCase):
    def test_happy_product_without_warnings_is_recommended(self) -> None:
        result = decide("no_warning_signs", summary(85, 5, 10, 0.78))
        self.assertEqual(result["decision"], "recommended")
        self.assertTrue(result["text"].startswith("Based on the reviews of this product"))
        self.assertIn("85%", result["text"])

    def test_a_small_sample_is_not_recommended_on_a_lucky_share(self) -> None:
        # 9 of 10 positive, but the lower bound of so few reviews is low.
        self.assertEqual(decide("no_warning_signs", summary(9, 0, 1, 0.6), usable=10)["decision"], "mixed")

    def test_middling_reviews_are_mixed(self) -> None:
        self.assertEqual(decide("no_warning_signs", summary(60, 10, 30))["decision"], "mixed")

    def test_mostly_negative_without_warnings_is_not_recommended(self) -> None:
        self.assertEqual(decide("no_warning_signs", summary(30, 10, 60))["decision"], "not_recommended")

    def test_safety_warning_is_never_recommended_however_happy_the_reviews(self) -> None:
        result = decide("safety_warning", summary(95, 0, 5), badges(safety=4))
        self.assertEqual(result["decision"], "not_recommended")
        self.assertIn("4 reviews mention a safety problem", result["points"])

    def test_possible_safety_issue_says_think_twice_unless_most_reviewers_are_unhappy(self) -> None:
        self.assertEqual(decide("possible_safety_issue", summary(90, 0, 10), badges(safety=1))["decision"], "caution")
        self.assertEqual(decide("possible_safety_issue", summary(10, 18, 72), badges(safety=3))["decision"], "not_recommended")

    def test_defects_with_happy_reviews_are_caution_and_with_unhappy_ones_not_recommended(self) -> None:
        self.assertEqual(decide("possible_counterfeit_or_defect", summary(70, 10, 20), badges(defect=12))["decision"], "caution")
        self.assertEqual(decide("possible_counterfeit_or_defect", summary(30, 10, 60), badges(defect=40))["decision"], "not_recommended")

    def test_unreliable_reviews_give_no_clear_advice(self) -> None:
        self.assertEqual(decide("reviews_may_be_unreliable", summary(100, 0, 0))["decision"], "caution")

    def test_too_few_reviews_gives_no_advice_either_way(self) -> None:
        result = decide("insufficient_evidence", summary(3, 0, 0), usable=3)
        self.assertEqual(result["decision"], "not_enough")
        self.assertNotIn("okay to buy", result["text"])

    def test_every_conclusion_carries_the_not_a_guarantee_notice(self) -> None:
        for state in ("no_warning_signs", "safety_warning", "possible_safety_issue", "insufficient_evidence"):
            self.assertIn("not proof", decide(state, summary(80, 10, 10, 0.7))["notice"])

    def test_weighted_shares_are_used_when_the_sample_was_weighted(self) -> None:
        data = summary(50, 0, 50) | {"sentiment_shares": {"positive": 0.9, "uncertain": 0.05, "negative": 0.05}, "positive_ratio_lower_bound": 0.8}
        self.assertEqual(decide("no_warning_signs", data)["decision"], "recommended")
        self.assertEqual(_sentiment_shares(data)["positive"], 0.9)

    def test_no_reviews_with_a_sentiment_label_gives_none_rather_than_a_guess(self) -> None:
        self.assertIsNone(decide("no_warning_signs", {"sentiment_counts": {}}))


    def test_the_paragraph_counts_the_reviews_behind_each_concern(self) -> None:
        found = [
            {"category": "safety", "mentions": 1},
            {"category": "counterfeit", "mentions": 3},
            {"category": "defect", "mentions": 82},
            {"category": "quality", "mentions": 46},
            {"category": "not_as_described", "mentions": 8},
        ]
        result = decide("possible_safety_issue", summary(476, 10, 26, 0.9), found, usable=512)
        self.assertEqual(result["assessment"], "Caution")
        self.assertIn("According to the 512 customer reviews analyzed", result["summary"])
        for phrase in ("(93%)", "product defects (82 reviews)", "weak or poor build quality (46 reviews)",
                       "differences from the product description (8 reviews)", "possible authenticity concerns (3 reviews)",
                       "one review mentioning a potential safety concern"):
            self.assertIn(phrase, result["summary"])
        self.assertEqual(result["lead"], "According to the reviews, this product is generally well-received, but some concerns were reported.")

    def test_a_product_with_no_concerns_names_none_and_never_says_it_is_safe(self) -> None:
        result = decide("no_warning_signs", summary(85, 5, 10, 0.78), badges())
        self.assertNotIn("However", result["summary"])
        self.assertNotIn("safe", result["summary"].replace("potential safety", ""))

    def test_too_few_reviews_gives_no_percentage(self) -> None:
        result = decide("insufficient_evidence", summary(3, 0, 0), usable=3)
        self.assertEqual(result["assessment"], "Not enough reviews")
        self.assertNotIn("%", result["summary"])


if __name__ == "__main__":
    unittest.main()
