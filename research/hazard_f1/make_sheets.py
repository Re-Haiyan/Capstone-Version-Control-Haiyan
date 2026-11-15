"""Step 2: stratified labelling sheets from the pool (protocol.md section 2). Deterministic.

    python research/hazard_f1/make_sheets.py

Writes data/sheet_<split>.csv (product, stars, review text; blank flags and confidence; shuffled; no checker output) and
data/key_<split>.csv (stratum, sampling weight and the deployed checker's flags: NOT to be opened while labelling).
"""
from __future__ import annotations

import collections
import csv
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
QUOTA = {  # stratum: (HD1, HD2, HF)
    "S1_safety": (40, 40, 40), "S2_counterfeit": (20, 20, 28), "S2_quality": (26, 26, 34), "S2_not_as_described": (26, 26, 34),
    "S2_defect": (30, 30, 40), "S3_unflagged_low_star": (40, 40, 56), "S4_unflagged_high_star": (20, 20, 28),
}
REDACT = [(re.compile(r"(?<!\d)(?:\+?63|0)\s?9\d{2}[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"), "[number removed]"), (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[email removed]"),
          (re.compile(r"https?://\S+|www\.\S+"), "[link removed]"), (re.compile(r"(?<!\d)\d{9,}(?!\d)"), "[number removed]")]


def stratum(row: dict) -> str:
    flags = set(row["h0"])
    if "safety" in flags:
        return "S1_safety"
    for flag in ("counterfeit", "quality", "not_as_described", "defect"):
        if flag in flags:
            return f"S2_{flag}"
    return "S3_unflagged_low_star" if (row["stars"] or 5) <= 3 else "S4_unflagged_high_star"


def redact(text: str) -> str:
    text = " ".join(str(text).split())
    for pattern, repl in REDACT:
        text = pattern.sub(repl, text)
    return text


def main() -> None:
    DATA.mkdir(exist_ok=True)
    rows = [json.loads(line) for line in open(HERE / "cache" / "pool.jsonl", encoding="utf-8")]
    for index, split in enumerate(("HD1", "HD2", "HF")):
        rng = random.Random(100 + index)
        pool = collections.defaultdict(list)
        for row in rows:
            if row["split"] == split:
                pool[stratum(row)].append(row)
        chosen = []
        for name, quotas in QUOTA.items():
            items = sorted(pool[name], key=lambda r: r["id"])
            rng.shuffle(items)
            take = items[: quotas[index]]
            for row in take:
                chosen.append({**row, "stratum": name, "stratum_size": len(items), "sampled": len(take), "weight": round(len(items) / len(take), 4)})
        rng.shuffle(chosen)
        for n, row in enumerate(chosen, 1):
            row["item_id"] = f"{split}-{n:03d}"
        with open(DATA / f"sheet_{split}.csv", "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["item_id", "product", "stars", "review_text", "flags", "confidence"])
            for row in chosen:
                w.writerow([row["item_id"], row["product"], row["stars"], redact(row["text"]), "", ""])
        with open(DATA / f"key_{split}.csv", "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["item_id", "pool_id", "product_hash", "category", "source", "stratum", "stratum_size", "sampled", "weight", "h0_flags"])
            for row in chosen:
                w.writerow([row["item_id"], row["id"], row["product_hash"], row["category"], row["source"], row["stratum"], row["stratum_size"], row["sampled"], row["weight"], ";".join(row["h0"])])
        print(split, len(chosen), "reviews,", len({r["product_hash"] for r in chosen}), "products;", {k: sum(1 for r in chosen if r["stratum"] == k) for k in QUOTA})


if __name__ == "__main__":
    main()
