"""agreement.py check: a completed sheet is validated before use, and provenance is recorded without inventing anything."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
import agreement  # noqa: E402


def write(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh); w.writerow(agreement.COLS)
        w.writerows(rows)


BLANK = [[f"S{i:03d}", 5, "Product", f"review text {i}", "", "", ""] for i in range(1, 7)]


class CheckSheets(unittest.TestCase):
    def run_check(self, rows, **kw):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); write(d / "blank.csv", BLANK); write(d / "done.csv", rows)
            lines = []
            problems = agreement.check(d / "done.csv", d / "blank.csv", out=lines.append, log_path=d / "log.csv", **kw)
            log = list(csv.DictReader(open(d / "log.csv", encoding="utf-8-sig"))) if (d / "log.csv").exists() else []
            return problems, lines, log

    def test_a_clean_sheet_has_no_problems(self):
        rows = [r[:4] + ["positive", "defect;delivery" if i == 0 else "none", "high"] for i, r in enumerate(BLANK)]
        problems, lines, _ = self.run_check(rows)
        self.assertFalse([k for k, v in problems.items() if k != "blank_rows" and v])

    def test_bad_values_changed_text_and_none_mixed_with_flags_are_reported(self):
        rows = [r[:4] + ["positive", "none", "high"] for r in BLANK]
        rows[0][4] = "great"; rows[1][5] = "brokenx"; rows[2][6] = "sure"; rows[3][3] = "edited review"; rows[4][5] = "none;defect"
        problems, _, _ = self.run_check(rows)
        self.assertEqual(problems["bad_sentiment"], ["S001"]); self.assertEqual(problems["bad_flags"], ["S002"]); self.assertEqual(problems["bad_confidence"], ["S003"])
        self.assertEqual(problems["changed_text"], ["S004"]); self.assertEqual(problems["none_mixed_with_flags"], ["S005"])

    def test_a_blank_row_is_missing_not_none_and_a_dropped_row_is_reported(self):
        rows = [r[:4] + ["positive", "none", "high"] for r in BLANK[:4]]
        rows[0][4:] = ["", "", ""]
        problems, _, _ = self.run_check(rows)
        self.assertEqual(problems["blank_rows"], 1); self.assertEqual(problems["missing_ids"], ["S005", "S006"])

    def test_provenance_is_recorded_only_when_asked_and_carries_a_checksum(self):
        rows = [r[:4] + ["positive", "none", "high"] for r in BLANK]
        _, _, log = self.run_check(rows)
        self.assertEqual(log, [])
        _, _, log = self.run_check(rows, annotator="A01", policy="v1")
        self.assertEqual(len(log), 1)
        self.assertEqual((log[0]["annotator_id"], log[0]["policy_version"], log[0]["rows_completed"]), ("A01", "v1", "6"))
        self.assertEqual(len(log[0]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
