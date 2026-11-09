import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/sentiment-analysis"))
sys.path.insert(0, str(ROOT / "scripts"))
from defaketive_sentiment.aspects import analyze_aspects
from annotate_reviews import fingerprint, split_for
from export_approved_annotations import validate


class AspectsTest(unittest.TestCase):
    def test_contrast_and_exact_unicode_spans(self):
        text = "📦 Mabilis delivery at mura, pero isang earbud lang gumagana."
        result = analyze_aspects(text)
        self.assertTrue(result["mixed_evidence"])
        self.assertEqual([(x["aspect"], x["label"]) for x in result["evidence"]],
                         [("delivery", "positive"), ("price", "positive"), ("functionality", "negative")])
        for item in result["evidence"]:
            self.assertEqual(text[slice(*item["span"])], item["text"])

    def test_abstentions(self):
        for text in ("", "Sana matibay quality", "Is delivery fast?", "No damage to packaging", "xyz"):
            with self.subTest(text=text):
                self.assertEqual(analyze_aspects(text)["evidence"], [])

    def test_negation(self):
        for text in ("Hindi gumagana", "not good quality", "seller doesn't respond"):
            with self.subTest(text=text):
                self.assertTrue(all(x["label"] != "positive" for x in analyze_aspects(text)["evidence"]))
        self.assertEqual(analyze_aspects("Hindi gumagana")["evidence"][0]["label"], "negative")

    def test_split_stability_and_legacy_exclusion(self):
        self.assertEqual(fingerprint("Good QUALITY!"), fingerprint("good quality"))
        self.assertEqual(split_for("Good QUALITY!", set()), split_for("good quality", set()))
        self.assertEqual(split_for("Good quality", {fingerprint("good quality")}), "legacy_exposed")

    def test_proposals_are_not_training_truth(self):
        self.assertIsNone(validate({"annotation_status": "pending_human_review"}))
        with self.assertRaises(ValueError):
            validate({"annotation_status": "approved", "id": "1", "human_sentiment": "", "reviewer": "", "reviewed_at": ""})

    def test_approved_evidence_requires_exact_text(self):
        row = {"annotation_status": "approved", "id": "synthetic", "review_text": "Fast delivery",
               "human_sentiment": "positive", "reviewer": "test-reviewer", "reviewed_at": "2026-11-08",
               "split": "test_candidate", "group_id": "test-only",
               "human_aspects": '[{"aspect":"delivery","label":"positive","text":"Fast delivery","span":[0,13]}]'}
        self.assertEqual(validate(row)["split"], "test_candidate")
        row["human_aspects"] = row["human_aspects"].replace('[0,13]', '[0,4]')
        with self.assertRaises(ValueError):
            validate(row)


if __name__ == "__main__":
    unittest.main()
