"""The product-conclusion sheets are blind (no system output), matched between annotators, and scoring refuses without judgements."""
import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
import conclusion_eval as ce  # noqa: E402

DIR = ROOT / "research" / "conclusion_eval"


def read(path):
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


class ConclusionSheets(unittest.TestCase):
    def setUp(self):
        self.a, self.b = read(DIR / "product_sheet_A.csv"), read(DIR / "product_sheet_B.csv")

    def test_same_products_different_order_empty_judgement(self):
        self.assertEqual({r["product_id"] for r in self.a}, {r["product_id"] for r in self.b})
        self.assertNotEqual([r["product_id"] for r in self.a], [r["product_id"] for r in self.b])
        for r in self.a + self.b:
            self.assertEqual((r["conclusion"], r["serious_safety_concern"], r["counterfeit_concern"], r["main_reason"], r["confidence"]), ("", "", "", "", ""))

    def test_no_system_output_on_the_sheets_or_in_the_reviews_file(self):
        self.assertEqual(list(self.a[0].keys()), ce.SHEET_COLS)
        self.assertEqual(list(read(DIR / "product_reviews.csv")[0].keys()), ["product_id", "stars", "review"])
        for r in self.a:
            self.assertRegex(r["product_id"], r"^P\d{3}$")

    def test_the_private_manifest_names_one_card_per_product(self):
        manifest = read(DIR / "manifest_private.csv")
        self.assertEqual({m["product_id"] for m in manifest}, {r["product_id"] for r in self.a})
        for m in manifest:
            self.assertIn(m["system_conclusion"], ce.CARDS)

    def test_every_product_has_reviews_to_read(self):
        counts = {}
        for r in read(DIR / "product_reviews.csv"):
            counts[r["product_id"]] = counts.get(r["product_id"], 0) + 1
        for r in self.a:
            self.assertGreater(counts.get(r["product_id"], 0), 0)

    def test_scoring_refuses_without_two_judged_sheets(self):
        with self.assertRaises(SystemExit):
            ce.score(DIR / "product_sheet_A.csv", DIR / "product_sheet_B.csv")

    def test_weighted_kappa_on_known_cases(self):
        self.assertAlmostEqual(ce.weighted_kappa([0, 1, 2, 3, 0, 1, 2, 3], [0, 1, 2, 3, 0, 1, 2, 3]), 1.0)
        self.assertLess(ce.weighted_kappa([0, 0, 3, 3, 0, 3], [3, 3, 0, 0, 3, 0]), 0.0)


if __name__ == "__main__":
    unittest.main()
