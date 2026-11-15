"""Show which word-list entries or model made the checker flag given HD1 items (development only).

    <app python> research/hazard_f1/why.py --impl <checkout> HD1-016 HD1-027 ...
"""
import argparse
import collections
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--impl", type=Path, required=True)
parser.add_argument("items", nargs="+")
args = parser.parse_args()
sys.path.insert(0, str(args.impl / "backend"))
sys.path.insert(0, str(args.impl / "backend" / "sentiment-analysis"))
import dashboard_utils as du  # noqa: E402

split = args.items[0].split("-")[0]
key = {r["item_id"]: r for r in csv.DictReader(open(HERE / "data" / f"key_{split}.csv", encoding="utf-8-sig"))}
sheet = {r["item_id"]: r for r in csv.DictReader(open(HERE / "data" / f"sheet_{split}.csv", encoding="utf-8-sig"))}
by_product = collections.defaultdict(list)
for item in args.items:
    r = sheet[item]
    by_product[(key[item]["product_hash"], r["product"])].append(r)
products = [{"name": name, "link": f"eval://{pid}", "platform": "lazada", "comments": [{"comment_id": r["item_id"], "content": r["review_text"], "rating": r["stars"]} for r in group]} for (pid, name), group in by_product.items()]
for p in du.analyze_products(products):
    for c in p.get("comments") or []:
        sa = c.get("sentiment_analysis") or {}
        print(f"\n{c['comment_id']} [{p.get('product_category')}] tags={sa.get('review_tags')} extra={sa.get('review_extra_tags')}")
        for s in sa.get("sentences") or []:
            terms = [(t.get("ngram"), t.get("category"), "neg" if t.get("negated") else "", t.get("source") or t.get("origin") or "") for t in (s.get("terms") or []) + (s.get("extra_terms") or [])]
            if terms or s.get("tags") or s.get("extra_tags"):
                print("   ", repr(str(s.get("text_raw"))[:90]), "tags", s.get("tags"), s.get("extra_tags"), "terms", [(str(a)[:40], b, c2) for a, b, c2, _ in terms], {k: v for k, v in s.items() if k in ("hazard_model", "learned", "model_flags")})
