#!/usr/bin/env python3
"""Prepare genuinely new, independently labelled multicategory review sheets.

The script NEVER labels reviews, runs the model, or writes to production. It
accepts a rights-cleared, human category-verified CSV of new products and
refuses product/text overlaps against historical repository evaluation files.
No row data is printed; blank sheets and a private manifest stay local.

Command:
 python research/fresh_multicategory_intake.py prepare --input new_reviews.csv \
    --out-dir research/independent_eval_private/pilot1 \
    --known-extra /path/to/production_saved_titles.csv

This is a group-balanced PILOT, not a representative marketplace sample.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import random
import re
import sqlite3
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "marketplace", "product_id", "product", "category", "review_id",
    "review_text", "stars", "collected_at", "rights_confirmed",
    "new_product_verified", "category_verified", "selection_method",
)
LABELS = ("sentiment", "flags", "confidence")
PUBLIC_COLS = ("id", "stars", "product", "review_text", *LABELS)
PRIVATE_COLS = (
    "id", "product_hash", "review_sha256", "category", "group",
    "marketplace", "collected_at", "title_classifier_category",
    "title_classifier_agrees", "collection_method",
)


def normal(value: object) -> str:
    return " ".join(re.findall(r"[^\W_]+", str(value or "").casefold(), re.UNICODE))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def cleared(value: object) -> bool:
    return str(value or "").strip().casefold() in {"yes", "true", "1"}


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("No CSV header in " + path.name)
        return [dict(row) for row in reader]


def history(root: Path, extra: Path | None) -> tuple[set[str], set[str], int]:
    """Inspect every historical evaluation CSV plus earlier proposed review sets.

    Existing data may include variants under different names; exact normalized
    overlap checks alone do not prove product disjointness. The collector must
    independently check seller/listing variants and production saved products.
    """
    evaluation = root / "evaluation"
    if not evaluation.is_dir():
        raise ValueError("Missing historical evaluation folder; cannot verify disjointness")
    files = sorted(evaluation.rglob("*.csv"))
    files.extend(
        p for p in (
            root / "research/fresh_eval/fresh_eval_sheet.csv",
            root / "research/agreement/sheet_A.csv",
        )
        if p.is_file()
    )
    if extra is not None and not extra.is_file():
        raise ValueError("Known-product export or SQLite database is missing")
    titles: set[str] = set()
    texts: set[str] = set()
    sources = 0
    for file in files:
        rows = csv_rows(file)
        if not rows:
            continue
        sources += 1
        for row in rows:
            title = next((
                row[k] for k in ("product", "product_title", "name", "title")
                if str(row.get(k) or "").strip()
            ), "")
            if title:
                titles.add(normal(title))
            content = next((
                row[k] for k in ("review_text", "review", "content", "text")
                if str(row.get(k) or "").strip()
            ), "")
            if content and len(normal(content)) >= 12:
                texts.add(digest(normal(content)))
    if extra is not None:
        if extra.suffix.casefold() in {".db", ".sqlite", ".sqlite3"}:
            # SQLite read-only mode: do not write, vacuum, migrate or alter VM state.
            uri = f"file:{extra.resolve().as_posix()}?mode=ro"
            with sqlite3.connect(uri, uri=True) as db:
                saved = db.execute("SELECT raw_json FROM products").fetchall()
            if not saved:
                raise ValueError("Saved-product database was empty; disjointness unknown")
            for (raw,) in saved:
                try:
                    product = json.loads(raw)
                except (TypeError, ValueError) as e:
                    raise ValueError("Malformed saved product: cannot prove disjointness") from e
                if not isinstance(product, dict) or not str(product.get("name") or "").strip():
                    raise ValueError("A saved product is missing its name")
                titles.add(normal(product["name"]))
            sources += 1
        else:
            rows = csv_rows(extra)
            if not rows:
                raise ValueError("Known-product CSV is empty; disjointness unknown")
            for row in rows:
                title = next((
                    row[k] for k in ("product", "product_title", "name", "title")
                    if str(row.get(k) or "").strip()
                ), "")
                if not title:
                    raise ValueError("Known-product CSV lacks a product title")
                titles.add(normal(title))
            sources += 1
    if not files or not titles:
        raise ValueError("Historical CSVs did not supply product titles; cannot verify")
    return titles, texts, sources


def _groups():
    sys.path.insert(0, str(ROOT / "backend/sentiment-analysis"))
    from defaketive_sentiment.product_category import (
        CATEGORIES, OTHER, classify_listing, group_of
    )
    return set(CATEGORIES) - {OTHER}, classify_listing, group_of


def ingest(
    source: Path,
    *,
    root: Path = ROOT,
    extra: Path | None = None,
) -> tuple[list[dict[str, str]], Counter, dict[str, Any]]:
    historical_titles, historical_texts, history_files = history(root, extra)
    # Import the exact current taxonomy from the requested root, not whichever
    # package an unrelated Python environment has installed.
    sys.path.insert(0, str(root / "backend/sentiment-analysis"))
    from defaketive_sentiment.product_category import CATEGORIES, OTHER, classify_listing, group_of

    valid_categories = set(CATEGORIES) - {OTHER}
    rows = csv_rows(source)
    if not rows:
        raise ValueError("No reviews supplied. Do not fabricate a holdout.")
    if not set(REQUIRED).issubset(rows[0]):
        raise ValueError("Missing required CSV columns: " + ", ".join(sorted(set(REQUIRED)-set(rows[0]))))

    rejected = Counter()
    eligible: list[dict[str, str]] = []
    product_identity: dict[str, tuple[str, str]] = {}
    seen_review_ids: set[tuple[str, str, str]] = set()
    seen_texts: set[str] = set()
    collected_dates: list[str] = []
    for i, item in enumerate(rows, start=2):
        if any(not cleared(item.get(key)) for key in (
            "rights_confirmed", "new_product_verified", "category_verified"
        )):
            raise ValueError(f"Row {i}: rights/new-product/category verification is not YES")
        market = str(item["marketplace"] or "").strip().lower()
        if market not in {"shopee", "lazada"}:
            raise ValueError(f"Row {i}: marketplace must be shopee or lazada")
        product_id = str(item["product_id"] or "").strip()
        product = str(item["product"] or "").strip()
        category = str(item["category"] or "").strip()
        review_id = str(item["review_id"] or "").strip()
        review = str(item["review_text"] or "").strip()
        method = str(item["selection_method"] or "").strip().lower()
        if not product_id or not product or not review_id or not review:
            raise ValueError(f"Row {i}: product ID, title, review ID and review text are required")
        if category not in valid_categories:
            raise ValueError(f"Row {i}: unknown verified product category")
        if method != "random":
            raise ValueError(f"Row {i}: only preselected random reviews qualify for this pilot")
        try:
            stars = int(str(item["stars"]).strip())
            if stars not in range(1, 6):
                raise ValueError
        except (TypeError, ValueError) as e:
            raise ValueError(f"Row {i}: stars must be 1..5") from e
        stamp = str(item["collected_at"] or "").strip()
        try:
            observed = date.fromisoformat(stamp)
            if observed > date.today():
                raise ValueError
        except ValueError as e:
            raise ValueError(f"Row {i}: collected_at must be a non-future ISO date") from e
        collected_dates.append(stamp)
        product_key = market + ":" + product_id
        fixed = product_identity.setdefault(product_key, (normal(product), category))
        if fixed != (normal(product), category):
            raise ValueError(f"Row {i}: one product ID has conflicting titles/categories")
        if normal(product) in historical_titles:
            rejected["historical_product"] += 1
            continue
        if product.lstrip().startswith(("=", "+", "-", "@")) or review.lstrip().startswith(("=", "+", "-", "@")):
            # Never turn an untrusted marketplace review into an executable
            # formula in an annotator's spreadsheet. Reject, do not rewrite.
            rejected["spreadsheet_formula_risk"] += 1
            continue
        if len(normal(review)) < 12:
            rejected["very_short_review"] += 1
            continue
        if len(review) > 5000:
            rejected["very_long_review"] += 1
            continue
        key = (market, product_id, review_id)
        if key in seen_review_ids:
            rejected["duplicate_review_id"] += 1
            continue
        seen_review_ids.add(key)
        text_hash = digest(normal(review))
        if text_hash in historical_texts:
            rejected["historical_review_text"] += 1
            continue
        if text_hash in seen_texts:
            rejected["duplicate_review_text"] += 1
            continue
        seen_texts.add(text_hash)
        eligible.append({
            "product_key": product_key,
            "product_hash": digest(product_key)[:20],
            "marketplace": market,
            "product": product,
            "category": category,
            "group": group_of(category),
            "review_text": review,
            "review_sha256": digest(review),
            "stars": str(stars),
            "collected_at": stamp,
            "title_classifier_category": classify_listing({"name": product}),
            "collection_method": method,
        })

    report = {
        "input_reviews": len(rows),
        "eligible_reviews": len(eligible),
        "excluded": dict(sorted(rejected.items())),
        "history_files_checked": history_files,
        "vm_saved_titles_checked": extra is not None,
        "earliest_collection_date": min(collected_dates),
        "latest_collection_date": max(collected_dates),
    }
    if not eligible:
        raise ValueError("No eligible product-disjoint reviews remain.")
    return eligible, rejected, report


def choose(
    eligible: list[dict[str, str]], *,
    target: int,
    max_per_product: int,
    min_groups: int,
    min_products: int,
    seed: int,
) -> list[dict[str, str]]:
    if target <= 0 or max_per_product <= 0:
        raise ValueError("Sample target and per-product cap must be positive")
    rng = random.Random(seed)
    by_group: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for row in eligible:
        by_group[row["group"]][row["product_key"]].append(row)
    if len(by_group) < min_groups:
        raise ValueError(
            f"Only {len(by_group)} product groups available; need {min_groups}"
        )

    # Round robin groups AND product IDs to avoid a single large marketplace
    # listing dominating a balanced pilot. Never select by model score.
    products: dict[str, list[tuple[str, list[dict[str, str]]]]] = {}
    for group, entries in by_group.items():
        shuffled = []
        for key, reviews in sorted(entries.items()):
            rows = list(reviews)
            rng.shuffle(rows)
            shuffled.append((key, rows[:max_per_product]))
        rng.shuffle(shuffled)
        products[group] = shuffled

    groups = sorted(products)
    rng.shuffle(groups)
    result = []
    indices = {g: 0 for g in groups}
    while len(result) < target:
        progressed = False
        for group in groups:
            slots = products[group]
            if not slots:
                continue
            checked = 0
            while checked < len(slots):
                index = indices[group] % len(slots)
                key, reviews = slots[index]
                indices[group] += 1
                checked += 1
                if reviews:
                    result.append(reviews.pop())
                    progressed = True
                    break
            if len(result) == target:
                break
        if not progressed:
            break
    if len(result) != target:
        raise ValueError(f"Only {len(result)} eligible capped reviews for {target}-review target")
    if len({r["product_key"] for r in result}) < min_products:
        raise ValueError("Not enough distinct products to protect product diversity")
    return result


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("x", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def prepare(args: argparse.Namespace) -> None:
    root = Path(args.repo_root).resolve(strict=True)
    source = Path(args.input).resolve(strict=True)
    extra = Path(args.known_extra).resolve(strict=True) if args.known_extra else None
    eligible, _rejected, report = ingest(source, root=root, extra=extra)
    selected = choose(
        eligible, target=args.target, max_per_product=args.max_per_product,
        min_groups=args.min_groups, min_products=args.min_products, seed=args.seed
    )
    out = Path(args.out_dir)
    paths = [out / x for x in (
        "annotator_A.csv", "annotator_B.csv", "PRIVATE_manifest.csv", "summary.json"
    )]
    if any(path.exists() for path in paths):
        raise ValueError("Output files already exist. Refusing to overwrite human work.")
    out.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    rows = []
    private = []
    for i, item in enumerate(selected, start=1):
        key = f"H{i:04d}"
        rows.append({
            "id": key, "stars": item["stars"], "product": item["product"],
            "review_text": item["review_text"],
            "sentiment": "", "flags": "", "confidence": "",
        })
        private.append({
            "id": key, "product_hash": item["product_hash"],
            "review_sha256": item["review_sha256"],
            "category": item["category"], "group": item["group"],
            "marketplace": item["marketplace"],
            "collected_at": item["collected_at"],
            "title_classifier_category": item["title_classifier_category"],
            "title_classifier_agrees": str(
                item["title_classifier_category"] == item["category"]
            ).lower(),
            "collection_method": item["collection_method"],
        })
    a = list(rows)
    b = list(rows)
    random.Random(args.seed + 100).shuffle(a)
    random.Random(args.seed + 200).shuffle(b)
    write_csv(paths[0], PUBLIC_COLS, a)
    write_csv(paths[1], PUBLIC_COLS, b)
    write_csv(paths[2], PRIVATE_COLS, private)
    summary = {
        **report,
        "status": "UNLABELLED_BLIND_PILOT_NOT_GOLD",
        "goal": "human-adjudicated product-disjoint multicategory sentiment+hazard evaluation",
        "frozen_production_sha": args.model_sha,
        "policy_version": args.policy,
        "seed": args.seed,
        "sampled_reviews": len(rows),
        "sampled_products": len({r["product_key"] for r in selected}),
        "sampled_categories": len({r["category"] for r in selected}),
        "sampled_groups": len({r["group"] for r in selected}),
        "group_counts": dict(sorted(Counter(r["group"] for r in selected).items())),
        "category_counts": dict(sorted(Counter(r["category"] for r in selected).items())),
        "title_category_disagreements": sum(
            r["category"] != r["title_classifier_category"] for r in selected
        ),
        "annotation_sheets_sha256": {
            paths[0].name: hashlib.sha256(paths[0].read_bytes()).hexdigest(),
            paths[1].name: hashlib.sha256(paths[1].read_bytes()).hexdigest(),
        },
        "labels_present": False,
        "accuracy_measured": False,
        "independent_holdout_complete": False,
        "limitation": "Source rights, random collection and new-product identity require human verification. Group-balanced pilot is not marketplace-prevalence-weighted. No score before independent human adjudication.",
    }
    paths[3].write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        k: summary[k] for k in (
            "status", "sampled_reviews", "sampled_products",
            "sampled_categories", "sampled_groups",
            "title_category_disagreements", "vm_saved_titles_checked"
        )
    }, sort_keys=True))
    print("Blank sheets, manifest and summary written locally; do NOT commit raw reviews.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare",))
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", default="research/independent_eval_private/pilot1")
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--known-extra", default=None,
                        help="Existing VM saved products SQLite DB (mode=ro), or CSV of their titles; keep local")
    parser.add_argument("--target", type=int, default=220)
    parser.add_argument("--max-per-product", type=int, default=5)
    parser.add_argument("--min-groups", type=int, default=8)
    parser.add_argument("--min-products", type=int, default=44)
    parser.add_argument("--seed", type=int, default=20261118)
    parser.add_argument("--model-sha", default="147eccbfcf206b37550ce9e8b0a71bba626dacc3")
    parser.add_argument("--policy", default="v1",
                        help="Use frozen agreed policy; default v1 until v2 approved")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.model_sha):
        parser.error("--model-sha must be an exact 40-character commit SHA")
    prepare(args)


if __name__ == "__main__":
    main()
