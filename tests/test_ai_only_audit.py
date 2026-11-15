"""Protect AI-only descriptive evaluation from accidental 'accuracy' claims."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[1] /
          "research/product_specific_conclusions/ai_annotation/"
          "gpt6_qa_20261115/ai_only_audit.py")
spec = importlib.util.spec_from_file_location("ai_only_audit", SCRIPT)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class AIOnlyDescriptiveReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = audit_module.audit()

    def test_provenance_cannot_be_mistaken_for_human_evaluation(self):
        self.assertFalse(self.data["is_independent_human_evaluation"])
        self.assertEqual(self.data["human_annotators"], 0)
        self.assertTrue(self.data["card_agreement"]["not_accuracy"])
        for field in ("factual_accuracy", "claim_precision", "feature_recall",
                      "word_quality_mean", "verified_safety_error_count"):
            self.assertIsNone(self.data[field])

    def test_card_agreement_is_descriptive_and_reproducible(self):
        result = self.data["card_agreement"]
        self.assertEqual(self.data["total_products"], 35)
        self.assertEqual(result["matches"], 24)
        self.assertEqual(result["total"], 35)
        self.assertEqual(len(result["disagreements"]), 11)
        self.assertAlmostEqual(result["fraction"], 24 / 35)
        self.assertIn("F020", {r["product_id"] for r in result["disagreements"]})

    def test_issues_are_counted_by_unique_product_and_text(self):
        self.assertEqual(self.data["total_system_summary_texts_triaged"], 70)
        priority = self.data["summary_triage_priorities_by_product"]
        self.assertEqual(sum(priority.values()), 35)
        summary = self.data["summary_triage_priorities_by_text"]
        self.assertEqual(sum(summary.values()), 70)
        self.assertEqual(summary["critical"], 2 * priority["critical"])
        self.assertIn("F002", self.data["suspected_unsupported_safety_products"])

    def test_ai_report_does_not_mutate_formal_human_pack(self):
        # Source sheets remain on the separate locked pack path.
        self.assertNotEqual(audit_module.HERE.resolve(), audit_module.PACK.resolve())
        self.assertEqual(audit_module.HERE.parent.parent.resolve(),
                         audit_module.PACK.parent.resolve())


if __name__ == "__main__":
    unittest.main()
