"""The VM preflight must be read-only and fail closed on missing backup evidence.

All fixtures are synthetic SQLite databases in a temporary directory; no
production data, secrets, service commands, or network access is required.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("pre_vm_audit", ROOT / "scripts" / "pre_vm_audit.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def create_db(path: Path, with_schema: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        if with_schema:
            conn.execute("CREATE TABLE synthetic_test (id INTEGER PRIMARY KEY, secret TEXT)")
            conn.execute("INSERT INTO synthetic_test (secret) VALUES ('never expose private value')")
        conn.commit()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PreVMAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name)
        self.live = self.parent / "live"
        self.backup = self.parent / "private-backup"
        for name, rel in zip(AUDIT.DB_NAMES, AUDIT.DB_RELATIVE):
            create_db(self.live / rel)
            create_db(self.backup / name)
        self.patch = mock.patch.object(
            AUDIT, "_git",
            side_effect=lambda _, *cmd: (
                "0123456789abcdef" if cmd == ("rev-parse", "HEAD") else
                "deployment" if cmd == ("branch", "--show-current") else
                "" if cmd == ("status", "--porcelain", "--untracked-files=no") else
                None
            ),
        )
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_valid_sources_and_independent_backups_are_read_only(self):
        paths = [self.live / rel for rel in AUDIT.DB_RELATIVE] + [
            self.backup / name for name in AUDIT.DB_NAMES
        ]
        hashes_before = [digest(p) for p in paths]
        result = AUDIT.inspect(self.live, self.backup)
        hashes_after = [digest(p) for p in paths]
        self.assertTrue(result["preflight_checks_pass"])
        self.assertFalse(result["production_release_approved"])
        self.assertEqual(hashes_before, hashes_after)
        self.assertEqual(result["live_checkout_sha"], "0123456789abcdef")
        raw = json.dumps(result)
        self.assertNotIn("never expose private value", raw)
        self.assertNotIn(str(self.backup), raw)

    def test_missing_snapshot_fails_closed(self):
        (self.backup / "accounts.db").unlink()
        result = AUDIT.inspect(self.live, self.backup)
        self.assertFalse(result["preflight_checks_pass"])
        self.assertEqual(result["databases"]["accounts.db"]["snapshot"]["integrity"], "missing")

    def test_no_backup_inside_git_checkout(self):
        copied = self.live / "backups" / "today"
        copied.mkdir(parents=True)
        for name in AUDIT.DB_NAMES:
            create_db(copied / name)
        result = AUDIT.inspect(self.live, copied)
        self.assertFalse(result["preflight_checks_pass"])
        self.assertFalse(result["backup_separate_from_checkout"])
        self.assertEqual(result["databases"]["accounts.db"]["snapshot"]["integrity"], "invalid_location")

    def test_no_live_database_missing(self):
        (self.live / "backend/instance/accounts.db").unlink()
        self.assertFalse(AUDIT.inspect(self.live, self.backup)["preflight_checks_pass"])

    def test_schema_absent_or_corrupted_backup_is_rejected(self):
        path = self.backup / "accounts.db"
        path.unlink()
        create_db(path, with_schema=False)
        self.assertEqual(AUDIT._sqlite_check(path)["integrity"], "failed")
        path.write_text("not a real SQLite database", encoding="utf-8")
        self.assertEqual(AUDIT._sqlite_check(path)["integrity"], "unreadable")
        self.assertFalse(AUDIT.inspect(self.live, self.backup)["preflight_checks_pass"])

    def test_git_unknown_or_dirty_fails_closed(self):
        for git_result in (None, " M serve.py"):
            with self.subTest(git_result=git_result):
                with mock.patch.object(AUDIT, "_git", return_value=git_result):
                    self.assertFalse(AUDIT.inspect(self.live, self.backup)["preflight_checks_pass"])

    def test_invalid_same_directory_or_hardlink_is_rejected(self):
        self.assertFalse(AUDIT.inspect(self.live, self.live)["preflight_checks_pass"])
        same_file = self.backup / "accounts.db"
        same_file.unlink()
        import os
        os.link(self.live / "backend/instance/accounts.db", same_file)
        report = AUDIT.inspect(self.live, self.backup)
        self.assertFalse(report["databases"]["accounts.db"]["distinct_files"])
        self.assertFalse(report["preflight_checks_pass"])

    def test_never_reports_that_release_is_approved(self):
        report = AUDIT.inspect(self.live, self.backup)
        self.assertFalse(report["production_release_approved"])
        self.assertTrue(any("does not authorize" in v for v in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
