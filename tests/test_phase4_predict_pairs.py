"""Synthetic-only test for Phase 4 real-extractor prediction export."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "research/product_specific_conclusions/phase4/predict_pairs.py"


class PredictionExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.impl = self.path / "synthetic_extractor"
        self.impl.mkdir()
        (self.impl / "aspect_profiles.py").write_text(
            "class A:\n"
            "    def __init__(self,id,kind): self.id=id; self.kind=kind\n"
            "def aspects_for(category,group): return [A('build_quality','product')]\n",
            encoding="utf-8",
        )
        (self.impl / "aspects.py").write_text(
            "ASPECT_RULES_VERSION='SYNTHETIC_ONLY'\n"
            "def extract(reviews,category,group):\n"
            "    return [{'id':'build_quality','polarity':'positive'}] "
            "if 'quality' in reviews[0]['content'].lower() else []\n"
            "def iter_claims(extraction):\n"
            "    for item in extraction: yield ({'id':item['id']},item['polarity'],None)\n",
            encoding="utf-8",
        )
        self.reviews = self.path / "D3.csv"
        rows = [
            {"review_id":"someid001","product_hash":"product001","category":"apparel",
             "group":"fashion","language":"en","stars":"5","review_text":"Quality of this synthetic item is good."},
            {"review_id":"someid002","product_hash":"product002","category":"apparel",
             "group":"fashion","language":"en","stars":"1","review_text":"This is only test text with no opinion."},
        ]
        with self.reviews.open("w", encoding="utf-8", newline="") as stream:
            w = csv.DictWriter(stream, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        self.out = self.path / "predictions.jsonl"
        self.meta = self.path / "metadata.json"

    def run_cli(self, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--split", "D3",
             "--reviews", str(self.reviews), "--impl", str(self.impl),
             "--role", "baseline", "--out", str(self.out),
             "--metadata-out", str(self.meta), *extra],
            capture_output=True, text=True, cwd=ROOT,
        )

    def test_actual_synthetic_extractor_runs_with_provenance(self):
        p = self.run_cli()
        self.assertEqual(p.returncode, 0, p.stderr)
        rows = [json.loads(x) for x in self.out.read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["pairs"], [{
            "kind": "product", "aspect_id": "build_quality", "polarity": "positive"
        }])
        self.assertEqual(rows[1]["pairs"], [])
        meta = json.loads(self.meta.read_text())
        self.assertEqual(meta["reviews"], 2)
        self.assertFalse(meta["labels_read"])
        self.assertFalse(meta["production_adoption_approved"])
        self.assertIn("predictions_sha256", meta)
        for blob in (self.out.read_text(), self.meta.read_text(), p.stdout):
            self.assertNotIn("Quality of this synthetic item", blob)
            self.assertNotIn("This is only test text", blob)

    def test_refuse_overwrite_predictions(self):
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertEqual(self.run_cli().returncode, 2)

    def test_f2_cannot_be_inspected_without_freeze(self):
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "--split", "F2",
             "--reviews", str(self.reviews), "--impl", str(self.impl),
             "--role", "candidate", "--out", str(self.out),
             "--metadata-out", str(self.meta)],
            capture_output=True, text=True, cwd=ROOT,
        )
        self.assertEqual(r.returncode, 2)
        self.assertFalse(self.out.exists())

    def test_refuse_extractor_without_profiles(self):
        (self.impl / "aspect_profiles.py").unlink()
        r = self.run_cli()
        self.assertEqual(r.returncode, 2)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
