"""Re-check the saved products that an older checker analysed, so they get a verdict from the current one.

"Older" means either a report in a format the app no longer reads ("Not analyzed yet") or a report made by an
earlier version of the checker. The app shows a saved report as it was stored, so run this after the checker
changes.

It uses the original app's own functions (nothing in the original app is edited) and the reviews that are
already stored in its database. No marketplace is contacted.

Run it with the original app's Python, from this folder:

    ..\\Capstone-Version-Control-Version-1.1\\.venv\\Scripts\\python.exe scripts\\recheck_products.py
    ..\\Capstone-Version-Control-Version-1.1\\.venv\\Scripts\\python.exe scripts\\recheck_products.py --apply

Without --apply it is a dry run: it lists what it would re-check and writes nothing at all.

With --apply it first copies defaketive.db into this project's backups/ folder and checks the copy, and only then
analyses and saves. To undo, close both apps and copy that backup file back over the original's defaketive.db.

Gradual, controlled re-checking (for a live server): the run is limited and resumable, because a re-checked report is then
current and is not chosen again.

    --max-products N   --max-reviews N   --max-minutes M     stop after this much work; run again later for the rest
    --duty 50                                                work half of the time (sleep as long as each product took)
    --max-load 1.5                                           wait while the machine's 1-minute load is above this (Linux)
    --order recent|small                                     recently saved first (default) or fewest reviews first

Each product is saved on its own, right after it is analysed, so a stop at any moment loses nothing and leaves nothing half done.
Before a product is replaced its previous stored report is appended to backups/recheck-journal-*.jsonl, so any run can be
undone product by product, without stopping the site and without a whole-database restore:

    python scripts/recheck_products.py --rollback backups/recheck-journal-20261120-031500.jsonl          (lists what it would restore)
    python scripts/recheck_products.py --rollback backups/recheck-journal-20261120-031500.jsonl --apply  (restores)

Only one run at a time (backups/recheck.lock).
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from collections import Counter
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent.parent
BACKUPS = Path(os.environ.get("RECHECK_BACKUPS") or HERE / "backups")  # RECHECK_BACKUPS: another folder (tests)


def _original_app() -> Path:
    """Where the original app is: DEFAKETIVE_ORIGINAL, else its own folder beside this project (the developer's PC,
    with the real database), else backend/, the copy this repo carries so it runs on another PC."""
    named = os.environ.get("DEFAKETIVE_ORIGINAL")
    if named:
        return Path(named)
    beside = HERE.parent / "Capstone-Version-Control-Version-1.1"
    return beside if (beside / "webapp.py").is_file() else HERE / "backend"


ORIGINAL = _original_app()
if not (ORIGINAL / "webapp.py").exists():
    sys.exit(f"The original DeFaketive app was not found at {ORIGINAL}. Set DEFAKETIVE_ORIGINAL to its folder.")

# The original resolves its own folders from where its files are, but work from its folder to be safe.
sys.path.insert(0, str(ORIGINAL))
os.chdir(ORIGINAL)

from dashboard_utils import (  # noqa: E402
    analysis_is_current,
    analyze_products,
    badge_view,
    is_badge_summary,
    model_unavailable_error,
    platform_name,
)
from data_store import DEFAULT_DB, save_products  # noqa: E402

# The original app's own note: the transformer takes about 13 seconds for 100 reviews.
SECONDS_PER_REVIEW = 0.13


def read_only(path: Path) -> sqlite3.Connection:
    """Open the database so that nothing can be written through this connection."""
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def saved_rows(path: Path) -> list[dict[str, Any]]:
    """Every saved product with the "source" it was saved under. Read only."""
    with closing(read_only(path)) as connection:
        rows = connection.execute("SELECT link, source, raw_json FROM products ORDER BY updated_at DESC").fetchall()
    products = []
    for link, source, payload in rows:
        try:
            product = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(product, dict):
            products.append({"link": link, "source": source or "", "product": product})
    return products


def saved_index(path: Path, with_verdict: bool = False) -> list[dict[str, Any]]:
    """One light record per saved product (link, source, name, platform, review count, why it is behind). The rows are read one at a
    time, so memory stays at the size of one product: the production database is 415 MB, far too much to hold parsed on a 3.8 GB
    server that is also serving the site."""
    records: list[dict[str, Any]] = []
    with closing(read_only(path)) as connection:
        for link, source, payload in connection.execute("SELECT link, source, raw_json FROM products ORDER BY updated_at DESC"):
            try:
                product = json.loads(payload)
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(product, dict):
                continue
            record = {
                "link": link, "source": source or "", "name": product.get("name"), "platform": platform_name(product),
                "reviews": review_total(product), "reason": recheck_reason(product),
            }
            if with_verdict:
                record["state"] = badge_view(product)["state"]
            records.append(record)
    return records


def load_row(path: Path, link: str, source: str) -> dict[str, Any]:
    """One saved product, read when its turn comes."""
    with closing(read_only(path)) as connection:
        row = connection.execute("SELECT raw_json FROM products WHERE link = ?", (link,)).fetchone()
    return {"link": link, "source": source, "product": json.loads(row[0])}


def counts(path: Path) -> dict[str, int]:
    with closing(read_only(path)) as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("products", "reviews")
        }


def recheck_reason(product: dict[str, Any]) -> str | None:
    """Why a saved report is behind the checker the app runs, or None when it is current.

    Two ways to be behind. The app shows "Not analyzed yet" when the saved result is not a badge summary at
    all. And a report can be in today's format but made by an earlier version of the checker: the app shows
    it as it was stored, so a fix to the checker does not reach it until it is re-checked. "Current" is
    decided by the original app's own test, so this script cannot disagree with the app.
    """
    if not is_badge_summary(product.get("sentiment_summary") or {}):
        return "older report format"
    if not analysis_is_current([product]):
        return "older checker version"
    return None


def needs_recheck(product: dict[str, Any]) -> bool:
    return recheck_reason(product) is not None


def review_total(product: dict[str, Any]) -> int:
    return len([item for item in product.get("comments") or [] if isinstance(item, dict)])


def short(text: Any, width: int = 58) -> str:
    text = " ".join(str(text or "Unnamed product").split())
    return text if len(text) <= width else text[: width - 1] + "…"


def verdict_counts(rows: list[dict[str, Any]]) -> Counter:
    return Counter(badge_view(row["product"])["state"] for row in rows)


def show_counts(title: str, tally: Counter) -> None:
    print(title)
    for state, number in sorted(tally.items(), key=lambda item: (-item[1], item[0])):
        print(f"  {number:>3}  {state}")


def back_up(source: Path, reason: str = "recheck") -> Path:
    """Copy the database with SQLite's own backup, then prove the copy is whole before anything else happens."""
    folder = BACKUPS
    folder.mkdir(exist_ok=True)
    target = folder / f"defaketive-before-{reason}-{datetime.now():%Y%m%d-%H%M%S}.db"
    with closing(read_only(source)) as original, closing(sqlite3.connect(target)) as copy:
        original.backup(copy)
    with closing(read_only(target)) as copy:
        healthy = copy.execute("PRAGMA integrity_check").fetchone()[0]
    if healthy != "ok" or counts(target) != counts(source):
        target.unlink(missing_ok=True)
        sys.exit("The backup did not match the database, so nothing was changed.")
    return target


LOCK = BACKUPS / "recheck.lock"


def take_lock() -> None:
    """Refuse to run twice at once. A lock left by a process that is gone is removed."""
    LOCK.parent.mkdir(exist_ok=True)
    for _ in range(2):
        try:
            descriptor = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, str(os.getpid()).encode())
            os.close(descriptor)
            return
        except FileExistsError:
            other = 0
            try:
                other = int(LOCK.read_text().strip() or 0)
                os.kill(other, 0)
            except PermissionError:
                pass  # the process exists (it belongs to someone else)
            except (ValueError, OSError):
                LOCK.unlink(missing_ok=True)
                continue
            sys.exit(f"Another re-check is running (process {other}). Nothing was changed.")
    sys.exit("Could not take the re-check lock. Nothing was changed.")


def release_lock() -> None:
    LOCK.unlink(missing_ok=True)


def machine_load() -> float | None:
    try:
        return os.getloadavg()[0]
    except (AttributeError, OSError):
        return None


def wait_for_load(limit: float | None, give_up_after: float = 600.0) -> bool:
    """Wait (up to give_up_after seconds) until the 1-minute load is at most `limit`. False means it never was."""
    if limit is None or machine_load() is None:
        return True
    waited = 0.0
    while machine_load() > limit:
        if waited >= give_up_after:
            return False
        time.sleep(15)
        waited += 15
    return True


def recent_backup(database: Path, hours: float = 12.0) -> Path | None:
    """A verified backup of this database made by this script in the last few hours, if any."""
    folder = BACKUPS
    newest = sorted(folder.glob("defaketive-before-*.db"), key=lambda item: item.stat().st_mtime, reverse=True) if folder.exists() else []
    if newest and time.time() - newest[0].stat().st_mtime < hours * 3600:
        return newest[0]
    return None


def journal_append(handle, row: dict[str, Any]) -> None:
    handle.write(json.dumps({"link": row["link"], "source": row["source"], "product": row["product"]}, ensure_ascii=False) + "\n")
    handle.flush()
    os.fsync(handle.fileno())


DATABASE = Path(os.environ.get("RECHECK_DB") or DEFAULT_DB)


def rollback(journal: Path, apply: bool) -> int:
    """Put back, product by product, the reports a run replaced. Newest replacement first; a product the current checker has
    not touched since is still the old one and is left alone."""
    if not journal.is_file():
        sys.exit(f"No journal at {journal}.")
    entries = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"{len(entries)} products were replaced by that run.")
    if not apply:
        for entry in entries[-10:]:
            print("  would restore:", short(entry["product"].get("name"), 60))
        print("\nNothing was written. Add --apply to restore them (the site may keep running).")
        return 0
    take_lock()
    try:
        restored = 0
        for entry in reversed(entries):
            save_products([entry["product"]], source=entry["source"], path=DATABASE)
            restored += 1
        print(f"{restored} products restored to the reports stored before the run.")
    finally:
        release_lock()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="back up the database, then re-check and save")
    parser.add_argument(
        "--behind", action="store_true",
        help="only say how many saved reports could be re-checked; exit code 3 when there are any (used by start.cmd)",
    )
    parser.add_argument("--max-products", type=int, default=0, help="stop after this many products (0 = no limit)")
    parser.add_argument("--max-reviews", type=int, default=0, help="stop before a product that would pass this many reviews in total (0 = no limit)")
    parser.add_argument("--max-minutes", type=float, default=0, help="stop starting new products after this many minutes (0 = no limit)")
    parser.add_argument("--duty", type=int, default=100, help="percent of the time to work (50 = sleep as long as each product took)")
    parser.add_argument("--max-load", type=float, default=None, help="wait while the 1-minute load average is above this")
    parser.add_argument("--order", choices=("recent", "small"), default="recent")
    parser.add_argument("--verdicts", action="store_true", help="also count the verdicts before and after (reads every report once more: slower)")
    parser.add_argument("--list", type=int, default=20, help="how many products to list before re-checking (0 = all)")
    parser.add_argument("--rollback", metavar="JOURNAL", help="restore the reports a previous run replaced")
    arguments = parser.parse_args()
    if not 1 <= arguments.duty <= 100:
        sys.exit("--duty must be between 1 and 100.")
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    database = Path(os.environ.get("RECHECK_DB") or DEFAULT_DB)  # RECHECK_DB: another database file (tests, a restored copy)
    if not database.exists():
        sys.exit(f"No database at {database}.")
    if arguments.rollback:
        return rollback(Path(arguments.rollback), arguments.apply)
    rows = saved_index(database, with_verdict=arguments.verdicts)
    old = [row for row in rows if row["reason"]]
    if arguments.behind:
        behind = sum(1 for row in old if row["reviews"] > 0)
        if behind:
            print(
                f"\nNote: {behind} saved report{'' if behind == 1 else 's'} {'was' if behind == 1 else 'were'} made with an "
                "earlier version of the checker.\n"
                "They are still shown, marked as such. To bring them up to date, close DeFaketive and run:\n"
                "  ..\\Capstone-Version-Control-Version-1.1\\.venv\\Scripts\\python.exe scripts\\recheck_products.py --apply\n"
            )
        return 3 if behind else 0
    # A product with no stored reviews has nothing to re-read, so it is left exactly as it is.
    chosen = [row for row in old if row["reviews"] > 0]
    if arguments.order == "small":
        chosen.sort(key=lambda row: row["reviews"])
    empty = [row for row in old if row["reviews"] == 0]
    reviews = sum(row["reviews"] for row in chosen)

    print(f"Database: {database}")
    print(f"{len(rows)} saved products, {len(old)} of them from an older checker ({reviews} stored reviews).")
    if arguments.verdicts:
        show_counts("\nVerdicts now:", Counter(row["state"] for row in rows))
    if empty:
        print("\nLeft alone, because no reviews are stored for them:")
        for row in empty:
            print(f"        {row['platform']:<10}  {short(row['name'])}")
    if not chosen:
        print("\nNothing to re-check.")
        return 0

    print("\nTo re-check:")
    for row in chosen[: arguments.list if arguments.list else len(chosen)]:
        print(f"  {row['reviews']:>4} reviews  {row['platform']:<10}  {short(row['name'], 44):<44}  {row['reason']}")
    if arguments.list and len(chosen) > arguments.list:
        print(f"  ... and {len(chosen) - arguments.list} more")
    print(f"\nRough time: {max(1, round(reviews * SECONDS_PER_REVIEW / 60))} minute(s), plus loading the model.")

    if not arguments.apply:
        print("\nDry run: nothing was written. Add --apply to back up the database and re-check these products.")
        return 0

    backup = recent_backup(database)
    if backup is None:
        backup = back_up(database)
        print(f"\nBackup written and checked: {backup}")
    else:
        print(f"\nUsing the verified backup made in the last 12 hours: {backup}")

    unavailable = model_unavailable_error()
    take_lock()
    journal_path = BACKUPS / f"recheck-journal-{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    started = time.monotonic()
    done = done_reviews = 0
    stopped = "all selected products were re-checked"
    try:
        with open(journal_path, "a", encoding="utf-8") as journal:
            for number, light in enumerate(chosen, start=1):
                size = light["reviews"]
                if arguments.max_products and done >= arguments.max_products:
                    stopped = f"reached --max-products {arguments.max_products}"
                    break
                if arguments.max_reviews and done and done_reviews + size > arguments.max_reviews:
                    stopped = f"the next product would pass --max-reviews {arguments.max_reviews}"
                    break
                if arguments.max_minutes and (time.monotonic() - started) / 60 >= arguments.max_minutes:
                    stopped = f"reached --max-minutes {arguments.max_minutes:g}"
                    break
                if not wait_for_load(arguments.max_load):
                    stopped = f"the machine stayed busier than --max-load {arguments.max_load} for 10 minutes"
                    break
                print(f"  [{number}/{len(chosen)}] {short(light['name'], 50)} ({size} reviews) ...", end=" ", flush=True)
                row = load_row(database, light["link"], light["source"])
                product = row["product"]
                began = time.monotonic()
                try:
                    result = analyze_products([product])[0]
                except unavailable as error:
                    # Everything saved so far is complete; the rest is untouched.
                    sys.exit(f"\nThe review model could not be loaded. {done} products were saved before this; the rest are unchanged.\n{error}")
                if needs_recheck(result):
                    print("no verdict from the current checker; left as it was")
                    continue
                journal_append(journal, row)  # the old report is on disk before it is replaced
                save_products([result], source=row["source"], path=database)
                done += 1
                done_reviews += size
                spent = time.monotonic() - began
                print(f"{badge_view(result)['headline']} ({spent:.1f}s)")
                if arguments.duty < 100:
                    time.sleep(spent * (100 - arguments.duty) / arguments.duty)
    finally:
        release_lock()
        if journal_path.exists() and journal_path.stat().st_size == 0:
            journal_path.unlink()
    print(f"\nStopped because {stopped}. {done} products ({done_reviews} reviews) re-checked in {time.monotonic() - started:.0f} seconds.")

    after = saved_index(database, with_verdict=arguments.verdicts)
    left = [row for row in after if row["reason"]]
    if arguments.verdicts:
        show_counts("\nVerdicts after:", Counter(row["state"] for row in after))
    print(f"\n{len(left)} saved products are still from an older checker (run again to continue).")
    print(f"Row counts: {counts(database)} (before: {counts(backup)}).")
    if done:
        print(f"To undo this run, product by product: python scripts/recheck_products.py --rollback {journal_path} --apply")
        print(f"To undo everything: close both apps, then copy\n  {backup}\nover\n  {database}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
