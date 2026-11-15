"""Step 1: a pool of unlabelled reviews with the DEPLOYED checker's flags (H0), split by product. See protocol.md.

    backend/.venv/Scripts/python.exe research/hazard_f1/make_pool.py

Writes research/hazard_f1/cache/pool.jsonl (not committed: full review text). Deterministic.
"""
from __future__ import annotations

import csv
import glob
import gzip
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
import dashboard_utils as du  # noqa: E402

SCANS = next(p for p in (ROOT / "backups" / "pool-scans", ROOT.parent / "Capstone-Version-Control" / "backups" / "pool-scans") if p.is_dir())
CACHE = HERE / "cache"
SALT = "hazard1"
PER_PRODUCT_LOW, PER_PRODUCT_HIGH = 25, 15


def norm(text: str) -> str:
    return re.sub(r"\W+", " ", str(text).lower()).strip()


def split_of(link: str) -> str:
    n = int(hashlib.sha1(f"{SALT}:{link}".encode("utf-8")).hexdigest(), 16) % 10
    return "HD1" if n < 3 else "HD2" if n < 6 else "HF"


def labelled_texts() -> set[str]:
    seen = set()
    for path in glob.glob(str(ROOT / "evaluation" / "**" / "*.csv"), recursive=True) + glob.glob(str(ROOT / "research" / "**" / "*.csv"), recursive=True):
        try:
            with open(path, encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                cols = [c for c in (reader.fieldnames or []) if c in ("review_text", "text", "content", "review")]
                if not cols:
                    continue
                for row in reader:
                    for c in cols:
                        if row.get(c):
                            seen.add(norm(row[c]))
        except Exception:
            continue
    return seen


def stars(value) -> int | None:
    try:
        return int(round(float(str(value).strip())))
    except Exception:
        return None


def main() -> None:
    CACHE.mkdir(exist_ok=True)
    rng = random.Random(20261116)
    known = labelled_texts()
    print("labelled texts excluded:", len(known), flush=True)
    products = []
    for path in sorted(SCANS.glob("search_*.json")):
        if "discovery" in path.name:
            continue
        for p in json.load(open(path, encoding="utf-8")):
            products.append((p, f"pool-scans/{path.name}"))
    for item in json.load(gzip.open(ROOT / "backend" / "seed" / "saved_products.json.gz", "rt", encoding="utf-8")):
        products.append((item["product"], "seed/saved_products.json.gz"))
    seen_text: set[str] = set()
    batch, meta = [], {}
    for product, source in products:
        link = str(product.get("link") or product.get("name") or "")
        low, high = [], []
        for review in product.get("comments") or []:
            if not isinstance(review, dict):
                continue
            text = str(review.get("content") or "").strip()
            key = norm(text)
            if len(text) < 15 or key in known or key in seen_text:
                continue
            seen_text.add(key)
            s = stars(review.get("rating"))
            (low if s is not None and s <= 3 else high).append((text, s))
        rng.shuffle(low)
        rng.shuffle(high)
        chosen = low[:PER_PRODUCT_LOW] + high[:PER_PRODUCT_HIGH]
        if not chosen:
            continue
        pid = hashlib.sha1(link.encode("utf-8")).hexdigest()[:12]
        comments = []
        for i, (text, s) in enumerate(chosen):
            rid = f"{pid}-{i:03d}"
            comments.append({"comment_id": rid, "content": text, "rating": s if s is not None else ""})
            meta[rid] = {"id": rid, "split": split_of(link), "product_hash": pid, "product": " ".join(str(product.get("name") or "").split())[:120], "source": source, "stars": s, "text": text}
        batch.append({"name": product.get("name"), "link": link, "platform": product.get("platform") or "lazada", "comments": comments})
    print("products", len(batch), "reviews", len(meta), flush=True)
    t0 = time.time()
    with open(CACHE / "pool.jsonl", "w", encoding="utf-8") as out:
        for start in range(0, len(batch), 20):
            for p in du.analyze_products(batch[start:start + 20]):
                for c in p.get("comments") or []:
                    sa = c.get("sentiment_analysis") or {}
                    row = meta[str(c.get("comment_id"))]
                    row["h0"] = sorted(set(sa.get("review_tags") or []) | set(sa.get("review_extra_tags") or []))
                    row["category"] = p.get("product_category") or ""
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"  analysed {min(start + 20, len(batch))}/{len(batch)} products in {time.time() - t0:.0f}s", flush=True)
    print("done")


if __name__ == "__main__":
    main()
