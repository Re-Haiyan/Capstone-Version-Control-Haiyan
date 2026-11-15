"""Analyse a sample of REAL non-gadget products (the project's own scans) with the app's own analysis pipeline.

    python research/product_specific_conclusions/analyse_real_nongadget.py [--per-profile hair=4,skin=6,...]

Only HELD-OUT products (see aspect_validation.py) whose search topic and category agree are used. The pipeline is the one the
app runs (XLM-RoBERTa ONNX sentiment, hazard checker); this script only calls it. No model file is read for writing or changed.
Output: cache/analysed_nongadget.json.gz (not for commit: it holds full review text). real_examples.py reads it.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
sys.path.insert(0, str(HERE))

import aspect_profiles as ap  # noqa: E402
import dashboard_utils as du  # noqa: E402
from aspect_validation import INTENDED, default_scans, half_of  # noqa: E402
from defaketive_sentiment.product_category import classify_listing, group_of  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-profile", default="hair=4,skin=6,apparel=4,appliance=5,food=5")
    parser.add_argument("--max-reviews", type=int, default=260)
    parser.add_argument("--min-reviews", type=int, default=60)
    parser.add_argument("--skip", type=Path, default=None, help="an earlier cache file: its products are not picked again (so a second pack uses UNREAD products)")
    parser.add_argument("--out", default="analysed_nongadget.json.gz")
    args = parser.parse_args()
    want = {k: int(v) for k, v in (item.split("=") for item in args.per_profile.split(","))}
    picked: dict[str, list] = {k: [] for k in want}
    seen = {p["link"] for p in json.load(gzip.open(args.skip, "rt", encoding="utf-8"))} if args.skip else set()
    for path in sorted(glob.glob(str(default_scans() / "search_*.json"))):
        if path.endswith("_discovery.json"):
            continue
        profile = INTENDED.get(Path(path).stem.replace("search_", ""))
        if profile not in want:
            continue
        for product in json.load(open(path, encoding="utf-8")):
            comments = product.get("comments") or []
            category = classify_listing({"name": str(product.get("name") or "")})
            if not (args.min_reviews <= len(comments) <= args.max_reviews) or ap.profile_key(category, group_of(category)) != profile:
                continue
            if half_of(str(product.get("link"))) != "test" or product["link"] in seen:
                continue
            seen.add(product["link"])
            picked[profile].append(product)
    chosen = [p for profile, items in picked.items() for p in sorted(items, key=lambda x: -len(x["comments"]))[: want[profile]]]
    print(f"analysing {len(chosen)} products, {sum(len(p['comments']) for p in chosen)} reviews", flush=True)
    out = []
    started = time.time()
    for i, product in enumerate(chosen, 1):
        t = time.time()
        analysed = du.analyze_products([product])[0]
        out.append(analysed)
        print(f"{i}/{len(chosen)} {product['name'][:50]!r} {len(product['comments'])} reviews {time.time() - t:.0f}s", flush=True)
    with gzip.open(HERE / "cache" / args.out, "wt", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print(f"done in {time.time() - started:.0f}s", flush=True)


if __name__ == "__main__":
    main()
