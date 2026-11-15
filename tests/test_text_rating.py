"""The rating sheets for the words of the conclusion are blind, matched between annotators, and scoring refuses without judgements."""
import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "product_specific_conclusions"))
import text_rating as tr  # noqa: E402

DIR = ROOT / "research" / "product_specific_conclusions" / "rating"


def read(path):
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


class RatingSheets(unittest.TestCase):
    def setUp(self):
        self.a, self.b, self.key = read(DIR / "sheet_A.csv"), read(DIR / "sheet_B.csv"), read(DIR / "key_private.csv")

    def test_same_products_different_order_empty_ratings(self):
        self.assertEqual({r["product_id"] for r in self.a}, {r["product_id"] for r in self.b})
        self.assertNotEqual([r["product_id"] for r in self.a], [r["product_id"] for r in self.b])
        for row in self.a + self.b:
            for column in tr.SHEET_COLS[2:]:
                self.assertEqual(row[column], "")

    def test_the_sheets_do_not_say_which_text_is_new(self):
        self.assertEqual(list(self.a[0].keys()), tr.TEXT_COLS + tr.SHEET_COLS[2:])
        for row in self.a + self.b:
            self.assertNotIn("old", (row["text_1"], row["text_2"]))
            self.assertNotIn("new", (row["text_1"], row["text_2"]))
            self.assertNotEqual(row["text_1"], row["text_2"])

    def test_the_key_covers_every_product_and_both_versions_in_random_order(self):
        self.assertEqual({k["product_id"] for k in self.key}, {r["product_id"] for r in self.a})
        for k in self.key:
            self.assertEqual({k["text_1"], k["text_2"]}, {"old", "new"})
        order = {(k["text_1"], k["text_2"]) for k in self.key}
        self.assertEqual(order, {("old", "new"), ("new", "old")}, "the position of the new text is not always the same")

    def test_scoring_refuses_without_judged_sheets(self):
        with self.assertRaises(SystemExit):
            tr.score(DIR / "sheet_A.csv", DIR / "sheet_B.csv")

    def test_weighted_kappa_on_known_cases(self):
        self.assertAlmostEqual(tr.weighted_kappa([1, 2, 3, 4, 5, 1, 2, 3], [1, 2, 3, 4, 5, 1, 2, 3]), 1.0)
        self.assertLess(tr.weighted_kappa([1, 1, 5, 5, 1, 5], [5, 5, 1, 1, 5, 1]), 0.0)


if __name__ == "__main__":
    unittest.main()
