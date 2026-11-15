"""Conservative source audit: protects severity reports and avoids claiming accuracy."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (ROOT / "research/product_specific_conclusions/ai_annotation/safety_source_audit.py")
spec = importlib.util.spec_from_file_location("safety_source_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class DirectEvidenceCandidates(unittest.TestCase):
    def test_synthetic_denied_heat_is_not_a_hazard_report(self):
        for phrase in (
            "Safe to use, walang usok o overheat",
            "No smoke and no overheating during use",
            "It doesn't overheat at all",
        ):
            with self.subTest(phrase=phrase):
                direct, denied, fake = audit.review_candidates(phrase)
                self.assertFalse(direct)
                self.assertTrue(denied)
                self.assertFalse(fake)

    def test_actual_hazard_survives_a_denial_in_prior_clause(self):
        direct, denied, _ = audit.review_candidates(
            "There was no smoke at first, but my charger exploded and produced sparks."
        )
        self.assertIn("fire_or_explosion", direct)
        self.assertIn("sparking_or_shock", direct)
        self.assertTrue(denied)

    def test_promotional_or_lyrical_burning_word_is_not_direct_injury(self):
        for phrase in (
            "We were good, we were gold. Watched it burn. I can buy myself flowers.",
            "Fireproof charger design with overheating protection",
            "The power bank never overheats; no smoke or sparks.",
        ):
            with self.subTest(phrase=phrase):
                direct, _, _ = audit.review_candidates(phrase)
                self.assertEqual(direct, set())

    def test_customer_fire_report_is_a_candidate_not_verified_fact(self):
        direct, _, _ = audit.review_candidates(
            "She charged the earbuds for ten minutes, then smelled smoke. "
            "The case was on fire."
        )
        self.assertIn("fire_or_explosion", direct)
        self.assertIn("burning_smoke", direct)

    def test_fake_allegation_is_not_automatically_confirmed(self):
        direct, _, allegation = audit.review_candidates(
            "Fake item. It looks nothing like the official unit."
        )
        self.assertEqual(direct, set())
        self.assertTrue(allegation)

    def test_summary_counts_can_be_parsed_both_ways(self):
        self.assertEqual(
            audit._count_claim("One review describes a possible safety problem",
                               audit.SAFETY_COUNT_PATTERNS), 1)
        self.assertEqual(
            audit._count_claim("5 reviews mentioning a potential safety concern",
                               audit.SAFETY_COUNT_PATTERNS), 5)
        self.assertEqual(
            audit._count_claim("7 reviews question whether the product is genuine",
                               audit.AUTH_COUNT_PATTERNS), 7)
        self.assertEqual(
            audit._count_claim("possible authenticity concerns (2 reviews)",
                               audit.AUTH_COUNT_PATTERNS), 2)


class PackSourceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit.build_report()
        cls.products = {r["product_id"]: r for r in cls.report["products"]}

    def test_conservative_report_scope_and_integrity(self):
        self.assertEqual(self.report["sources"]["review_rows"], 5946)
        self.assertEqual(self.report["sources"]["product_rows"], 35)
        self.assertEqual(len(self.products), 35)
        self.assertFalse(self.report["human_evaluation"])
        self.assertFalse(self.report["ground_truth"])
        self.assertIsNone(self.report["verified_error_count"])

    def test_source_linked_examples_exist(self):
        f020 = self.products["F020"]
        self.assertIn("6", f020["direct_hazard_candidate_review_ids"])
        self.assertIn("serious_event_candidate_with_too_few_reviews_headline",
                      f020["review_flags"])
        self.assertIn("73", self.products["F002"]["denied_or_benign_hazard_review_ids"])

    def test_pack_source_not_reinterpreted_as_lyrical_injury(self):
        f014 = self.products["F014"]
        self.assertNotIn("190", f014["direct_hazard_candidate_review_ids"])

    def test_report_does_not_emit_raw_private_review_text(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "report.csv"
            audit.write_csv(self.report, dest)
            rows = list(csv.DictReader(dest.open(encoding="utf-8", newline="")))
            self.assertEqual(len(rows), 35)
            self.assertTrue(all("review_text" not in row for row in rows))
            for row in rows:
                self.assertEqual(row["direct_hazard_candidate_review_ids"].count("OTP"), 0)
            # JSON only includes generic IDs and audit labels.
            report_text = json.dumps(self.report, ensure_ascii=False)
            self.assertNotIn("review_text", report_text)


if __name__ == "__main__":
    unittest.main()
