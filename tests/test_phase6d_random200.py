"""Phase 6D: source-locked random-200 GPT-6 AI annotations and safe comparison.

Tests do not depend on a paid model or freshly fabricated labels.
"""
import importlib.util
import unittest
from pathlib import Path

PATH = (Path(__file__).resolve().parents[1] /
        "research/xlmr_optimization/phase6_annotation/phase6d_audit.py")
spec = importlib.util.spec_from_file_location("phase6d_audit", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Phase6DTests(unittest.TestCase):
    def test_exact_random_200_originals_locked_and_second_ai_complete(self):
        records = mod.load()
        self.assertEqual(len(records), 200)
        self.assertEqual(len({r["id"] for r in records}), 200)
        self.assertEqual({r["sample_position"] for r in records}, set(range(1, 201)))
        self.assertTrue(all(r["gpt6_confidence"] in {"high", "low"} for r in records))

    def test_all_proposed_disagreements_remain_unverified(self):
        records = mod.load()
        report, disputes = mod.summarize(records)
        self.assertEqual(report["disagreements"], len(disputes))
        self.assertEqual(report["all"]["matching"]+len(disputes), 200)
        self.assertEqual(report["all"]["matching"], 120)
        self.assertEqual(report["claude_neutral_to_gpt6_positive"], 74)

    def test_kappa_of_matching_class_balanced_labels_is_one(self):
        result = mod.label_agreement(
            ["negative", "neutral", "positive"], ["negative", "neutral", "positive"])
        self.assertEqual(result["cohens_kappa"], 1)
        self.assertEqual(result["matrix_rows_claude_columns_gpt6"][1][1], 1)

    def test_kappa_zero_for_chance_agreement(self):
        result = mod.label_agreement(
            ["positive", "positive", "neutral", "neutral"],
            ["positive", "neutral", "positive", "neutral"])
        self.assertEqual(result["cohens_kappa"], 0)

    def test_rejects_invalid_sentiment(self):
        with self.assertRaises(ValueError):
            mod.label_agreement(["wrong"], ["neutral"])

    def test_prior_gpt6_overlap_explicit(self):
        records = mod.load()
        previous = [r["id"] for r in records if r["previous_gpt6_exposure"]]
        self.assertEqual(len(previous), 13)
        self.assertIn("N0678", previous)
        self.assertIn("D229", previous)

    def test_bootstrap_is_deterministic_and_bounds_plausible(self):
        labels = [("negative", "negative"), ("neutral", "positive"),
                  ("positive", "positive"), ("neutral", "neutral")] * 5
        x = mod.confidence_interval(labels, trials=100)
        y = mod.confidence_interval(labels, trials=100)
        self.assertEqual(x, y)
        self.assertTrue(0 <= x["raw_agreement_95pct"][0] <= x["raw_agreement_95pct"][1] <= 1)

    def test_aggregate_never_claims_human_gold(self):
        report, _ = mod.summarize(mod.load())
        self.assertIn("NOT human gold", report["purpose"])
        self.assertEqual(report["sources"]["reannotator"], "GPT-6 ChatGPT, AI, not human")
        self.assertEqual(report["all"]["n"], 200)


if __name__ == "__main__":
    unittest.main()
