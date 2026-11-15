"""The recommendation policy that runs today is reproduced exactly, and the experimental candidate cannot weaken a hazard override."""

from __future__ import annotations

import gzip
import itertools
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import dashboard_utils as du  # noqa: E402
import recommendation_policy as rp  # noqa: E402

DECISIONS = {"recommended", "mixed", "caution", "not_recommended", "not_enough"}
STATES = ("no_warning_signs", "possible_safety_issue", "possible_counterfeit_or_defect", "safety_warning", "reviews_may_be_unreliable", "insufficient_evidence")


def summary(positive: int, uncertain: int, negative: int, bound: float) -> dict:
    return {"sentiment_counts": {"positive": positive, "uncertain": uncertain, "negative": negative}, "positive_ratio_lower_bound": bound}


def shares(positive: int, uncertain: int, negative: int) -> dict:
    total = positive + uncertain + negative
    return {"positive": positive / total, "uncertain": uncertain / total, "negative": negative / total}


def grid():
    for pos in range(0, 101, 5):
        for neg in range(0, 101 - pos, 5):
            yield pos, 100 - pos - neg, neg


class Reproduction(unittest.TestCase):
    def test_the_thresholds_are_the_ones_dashboard_utils_uses(self):
        self.assertEqual((rp.RECOMMEND_SHARE, rp.RECOMMEND_BOUND, rp.MIXED_SHARE), (du.CONCLUSION_RECOMMEND_SHARE, du.CONCLUSION_RECOMMEND_BOUND, du.CONCLUSION_MIXED_SHARE))

    def test_current_decision_equals_the_live_decision_on_a_grid_of_every_state(self):
        checked = 0
        for state, (pos, neu, neg), bound in itertools.product(STATES, grid(), (0.0, 0.5, 0.7, 0.9)):
            data = summary(pos, neu, neg, bound)
            found = [{"category": "safety", "mentions": 1}, {"category": "counterfeit", "mentions": 1}, {"category": "defect", "mentions": 1}]
            live = du._conclusion(data, state, found, 100)
            expected = live["decision"] if live else None
            self.assertEqual(rp.current_decision(state, du._sentiment_shares(data), bound), expected, (state, pos, neu, neg, bound))
            checked += 1
        self.assertGreater(checked, 5000)

    def test_current_decision_equals_the_live_decision_on_every_saved_product(self):
        products = [item["product"] for item in json.load(gzip.open(ROOT / "backend" / "seed" / "saved_products.json.gz", "rt", encoding="utf-8"))]
        self.assertEqual(len(products), 182)
        for product in products:
            view = du.badge_view(product)
            summary_ = product["sentiment_summary"]
            expected = (view["conclusion"] or {}).get("decision")
            got = rp.current_decision(view["state"], du._sentiment_shares(summary_), float(summary_.get("positive_ratio_lower_bound") or 0.0))
            self.assertEqual(got, expected, product["name"])


class Candidate(unittest.TestCase):
    def test_only_the_five_existing_values_are_ever_returned(self):
        for state, (pos, neu, neg), bound in itertools.product(STATES, grid(), (0.0, 0.7)):
            self.assertIn(rp.candidate_decision(state, shares(pos, neu, neg), bound)[0], DECISIONS)

    def test_the_45_20_35_case_is_mixed_not_not_recommended(self):
        data = shares(45, 20, 35)
        self.assertEqual(rp.current_decision("no_warning_signs", data, 0.4), "not_recommended")
        self.assertEqual(rp.candidate_decision("no_warning_signs", data, 0.4)[0], "mixed")

    def test_the_25_65_10_case_is_not_called_negative(self):
        data = shares(25, 65, 10)
        self.assertEqual(rp.current_decision("no_warning_signs", data, 0.2), "not_recommended")
        self.assertNotEqual(rp.candidate_decision("no_warning_signs", data, 0.2)[0], "not_recommended")

    def test_a_negative_majority_is_still_not_recommended(self):
        self.assertEqual(rp.candidate_decision("no_warning_signs", shares(20, 20, 60), 0.2)[0], "not_recommended")
        self.assertEqual(rp.candidate_decision("no_warning_signs", shares(30, 25, 45), 0.2)[0], "not_recommended")

    def test_a_safety_warning_is_never_lowered_by_praise(self):
        for pos, neu, neg in grid():
            self.assertEqual(rp.candidate_decision("safety_warning", shares(pos, neu, neg), 0.9)[0], "not_recommended")

    def test_unreliable_and_insufficient_keep_their_decisions(self):
        for pos, neu, neg in grid():
            self.assertEqual(rp.candidate_decision("reviews_may_be_unreliable", shares(pos, neu, neg), 0.5)[0], "caution")
            self.assertEqual(rp.candidate_decision("insufficient_evidence", shares(pos, neu, neg), 0.5)[0], "not_enough")

    def test_a_hazard_concern_is_never_turned_into_recommended_or_mixed(self):
        for state in rp.HAZARD_CONCERN_STATES:
            for (pos, neu, neg), bound in itertools.product(grid(), (0.0, 0.9)):
                self.assertIn(rp.candidate_decision(state, shares(pos, neu, neg), bound)[0], ("caution", "not_recommended"))

    def test_the_candidate_never_promotes_a_product_to_recommended(self):
        for state, (pos, neu, neg), bound in itertools.product(STATES, grid(), (0.0, 0.5, 0.7, 0.9)):
            data = shares(pos, neu, neg)
            if rp.candidate_decision(state, data, bound)[0] == "recommended":
                self.assertEqual(rp.current_decision(state, data, bound), "recommended")

    def test_a_hazard_concern_with_mostly_neutral_reviews_is_caution_not_not_recommended(self):
        self.assertEqual(rp.current_decision("possible_safety_issue", shares(30, 60, 10), 0.3), "not_recommended")
        self.assertEqual(rp.candidate_decision("possible_safety_issue", shares(30, 60, 10), 0.3)[0], "caution")

    def test_every_change_is_explained(self):
        self.assertIn("not_recommended -> mixed", rp.explain("not_recommended", "mixed", shares(45, 20, 35)))
        self.assertEqual(rp.explain("mixed", "mixed", shares(60, 20, 20)), "")


if __name__ == "__main__":
    unittest.main()
