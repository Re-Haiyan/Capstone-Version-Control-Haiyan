"""Score every labelled review with the rules of a given checkout, then compare two checkouts (defect precision, recall, F1).

    # 1. score a checkout (the deployed baseline, then the branch under test); every prediction is kept
    python research/defect_gaps_eval.py score --root D:\\cvc-baseline --out research/results/defect_gaps_baseline.json
    python research/defect_gaps_eval.py score --root .               --out research/results/defect_gaps_candidate.json
    # 2. compare them
    python research/defect_gaps_eval.py compare research/results/defect_gaps_baseline.json research/results/defect_gaps_candidate.json

Labels come from this repository's evaluation/ files (high-confidence rows only, one row per distinct review text; the held-out
test split is read first so that no test review is counted twice). --root only chooses WHICH CODE scores them.

Sets, in the order they are read (a review text is kept in the first set that has it):
  test_v3      the 846-review held-out test the earlier rule tuning scored once
  gold_200, heldout_100, fresh, fresh2, nongadget, nongadget2   other labelled batches no rule of this change was written from
  train_v3     the labelled training rows (the earlier rules were tuned on these, so they favour the baseline)
Nothing here is used to write or select a rule: the script only counts.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import multiprocessing as mp
import os
import pathlib
import random
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SETS = [
    ("test_v3", "evaluation/annotated/test_v3.csv"),
    ("gold_200", "evaluation/gold_labels_200.csv"),
    ("heldout_100", "evaluation/heldout_labels_100.csv"),
    ("fresh", "evaluation/fresh/label_batch_fresh.csv"),
    ("fresh2", "evaluation/fresh2/label_batch_fresh2.csv"),
    ("nongadget", "evaluation/nongadget/label_batch_nongadget.csv"),
    ("nongadget2", "evaluation/nongadget/label_batch_nongadget_part2.csv"),
    ("train_v3", "evaluation/annotated/train_v3.csv"),
]
FLAGS = ("defect", "counterfeit", "safety", "not_as_described", "quality")


def norm(text: str) -> str:
    return re.sub(r"\W+", " ", (text or "").casefold()).strip()


def gold_flags(raw: str) -> set[str]:
    return {part for part in re.split(r"[,;|\s]+", (raw or "").strip().lower()) if part and part != "none"}


def load_rows() -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    for name, rel in SETS:
        path = REPO / rel
        if not path.is_file():
            continue
        for r in csv.DictReader(open(path, encoding="utf-8-sig")):
            if (r.get("confidence") or "").strip().lower() != "high" or not (r.get("flags") or "").strip():
                continue
            key = norm(r.get("review_text", ""))
            if not key or key in seen:
                continue
            seen.add(key)
            try:
                stars = int(float(r.get("stars") or 3))
            except ValueError:
                stars = 3
            rows.append({"id": f"{name}:{r['id']}", "set": name, "product": (r.get("product") or "").strip(), "stars": stars,
                         "text": r["review_text"], "gold": sorted(gold_flags(r["flags"]))})
    return rows


_model = None


def _work(args):
    root, chunk = args
    global _model
    if _model is None:
        sys.path.insert(0, str(pathlib.Path(root).resolve() / "backend" / "sentiment-analysis"))
        from defaketive_sentiment import registry

        _model = registry.load_model()
    out = {}
    for row in chunk:
        a = _model.analyze_batch([row["text"]], [row["stars"]], listing={"name": row["product"]})[0]
        tags = set(a.get("review_tags") or []) | set(a.get("review_extra_tags") or [])
        ev = (a.get("review_evidence") or {}).get("defect") or {}
        out[row["id"]] = {"pred": sorted(t for t in tags if t in FLAGS), "defect_evidence": ev.get("state")}
    return out


def score(root: str, out: str, workers: int) -> None:
    rows = load_rows()
    chunks = [rows[i::workers * 6] for i in range(workers * 6)]
    result: dict = {}
    with mp.Pool(workers) as pool:
        for part in pool.imap_unordered(_work, [(root, c) for c in chunks if c]):
            result.update(part)
    payload = {"root": str(root), "rows": [{**r, **result[r["id"]]} for r in rows]}
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(payload, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(rows)} labelled reviews scored with the code in {root}")


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    f = 2 * p * r / (p + r) if p == p and r == r and p + r else float("nan")
    return p, r, f


def counts(rows: list[dict], flag: str) -> tuple[int, int, int, int]:
    tp = sum(1 for r in rows if flag in r["gold"] and flag in r["pred"])
    fp = sum(1 for r in rows if flag not in r["gold"] and flag in r["pred"])
    fn = sum(1 for r in rows if flag in r["gold"] and flag not in r["pred"])
    tn = len(rows) - tp - fp - fn
    return tp, fp, fn, tn


def fmt(x: float) -> str:
    return "  n/a" if x != x else f"{x:5.3f}"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def paired_bootstrap(base: list[dict], cand: list[dict], flag: str, n: int = 2000, seed: int = 7) -> tuple[float, float, float]:
    """F1(candidate) - F1(baseline), 95% interval, resampling whole products (rows with no product are their own cluster)."""
    clusters: dict[str, list[int]] = {}
    for i, r in enumerate(base):
        clusters.setdefault(r["product"] or f"row{i}", []).append(i)
    keys = list(clusters)
    rng = random.Random(seed)
    diffs = []
    for _ in range(n):
        pick = [i for k in (rng.choice(keys) for _ in keys) for i in clusters[k]]
        b = prf(*counts([base[i] for i in pick], flag)[:3])[2]
        c = prf(*counts([cand[i] for i in pick], flag)[:3])[2]
        if b == b and c == c:
            diffs.append(c - b)
    diffs.sort()
    point = prf(*counts(cand, flag)[:3])[2] - prf(*counts(base, flag)[:3])[2]
    return point, diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs)) - 1]


def compare(base_path: str, cand_path: str, show: int) -> None:
    base = {r["id"]: r for r in json.load(open(base_path, encoding="utf-8"))["rows"]}
    cand = {r["id"]: r for r in json.load(open(cand_path, encoding="utf-8"))["rows"]}
    ids = [i for i in base if i in cand]
    B = [base[i] for i in ids]
    C = [cand[i] for i in ids]
    groups = {"ALL": lambda r: True, "test_v3 (held-out)": lambda r: r["set"] == "test_v3",
              "other labelled batches": lambda r: r["set"] not in ("test_v3", "train_v3"), "train_v3": lambda r: r["set"] == "train_v3"}
    print(f"{len(ids)} labelled reviews, same rows for both checkouts\n")
    print("DEFECT (precision / recall / F1; tp fp fn) -- baseline vs candidate")
    for name, pick in groups.items():
        b = [r for r in B if pick(r)]
        c = [r for r in C if pick(r)]
        bc, cc = counts(b, "defect"), counts(c, "defect")
        bp, cp = prf(*bc[:3]), prf(*cc[:3])
        print(f"  {name:<24} n={len(b):>5} positives={bc[0] + bc[2]:>4} | base {fmt(bp[0])} {fmt(bp[1])} {fmt(bp[2])} ({bc[0]},{bc[1]},{bc[2]}) | cand {fmt(cp[0])} {fmt(cp[1])} {fmt(cp[2])} ({cc[0]},{cc[1]},{cc[2]})")
    pt, lo, hi = paired_bootstrap(B, C, "defect")
    print(f"\n  paired product-bootstrap F1(cand)-F1(base), ALL rows: {pt:+.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]")
    pt2, lo2, hi2 = paired_bootstrap([r for r in B if r["set"] == "test_v3"], [r for r in C if r["set"] == "test_v3"], "defect")
    print(f"  paired product-bootstrap F1(cand)-F1(base), test_v3:  {pt2:+.4f}  95% CI [{lo2:+.4f}, {hi2:+.4f}]")
    print("\nEVERY OTHER FLAG must be identical (this change must not touch them):")
    for flag in FLAGS[1:]:
        diff = sum(1 for b, c in zip(B, C) if (flag in b["pred"]) != (flag in c["pred"]))
        print(f"  {flag:<18} rows whose prediction changed: {diff}")
    changed = [(b, c) for b, c in zip(B, C) if ("defect" in b["pred"]) != ("defect" in c["pred"])]
    gained = [(b, c) for b, c in changed if "defect" in c["pred"]]
    lost = [(b, c) for b, c in changed if "defect" in b["pred"]]
    print(f"\nROWS WHOSE DEFECT PREDICTION CHANGED: {len(changed)}  (now flagged: {len(gained)}, no longer flagged: {len(lost)})")
    for label, items in (("NOW FLAGGED", gained), ("NO LONGER FLAGGED", lost)):
        right = sum(1 for b, c in items if ("defect" in b["gold"]) == (label == "NOW FLAGGED"))
        print(f"  {label}: {len(items)} rows, the new answer agrees with the gold label in {right}")
    for label, items in (("NOW FLAGGED", gained), ("NO LONGER FLAGGED", lost)):
        for b, c in items[:show]:
            text = " ".join(b["text"].split())
            print(f"  [{label}] gold={'defect' if 'defect' in b['gold'] else 'no defect'} ({b['set']}, {b['stars']}★) {text[:200]}")


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")  # review text has stars, emoji and Filipino accents
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("score")
    a.add_argument("--root", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    b = sub.add_parser("compare")
    b.add_argument("baseline")
    b.add_argument("candidate")
    b.add_argument("--show", type=int, default=60)
    args = parser.parse_args()
    if args.cmd == "score":
        score(args.root, args.out, args.workers)
    else:
        compare(args.baseline, args.candidate, args.show)


if __name__ == "__main__":
    main()
