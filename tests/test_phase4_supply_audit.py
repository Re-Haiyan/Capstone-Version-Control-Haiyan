"""Synthetic-only tests for phase4/supply_audit.py: aggregate counts only, historical exclusion, no review text in the output, rights never implied."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "research/product_specific_conclusions/phase4/supply_audit.py"


def make_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.execute("create table products (raw_json text)")
    fresh = {"link": "https://www.lazada.com.ph/products/synthetic-audit-product-1.html", "name": "Synthetic audit kettle model zq1",
             "comments": [{"content": "Synthetic sentence one about a kettle that heats water."}, {"content": "Synthetic sentence one about a kettle that heats water."},
                          {"content": "A different synthetic remark concerning the handle grip."}]}
    con.execute("insert into products values (?)", (json.dumps(fresh),))
    con.execute("insert into products values (?)", (json.dumps({"name": "no link here", "comments": []}),))
    con.commit(); con.close()


class SupplyAudit(unittest.TestCase):
    def test_counts_only_and_no_rights_claim(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "x.db"; make_db(db); out = Path(d) / "o.json"
            r = subprocess.run([sys.executable, str(SCRIPT), "--db", str(db), "--out", str(out)], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertIn("rights NOT established", data["purpose"])
            self.assertTrue(data["split_estimate_not_intake_assignment"])
            self.assertTrue(data["privacy_and_intake_eligibility_not_verified"])
            self.assertIn("canonical listing_id", data["split_estimate_caveat"])
            self.assertEqual(data["counts"]["products_in_database"], 2)
            self.assertEqual(data["counts"]["product_missing_link_or_title"], 1)
            self.assertEqual(data["counts"]["review_duplicate_within_supply"], 1)
            self.assertEqual(sum(data["surviving_reviews_by_split_if_rights_were_confirmed"].values()), 2)
            blob = out.read_text(encoding="utf-8") + r.stdout
            for forbidden in ("Synthetic sentence", "synthetic-audit-product", "kettle", "lazada.com.ph", "rights_confirmed"):
                self.assertNotIn(forbidden, blob)


if __name__ == "__main__":
    unittest.main()
