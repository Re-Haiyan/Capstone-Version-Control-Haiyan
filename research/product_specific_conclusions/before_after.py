"""Old generic conclusion vs new product-specific conclusion, on the same saved products.

    python research/product_specific_conclusions/before_after.py [--before-rev deployment]

The OLD text is produced by the real old code (dashboard_utils.py as committed on --before-rev), not rewritten by hand.
Writes before_after.csv and before_after_summary.json next to this file. Everything in the summary is AUTOMATIC
and checkable (counts, wording checks, traceability); none of it is a human judgement of quality, and none of it is
an F1 score of the sentiment model or the hazard checker. Human judgement needs human_evaluation.md.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import statistics
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))

import dashboard_utils as new  # noqa: E402


def load_old(rev: str) -> types.ModuleType:
    source = subprocess.check_output(["git", "show", f"{rev}:backend/dashboard_utils.py"], cwd=ROOT)
    module = types.ModuleType("dashboard_utils_before")
    module.__file__ = str(ROOT / "backend" / "dashboard_utils.py")
    exec(compile(source, f"{rev}:dashboard_utils.py", "exec"), module.__dict__)
    return module


def words(text: str) -> int:
    return len(text.split())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-rev", default="deployment")
    args = parser.parse_args()
    old = load_old(args.before_rev)
    seed = ROOT / "backend" / "seed" / "saved_products.json.gz"
    products = [item["product"] for item in json.load(gzip.open(seed, "rt", encoding="utf-8"))]
    rows = []
    stats = {"products": 0, "with_text": 0, "old_wrong_majority_claims": 0, "new_wrong_majority_claims": 0}
    old_words, new_words, named, quotes_ok, quotes_total = [], [], [], 0, 0
    decisions_equal = 0
    for product in products:
        before = old.badge_view(product)["conclusion"]
        after_view = new.badge_view(product, aspects=True)
        after = after_view["conclusion"]
        if not before or not after:
            continue
        stats["products"] += 1
        shares = new._sentiment_shares(product["sentiment_summary"])
        negative = (shares or {}).get("negative", 0.0)
        old_text = f"{before['lead']} {before['summary']}"
        new_text = f"{after['lead']} {after['summary']}"
        # The wording bug: "mostly negative" said when negative reviews are not a majority.
        if "mostly negative" in before["summary"] and negative <= 0.5:
            stats["old_wrong_majority_claims"] += 1
        if "mostly negative" in after["summary"] and negative <= 0.5:
            stats["new_wrong_majority_claims"] += 1
        evidence = after.get("evidence")
        decisions_equal += before["decision"] == after["decision"]
        if evidence:
            stats["with_text"] += 1
            why = evidence["why"]
            product_reasons = [w for w in why if w["kind"] == "product"]
            named.append(len(product_reasons))
            # A review's evidence id is its comment_id, or "review-<position in the saved list>" when it has none.
            by_id = {f"review-{i}": c for i, c in enumerate(product["comments"])} | {str(c["comment_id"]): c for c in product["comments"] if c.get("comment_id")}
            for item in why:
                for quote in item["quotes"]:
                    quotes_total += 1
                    raw_text = str(by_id.get(quote["review_id"], {}).get("content", ""))
                    raw = " ".join(raw_text.split())
                    text = quote["text"]
                    found = text in raw or (text.endswith("…") and text[:-1].rstrip() in raw)
                    if quote["span"]:
                        sliced = " ".join(raw_text[quote["span"][0] : quote["span"][1]].split())
                        found = found and (sliced == text or (text.endswith("…") and sliced.startswith(text[:-1].rstrip())))
                    quotes_ok += found
        old_words.append(words(old_text))
        new_words.append(words(new_text))
        rows.append(
            {
                "link": product["link"],
                "name": product["name"][:90],
                "category": new.product_category_of(product),
                "decision": after["decision"],
                "evidence_status": after.get("evidence_status", "none"),
                "product_reasons_named": len([w for w in (evidence or {}).get("why", []) if w["kind"] == "product"]),
                "old_words": words(old_text),
                "new_words": words(new_text),
                "old_lead": before["lead"],
                "old_summary": before["summary"],
                "new_lead": after["lead"],
                "new_summary": after["summary"],
            }
        )
    with open(HERE / "before_after.csv", "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    status = {}
    for row in rows:
        status[row["evidence_status"]] = status.get(row["evidence_status"], 0) + 1
    summary = {
        "before_rev": args.before_rev,
        "products_compared": stats["products"],
        "decisions_unchanged": f"{decisions_equal} of {stats['products']}",
        "evidence_status": status,
        "products_naming_at_least_one_product_reason": sum(1 for n in named if n),
        "median_product_reasons_per_product": statistics.median(named) if named else 0,
        "words_old_median": statistics.median(old_words),
        "words_new_median": statistics.median(new_words),
        "words_new_max": max(new_words),
        "new_texts_over_100_words": sum(1 for n in new_words if n > 100),
        "wording_bug": {
            "old_said_mostly_negative_without_a_negative_majority": stats["old_wrong_majority_claims"],
            "new_said_mostly_negative_without_a_negative_majority": stats["new_wrong_majority_claims"],
        },
        "quotations_checked": quotes_total,
        "quotations_found_verbatim_in_their_review": quotes_ok,
    }
    (HERE / "before_after_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
