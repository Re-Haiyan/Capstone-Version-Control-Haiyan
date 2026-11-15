"""research/xlmr_optimization/import_ai_annotations.py: validation and provenance logging of AI-assisted annotations. The rows below are SYNTHETIC fixtures made by the test; they are not annotations."""
import csv, os, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "research" / "xlmr_optimization" / "import_ai_annotations.py"
COLS = ["id", "product", "category_group", "platform", "language_hint", "review_text", "sentiment", "tags", "positive_aspect", "negative_aspect", "confidence", "rationale"]


class Import(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.sheet = self.d / "sheet.csv"
        with open(self.sheet, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(COLS)
            for i in range(4):
                w.writerow([f"D{i:03d}", "p", "electronics", "x", "english", f"synthetic fixture {i}", "", "", "", "", "", ""])
        self.prompt = self.d / "prompt.md"; self.prompt.write_text("prompt", encoding="utf-8")
        self.env = {**os.environ, "AI_ANNOTATION_DIR": str(self.d / "out")}

    def returned(self, rows, name="r.csv"):
        p = self.d / name
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["id", "sentiment", "tags", "positive_aspect", "negative_aspect", "confidence", "rationale"]); w.writerows(rows)
        return p

    def run_import(self, path, extra=None):
        args = [sys.executable, str(SCRIPT), str(path), "--sheet", str(self.sheet), "--model", "fixture-model", "--prompt", str(self.prompt), "--submitted-by", "tester", "--date", "2026-01-01"] + (extra or [])
        return subprocess.run(args, capture_output=True, text=True, env=self.env)

    def test_valid_import_is_merged_logged_and_not_repeatable(self):
        r = self.returned([["D000", "positive", "", "", "", "high", "x"], ["D001", "neutral", "no-opinion", "", "", "high", "x"]])
        done = self.run_import(r)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        merged = list(csv.DictReader(open(self.d / "out/ai_labelled/sheet_ai_v1.csv", encoding="utf-8-sig")))
        self.assertEqual([m["review_text"] for m in merged], ["synthetic fixture 0", "synthetic fixture 1"])  # text comes from the sheet
        log = list(csv.DictReader(open(self.d / "out/ai_annotation_log.csv", encoding="utf-8")))
        self.assertEqual((len(log), log[0]["model_as_stated_by_submitter"], log[0]["rows"]), (1, "fixture-model", "2"))
        self.assertEqual(self.run_import(r).returncode, 1, "a second import of the same ids must be refused")

    def test_rule_violations_and_unknown_ids_are_rejected_and_nothing_is_written(self):
        for rows in ([["D000", "mixed", "", "", "", "high", "x"]], [["D009", "positive", "", "", "", "high", "x"]], [["D000", "neutral", "mixed", "a", "b", "high", "x"]], [["D000", "positive", "", "", "", "high", "x"]] * 2):
            done = self.run_import(self.returned(rows))
            self.assertEqual(done.returncode, 1)
        self.assertFalse((self.d / "out/ai_labelled/sheet_ai_v1.csv").exists())

    def test_provenance_arguments_are_required(self):
        r = self.returned([["D000", "positive", "", "", "", "high", "x"]])
        done = subprocess.run([sys.executable, str(SCRIPT), str(r), "--sheet", str(self.sheet)], capture_output=True, text=True, env=self.env)
        self.assertNotEqual(done.returncode, 0)


if __name__ == "__main__":
    unittest.main()
