"""Reproducible, non-final-test category audit on documented listings and saved reviews.

Run this same script against the feature branch and its baseline worktree, in
separate Python processes to avoid cross-version module caching. This is an
invariance / disagreement audit, NOT accuracy or independently labelled F1.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path


def load_products(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("products", "data", "items"):
            if isinstance(data.get(key), list):
                return [item for item in data[key] if isinstance(item, dict)]
    raise ValueError("Unsupported saved pool shape; do not invent fallback products")


def snapshot(source_root: Path) -> dict:
    source_root = source_root.resolve()
    sys.path[:0] = [
        str(source_root / "backend"),
        str(source_root / "backend" / "sentiment-analysis"),
    ]
    import aspect_profiles  # noqa: PLC0415
    import aspects  # noqa: PLC0415
    from defaketive_sentiment.product_category import classify_listing, group_of  # noqa: PLC0415

    # These examples and their names originated from actual scan/audit records.
    # The original intended *profile* is not always one precise catalogue slug.
    data = json.loads(
        (source_root / "research/product_specific_conclusions/aspect_validation_real.json")
        .read_text(encoding="utf-8")
    )
    expected = {
        "hair_shampoo": {"haircare"},
        "lipstick": {"makeup"},
        "protein_powder": {"health_supplements"},
        "vitamins_supplement": {"health_supplements"},
        "whitening_serum": {"skincare"},
    }
    cases = []
    for topic, rows in data["classifier_disagreements"].items():
        for item in rows:
            title = item["product"]
            category = classify_listing({"name": title})
            cases.append(
                {
                    "topic": topic,
                    "title": title,
                    "previously_documented_category": item["classified_as"],
                    "expected_category": sorted(expected[topic]),
                    "now_classified_as": category,
                    "fixed": category in expected[topic],
                    "reviews_in_documented_scan": item["reviews"],
                }
            )

    products = load_products(source_root / "backend/seed/saved_products.json.gz")
    saved = []
    for item in products:
        title = str(item.get("name") or "")
        category = classify_listing({"name": title})
        group = group_of(category)
        comments = item.get("comments")
        if not isinstance(comments, list):
            comments = []
        # Always take the same bounded prefix; already-development real reviews
        # only. The 150-review locked evaluation is NOT part of this sampling.
        sample = [
            x for x in comments
            if isinstance(x, dict) and str(x.get("content") or x.get("comment") or "").strip()
        ][:30]
        extracted = aspects.extract(sample, category, group) if sample else None
        aspect_counts = {}
        if extracted:
            for aspect in extracted.get("aspects") or []:
                positive = int((aspect.get("positive") or {}).get("reviews") or 0)
                negative = int((aspect.get("negative") or {}).get("reviews") or 0)
                if positive or negative:
                    aspect_counts[aspect["id"]] = [positive, negative]
        # Existing saved sentiment / hazard results are recorded as-is, not
        # treated as a new analysis or an unchanged-hazard claim.
        summary = item.get("sentiment_summary") or {}
        saved.append(
            {
                "name": title,
                "link": str(item.get("link") or ""),
                "category": category,
                "group": group,
                "profile": aspect_profiles.profile_key(category, group),
                "sample_reviews": len(sample),
                "aspect_counts": aspect_counts,
                "saved_sentiment_counts": summary.get("sentiment_counts"),
                "saved_verdict": (summary.get("verdict") or {}).get("state"),
            }
        )

    return {
        "kind": "nonindependent_development_audit",
        "source": "actual documented listing titles + saved product reviews",
        "category_revision": __import__(
            "defaketive_sentiment.product_category", fromlist=["PRODUCT_CATEGORY_REVISION"]
        ).PRODUCT_CATEGORY_REVISION,
        "aspect_rules_version": aspect_profiles.ASPECT_RULES_VERSION,
        "documented_titles": cases,
        "saved_products": saved,
    }


def compare(before: dict, after: dict) -> dict:
    a = before["documented_titles"]
    b = after["documented_titles"]
    if len(a) != len(b):
        raise ValueError("Documented titles differ")
    title_changes = []
    for x, y in zip(a, b):
        if x["title"] != y["title"]:
            raise ValueError("Documented title order differs")
        if x["now_classified_as"] != y["now_classified_as"]:
            title_changes.append({
                "topic": x["topic"],
                "title": x["title"],
                "old": x["now_classified_as"],
                "new": y["now_classified_as"],
                "fixed": y["fixed"],
            })
    bp = {x["link"]: x for x in before["saved_products"]}
    ap = {x["link"]: x for x in after["saved_products"]}
    if bp.keys() != ap.keys():
        raise ValueError("Saved product identities differ")
    category_changes, aspect_changes, saved_sentiment_changes, saved_verdict_changes = [], [], [], []
    for link, x in bp.items():
        y = ap[link]
        if x["category"] != y["category"]:
            category_changes.append({"name": x["name"], "old": x["category"], "new": y["category"]})
        if x["profile"] != y["profile"] or x["aspect_counts"] != y["aspect_counts"]:
            aspect_changes.append({
                "name": x["name"], "category": y["category"],
                "before_profile": x["profile"], "after_profile": y["profile"],
                "before": x["aspect_counts"], "after": y["aspect_counts"]
            })
        if x["saved_sentiment_counts"] != y["saved_sentiment_counts"]:
            saved_sentiment_changes.append(link)
        if x["saved_verdict"] != y["saved_verdict"]:
            saved_verdict_changes.append(link)
    return {
        "old_rule": before["category_revision"],
        "new_rule": after["category_revision"],
        "documented_mistakes": len(b),
        "before_fixed": sum(x["fixed"] for x in a),
        "after_fixed": sum(x["fixed"] for x in b),
        "documented_title_changes": title_changes,
        "saved_products": len(bp),
        "saved_category_changes": category_changes,
        "saved_aspect_changes": aspect_changes,
        "saved_sentiment_snapshot_changes": saved_sentiment_changes,
        "saved_verdict_snapshot_changes": saved_verdict_changes,
        "limits": [
            "Stored labels/verdicts are compared without rescoring the hazard or sentiment models.",
            "Aspect changes are computed on the first 30 real written reviews per saved product, not the locked final evaluation.",
            "This is NOT an independent category accuracy estimate, aspect F1, or full model invariance proof.",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument("--output", type=Path)
    p.add_argument("--compare", nargs=2, type=Path, metavar=("BASELINE_JSON", "CANDIDATE_JSON"))
    args = p.parse_args()
    if args.compare:
        payload = compare(*(json.loads(file.read_text(encoding="utf-8")) for file in args.compare))
    else:
        payload = snapshot(args.source_root)
    result = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
