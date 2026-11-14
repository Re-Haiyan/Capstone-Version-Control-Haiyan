"""The annotation sheets hide everything they must hide, give both annotators the same reviews, and the agreement scoring
handles missing annotations and refuses to report on too little data. Real annotations are never used (and none exist)."""
import csv
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
import agreement  # noqa: E402

SHEETS = ROOT / "research" / "agreement"


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8-sig")))


class SheetsAreBlindAndMatched(unittest.TestCase):
    def setUp(self):
        self.a, self.b = read(SHEETS / "sheet_A.csv"), read(SHEETS / "sheet_B.csv")

    def test_both_annotators_get_the_same_reviews(self):
        self.assertEqual(len(self.a), 300)
        self.assertEqual({r["id"] for r in self.a}, {r["id"] for r in self.b})
        by_a = {r["id"]: r for r in self.a}
        for r in self.b:
            for col in ("stars", "product", "review_text"):
                self.assertEqual(r[col], by_a[r["id"]][col])

    def test_the_label_columns_are_empty(self):
        for sheet in (self.a, self.b):
            for r in sheet:
                self.assertEqual((r["sentiment"], r["flags"], r["confidence"]), ("", "", ""))

    def test_nothing_reveals_a_prediction_a_label_or_the_stratum(self):
        self.assertEqual(list(self.a[0].keys()), agreement.COLS)  # no stratum, source, category, prediction or old-label column
        for r in self.a:
            self.assertRegex(r["id"], r"^S\d{3}$")  # an anonymous id: the original prefix named the source file and so the stratum

    def test_the_order_differs_between_annotators(self):
        self.assertNotEqual([r["id"] for r in self.a], [r["id"] for r in self.b])

    def test_review_text_and_product_context_are_preserved(self):
        mapping = {r["sheet_id"]: r["original_id"] for r in read(SHEETS / "id_map.csv")}
        originals = {}
        for name in ("train_v3", "test_v3"):
            originals.update({r["id"]: r for r in read(ROOT / "evaluation/annotated" / f"{name}.csv")})
        for r in self.a:
            o = originals[mapping[r["id"]]]
            self.assertEqual(r["review_text"], o["review_text"])
            self.assertEqual(r["product"], " ".join(o["product"].split()))

    def test_the_strata_are_150_and_150_and_only_in_the_private_map(self):
        strata = [r["stratum"] for r in read(SHEETS / "id_map.csv")]
        self.assertEqual((strata.count("random"), strata.count("ambiguous_or_rare")), (150, 150))


def sheet(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(agreement.COLS)
        for r in rows:
            w.writerow(r)


class ScoringHandlesMissingAndTooLittle(unittest.TestCase):
    def rows(self, n, flags):
        return [[f"S{i:03d}", 5, "p", f"text {i}", "positive", flags(i), "high"] for i in range(1, n + 1)]

    def test_refuses_with_too_few_completed_reviews(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            sheet(d / "a.csv", self.rows(10, lambda i: "none")); sheet(d / "b.csv", self.rows(10, lambda i: "none"))
            with self.assertRaises(SystemExit):
                agreement.score(d / "a.csv", d / "b.csv", id_map_path=d / "nope.csv", out=lambda *_: None)

    def test_a_blank_row_is_missing_not_none(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ra, rb = self.rows(60, lambda i: "defect" if i % 3 == 0 else "none"), self.rows(60, lambda i: "defect" if i % 3 == 0 else "none")
            for r in rb[:25]:
                r[5] = ""  # annotator B left 25 rows blank
            sheet(d / "a.csv", ra); sheet(d / "b.csv", rb)
            A, B = agreement._read(d / "a.csv"), agreement._read(d / "b.csv")
            self.assertEqual(len(agreement.completed_in_both(A, B)), 35)

    def test_identical_sheets_give_perfect_agreement_and_disagreement_lowers_it(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            same = self.rows(80, lambda i: "defect" if i % 4 == 0 else "none")
            sheet(d / "a.csv", same); sheet(d / "b.csv", same)
            r = agreement.score(d / "a.csv", d / "b.csv", id_map_path=d / "nope.csv", out=lambda *_: None)
            self.assertAlmostEqual(r["ALL completed in both sheets"]["defect"]["kappa"], 1.0)
            flipped = self.rows(80, lambda i: "none" if i % 4 == 0 else "defect")
            sheet(d / "c.csv", flipped)
            r2 = agreement.score(d / "a.csv", d / "c.csv", id_map_path=d / "nope.csv", out=lambda *_: None)
            self.assertLess(r2["ALL completed in both sheets"]["defect"]["kappa"], 0.0)


if __name__ == "__main__":
    unittest.main()
