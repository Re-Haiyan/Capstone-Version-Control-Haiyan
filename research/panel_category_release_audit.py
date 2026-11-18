#!/usr/bin/env python3
"""Read-only paired pc4/pc6 audit on bundled development review records.

Run 'scan' in two separate Python processes / Git worktrees, so importing the
baseline really uses its own code rather than monkeypatching candidate internals.
Never edits databases or writes raw customer reviews to audit files.
This compares predictions, not ground-truth precision/recall or VM staging.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

FLAGS = ("counterfeit", "defect", "safety", "quality", "not_as_described")
TEXT_FIELDS = ("content", "review_text", "text", "review", "comment", "body")


def digest(*parts: object) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:20]


def load_products(root: Path) -> list[dict]:
    src = root / "backend/seed/saved_products.json.gz"
    if not src.is_file():
        raise RuntimeError("Bundled review corpus missing; cannot claim coverage")
    with gzip.open(src, "rt", encoding="utf-8") as stream:
        rows = json.load(stream)
    products = [x.get("product") for x in rows if isinstance(x, dict)]
    return [x for x in products if isinstance(x, dict) and str(x.get("name") or "").strip()]


def _rating(comment: dict) -> int:
    try:
        n = int(float(comment.get("rating") or comment.get("stars") or 3))
        return n if n in range(1, 6) else 3
    except (ValueError, TypeError, OverflowError):
        return 3


def prepare_rows(products: list[dict], limit: int) -> list[tuple]:
    """Deterministic breadth-first sample with all products considered equally."""
    buckets = []
    for p in products:
        title = str(p.get("name") or "")
        comments = p.get("comments") or []
        choices = []
        for c in comments:
            if not isinstance(c, dict):
                continue
            text = next((str(c.get(k) or "").strip() for k in TEXT_FIELDS if str(c.get(k) or "").strip()), "")
            if len(text) < 12:
                continue
            rating = _rating(c)
            key = digest(title, text, rating)
            choices.append((key, title, text, rating))
        if choices:
            buckets.append((digest(title), sorted(choices, key=lambda v: v[0])))
    buckets.sort(key=lambda v: v[0])
    result = []
    position = 0
    while len(result) < limit and any(position < len(arr) for _, arr in buckets):
        for _, arr in buckets:
            if position < len(arr) and len(result) < limit:
                result.append(arr[position])
        position += 1
    return result


def scan(args: argparse.Namespace) -> int:
    root = Path(args.checkout).resolve(strict=True)
    os.environ["DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW"] = ""  # never activate pilot
    os.environ["DEFAKETIVE_CATEGORY_SENTIMENT_ADAPTER"] = ""
    os.environ["DEFAKETIVE_SENTIMENT_CALIBRATOR"] = ""  # no extra calibration
    os.environ["DEFAKETIVE_MODEL_MODE"] = "hazard_badges"
    os.environ["DEFAKETIVE_SENTIMENT_MODEL"] = "xlmr"
    os.environ["DEFAKETIVE_HAZARD_MODEL"] = "learned"
    sys.path.insert(0, str(root / "backend/sentiment-analysis"))
    sys.path.insert(0, str(root / "backend"))
    from defaketive_sentiment import registry, product_category  # noqa: E402

    products = load_products(root)
    selections = prepare_rows(products, args.limit)
    if not selections:
        raise RuntimeError("Empty or unreadable sample: no GO claim allowed")
    model = registry.load_model()
    mapped = {}
    for p in products:
        title = str(p["name"])
        mapped[digest(title)] = {
            "category": product_category.classify_listing({"name": title}),
            "group": product_category.group_of(product_category.classify_listing({"name": title})),
        }

    review_results = {}
    by_product: dict[str, list] = defaultdict(list)
    for index, (key, title, text, rating) in enumerate(selections, 1):
        result = model.analyze(text, rating, listing={"name": title})
        labels = set(result.get("review_tags") or ()) | set(result.get("review_extra_tags") or ())
        review_results[key] = {
            "product": digest(title),
            "label": result.get("label"),
            "flags": sorted(x for x in labels if x in FLAGS),
        }
        by_product[digest(title)].append(result)
        if index % 100 == 0:
            print(f"Scanned {index}/{len(selections)} without writing review text", flush=True)

    product_verdicts = {}
    for product_key, results in by_product.items():
        cat = mapped[product_key]["category"]
        summary = model.summarize(results, reviews_available=len(results), product_type=cat)
        product_verdicts[product_key] = (summary.get("verdict") or {}).get("state")

    payload = {
        "schema": "panel-category-paired-1",
        "corpus": "bundled development saved reports (not independent, not live VM)",
        "model": "existing XLM-RoBERTa and learned hazard scorer",
        "category_revision": product_category.PRODUCT_CATEGORY_REVISION,
        "product_count": len(mapped),
        "sampled_products": len(by_product),
        "sampled_reviews": len(review_results),
        "products": mapped,
        "reviews": review_results,
        "sampled_verdicts": product_verdicts,
    }
    Path(args.out).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "category_revision": payload["category_revision"],
        "product_count": payload["product_count"],
        "sampled_products": payload["sampled_products"],
        "sampled_reviews": payload["sampled_reviews"],
        "categories": dict(sorted(Counter(p["category"] for p in mapped.values()).items())),
    }, sort_keys=True))
    return 0


def compare(args: argparse.Namespace) -> int:
    old = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    new = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
    if old["schema"] != new["schema"] or set(old["products"]) != set(new["products"]):
        raise RuntimeError("Mismatched corpus: comparison invalid")
    if set(old["reviews"]) != set(new["reviews"]):
        raise RuntimeError("Mismatched sampled reviews: comparison invalid")
    product_changes = [{
        "id": key, "old": old["products"][key]["category"], "new": new["products"][key]["category"]
    } for key in sorted(old["products"])
        if old["products"][key]["category"] != new["products"][key]["category"]]
    lost, gained = Counter(), Counter()
    changed_ids = []
    sentiment_changes = 0
    for key in sorted(old["reviews"]):
        a, b = old["reviews"][key], new["reviews"][key]
        if a["label"] != b["label"]:
            sentiment_changes += 1
        dropped = set(a["flags"]) - set(b["flags"])
        added = set(b["flags"]) - set(a["flags"])
        lost.update(dropped)
        gained.update(added)
        if dropped or added:
            changed_ids.append(key)
    verdict_ids = sorted(
        k for k in old["sampled_verdicts"]
        if old["sampled_verdicts"].get(k) != new["sampled_verdicts"].get(k)
    )
    result = {
        "research_only": True,
        "independent_accuracy_measured": False,
        "vm_deployment_verified": False,
        "same_review_corpus": True,
        "baseline_revision": old["category_revision"],
        "candidate_revision": new["category_revision"],
        "products_compared": old["product_count"],
        "sampled_products": old["sampled_products"],
        "reviews_compared": old["sampled_reviews"],
        "changed_category_count": len(product_changes),
        "changed_categories": product_changes,
        "sentiment_changed_count": sentiment_changes,
        "hazard_flag_losses": {c: lost[c] for c in FLAGS},
        "hazard_flag_gains": {c: gained[c] for c in FLAGS},
        "changed_flag_reviews_count": len(changed_ids),
        "changed_flag_review_hashes": changed_ids[:30],
        "changed_sampled_verdict_count": len(verdict_ids),
        "changed_sampled_verdict_hashes": verdict_ids[:30],
    }
    result["requires_manual_review"] = bool(sentiment_changes or changed_ids or verdict_ids)
    Path(args.out).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("changed_categories", "changed_flag_review_hashes",
                                   "changed_sampled_verdict_hashes")}, indent=2, sort_keys=True))
    if result["requires_manual_review"] and args.strict:
        raise RuntimeError("Paired audit found a changed sentiment, flag, or sampled verdict: manual adjudication needed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    scan_cmd = sub.add_parser("scan")
    scan_cmd.add_argument("--checkout", required=True)
    scan_cmd.add_argument("--out", required=True)
    scan_cmd.add_argument("--limit", type=int, default=600)
    compare_cmd = sub.add_parser("compare")
    compare_cmd.add_argument("--baseline", required=True)
    compare_cmd.add_argument("--candidate", required=True)
    compare_cmd.add_argument("--out", required=True)
    compare_cmd.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    return scan(args) if args.command == "scan" else compare(args)


if __name__ == "__main__":
    raise SystemExit(main())
