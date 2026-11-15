"""Integrity tests for *provisional* GPT-6 QA files. No human labels are created."""
import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "research" / "product_specific_conclusions" / "human_eval_pack"
QA = ROOT / "research" / "product_specific_conclusions" / "ai_annotation" / "gpt6_qa_20261115"
ALLOWED_CARDS = {
    "Well reviewed", "Mixed reviews", "Some concerns", "Not recommended", "Too few reviews"
}
ALLOWED_PRIORITIES = {"low", "medium", "high", "critical"}


def rows(path):
    with open(path, encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


class GPT6ProvisionalAnnotationIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_cards = rows(PACK / "card_sheet_A.csv")
        cls.raw_summaries = rows(PACK / "words_sheet_A.csv")
        cls.raw_reviews = rows(PACK / "reviews.csv")
        cls.card = rows(QA / "card_preannotations_ai.csv")
        cls.summaries = rows(QA / "summary_triage_ai.csv")

    def test_cards_complete_per_product_with_valid_values(self):
        target = {r["product_id"] for r in self.raw_cards}
        self.assertEqual(len(target), 35)
        self.assertEqual(len(self.card), 35)
        self.assertEqual({r["product_id"] for r in self.card}, target)
        titles = {r["product_id"]: r["product"] for r in self.raw_cards}
        for r in self.card:
            with self.subTest(product_id=r["product_id"]):
                self.assertEqual(r["product"], titles[r["product_id"]])
                self.assertIn(r["assessment"], ALLOWED_CARDS)
                self.assertIn(r["serious_safety_concern"], ("yes", "no"))
                self.assertIn(r["counterfeit_concern"], ("yes", "no"))
                self.assertIn(r["confidence"], ("low", "medium", "high"))
                self.assertTrue(r["main_reason"].strip())
                self.assertIn("AI", r["review_status"])
                self.assertIn("non-blind", r["source"].lower())

    def test_review_evidence_references_resolve(self):
        seen = {(r["product_id"], r["review_no"]) for r in self.raw_reviews}
        self.assertEqual(len(self.raw_reviews), 5946)
        for r in (*self.card, *self.summaries):
            with self.subTest(product_id=r["product_id"], row=r.get("summary_id")):
                for review_no in r["evidence_review_nos"].split(";"):
                    self.assertIn((r["product_id"], review_no), seen)

    def test_every_summary_variant_triaged_once(self):
        target = {r["product_id"] for r in self.raw_summaries}
        expected = {f"{pid}-T{n}" for pid in target for n in (1, 2)}
        self.assertEqual(len(self.summaries), 70)
        self.assertEqual({r["summary_id"] for r in self.summaries}, expected)
        for r in self.summaries:
            with self.subTest(summary=r["summary_id"]):
                self.assertIn(r["priority"], ALLOWED_PRIORITIES)
                self.assertTrue(r["issue_codes"].strip())
                self.assertTrue(r["triage_note"].strip())
                self.assertIn("NOT SCORED", r["numeric_rating_status"])
                self.assertIn("NOT human", r["source"])

    def test_high_priority_hazards_flagged_but_not_adjudicated(self):
        by_id = {r["product_id"]: r for r in self.card}
        self.assertEqual(by_id["F020"]["serious_safety_concern"], "yes")
        summary = {r["summary_id"]: r for r in self.summaries}
        for id_ in ("F002", "F011", "F014", "F030", "F032"):
            self.assertIn("SUSPECT_UNSUPPORTED_SAFETY", summary[f"{id_}-T1"]["issue_codes"])
            self.assertIn("SUSPECT_UNSUPPORTED_SAFETY", summary[f"{id_}-T2"]["issue_codes"])

    def test_provenance_never_represents_human_annotation(self):
        provenance = json.loads((QA / "provenance.json").read_text(encoding="utf-8"))
        self.assertIn("GPT-6", provenance["model"])
        self.assertEqual(provenance["human_review"], "none")
        self.assertIn("NOT blind", provenance["blinding"])
        self.assertEqual(provenance["datasets"]["review_rows_programmatically_inspected"], 5946)
        self.assertIn("none", provenance["release_approval"])


if __name__ == "__main__":
    unittest.main()
