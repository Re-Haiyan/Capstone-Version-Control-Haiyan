#!/usr/bin/env python3
"""Historical real-review context audit, not an independent accuracy study.

The bundled development and previously inspected marketplace reviews contain
real user language, but their original labels lack verified human provenance.
This script deliberately ignores those labels and reports ONLY aggregate
coverage and disagreement with the shipped XLM-RoBERTa model. It never writes
reviews, product names, reviewer IDs, or model outputs to a persistent dataset.
It does not edit the VM and cannot justify automatic sentiment overrides.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=800)
    parser.add_argument("--database", type=Path, default=None,
                        help="Optional VM review SQLite DB (read-only)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.limit < 100 or args.limit > 5000:
        raise ValueError("Limit must be between 100 and 5000.")
    root = args.checkout.resolve(strict=True)
    os.environ["DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW"] = ""
    os.environ["DEFAKETIVE_SENTIMENT_CALIBRATOR"] = ""
    os.environ["DEFAKETIVE_CATEGORY_SENTIMENT_ADAPTER"] = ""
    os.environ["DEFAKETIVE_MODEL_MODE"] = "hazard_badges"
    os.environ["DEFAKETIVE_SENTIMENT_MODEL"] = "xlmr"
    os.environ["DEFAKETIVE_HAZARD_MODEL"] = "learned"
    sys.path[:0] = [
        str(root), str(root / "research"),
        str(root / "backend"), str(root / "backend" / "sentiment-analysis")
    ]
    from panel_category_release_audit import load_products, prepare_rows  # noqa: E402
    from defaketive_sentiment import category_context, product_category, registry  # noqa: E402

    products = load_products(root, args.database)
    sample = prepare_rows(products, args.limit)
    if len(sample) < 100:
        raise RuntimeError("Insufficient eligible real reviews for a meaningful diagnostic.")
    model = registry.load_model()
    statuses = Counter()
    by_group = defaultdict(Counter)
    by_category = defaultdict(Counter)
    checked = 0
    candidate_disagrees = 0
    invalid = 0
    unique_titles = set()

    for _key, title, text, rating in sample:
        output = model.analyze(text, rating, listing={"name": title})
        ctx = (output.get("sentiment") or {}).get("category_context")
        category = product_category.classify_listing({"name": title})
        if not isinstance(ctx, dict) or ctx.get("revision") != "category-context-v2":
            invalid += 1
            continue
        if (
            ctx.get("used_for_decision") is not False
            or ctx.get("sentiment_overridden") is not False
            or ctx.get("product_category") != category
            or ctx.get("initial_label") != output.get("label")
        ):
            invalid += 1
            continue

        group = product_category.group_of(category)
        status = str(ctx.get("status") or "")
        if status not in {
            "agrees", "differs", "expected_behavior", "ambiguous",
            "no_signal", "unclassified", "unavailable"
        }:
            invalid += 1
            continue
        checked += 1
        statuses[status] += 1
        by_group[group][status] += 1
        by_category[category][status] += 1
        candidate_disagrees += int(status == "differs")
        unique_titles.add(title)
    report = {
        "schema": "context-v2-marketplace-diagnostic-1",
        "dataset": "VM SQLite read-only sample" if args.database else
                   "bundled historical development/reused evaluation reviews",
        "independent_accuracy_measured": False,
        "human_gold_labels_available": False,
        "sentiment_predictions_changed_by_this_stage": 0,
        "reviews_sampled": len(sample),
        "reviews_checked": checked,
        "products_checked": len(unique_titles),
        "categories_represented": len(by_category),
        "groups_represented": len(by_group),
        "invalid_pipeline_metadata": invalid,
        "context_disagreement_with_initial_xlmr": candidate_disagrees,
        "status_counts": dict(sorted(statuses.items())),
        "by_group": {group: dict(sorted(c.items())) for group, c in sorted(by_group.items())},
        "by_category": {category: dict(sorted(c.items())) for category, c in sorted(by_category.items())},
        "limitations": "Historical/non-independent language sample; disagreement is not error; no F1/accuracy claim.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    # Only aggregate counts on stdout; never echo product names or review text.
    print(json.dumps({k: report[k] for k in (
        "dataset", "reviews_sampled", "reviews_checked", "products_checked",
        "categories_represented", "groups_represented",
        "invalid_pipeline_metadata", "context_disagreement_with_initial_xlmr",
        "status_counts"
    )}, sort_keys=True))
    if invalid or checked != len(sample):
        raise RuntimeError("Pipeline metadata changed, missing, or not read-only: NO-GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
