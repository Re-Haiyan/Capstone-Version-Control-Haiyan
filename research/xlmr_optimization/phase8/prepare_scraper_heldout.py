"""Private, unlabelled held-out v2 intake for DeFaketive's EXISTING Lazada scraper.

Input: genuine, authorized product/review JSON output from backend/lazada-scraper.
No network, model prediction, reference-label inference, or scraping here.
FAIL CLOSED if permission record, historical inputs, or private output are missing.
The outputs contain customer reviews: NEVER write them inside the public repo.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import pathlib
import random
import re
import sys
import unicodedata
from urllib.parse import urlsplit, urlunsplit

ROOT = pathlib.Path(__file__).resolve().parents[3]
X = ROOT / "research" / "xlmr_optimization"
FIELDS = ["id", "product", "category_group", "platform", "language_hint", "review_text",
          "sentiment", "tags", "positive_aspect", "negative_aspect", "confidence", "rationale"]
HISTORY = [
    "research/xlmr_optimization/annotation/dev_pool_sheet.csv",
    "research/xlmr_optimization/annotation/neutral_candidate_pool.csv",
    "research/xlmr_optimization/annotation/final_test_sheet_A.csv",
    "evaluation/annotated/train_v3.csv",
    "evaluation/annotated/test_v3.csv",
    "evaluation/fresh/label_batch_fresh.csv",
    "evaluation/fresh2/label_batch_fresh2.csv",
    "evaluation/gold_labels_200.csv",
    "evaluation/heldout_labels_100.csv",
]
KEYWORDS = {
    "electronics": ("phone", "charger", "headphone", "earphone", "monitor", "laptop", "keyboard", "computer", "power bank", "smartwatch", "tablet", "camera"),
    "home_living": ("furniture", "kitchen", "fan", "bed", "chair", "trolley", "lamp", "vacuum", "curtain"),
    "fashion": ("dress", "shirt", "sneaker", "sandal", "clothes", "pants", "bag", "shoes"),
    "beauty_health": ("skincare", "shampoo", "lipstick", "sunscreen", "serum", "cosmetics", "makeup"),
    "food_grocery": ("coffee", "rice", "snack", "cereal", "grocery", "noodle", "milk", "tea"),
    "automotive_tools": ("motorcycle", "car", "wrench", "drill", "helmet", "vehicle", "scooter"),
}


def norm(text):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", str(text or "")).casefold()))


def clean(text):
    return " ".join(str(text or "").split())


def urlkey(url):
    try:
        p = urlsplit(str(url or ""))
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/").lower(), "", "")) if p.netloc else ""
    except ValueError:
        return ""


def product_key(url):
    """Canonical Lazada product ID, invariant to a changed listing URL slug."""
    address = urlkey(url)
    host = urlsplit(address).hostname or ""
    if host == "lazada.com.ph" or host.endswith(".lazada.com.ph"):
        m = re.search(r"-i(\d{5,})(?:-s\d+)?\.html", urlsplit(address).path)
        if m:
            return "lazada:item:" + m.group(1)
    return address


def checksum(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def csvrows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def writecsv(path, names, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def rights(path):
    if not path.is_file():
        raise ValueError("Written permission record required; use --authorization-record.")
    doc = json.loads(path.read_text(encoding="utf-8"))
    required = ("source", "authorized_by", "rights_basis", "record_date")
    if any(not doc.get(key) for key in required):
        raise ValueError("Missing source, grantor, rights basis or date in authorization record")
    if doc["source"] != "lazada_ph" or doc.get("allowed_collection") is not True or doc.get("allowed_research_storage") is not True:
        raise ValueError("Record does not grant collection AND research storage rights for Lazada PH")
    # Study coordinator must verify authenticity independently; cannot be proven by this program.


def old_corpus(private_map):
    blocked_titles, blocked_links, blocked_text = set(), set(), set()
    source_counts = {}
    paths = [ROOT / p for p in HISTORY]
    if private_map:
        paths.append(private_map)
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError("Historical exclusion file missing: " + str(path))
        rows = csvrows(path)
        source_counts[path.name] = len(rows)
        if private_map and path == private_map and (not rows or not {"product_link", "product"}.issubset(rows[0])):
            raise ValueError("Private historical map needs product_link and product columns")
        for row in rows:
            title = norm(row.get("product") or row.get("product_name") or row.get("title"))
            link = urlkey(row.get("product_link") or row.get("link"))
            text = norm(row.get("review_text") or row.get("content") or row.get("review"))
            if title:
                blocked_titles.add(title)
            if link:
                blocked_links.add(product_key(link))
            if text:
                blocked_text.add(text)
    return blocked_titles, blocked_links, blocked_text, source_counts


def products(paths):
    for path in paths:
        items = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            raise ValueError("Expected original Lazada scraper JSON product list")
        for product in items:
            if not isinstance(product, dict) or product.get("review_filter_warning"):
                continue
            link = urlkey(product.get("link"))
            host = urlsplit(link).hostname or ""
            if not (host == "lazada.com.ph" or host.endswith(".lazada.com.ph")):
                continue
            name = clean(product.get("name"))
            if not name:
                continue
            category = str(product.get("research_stratum") or product.get("category_group") or "").lower()
            if category not in (*KEYWORDS, "other"):
                category = next((group for group, words in KEYWORDS.items() if any(w in name.lower() for w in words)), "other")
            for review in product.get("comments", []):
                if not isinstance(review, dict):
                    continue
                comment = clean(review.get("content"))
                identity = str(review.get("comment_id") or "")
                try:
                    stars = int(float(review.get("rating")))
                except (TypeError, ValueError):
                    continue
                if not identity or stars not in range(1, 6) or len(comment) < 12:
                    continue
                yield {
                    "text": comment, "id": identity, "stars": stars, "product": name,
                    "link": link, "category": category, "source_file": path.name,
                }


def possible_contact(text):
    return bool(re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
                or re.search(r"(?<!\d)(?:\+?63|0)9\d{9}(?!\d)", text))


def dedupe(rows, old_titles, old_links, old_text):
    kept, omitted = [], collections.Counter()
    seen_ids, seen_text = set(), set()
    for r in rows:
        if norm(r["product"]) in old_titles or product_key(r["link"]) in old_links:
            omitted["historical_product"] += 1
            continue
        t = norm(r["text"])
        if len(t) < 12 or possible_contact(r["text"]):
            omitted["short_or_personal_data"] += 1
            continue
        if t in old_text:
            omitted["historical_text"] += 1
            continue
        uid = (product_key(r["link"]), r["id"])
        if uid in seen_ids or t in seen_text:
            omitted["duplicate"] += 1
            continue
        seen_ids.add(uid)
        seen_text.add(t)
        kept.append(r)
    return kept, omitted


def exclude_near_duplicates(rows, old_text):
    # Character 3-5-gram 0.90 cosine similarity to ANY historical reference.
    if not rows or not old_text:
        return rows, 0
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    historical = sorted(x for x in old_text if len(x) >= 12)
    if not historical:
        return rows, 0
    v = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
    all_vectors = v.fit_transform(historical + [r["text"] for r in rows])
    block = all_vectors[:len(historical)]
    candidate = all_vectors[len(historical):]
    accepted, excluded = [], 0
    for start in range(0, len(rows), 128):
        m = candidate[start:start+128] @ block.T
        mx = m.max(axis=1).toarray().ravel() if m.nnz else np.zeros(min(128, len(rows)-start))
        for r, cosine in zip(rows[start:start+128], mx):
            if cosine >= 0.90:
                excluded += 1
            else:
                accepted.append(r)
    return accepted, excluded


def balanced_product_sample(rows, target, max_per_product, seed):
    rng = random.Random(seed)
    product_rows = collections.defaultdict(list)
    for r in rows:
        product_rows[product_key(r["link"])].append(r)
    for collection in product_rows.values():
        rng.shuffle(collection)
    links = list(product_rows)
    rng.shuffle(links)
    chosen = [product_rows[p].pop() for p in links[:target]]
    counts = collections.Counter(product_key(r["link"]) for r in chosen)
    remaining = [r for link in links for r in product_rows[link]]
    rng.shuffle(remaining)
    for r in remaining:
        if len(chosen) >= target:
            break
        if counts[product_key(r["link"])] < max_per_product:
            chosen.append(r)
            counts[product_key(r["link"])] += 1
    return sorted(chosen, key=lambda r: (r["link"], r["id"]))


def main():
    ap = argparse.ArgumentParser(description="Prepare private, blinded, unlabelled held-out v2 from authorized Lazada scraper JSON.")
    ap.add_argument("--scrape-json", type=pathlib.Path, nargs="+", required=True)
    ap.add_argument("--authorization-record", type=pathlib.Path, required=True)
    ap.add_argument("--private-historical-map", type=pathlib.Path)
    ap.add_argument("--output-private", type=pathlib.Path, required=True)
    ap.add_argument("--target", type=int, default=400)
    ap.add_argument("--min-products", type=int, default=100)
    ap.add_argument("--max-per-product", type=int, default=6)
    ap.add_argument("--seed", type=int, default=20261116)
    a = ap.parse_args()
    if a.target < a.min_products or a.min_products < 1 or not 1 <= a.max_per_product <= 6:
        ap.error("Require valid target, minimum products and max-per-product 1..6")
    rights(a.authorization_record)
    output = a.output_private.resolve()
    if ROOT.resolve() == output or ROOT.resolve() in output.parents:
        raise ValueError("Private customer reviews cannot be written inside the public repository")
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing review/annotation directory")
    old_titles, old_links, old_text, history_counts = old_corpus(a.private_historical_map)
    raw = list(products(a.scrape_json))
    usable, omitted = dedupe(raw, old_titles, old_links, old_text)
    usable, n_near = exclude_near_duplicates(usable, old_text)
    omitted["near_historical_text"] = n_near
    chosen = balanced_product_sample(usable, a.target, a.max_per_product, a.seed)
    n_products = len({product_key(r["link"]) for r in chosen})
    enough = len(chosen) == a.target and n_products >= a.min_products
    status = ("insufficient_new_reviews_or_products" if not enough
              else "provisional_missing_historical_product_ids" if not a.private_historical_map
              else "unlabelled_candidate_needs_independent_approval")
    output.mkdir(parents=True)
    sheet, restricted = [], []
    for index, r in enumerate(chosen, 1):
        sid = f"V2{index:04d}"
        sheet.append(dict(id=sid, product=r["product"][:140],
                          category_group=r["category"], platform="Lazada PH",
                          language_hint="unreviewed", review_text=r["text"],
                          sentiment="", tags="", positive_aspect="", negative_aspect="",
                          confidence="", rationale=""))
        restricted.append(dict(id=sid, product_link=r["link"],
                               source_review_id=r["id"], canonical_product_key=product_key(r["link"]), star_hidden=r["stars"],
                               source_file=r["source_file"]))
    for annotator, shuffle_seed in (("A", 11), ("B", 19)):
        shuffled = list(sheet)
        random.Random(shuffle_seed).shuffle(shuffled)
        writecsv(output / f"blind_reviewer_{annotator}.csv", FIELDS, shuffled)
    writecsv(output / "PRIVATE_source_map.csv",
             ["id", "product_link", "source_review_id", "canonical_product_key", "star_hidden", "source_file"], restricted)
    manifest = {
        "status": status,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "raw_scraper_review_count": len(raw),
        "usable_after_exclusions": len(usable),
        "target_reviews": a.target,
        "reviews_selected": len(chosen),
        "distinct_product_links": n_products,
        "max_reviews_per_product": a.max_per_product,
        "star_distribution_for_coordinator_only": dict(collections.Counter(str(r["stars"]) for r in chosen)),
        "category_distribution": dict(collections.Counter(r["category"] for r in chosen)),
        "excluded_counts": dict(omitted),
        "historical_source_counts": history_counts,
        "authentic_history_product_ids_checked": bool(a.private_historical_map),
        "checksums": {p.name: checksum(p) for p in (*a.scrape_json, output / "blind_reviewer_A.csv",
                                                     output / "blind_reviewer_B.csv", output / "PRIVATE_source_map.csv")},
        "source_rights": "Research coordinator must independently verify written permission and retention rights",
        "annotated": False, "model_predictions_or_scores_present": False,
        "frozen_independent_test": False,
        "limitations": [
            "Rights record is not independent legal verification",
            "Private historic product-ID coverage must be reviewed",
            "Near-duplicate character cosine check does not prove zero semantic leakage",
            "Category assignment may require human verification",
            "Star rating is for stratified sampling only and cannot be a sentiment label",
            "Two independent human annotations and adjudication still needed",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status, "reviews_selected": len(chosen),
        "distinct_product_links": n_products, "raw_candidates": len(raw),
        "excluded_counts": dict(omitted), "output_is_private": True
    }, indent=2))
    return 0 if enough else 2


if __name__ == "__main__":
    sys.exit(main())
