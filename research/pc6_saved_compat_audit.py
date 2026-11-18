#!/usr/bin/env python3
"""Read-only saved-report compatibility summary for the pc4-to-pc6 release.

Run only in isolated staging using the actual VM's saved DB as a read-only
source. Prints aggregate counts, never review/customer content and never
changes saved analyses. This is NOT model inference or a category accuracy
evaluation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkout", type=Path, required=True)
    ap.add_argument("--database", type=Path, required=True)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    root = args.checkout.resolve(strict=True)
    db = args.database.resolve(strict=True)
    sys.path.insert(0, str(root / "backend"))
    sys.path.insert(0, str(root / "backend/sentiment-analysis"))
    import dashboard_utils  # noqa: E402
    from defaketive_sentiment.product_category import classify_listing  # noqa: E402

    active = dashboard_utils.sentiment_model_version()
    if "+pc6+" not in active:
        raise RuntimeError(f"Unexpected checker version: pc6 is not active")
    previous = active.replace("+pc6+", "+pc4+", 1)

    with sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True) as con:
        records = con.execute("SELECT raw_json FROM products").fetchall()
    summary = Counter()
    for (raw,) in records:
        try:
            product = json.loads(raw)
        except (ValueError, TypeError):
            summary["malformed_rows"] += 1
            continue
        if not isinstance(product, dict):
            summary["malformed_rows"] += 1
            continue
        summary["reports"] += 1
        category = product.get("product_category")
        new_category = classify_listing({"name": str(product.get("name") or "")})
        versions = [
            (review.get("sentiment_analysis") or {}).get("model_version")
            for review in product.get("comments") or []
            if isinstance(review, dict) and review.get("included_in_analysis") is not False
        ]
        was_previous = bool(versions) and all(v == previous for v in versions)
        current = dashboard_utils.analysis_is_current([product])
        if was_previous:
            summary["pc4_exact_reports"] += 1
        if current:
            summary["reports_current_under_pc6"] += 1
        else:
            summary["reports_stale_under_pc6"] += 1
        if category is None or not isinstance(category, str) or not category.strip():
            summary["missing_saved_category"] += 1
        elif category != new_category:
            summary["changed_category"] += 1
        if was_previous and not current:
            if not category:
                summary["pc4_stale_missing_category"] += 1
            elif category != new_category:
                summary["pc4_stale_changed_category"] += 1
            else:
                summary["pc4_stale_unexplained"] += 1
        if was_previous and current and category != new_category:
            summary["unsafe_legacy_marked_current"] += 1

    print(json.dumps(dict(sorted(summary.items())), sort_keys=True, indent=2))
    if args.strict and (summary["unsafe_legacy_marked_current"] or summary["pc4_stale_unexplained"]):
        raise RuntimeError("Unexpected saved-report compatibility result: NO-GO")
    if args.strict and summary["pc4_exact_reports"] and not summary["reports_current_under_pc6"]:
        raise RuntimeError("Every pc4 report became stale: NO-GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
