"""Source-only integrity checks for Phase 5."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "research/xlmr_optimization/phase5/label_quality_audit.py"
spec = importlib.util.spec_from_file_location("phase5audit", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def write(path, rows):
    keys = ["id", "review_text", "product", "language_hint", "platform", "sentiment", "tags", "confidence"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


class LabelAuditTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        (self.root/"annotation"/"ai_labelled").mkdir(parents=True)
        self.a = {"id": "N0001", "review_text": "Hindi ko pa nasubukan, will update later",
                  "product": "one", "language_hint": "taglish", "platform": "Lazada",
                  "sentiment": "", "tags": "", "confidence": ""}
        self.b = dict(self.a, sentiment="neutral", tags="no-opinion", confidence="low")
        self.raw = self.root/"annotation"/"source.csv"
        self.ai = self.root/"annotation"/"ai_labelled"/"labeled.csv"

    def test_valid_pair(self):
        write(self.raw, [self.a]); write(self.ai, [self.b])
        rows = m.audit_pair(self.root, "candidates", "source.csv", "labeled.csv", 1)
        self.assertIn("undersampled_language", rows[0]["flags"])

    def test_text_mutation_rejected(self):
        write(self.raw, [self.a]); write(self.ai, [dict(self.b, review_text="cut off")])
        with self.assertRaisesRegex(ValueError, "review_text altered"):
            m.audit_pair(self.root, "candidates", "source.csv", "labeled.csv", 1)

    def test_duplicate_id_rejected(self):
        write(self.raw, [self.a, self.a])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            m.read(self.raw)

    def test_queue_is_deterministic(self):
        rows = [{"id":f"N{i:04}", "split":"candidates", "label":"neutral", "language":"taglish",
                 "flags":["undersampled_language"], "tag_shape":False} for i in range(30)]
        self.assertEqual(m.select_queue(rows), m.select_queue(list(reversed(rows))))
        self.assertNotIn("original_label", m.select_queue(rows)[0])


if __name__ == "__main__":
    unittest.main()
