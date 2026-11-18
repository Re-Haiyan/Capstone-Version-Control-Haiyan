"""Synthetic-only tests for fresh multi-category annotation intake.

Never imports real customer reviews into tests and never asserts a model score.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
from fresh_multicategory_intake import ingest, choose, prepare  # noqa: E402
import argparse


def write(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class IndependentEvaluationIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.eval = self.root / "evaluation" / "old_pool.csv"
        write(self.eval, ["product", "review_text"], [
            {"product": "Previously Studied Smartphone", "review_text": "This is an earlier product review"},
            {"product": "Previously Studied Dress", "review_text": "This review was seen in old evaluation"},
        ])
        self.extra = self.root / "vm_titles.csv"
        write(self.extra, ["name"], [{"name": "Previously Saved Heater"}])
        self.source = self.root / "fresh_reviews.csv"
        self.fields = [
            "marketplace", "product_id", "product", "category", "review_id",
            "review_text", "stars", "collected_at", "rights_confirmed",
            "new_product_verified", "category_verified", "selection_method",
        ]
        self.rows = []
        for cat, title, n in (
            ("phone", "Novel Smartphone", 3),
            ("apparel", "Cotton Shirt", 3),
            ("small_appliance", "Electric Heater", 3),
        ):
            for i in range(n):
                product_name = f"{title} Model {i}"
                for j in range(3):
                    self.rows.append({
                        "marketplace": "shopee", "product_id": f"{cat}-{i}",
                        "product": product_name, "category": cat,
                        "review_id": f"{cat}-{i}-{j}",
                        "review_text": f"Review describes experience with {cat} model {i} take {j}.",
                        "stars": str(1 + j), "collected_at": "2026-11-18",
                        "rights_confirmed": "yes", "new_product_verified": "yes",
                        "category_verified": "yes", "selection_method": "random",
                    })
        write(self.source, self.fields, self.rows)

    def test_new_data_are_blind_and_product_balanced(self) -> None:
        eligible, rejected, report = ingest(self.source, root=self.root, extra=self.extra)
        self.assertEqual(len(eligible), 27)
        self.assertEqual(sum(rejected.values()), 0)
        self.assertTrue(report["vm_saved_titles_checked"])
        selected = choose(eligible, target=12, max_per_product=2, min_groups=3, min_products=6, seed=41)
        self.assertEqual(len(selected), 12)
        self.assertEqual(len({r["group"] for r in selected}), 3)
        from collections import Counter
        self.assertLessEqual(max(Counter(r["product_key"] for r in selected).values()), 2)

        out = self.root / "private_pilot"
        args = argparse.Namespace(
            repo_root=str(self.root), input=str(self.source), known_extra=str(self.extra),
            out_dir=str(out), target=12, max_per_product=2,
            min_groups=3, min_products=6, seed=41,
            model_sha="147eccbfcf206b37550ce9e8b0a71bba626dacc3",
            policy="v1",
        )
        prepare(args)
        summary = json.loads((out / "summary.json").read_text())
        self.assertFalse(summary["accuracy_measured"])
        self.assertFalse(summary["labels_present"])
        self.assertEqual(summary["sampled_reviews"], 12)
        self.assertEqual(summary["sampled_groups"], 3)
        with (out / "annotator_A.csv").open(encoding="utf-8-sig") as f:
            a = list(csv.DictReader(f))
        with (out / "annotator_B.csv").open(encoding="utf-8-sig") as f:
            b = list(csv.DictReader(f))
        self.assertEqual({r["id"] for r in a}, {r["id"] for r in b})
        self.assertNotEqual([r["id"] for r in a], [r["id"] for r in b])
        self.assertTrue(all(not r["sentiment"] and not r["flags"] and not r["confidence"] for r in a+b))
        manifest = (out / "PRIVATE_manifest.csv").read_text(encoding="utf-8-sig")
        self.assertNotIn("Review describes experience", manifest)
        self.assertIn("title_classifier_agrees", manifest)
        with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
            prepare(args)

    def test_historical_and_vm_products_are_excluded(self) -> None:
        candidates = list(self.rows)
        candidates[0] = {**candidates[0], "product": "Previously Studied Smartphone"}
        candidates[1] = {**candidates[1], "product": "Previously Saved Heater"}
        candidates[2] = {
            **candidates[2], "review_text": "This review was seen in old evaluation"
        }
        # Different product ID for previously studied product, to avoid the
        # conflicting-title hard stop on a single source product key.
        for i in range(3):
            candidates[i] = {**candidates[i], "product_id": f"special-{i}"}
        write(self.source, self.fields, candidates)
        eligible, rejected, _ = ingest(self.source, root=self.root, extra=self.extra)
        self.assertEqual(rejected["historical_product"], 2)
        self.assertEqual(rejected["historical_review_text"], 1)
        self.assertEqual(len(eligible), 24)

    def test_read_only_saved_sqlite_catalog_is_supported(self) -> None:
        import sqlite3
        db = self.root / "saved_products.db"
        with sqlite3.connect(db) as con:
            con.execute("CREATE TABLE products (raw_json TEXT NOT NULL)")
            con.execute(
                "INSERT INTO products (raw_json) VALUES (?)",
                (json.dumps({"name": "Cotton Shirt Model 0"}),),
            )
        eligible, rejected, report = ingest(self.source, root=self.root, extra=db)
        self.assertEqual(rejected["historical_product"], 3)
        self.assertEqual(len(eligible), 24)
        self.assertTrue(report["vm_saved_titles_checked"])

    def test_spreadsheet_formula_in_marketplace_reviews_is_rejected(self) -> None:
        rows = list(self.rows)
        rows[0] = {**rows[0], "review_text": "=HYPERLINK(\"evil\",\"click\")"}
        write(self.source, self.fields, rows)
        eligible, rejected, _ = ingest(self.source, root=self.root)
        self.assertEqual(rejected["spreadsheet_formula_risk"], 1)
        self.assertEqual(len(eligible), 26)

    def test_disallow_unauthorized_data_and_unverified_labels(self) -> None:
        for field, value in (
            ("rights_confirmed", "no"),
            ("new_product_verified", ""),
            ("category_verified", "maybe"),
            ("selection_method", "keyword"),
            ("category", "unknown"),
            ("stars", "9"),
            ("marketplace", "other"),
            ("collected_at", "2040-01-01"),
        ):
            with self.subTest(field=field):
                candidates = list(self.rows)
                candidates[0] = {**candidates[0], field: value}
                write(self.source, self.fields, candidates)
                with self.assertRaises(ValueError):
                    ingest(self.source, root=self.root)
        write(self.source, self.fields, self.rows)

    def test_group_or_product_coverage_does_not_get_faked(self) -> None:
        eligible, *_ = ingest(self.source, root=self.root)
        with self.assertRaisesRegex(ValueError, "product groups available"):
            choose(eligible, target=12, max_per_product=2, min_groups=8, min_products=3, seed=1)
        with self.assertRaisesRegex(ValueError, "eligible capped reviews"):
            choose(eligible, target=100, max_per_product=2, min_groups=2, min_products=2, seed=1)
        with self.assertRaisesRegex(ValueError, "distinct products"):
            choose(eligible, target=6, max_per_product=2, min_groups=2, min_products=7, seed=1)

    def test_existing_history_folder_is_required(self) -> None:
        self.eval.unlink()
        self.eval.parent.rmdir()
        with self.assertRaisesRegex(ValueError, "Missing historical evaluation"):
            ingest(self.source, root=self.root)


if __name__ == "__main__":
    unittest.main()
