"""Build the Phase 3 development and fresh-final samples (see protocol.md). Deterministic.

    python research/product_specific_conclusions/phase3/make_data.py

Writes phase3/data/: blank annotation sheets for D1, D2 and F, and data_manifest.csv (split, profile, category, group, language, source,
collection date, hashed product, text hash). Product links and names are not written; only a hash of the link.
Nothing from the locked pack (human_eval_pack/) is used except to EXCLUDE it. The F sheet must not be read before the extractor is frozen.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
ROOT = RESEARCH.parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
sys.path.insert(0, str(RESEARCH))

import aspect_profiles as ap  # noqa: E402
import aspects  # noqa: E402
import dashboard_utils as du  # noqa: E402
from aspect_validation import INTENDED, default_scans  # noqa: E402
from defaketive_sentiment.product_category import classify_listing, group_of  # noqa: E402
from final_eval_pack import collapse, redact  # noqa: E402

DATA = HERE / "data"
PACK = RESEARCH / "human_eval_pack"
SALT = "phase3"
QUOTA = {  # profile: (D1, D2, F)
    "hair": (24, 18, 22), "skin": (30, 22, 26), "apparel": (18, 14, 16), "food": (24, 18, 20), "appliance": (24, 18, 20),
    "powerbank": (18, 14, 14), "earbuds": (12, 8, 10), "general": (10, 8, 12),
}
PER_PRODUCT = 8
JACCARD = 0.8


def norm(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def tokens(text: str) -> frozenset:
    return frozenset(norm(text).split())


def split_of(link: str) -> str:
    """Product-grouped: by a hash of the product link, never by review."""
    n = int(hashlib.sha1(f"{SALT}:{link}".encode("utf-8")).hexdigest(), 16) % 10
    return "D1" if n < 4 else "D2" if n < 7 else "F"


def read_pack():
    with open(PACK / "reviews.csv", encoding="utf-8-sig") as fh:
        reviews = [r["review_text"] for r in csv.DictReader(fh)]
    with open(PACK / "card_sheet_A.csv", encoding="utf-8-sig") as fh:
        names = {r["product"].strip() for r in csv.DictReader(fh)}
    return reviews, names


def candidates(pack_names: set[str]):
    """Products with their reviews, from the raw scans and from the saved electronics. Locked-pack products are dropped here."""
    out = []
    scans = default_scans()
    for path in sorted(scans.glob("search_*.json")):
        topic = path.stem.replace("search_", "")
        if "discovery" in topic or topic not in INTENDED:
            continue
        for p in json.load(open(path, encoding="utf-8")):
            name = str(p.get("name") or "")
            if name[:100].strip() in pack_names:
                continue
            category = classify_listing({"name": name})
            group = group_of(category) if category else None
            profile = ap.profile_key(category, group)
            if profile != INTENDED[topic]:
                continue  # the classifier disagrees with the search topic: left out, as in aspect_validation
            out.append({"link": p["link"], "profile": profile, "category": category, "group": group, "source": f"pool-scans/{path.name}", "date": "2026-11-13 to 2026-11-14 (scan_log.json)", "reviews": p.get("comments") or [], "development_only": False})
    saved = json.load(gzip.open(ROOT / "backend" / "seed" / "saved_products.json.gz", "rt", encoding="utf-8"))
    for item in saved:
        p = item["product"]
        name = str(p.get("name") or "")
        if name[:100].strip() in pack_names:
            continue
        category, group = du.product_category_of(p), du.product_group(p)
        profile = ap.profile_key(category, group)
        if profile not in QUOTA:
            continue
        out.append({"link": str(p.get("link") or name), "profile": profile, "category": category, "group": group, "source": "saved_products.json.gz (seed)", "date": "not recorded in the seed file", "reviews": p.get("comments") or [], "development_only": True})
    return out


def main() -> None:
    DATA.mkdir(exist_ok=True)
    pack_reviews, pack_names = read_pack()
    pack_exact = {norm(t) for t in pack_reviews}
    pack_sets = [tokens(t) for t in pack_reviews if len(norm(t)) > 15]
    rng = random.Random(20261115)
    products = candidates(pack_names)
    taken_exact, taken_sets, rows = set(), [], []
    plan = {}
    for profile, quotas in QUOTA.items():
        for split, want in zip(("D1", "D2", "F"), quotas):
            plan[(profile, split)] = want
    by_group: dict[tuple, list] = {}
    for p in products:
        split = split_of(p["link"])
        if split == "F" and p["development_only"]:
            split = "D1" if int(hashlib.sha1(("x" + p["link"]).encode()).hexdigest(), 16) % 2 else "D2"  # seen-while-tuning products are never final
        by_group.setdefault((p["profile"], split), []).append(p)
    short_of = {}
    for (profile, split), want in plan.items():
        pool = by_group.get((profile, split), [])
        rng.shuffle(pool)
        chosen = []
        for p in pool:
            texts = [(str(r.get("content") or ""), r) for r in p["reviews"] if isinstance(r, dict)]
            texts = [(redact(collapse(t)), r) for t, r in texts if len(t.strip()) >= 20]
            rng.shuffle(texts)
            used = 0
            for text, review in texts:
                if len(chosen) >= want or used >= PER_PRODUCT:
                    break
                key = norm(text)
                if key in pack_exact or key in taken_exact:
                    continue
                toks = tokens(text)
                if len(key) > 15 and any(len(toks & s) / len(toks | s) >= JACCARD for s in pack_sets + taken_sets if toks and s):
                    continue
                taken_exact.add(key)
                taken_sets.append(toks)
                chosen.append((p, text, review))
                used += 1
            if len(chosen) >= want:
                break
        if len(chosen) < want:
            short_of[(profile, split)] = (len(chosen), want)
        for p, text, review in chosen:
            rows.append({"split": split, "profile": profile, "category": p["category"] or "", "group": p["group"] or "", "language": aspects.language_of(text), "source": p["source"], "collection_date": p["date"], "product_hash": hashlib.sha1(p["link"].encode()).hexdigest()[:12], "stars": review.get("rating", ""), "review_text": text, "development_only": p["development_only"]})
    rng.shuffle(rows)
    counters = {"D1": 0, "D2": 0, "F": 0}
    for r in rows:
        counters[r["split"]] += 1
        r["item_id"] = f"{r['split']}-{counters[r['split']]:03d}"
        r["text_sha256"] = hashlib.sha256(r["review_text"].encode("utf-8")).hexdigest()[:16]
    cols = ["item_id", "profile", "stars", "review_text", "features", "note"]
    for split in ("D1", "D2", "F"):
        with open(DATA / f"sheet_{split}.csv", "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows({**r, "features": "", "note": ""} for r in rows if r["split"] == split)
    mcols = ["item_id", "split", "profile", "category", "group", "language", "source", "collection_date", "product_hash", "stars", "text_sha256", "development_only"]
    with open(DATA / "data_manifest.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=mcols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["item_id"]))
    print({s: counters[s] for s in counters}, "short of quota:", short_of)
    print("products per split:", {s: len({r["product_hash"] for r in rows if r["split"] == s}) for s in counters})


if __name__ == "__main__":
    main()
