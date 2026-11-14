"""The proposed fresh evaluation set is blind, blank, and product-disjoint from everything already labelled or inspected."""
import csv
import glob
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRESH = ROOT / "research" / "fresh_eval"
norm = lambda p: " ".join(p.split())


def read(path):
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


class FreshEvaluationSet(unittest.TestCase):
    def setUp(self):
        self.sheet = read(FRESH / "fresh_eval_sheet.csv")
        self.manifest = read(FRESH / "split_manifest.csv")

    def test_the_sheet_is_blank_and_anonymous(self):
        self.assertEqual(list(self.sheet[0].keys()), ["id", "stars", "product", "review_text", "sentiment", "flags", "confidence"])
        for r in self.sheet:
            self.assertRegex(r["id"], r"^F\d{4}$")
            self.assertEqual((r["sentiment"], r["flags"], r["confidence"]), ("", "", ""))

    def test_manifest_matches_the_sheet_and_names_every_role(self):
        self.assertEqual({r["id"] for r in self.sheet}, {r["sheet_id"] for r in self.manifest})
        self.assertEqual({r["role"] for r in self.manifest}, {"representative", "enrichment", "al_candidate"})

    def test_test_products_were_never_labelled_pooled_or_inspected(self):
        seen = set()
        for f in glob.glob(str(ROOT / "evaluation" / "**" / "*.csv"), recursive=True):
            if f.endswith("_key.csv"):
                continue
            seen |= {norm(r["product"]) for r in read(f) if r.get("product")}
        test_products = {norm(r["product"]) for r in self.manifest if r["role"] in ("representative", "enrichment")}
        self.assertTrue(test_products)
        self.assertFalse(test_products & seen)

    def test_active_learning_candidates_never_share_a_product_with_the_test_products(self):
        test_products = {norm(r["product"]) for r in self.manifest if r["role"] in ("representative", "enrichment")}
        candidates = {norm(r["product"]) for r in self.manifest if r["role"] == "al_candidate"}
        self.assertFalse(test_products & candidates)

    def test_only_the_representative_role_carries_sampling_weights(self):
        for r in self.manifest:
            self.assertEqual(r["sampling_weight"] != "", r["role"] == "representative")
            if r["role"] == "representative":
                self.assertGreater(float(r["sampling_weight"]), 0)


if __name__ == "__main__":
    unittest.main()
