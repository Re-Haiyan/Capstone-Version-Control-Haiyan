"""Score a version of the hazard checker on a labelled split (protocol.md). Runs the checker itself; never reads cached flags.

    <app python> research/hazard_f1/score.py --impl <repo checkout whose backend/ is the checker> --split HD1 --name H0 [--errors]

Gold: raw/labels_<split>.txt, high-confidence rows only. Weighted figures use the sampling weights in data/key_<split>.csv
(an estimate for the whole pool); unweighted figures describe the sample. Intervals: 95%, bootstrap over products (1,000 draws).
`--errors` writes the mis-flags; use it for HD1 only until a candidate is frozen.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLAGS = ("safety", "defect", "counterfeit", "quality", "not_as_described")


def read_labels(split: str) -> dict:
    out = {}
    for line in open(HERE / "raw" / f"labels_{split}.txt", encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        item, flags, conf = line.split("|")
        out[f"{split}-{item}"] = (set() if flags == "none" else set(flags.split(";")), conf)
    return out


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    f = 2 * p * r / (p + r) if tp and p + r else (0.0 if tp + fp + fn else float("nan"))
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3)}


def tally(rows, flag, weighted):
    tp = fp = fn = 0.0
    for r in rows:
        w = r["weight"] if weighted else 1.0
        g, p = flag in r["gold"], flag in r["pred"]
        tp += w * (g and p)
        fp += w * (p and not g)
        fn += w * (g and not p)
    return tp, fp, fn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--impl", type=Path, required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--errors", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(args.impl / "backend"))
    sys.path.insert(0, str(args.impl / "backend" / "sentiment-analysis"))
    import dashboard_utils as du  # noqa: E402

    labels = read_labels(args.split)
    key = {r["item_id"]: r for r in csv.DictReader(open(HERE / "data" / f"key_{args.split}.csv", encoding="utf-8-sig"))}
    sheet = list(csv.DictReader(open(HERE / "data" / f"sheet_{args.split}.csv", encoding="utf-8-sig")))
    by_product = collections.defaultdict(list)
    for r in sheet:
        by_product[(key[r["item_id"]]["product_hash"], r["product"])].append(r)
    products = [{"name": name, "link": f"eval://{pid}", "platform": "lazada",
                 "comments": [{"comment_id": r["item_id"], "content": r["review_text"], "rating": r["stars"]} for r in group]}
                for (pid, name), group in by_product.items()]
    t0 = time.time()
    pred = {}
    for p in du.analyze_products(products):
        for c in p.get("comments") or []:
            sa = c.get("sentiment_analysis") or {}
            pred[str(c.get("comment_id"))] = set(sa.get("review_tags") or []) | set(sa.get("review_extra_tags") or [])
    rows = []
    for r in sheet:
        gold, conf = labels[r["item_id"]]
        if conf != "H":
            continue
        k = key[r["item_id"]]
        rows.append({"id": r["item_id"], "gold": gold, "pred": pred.get(r["item_id"], set()) & set(FLAGS), "weight": float(k["weight"]), "product": k["product_hash"], "stratum": k["stratum"], "text": r["review_text"], "name": r["product"], "stars": r["stars"]})
    out = {"name": args.name, "split": args.split, "impl": str(args.impl), "scored_rows": len(rows), "low_confidence_rows_left_out": len(sheet) - len(rows),
           "products": len({r["product"] for r in rows}), "seconds": round(time.time() - t0, 1), "flags": {}}
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r["product"]].append(r)
    names = sorted(groups)
    rng = random.Random(7)
    draws = [[x for n in (rng.choice(names) for _ in names) for x in groups[n]] for _ in range(1000)]
    for flag in FLAGS:
        entry = {}
        for label, weighted in (("weighted", True), ("unweighted", False)):
            tp, fp, fn = tally(rows, flag, weighted)
            stats = prf(tp, fp, fn)
            f1s = sorted(v for v in (prf(*tally(d, flag, weighted))["f1"] for d in draws) if v == v)
            stats.update(tp=round(tp, 1), fp=round(fp, 1), fn=round(fn, 1), f1_95=[f1s[int(0.025 * len(f1s))], f1s[int(0.975 * len(f1s)) - 1]] if f1s else None)
            entry[label] = stats
        out["flags"][flag] = entry
    for label in ("weighted", "unweighted"):
        out[f"macro_f1_{label}"] = round(sum(out["flags"][f][label]["f1"] for f in FLAGS) / len(FLAGS), 3)
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / f"{args.name}_{args.split}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    if args.errors:
        with open(HERE / "results" / f"{args.name}_{args.split}_errors.csv", "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["item_id", "flag", "outcome", "stratum", "stars", "product", "text"])
            for r in rows:
                for flag in FLAGS:
                    g, p = flag in r["gold"], flag in r["pred"]
                    if g != p:
                        w.writerow([r["id"], flag, "fp" if p else "fn", r["stratum"], r["stars"], r["name"][:50], r["text"][:400]])
    print(args.name, args.split, "rows", len(rows), "macro F1 weighted", out["macro_f1_weighted"], "unweighted", out["macro_f1_unweighted"])
    for flag in FLAGS:
        w, u = out["flags"][flag]["weighted"], out["flags"][flag]["unweighted"]
        print(f"  {flag:17s} weighted P {w['precision']:.3f} R {w['recall']:.3f} F1 {w['f1']:.3f} {w['f1_95']} | sample P {u['precision']:.3f} R {u['recall']:.3f} F1 {u['f1']:.3f} (tp {u['tp']:.0f} fp {u['fp']:.0f} fn {u['fn']:.0f})")


if __name__ == "__main__":
    main()
