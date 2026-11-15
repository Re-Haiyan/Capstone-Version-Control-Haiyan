"""Read-only DeFaketive VM preflight; NEVER upgrades, restarts, or backs up.

Run from the Git checkout (or pass --live-root) after the operator has separately
created a dated, access-controlled off-VM database backup. The script checks
SQLite consistency without reading user records. A pass only means that this
subset of preflight checks passed; it is NEVER production release approval.

  python scripts/pre_vm_audit.py --live-root /opt/defaketive \
    --backup-dir /secure/off-repo/snapshot-YYYY-MM-DD --require-safe

No service restart, git pull, migration, configuration modification or database
writes are performed. Do not commit the resulting output to the repository.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

DB_NAMES = ("defaketive.db", "accounts.db")
DB_RELATIVE = ("backend/defaketive.db", "backend/instance/accounts.db")


def _git(root: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True, text=True, timeout=8, check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _sqlite_check(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"present": False, "integrity": "missing"}
    # SQLite 'mode=ro' explicitly forbids database writes. Do not use connect()
    # without URI mode: that may create an empty database on a typo.
    connection = None
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
        result = connection.execute("PRAGMA quick_check").fetchone()
        tables = connection.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        ok = bool(result) and result[0] == "ok" and tables > 0
        return {"present": True, "integrity": "ok" if ok else "failed",
                "schema_present": tables > 0}
    except (sqlite3.Error, OSError):
        return {"present": True, "integrity": "unreadable"}
    finally:
        if connection is not None:
            connection.close()


def _contained(child: Path, directory: Path) -> bool:
    resolved = child.resolve()
    base = directory.resolve()
    return resolved == base or base in resolved.parents


def inspect(live_root: Path, backup_dir: Path) -> dict[str, object]:
    live_root, backup_dir = live_root.resolve(), backup_dir.resolve()
    checkout = {
        "sha": _git(live_root, "rev-parse", "HEAD"),
        "branch": _git(live_root, "branch", "--show-current"),
        "tracked_changes": _git(live_root, "status", "--porcelain", "--untracked-files=no"),
    }
    # Do not print paths, service environments, personal data, account counts,
    # review text or secrets. A real production backup must be stored OFF the
    # checkout and cannot be identical to the original live database.
    backup_is_separate = (
        live_root != backup_dir
        and not _contained(backup_dir, live_root)
        and not _contained(live_root, backup_dir)
    )
    databases: dict[str, object] = {}
    for name, rel in zip(DB_NAMES, DB_RELATIVE):
        source = live_root / rel
        backup = backup_dir / name
        distinct = backup_is_separate
        if source.exists() and backup.exists():
            try:
                distinct = distinct and not source.samefile(backup)
            except OSError:
                distinct = False
        databases[name] = {
            "production": _sqlite_check(source),
            "snapshot": _sqlite_check(backup) if distinct else {"present": False, "integrity": "invalid_location"},
            "distinct_files": distinct,
        }
    source_ok = all(
        row["production"].get("integrity") == "ok" for row in databases.values()
    )
    snapshot_ok = all(
        row["snapshot"].get("integrity") == "ok" and row["distinct_files"]
        for row in databases.values()
    )
    checkout_ok = (
        checkout["sha"] is not None
        and checkout["tracked_changes"] is not None
        and checkout["tracked_changes"] == ""
    )
    ok = source_ok and snapshot_ok and checkout_ok
    return {
        "kind": "read_only_pre_vm_snapshot_integrity_audit",
        "live_checkout_sha": checkout["sha"],
        "live_branch": checkout["branch"],
        "checkout_clean": checkout_ok,
        "backup_separate_from_checkout": backup_is_separate,
        "databases": databases,
        "preflight_checks_pass": ok,
        "production_release_approved": False,
        "warnings": [
            "No Azure VM state, live service health, runtime performance, backup age, "
            "full restoration, owner permissions or GitHub CI is verified by this script.",
            "Passing this audit does not authorize merging, updating or restarting production.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live-root", required=True, type=Path)
    parser.add_argument("--backup-dir", required=True, type=Path)
    parser.add_argument("--require-safe", action="store_true",
                        help="Exit 2 if checkout or either SQLite source/snapshot check fails")
    args = parser.parse_args()
    report = inspect(args.live_root, args.backup_dir)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 2 if args.require_safe and not report["preflight_checks_pass"] else 0


if __name__ == "__main__":
    sys.exit(main())
