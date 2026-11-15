"""research/xlmr_optimization/sentiment_agreement.py: the annotation workflow tooling. The sheets here are SYNTHETIC test fixtures made by the
test itself to exercise the code; they are not annotations and no figure from them means anything."""
import contextlib, csv, io, pathlib, sys, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "research" / "xlmr_optimization"))
import sentiment_agreement as sa  # noqa: E402

COLS = ["id", "product", "category_group", "platform", "language_hint", "review_text", "sentiment", "confidence", "rationale"]


def sheet(folder, name, labels, edit=None):
    path = folder / name
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        for i, lab in enumerate(labels):
            text = f"synthetic fixture review {i}" if edit != i else "edited text"
            w.writerow([f"T{i:03d}", "fixture product", "electronics", "x", "english", text, lab, "high" if lab else "", "r" if lab else ""])
    return path


class Workflow(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())
        sa.ANN = self.dir

    def run_quiet(self, fn, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = fn(*args)
        return code, out.getvalue()

    def test_check_flags_edited_text_bad_values_and_missing_rows(self):
        blank = sheet(self.dir, "blank.csv", [""] * 40)
        good = sheet(self.dir, "good.csv", ["positive", "negative", "neutral", "mixed"] * 10)
        self.assertEqual(self.run_quiet(sa.check, good, blank)[0], 0)
        self.assertEqual(self.run_quiet(sa.check, sheet(self.dir, "e.csv", ["positive"] * 40, edit=3), blank)[0], 1)
        self.assertEqual(self.run_quiet(sa.check, sheet(self.dir, "b.csv", ["great"] * 40), blank)[0], 1)

    def test_provenance_line_is_written_with_a_hash(self):
        good = sheet(self.dir, "A.csv", ["positive"] * 40)
        self.run_quiet(sa.check, good, None, "A01", "v1")
        line = list(csv.DictReader(open(self.dir / "provenance_log.csv")))[0]
        self.assertEqual((line["annotator_id"], line["policy_version"], line["rows_completed"]), ("A01", "v1", "40"))
        self.assertEqual(len(line["sha256"]), 64)

    def test_score_refuses_under_30_and_gives_kappa_one_for_identical_sheets(self):
        few = sheet(self.dir, "f.csv", ["positive"] * 10 + [""] * 30)
        with self.assertRaises(SystemExit):
            self.run_quiet(sa.score, few, few)
        labels = ["positive", "negative", "neutral"] * 20
        a = sheet(self.dir, "a.csv", labels)
        self.assertAlmostEqual(sa.kappa(labels, labels, ["positive", "negative", "neutral"]), 1.0)
        code, out = self.run_quiet(sa.score, a, a)
        self.assertIn("kappa 1.000", out)

    def test_adjudication_lists_only_disagreements_and_leaves_final_fields_empty(self):
        a = sheet(self.dir, "a.csv", ["positive"] * 30 + ["negative"] * 10)
        b = sheet(self.dir, "b.csv", ["positive"] * 30 + ["neutral"] * 10)
        self.run_quiet(sa.adjudication, a, b)
        rows = list(csv.DictReader(open(self.dir / "adjudication_sheet.csv", encoding="utf-8-sig")))
        self.assertEqual(len(rows), 10)
        self.assertTrue(all(r["final_label"] == "" and r["adjudicator_id"] == "" for r in rows))


if __name__ == "__main__":
    unittest.main()
