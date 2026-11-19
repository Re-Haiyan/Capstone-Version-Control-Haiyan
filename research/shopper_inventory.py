"""Read-only inventory of the actual saved catalog and scraper outputs."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/sentiment-analysis"))
from defaketive_sentiment.product_category import classify_listing


def inventory(database: Path, results: list[Path], scraper_root: Path | None = None) -> dict:
    categories, aliases, platforms = Counter(), defaultdict(Counter), Counter()
    counts, sources, errors = Counter(), {}, []

    def consume(products, source):
        if isinstance(products, dict):
            products = products.get("products", [])
        if not isinstance(products, list):
            return
        sources[source] = len(products)
        for product in products:
            if not isinstance(product, dict):
                continue
            canonical = classify_listing(product)
            categories[canonical] += 1
            for field in ("category", "product_category", "product_type"):
                value = str(product.get(field) or "").strip()
                if value:
                    aliases[value][canonical] += 1
            platforms[str(product.get("platform") or "unspecified")] += 1
            reviews = product.get("comments") or []
            counts["products"] += 1
            counts["reviews"] += len(reviews)
            counts["zero_review_products"] += not reviews
            counts["few_review_products"] += 0 < len(reviews) < 5

    if database.is_file():
        with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
            consume([json.loads(r[0]) for r in connection.execute("SELECT raw_json FROM products")], "sqlite")
    if scraper_root:
        results = [*results, *sorted(scraper_root.glob("*_ph_*.json"))]
    for path in results:
        files = sorted(path.rglob("*.json")) if path.is_dir() else [path]
        for file in files:
            try:
                opener = gzip.open if file.suffix == ".gz" else open
                with opener(file, "rt", encoding="utf-8") as stream:
                    consume(json.load(stream), str(file.relative_to(ROOT)) if file.is_relative_to(ROOT) else str(file))
            except (OSError, ValueError) as exc:
                errors.append({"file": str(file), "error": str(exc)})
    return {"counts": dict(counts), "categories": dict(sorted(categories.items())),
            "aliases": {k: dict(v) for k, v in sorted(aliases.items())},
            "platforms": dict(platforms), "sources": sources, "errors": errors}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--results", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path)
    parser.add_argument("--scraper-root", type=Path)
    args = parser.parse_args()
    report = inventory(args.database, args.results, args.scraper_root)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
