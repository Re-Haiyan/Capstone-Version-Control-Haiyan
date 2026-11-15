"""Synthetic-only tests; never fetch, import, or publish real review text."""
from __future__ import annotations

import contextlib
import csv
import io
import json
import pathlib
import sys
import tempfile
import unittest

import prepare_scraper_heldout as intake


class PrivateIntakeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = pathlib.Path(tmp.name)
        self.root = self.dir / "fake_repo"
        self.root.mkdir()
        self.previous_root = intake.ROOT
        self.previous_history = intake.HISTORY
        self.addCleanup(lambda: setattr(intake, "ROOT", self.previous_root))
        self.addCleanup(lambda: setattr(intake, "HISTORY", self.previous_history))
        intake.ROOT = self.root
        intake.HISTORY = ("history.csv",)
        with (self.root / "history.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["product", "review_text", "product_link"])
            w.writeheader()
            w.writerow({
                "product": "Historic existing item",
                "review_text": "This old review was already used for training",
                "product_link": "https://www.lazada.com.ph/products/historic-i999999.html",
            })
        self.rights = self.dir / "rights.json"
        self.rights.write_text(json.dumps({
            "source": "lazada_ph", "authorized_by": "synthetic test author",
            "rights_basis": "synthetic-only", "record_date": "2026-11-16",
            "allowed_collection": True, "allowed_research_storage": True,
        }))
        products = []
        for i in range(101):
            products.append({
                "name": f"Novel item synthetic alpha {i}",
                "link": f"https://www.lazada.com.ph/products/novel-{i}-i{200000+i}.html",
                "comments": [{"comment_id": str(i*7+k), "rating": (k%5)+1,
                              "content": f"A synthetic fictional review for item number {i} example {k} and no real customers"}
                             for k in range(5)]
            })
        products.extend([
            {"name": "Historic existing item", "link": "https://www.lazada.com.ph/products/historic-i999999.html",
             "comments": [{"comment_id": "h", "rating": 1, "content": "This old review was already used for training"}]},
            {"name": "Privacy example", "link": "https://www.lazada.com.ph/products/priv-i999998.html",
             "comments": [{"comment_id": "p", "rating": 2, "content": "Please text me 09171234567 about the fictional item"}]},
        ])
        self.infile = self.dir / "raw.json"
        self.infile.write_text(json.dumps(products))
        self.out = self.dir / "private"

    def call(self, *arguments):
        former = sys.argv
        try:
            sys.argv = ["script", "--scrape-json", str(self.infile),
                        "--authorization-record", str(self.rights),
                        "--output-private", str(self.out), *arguments]
            with contextlib.redirect_stdout(io.StringIO()) as capture:
                code = intake.main()
            return code, capture.getvalue()
        finally:
            sys.argv = former

    def test_private_output_and_no_invented_labels(self):
        code, stdout = self.call()
        self.assertEqual(code, 0)
        self.assertNotIn("synthetic fictional review", stdout)
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(manifest["reviews_selected"], 400)
        self.assertGreaterEqual(manifest["distinct_product_links"], 100)
        self.assertEqual(manifest["status"], "provisional_missing_historical_product_ids")
        self.assertGreater(manifest["excluded_counts"]["historical_product"], 0)
        self.assertGreater(manifest["excluded_counts"]["short_or_personal_data"], 0)
        blind = intake.csvrows(self.out / "blind_reviewer_A.csv")
        self.assertEqual(len(blind), 400)
        self.assertTrue(all(not r["sentiment"] for r in blind))
        self.assertTrue(all("stars" not in r and "source_review_id" not in r for r in blind))
        self.assertTrue(all("09171234567" not in r["review_text"] for r in blind))
        self.assertTrue(all("This old review" not in r["review_text"] for r in blind))

    def test_permissions_required(self):
        self.rights.unlink()
        with self.assertRaisesRegex(ValueError, "Written permission"):
            self.call()
        self.assertFalse(self.out.exists())

    def test_no_fabrication_if_too_few_reviews(self):
        code, _ = self.call("--target", "700")
        self.assertEqual(code, 2)
        manifest = json.loads((self.out / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "insufficient_new_reviews_or_products")
        self.assertLess(manifest["reviews_selected"], 700)

    def test_item_id_dedupes_changed_slug(self):
        original = "https://www.lazada.com.ph/products/first-slug-i2345678.html?aff=123"
        renamed = "https://www.lazada.com.ph/products/renamed-slug-i2345678.html"
        self.assertEqual(intake.product_key(original), intake.product_key(renamed))
        kept, discarded = intake.dedupe(
            [{"product": "Different title", "link": renamed, "id": "9",
              "text": "This product has a review but is historically present"}],
            set(), {intake.product_key(original)}, set())
        self.assertEqual(len(kept), 0)
        self.assertEqual(discarded["historical_product"], 1)

    def test_no_raw_reviews_in_public_repo(self):
        former = sys.argv
        try:
            sys.argv = ["script", "--scrape-json", str(self.infile),
                        "--authorization-record", str(self.rights),
                        "--output-private", str(self.root / "private")]
            with self.assertRaisesRegex(ValueError, "public repository"):
                intake.main()
        finally:
            sys.argv = former


if __name__ == "__main__":
    unittest.main()
