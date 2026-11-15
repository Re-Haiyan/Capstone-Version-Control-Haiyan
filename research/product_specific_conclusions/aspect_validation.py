"""Run the aspect extractor on REAL reviews of the product types the saved pool lacks, and report what it finds.

    python research/product_specific_conclusions/aspect_validation.py [--scans DIR] [--sample 40]

Data: the project's own Lazada scans (backups/pool-scans/search_*.json: hair shampoo, facial cleanser, lipstick, sunscreen,
whitening serum, women's dresses, bed sheets, school bags, air fryer, rice cooker, vitamins, protein powder, cat and dog food,
baby bottles, kids' toys, building blocks). They are the team's scrapes of public reviews, read here and never altered.
Nothing is invented. A product type with no scan has no real data and is reported as such.

THE SPLIT. Products are split by a hash of their link: an even hash is the DEVELOPMENT half (the only half whose reviews were
read to write the real-review additions to the tables), an odd hash is the HELD-OUT half (not read before those additions).
Coverage is reported for both. The annotator sample is drawn from the held-out half only.

WHICH PROFILE. A listing's profile follows the project's category classifier, which sometimes puts a product in the wrong
type (lipsticks as kitchenware, toy cars as automotive). `INTENDED` maps each scan's search topic to the profile it is meant to
exercise; listings where the classifier disagrees are counted and left out of that profile's figures, and reported.

Writes (next to this file): aspect_validation_real.json and aspect_validation_sample.csv (random claims from the held-out
half for INDEPENDENT annotators: the `label` column is empty). Coverage is not accuracy: it says how often the tables find
something to say, not whether what they say is right.
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))

import aspect_profiles as ap  # noqa: E402
import aspects  # noqa: E402
import conclusion_text  # noqa: E402
from defaketive_sentiment.product_category import classify_listing, group_of  # noqa: E402

PROFILES_UNDER_TEST = ("hair", "skin", "apparel", "footwear", "food", "appliance", "motorcycle")
# What each scan's search topic is meant to exercise. A scan not listed (cat food, toys, baby bottles ...) has no profile of its own.
INTENDED = {
    "hair_shampoo": "hair",
    "facial_cleanser": "skin",
    "lipstick": "skin",
    "sunscreen": "skin",
    "whitening_serum": "skin",
    "dress_women": "apparel",
    "air_fryer": "appliance",
    "rice_cooker": "appliance",
    "vitamins_supplement": "food",
    "protein_powder": "food",
}


def half_of(link: str) -> str:
    return "dev" if int(hashlib.sha1(link.encode("utf-8")).hexdigest(), 16) % 2 == 0 else "test"


def default_scans() -> Path:
    for candidate in (ROOT / "backups" / "pool-scans", ROOT.parent / "Capstone-Version-Control" / "backups" / "pool-scans"):
        if candidate.is_dir():
            return candidate
    raise SystemExit("No scans folder found; pass --scans.")


def new_bucket() -> dict:
    return {"products": 0, "reviews": 0, "claimed": 0, "aspects": collections.defaultdict(lambda: [0, 0]), "skipped": collections.Counter(), "limited": 0, "claims": [], "titles": []}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scans", type=Path, default=None)
    parser.add_argument("--sample", type=int, default=40)
    args = parser.parse_args()
    scans = args.scans or default_scans()
    buckets: dict[tuple[str, str], dict] = {}
    misclassified: dict[str, list] = collections.defaultdict(list)
    seen: set[str] = set()
    for path in sorted(glob.glob(str(scans / "search_*.json"))):
        if path.endswith("_discovery.json"):
            continue
        topic = Path(path).stem.replace("search_", "")
        data = json.load(open(path, encoding="utf-8"))
        for product in data if isinstance(data, list) else data.get("products", []):
            comments = [c for c in (product.get("comments") or []) if isinstance(c, dict)]
            link = str(product.get("link") or "")
            if not comments or link in seen:
                continue
            seen.add(link)
            category = classify_listing({"name": str(product.get("name") or "")})
            group = group_of(category)
            profile = ap.profile_key(category, group)
            wanted = INTENDED.get(topic)
            if wanted is None:
                continue  # the scan has no profile of its own to exercise
            if profile != wanted:
                misclassified[topic].append({"product": str(product.get("name") or "")[:70], "classified_as": category, "profile_read": profile, "intended_profile": wanted, "reviews": len(comments)})
                continue
            bucket = buckets.setdefault((wanted, half_of(link)), new_bucket())
            result = aspects.extract(comments, category, group)
            bucket["products"] += 1
            bucket["titles"].append(str(product.get("name") or "")[:70])
            bucket["reviews"] += result["reviews_considered"]
            claimed = set()
            for row in result["aspects"]:
                if row["kind"] != "product":
                    continue
                bucket["aspects"][row["id"]][0] += row["positive"]["reviews"]
                bucket["aspects"][row["id"]][1] += row["negative"]["reviews"]
                for polarity in ("positive", "negative"):
                    claimed.update(row[polarity]["review_ids"])
                    for q in row[polarity]["quotes"]:
                        bucket["claims"].append({"profile": wanted, "category": category, "product": str(product.get("name") or "")[:60], "aspect": row["id"], "polarity": polarity, "review_id": q["review_id"], "quote": q["text"], "span": q["span"], "language": q["language"]})
            bucket["claimed"] += len(claimed)
            bucket["skipped"].update(result["skipped_clauses"])
            bucket["limited"] += int(conclusion_text.evidence_status(result) == "limited")
    report: dict = {"split_rule": "sha1(link) even = development half (read to write the real-review additions); odd = held-out half (not read first)"}
    rng = random.Random(2026)
    sample_rows = []
    for profile in sorted(set(PROFILES_UNDER_TEST) | {p for p, _ in buckets}):
        entry: dict = {}
        for half in ("dev", "test"):
            bucket = buckets.get((profile, half))
            if not bucket:
                entry[half] = {"products": 0, "real_reviews": 0}
                continue
            top = sorted(((n, p, q) for n, (p, q) in bucket["aspects"].items()), key=lambda t: -(t[1] + t[2]))
            entry[half] = {
                "products": bucket["products"],
                "real_reviews_with_text_after_dedupe": bucket["reviews"],
                "reviews_with_a_product_aspect_claim": bucket["claimed"],
                "share_with_a_claim": round(bucket["claimed"] / bucket["reviews"], 3) if bucket["reviews"] else 0,
                "products_with_limited_product_evidence": bucket["limited"],
                "aspects_positive_negative_reviews": {n: [p, q] for n, p, q in top},
                "skipped_clauses": dict(bucket["skipped"]),
            }
            if half == "test":
                claims = bucket["claims"]
                rng.shuffle(claims)
                sample_rows += claims[: args.sample]
        if not any(entry[h].get("products") for h in ("dev", "test")):
            entry["note"] = "no real reviews of this product type in the project's scans"
        report[profile] = entry
    report["classifier_disagreements"] = {topic: rows for topic, rows in misclassified.items()}
    (HERE / "aspect_validation_real.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(HERE / "aspect_validation_sample.csv", "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["profile", "category", "product", "aspect", "polarity", "review_id", "quote", "span", "language", "label", "note"])
        writer.writeheader()
        for row in sample_rows:
            writer.writerow({**row, "span": json.dumps(row["span"]), "label": "", "note": ""})
    for profile in sorted(k for k in report if k in PROFILES_UNDER_TEST):
        e = report[profile]
        print(f"{profile:10} dev: {e['dev'].get('products', 0):3} products {e['dev'].get('real_reviews_with_text_after_dedupe', 0):6} reviews {e['dev'].get('share_with_a_claim', 0):.3f} claimed | held-out: {e['test'].get('products', 0):3} products {e['test'].get('real_reviews_with_text_after_dedupe', 0):6} reviews {e['test'].get('share_with_a_claim', 0):.3f} claimed")
    print("classifier disagreements:", {t: len(r) for t, r in misclassified.items()})


if __name__ == "__main__":
    main()
