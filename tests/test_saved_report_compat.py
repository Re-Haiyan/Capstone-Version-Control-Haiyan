"""Saved-report compatibility after a checker version change (the `pc4` stamp).

1. The public app shows saved reports as stored and marks the ones an older checker made. It never re-analyses them on a request.
2. scripts/recheck_products.py re-checks them gradually: limited, resumable, one product per transaction, with a per-product journal
   that undoes a run, a lock against two runs, and no write at all in a dry run.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from server_under_test import app, webapp  # noqa: E402

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "backend"))
sys.path.insert(0, str(HERE / "backend" / "sentiment-analysis"))
import dashboard_utils  # noqa: E402
import data_store  # noqa: E402


class AppDoesNotReanalyseSavedReports(unittest.TestCase):
    def test_lists_and_details_are_served_as_stored_and_marked(self):
        def forbidden(*args, **kwargs):
            raise AssertionError("a request tried to re-analyse saved reports")

        client = app.test_client()
        with mock.patch.object(dashboard_utils, "analyze_products", forbidden), mock.patch.object(webapp, "analyze_products", forbidden):
            listing = client.get("/api/saved/products")
            self.assertEqual(listing.status_code, 200)
            cards = listing.get_json()["products"]
            self.assertTrue(cards)
            behind = [c for c in cards if c.get("checked_with_current") is False]
            self.assertTrue(behind, "the real database holds reports made by earlier checkers; they must be marked")
            detail = client.get("/api/saved/detail", query_string={"link": behind[0]["link"]})
            self.assertEqual(detail.status_code, 200)
            self.assertIs(detail.get_json()["product"]["checked_with_current"], False)
            self.assertEqual(client.get("/api/picks").status_code, 200)


def _fixture(folder: Path) -> tuple[Path, list[dict]]:
    """A temporary database of three small saved products, each stamped with the previous checker's version."""
    source = HERE / "backend" / "defaketive.db"
    with closing(sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)) as connection:
        rows = connection.execute("SELECT raw_json FROM products WHERE review_count BETWEEN 3 AND 8 ORDER BY review_count LIMIT 3").fetchall()
    products = [json.loads(row[0]) for row in rows]
    products = dashboard_utils.analyze_products(products)
    for product in products:
        for review in product["comments"]:
            if isinstance(review.get("sentiment_analysis"), dict):
                review["sentiment_analysis"]["model_version"] = "legacy+pc3"
    database = folder / "saved.db"
    data_store.save_products(products, source="test", path=database)
    return database, products


def _stale(database: Path) -> int:
    with closing(sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)) as connection:
        stored = [json.loads(row[0]) for row in connection.execute("SELECT raw_json FROM products")]
    return sum(1 for product in stored if not dashboard_utils.analysis_is_current([product]))


def _counts(database: Path) -> tuple[int, int]:
    with closing(sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)) as connection:
        return connection.execute("SELECT COUNT(*) FROM products").fetchone()[0], connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]


def _digest(database: Path) -> str:
    return hashlib.sha256(database.read_bytes()).hexdigest()


class GradualRecheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = Path(tempfile.mkdtemp(prefix="recheck-test-"))
        cls.database, cls.original = _fixture(cls.folder)
        cls.backups = cls.folder / "backups"
        cls.env = {**os.environ, "RECHECK_DB": str(cls.database), "RECHECK_BACKUPS": str(cls.backups), "PYTHONIOENCODING": "utf-8"}
        cls.rows_before = _counts(cls.database)

    @classmethod
    def tearDownClass(cls):
        import shutil

        shutil.rmtree(cls.folder, ignore_errors=True)

    def run_script(self, *args, expect=0):
        done = subprocess.run([sys.executable, str(HERE / "scripts" / "recheck_products.py"), *args], env=self.env, capture_output=True, text=True, cwd=str(HERE))
        self.assertEqual(done.returncode, expect, done.stdout[-1500:] + done.stderr[-1500:])
        return done.stdout

    def test_1_the_fixture_is_stale(self):
        self.assertEqual(_stale(self.database), 3)

    def test_2_a_dry_run_writes_nothing(self):
        before = _digest(self.database)
        self.run_script()
        self.assertEqual(_digest(self.database), before)
        self.assertFalse(self.backups.exists() and list(self.backups.glob("*")))

    def test_3_a_running_lock_stops_a_second_run_and_changes_nothing(self):
        self.backups.mkdir(exist_ok=True)
        lock = self.backups / "recheck.lock"
        lock.write_text(str(os.getpid()))
        try:
            before = _digest(self.database)
            self.run_script("--apply", expect=1)
            self.assertEqual(_digest(self.database), before)
        finally:
            lock.unlink(missing_ok=True)

    def test_4_a_limited_run_then_the_rest_then_a_rollback(self):
        # The site's own reader (saved_pool) keeps reading the database while the re-check saves into it.
        import threading
        from saved_pool import SavedPool

        pool, seen, errors, stop = SavedPool(self.database), [], [], threading.Event()

        def poll():
            while not stop.is_set():
                try:
                    products, _ = pool.snapshot()
                    seen.append(sum(1 for p in products if dashboard_utils.analysis_is_current([p])))
                except Exception as error:  # noqa: BLE001
                    errors.append(repr(error))
                stop.wait(0.05)

        reader = threading.Thread(target=poll, daemon=True)
        reader.start()
        try:
            out = self.run_script("--apply", "--max-products", "2", "--duty", "50")
        finally:
            stop.set()
            reader.join(5)
        self.assertEqual(errors, [], "the site's reader never failed while the re-check was saving")
        self.assertEqual(pool.snapshot()[0] and sum(1 for p in pool.snapshot()[0] if dashboard_utils.analysis_is_current([p])), 2, "the site sees the two re-checked reports as current, and only those")
        self.assertIn("reached --max-products 2", out)
        self.assertEqual(_stale(self.database), 1, "exactly two of three were re-checked")
        self.assertEqual(_counts(self.database), self.rows_before, "no product or review row was added or lost")
        journals = sorted(self.backups.glob("recheck-journal-*.jsonl"))
        self.assertEqual(len(journals), 1)
        first = journals[0]
        self.assertEqual(len(first.read_text(encoding="utf-8").splitlines()), 2)
        self.assertTrue(list(self.backups.glob("defaketive-before-*.db")), "a verified backup was made")
        self.assertFalse((self.backups / "recheck.lock").exists(), "the lock is released")

        out = self.run_script("--apply")  # resumes where it stopped; reuses the recent backup
        self.assertIn("Using the verified backup", out)
        self.assertEqual(_stale(self.database), 0)
        self.assertEqual(_counts(self.database), self.rows_before)

        self.run_script("--apply")  # nothing left to do
        self.assertEqual(_stale(self.database), 0)

        listing = self.run_script("--rollback", str(first))
        self.assertIn("Nothing was written", listing)
        self.assertEqual(_stale(self.database), 0)
        self.run_script("--rollback", str(first), "--apply")
        self.assertEqual(_stale(self.database), 2, "the two products of the first run are back as they were stored")
        self.assertEqual(_counts(self.database), self.rows_before)
        with closing(sqlite3.connect(f"file:{self.database.as_posix()}?mode=ro", uri=True)) as connection:
            restored = {json.loads(r[0])["link"]: json.loads(r[0]) for r in connection.execute("SELECT raw_json FROM products")}
        replaced = [json.loads(line)["link"] for line in first.read_text(encoding="utf-8").splitlines()]
        originals = {p["link"]: p for p in self.original}
        for link in replaced:
            self.assertEqual(restored[link]["comments"][0]["sentiment_analysis"]["model_version"], "legacy+pc3")
            self.assertEqual(len(restored[link]["comments"]), len(originals[link]["comments"]))


if __name__ == "__main__":
    unittest.main()
