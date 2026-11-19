#!/usr/bin/env python3
"""Read-only category revision compatibility preflight on the VM's saved product database.

Never rewrites saved reports. Counts potential category changes, exact legacy
version matches, current vs stale, and unsafe compatibility. Suppresses titles,
review text, customer identifiers, and product links in output.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout",type=Path,required=True)
    parser.add_argument("--database",type=Path,required=True)
    parser.add_argument("--expected-revision", choices=("pc7", "pc8"), default="pc7")
    parser.add_argument("--strict",action="store_true")
    args=parser.parse_args()
    root=args.checkout.resolve(strict=True)
    db=args.database.resolve(strict=True)
    sys.path[:0]=[str(root/"backend"),str(root/"backend/sentiment-analysis")]
    import dashboard_utils  # noqa: E402
    from defaketive_sentiment.product_category import classify_listing  # noqa: E402

    current=dashboard_utils.sentiment_model_version()
    revision = args.expected_revision
    stamp = f"+{revision}+"
    if stamp not in current:
        raise RuntimeError(f"{revision} model-version stamp is missing; stop")
    legacy_revisions = ("pc7", "pc6", "pc4") if revision == "pc8" else ("pc6", "pc4")
    previous_versions = [current.replace(stamp, f"+{old}+", 1) for old in legacy_revisions]
    summary=Counter()
    con=sqlite3.connect(f"file:{db.as_posix()}?mode=ro",uri=True)
    try:
        rows=con.execute("SELECT raw_json FROM products").fetchall()
    finally:
        con.close()

    for (raw,) in rows:
        try:
            product=json.loads(raw)
        except (TypeError,ValueError):
            summary["malformed_rows"]+=1
            continue
        if not isinstance(product,dict):
            summary["malformed_rows"]+=1
            continue
        summary["reports"]+=1
        saved=product.get("product_category")
        detected=classify_listing({"name":str(product.get("name") or "")})
        mismatch=not isinstance(saved,str) or saved!=detected
        if mismatch:
            summary["changed_or_missing_category"]+=1
        versions=[
            (row.get("sentiment_analysis") or {}).get("model_version")
            for row in product.get("comments") or []
            if isinstance(row,dict) and row.get("included_in_analysis") is not False
        ]
        legacy=bool(versions) and all(x==versions[0] for x in versions) and versions[0] in previous_versions
        is_current=dashboard_utils.analysis_is_current([product])
        summary["current" if is_current else "stale"]+=1
        if legacy:
            summary["legacy_reports"]+=1
            if mismatch and is_current:
                summary["unsafe_mismatch_accepted"]+=1
            if not mismatch and not is_current:
                summary["unexplained_legacy_stale"]+=1
            if mismatch and not is_current:
                summary["expected_category_stale"]+=1
    print(json.dumps(dict(sorted(summary.items())),indent=2,sort_keys=True))
    if args.strict and (
        summary["malformed_rows"] or
        summary["unsafe_mismatch_accepted"] or
        summary["unexplained_legacy_stale"]
    ):
        raise RuntimeError(f"{revision} saved-report compatibility: NO-GO")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
