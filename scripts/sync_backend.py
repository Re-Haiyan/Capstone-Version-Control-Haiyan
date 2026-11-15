"""Copy the part of the original app this app runs on into backend/, WITHOUT overwriting work done here since.

What is copied: the files the running app was traced to import or open on 14 Oct 2026 (the Flask server, the review
checker with its word lists and models, the "what is typical" baseline, the Lazada scanner), the original app's own
pages (it serves them at its root), its requirements and its licences. Not copied: research, labelling sheets, tests,
the Shopee and Temu scanners (the app scans Lazada only), and anything with personal data (databases, accounts,
session cookies).

backend/ began as a byte-for-byte copy of the original app (so this one repo runs on another PC). It has since grown
its own work: files edited here (the conclusion words, the hazard rules, the sentiment model) and files that exist only
here (category_copy.py, the product-specific conclusion modules, the category word lists). The original app is older.
A copy that blindly replaced every listed file would silently turn that work back into the older version (on the day
this was fixed, 18 of the 93 listed files had already been edited here).

So this script copies a file only when that is safe, and says clearly when it is not:

  new         the file is not in backend/ yet                                        -> copied
  unchanged   backend/ already has the same bytes                                    -> nothing to do
  updated     backend/'s copy is exactly what the last sync wrote (never edited here)
              and the original has changed                                           -> replaced
  conflict    backend/'s copy was edited here since the last sync, and the original
              differs                                                                -> NOT touched, listed, exit code 1
  kept        listed before, gone from the original, but edited here since            -> NOT deleted, listed
  removed     listed before, gone from the original, never edited here               -> deleted
  local       in backend/ but never in the original (LOCAL_MODULES, word lists ...)  -> never touched, never deleted

`--dry-run` shows the plan and writes nothing. `--force` overwrites conflicts with the original's version (it still never
touches local files); use it only for a file you mean to throw away. After a sync the script checks that every
LOCAL_MODULES file is still there and stops with an error if one is not.

backend/BACKEND_FILES.json records, for every copied file, the SHA-256 the sync wrote, so "edited here since" means "its
SHA-256 differs from the one recorded"; for a conflict the OLD hash is kept so it stays visible as edited. It also lists
the local modules.

    ..\\Capstone-Version-Control-Version-1.1\\.venv\\Scripts\\python.exe scripts\\sync_backend.py --dry-run
    ..\\Capstone-Version-Control-Version-1.1\\.venv\\Scripts\\python.exe scripts\\sync_backend.py

DEFAKETIVE_ORIGINAL names the original app's folder; DEFAKETIVE_BACKEND names the backend folder to write (tests use a copy).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ORIGINAL = Path(os.environ.get("DEFAKETIVE_ORIGINAL") or HERE.parent / "Capstone-Version-Control-Version-1.1")
BACKEND = Path(os.environ.get("DEFAKETIVE_BACKEND") or HERE / "backend")

# Folders are copied whole (without __pycache__); files one by one.
RUNTIME = (
    "webapp.py",
    "accounts.py",
    "data_store.py",
    "dashboard_utils.py",
    "research_utils.py",
    "requirements.txt",
    "LICENSE",
    "templates/",
    "static/",
    "sentiment-analysis/defaketive_sentiment/",
    "sentiment-analysis/models/hazard_classifier_v6/",
    "sentiment-analysis/models/extra_labels_v1/",
    "sentiment-analysis/models/reference_baselines_v1.json",
    "sentiment-analysis/models/sentiment_onnx/xlmr_firecs_v1/",
    "lazada-scraper/src/",
    "lazada-scraper/LICENSE",
)
# Files that exist only in this repo. The sync never copies over, deletes or lists them as copied; it only checks that they
# are still there. Add a new backend module here when it is not part of the original app.
LOCAL_MODULES = (
    "category_copy.py",  # the words of a report by kind of product
    "aspect_profiles.py",  # product-specific conclusions: what shoppers talk about, per product type
    "aspects.py",  # product-specific conclusions: reading the reviews
    "recommendation_policy.py",  # the live decision rules re-stated, and the experimental candidate policy (not wired in)
    "conclusion_text.py",  # product-specific conclusions: the words of the card
)
SKIP_PARTS = {"__pycache__"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def runtime_files(original: Path = ORIGINAL, runtime: tuple[str, ...] = RUNTIME) -> list[str]:
    files: list[str] = []
    for entry in runtime:
        source = original / entry
        if entry.endswith("/"):
            if not source.is_dir():
                sys.exit(f"Missing in the original app: {entry}")
            for path in sorted(source.rglob("*")):
                relative = path.relative_to(original)
                if path.is_file() and not SKIP_PARTS & set(relative.parts) and path.suffix not in SKIP_SUFFIXES:
                    files.append(relative.as_posix())
        elif source.is_file():
            files.append(entry)
        else:
            sys.exit(f"Missing in the original app: {entry}")
    return files


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def original_commit(original: Path = ORIGINAL) -> dict[str, object]:
    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=original, capture_output=True, text=True).stdout.strip()
        except OSError:
            return ""

    return {"commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current")}


def plan(original: Path, backend: Path, files: list[str], manifest: dict[str, str]) -> dict[str, list[str]]:
    """What a sync would do to each file, without doing it."""
    actions: dict[str, list[str]] = {"new": [], "unchanged": [], "updated": [], "conflict": [], "kept": [], "removed": []}
    for path in files:
        source, target = original / path, backend / path
        if not target.is_file():
            actions["new"].append(path)
            continue
        digest, here = sha256(source), sha256(target)
        if here == digest:
            actions["unchanged"].append(path)
        elif path in manifest and here == manifest[path]:
            actions["updated"].append(path)  # still exactly what the last sync wrote: safe to replace
        else:
            actions["conflict"].append(path)  # edited here (or never recorded): the original is OLDER work
    for path in manifest:
        if path in files:
            continue
        target = backend / path
        if not target.is_file():
            continue
        (actions["removed"] if sha256(target) == manifest[path] else actions["kept"]).append(path)
    return actions


def sync(
    original: Path = ORIGINAL,
    backend: Path = BACKEND,
    runtime: tuple[str, ...] = RUNTIME,
    local: tuple[str, ...] = LOCAL_MODULES,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, object]:
    """Run (or plan) a sync. Returns the plan, the files written and the conflicts; exits if a local module is missing."""
    if not (original / "webapp.py").is_file():
        sys.exit(f"The original DeFaketive app was not found at {original}. Set DEFAKETIVE_ORIGINAL to its folder.")
    manifest_path = backend / "BACKEND_FILES.json"
    before = json.loads(manifest_path.read_bytes()) if manifest_path.is_file() else {"files": {}}
    recorded: dict[str, str] = dict(before.get("files", {}))
    files = runtime_files(original, runtime)
    actions = plan(original, backend, files, recorded)
    written: list[str] = []
    overwritten = actions["conflict"] if force else []
    if not dry_run:
        for path in actions["removed"]:
            (backend / path).unlink(missing_ok=True)
            recorded.pop(path, None)
        for path in actions["new"] + actions["updated"] + overwritten:
            target = backend / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original / path, target)
            recorded[path] = sha256(original / path)
            written.append(path)
        for path in actions["unchanged"]:
            recorded.setdefault(path, sha256(backend / path))
        manifest_path.write_bytes(
            (
                json.dumps(
                    {
                        "what": "Files copied from the original app by scripts/sync_backend.py. A file edited here since is never overwritten (see the script). 'local_modules' exist only here.",
                        "original": original_commit(original),
                        "copied_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "files": dict(sorted(recorded.items())),
                        "local_modules": {name: sha256(backend / name) for name in local if (backend / name).is_file()},
                    },
                    indent=1,
                )
                + "\n"
            ).encode("utf-8")
        )
    missing = [name for name in local if not (backend / name).is_file()]
    if missing:
        sys.exit("Local modules are missing from backend/ after the sync: " + ", ".join(missing) + ". Restore them (git checkout) before running or deploying.")
    return {"plan": actions, "written": written, "overwritten": overwritten, "conflicts": [] if force else actions["conflict"], "dry_run": dry_run}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="show what would happen and write nothing")
    parser.add_argument("--force", action="store_true", help="overwrite files edited here with the original's version (never touches local modules)")
    args = parser.parse_args(argv)
    result = sync(force=args.force, dry_run=args.dry_run)
    actions = result["plan"]
    print(
        f"backend/: {'plan only, nothing written' if args.dry_run else 'synced'}: {len(actions['new'])} new, {len(actions['updated'])} updated, "
        f"{len(actions['unchanged'])} unchanged, {len(actions['removed'])} removed, {len(actions['kept'])} kept, {len(actions['conflict'])} conflict(s)."
    )
    for path in actions["conflict"]:
        print(f"  CONFLICT  {path}" + ("  (overwritten, --force)" if path in result["overwritten"] else "  (edited here since the last sync; the original's version was NOT copied)"))
    for path in actions["kept"]:
        print(f"  KEPT      {path}  (gone from the original but edited here; NOT deleted)")
    if result["conflicts"]:
        print("Exit 1: the files above differ from the original and were edited here. Merge them by hand, or use --force for a file you mean to discard.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
