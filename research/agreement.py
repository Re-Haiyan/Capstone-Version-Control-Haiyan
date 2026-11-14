"""Inter-annotator agreement: build independent annotation sheets, then score two completed sheets.

    # 1. make the sheets (no model output, strata hidden from annotators)
    python research/agreement.py make
    # 2. after two people annotate independently:
    python research/agreement.py score research/agreement/sheet_A_done.csv research/agreement/sheet_B_done.csv

`make` writes, in research/agreement/: sheet_A.csv and sheet_B.csv (identical rows, shuffled differently, empty label
columns), strata_key.csv (id -> stratum; do not give it to annotators) and research/annotator_agreement_template.csv.
Strata: 150 random reviews from the historical test file, and 150 selected as ambiguous or rare-label from the
adjudication queue (research/annotation_audit_queue.csv) and the safety/counterfeit/delivery positives of the training file.
`score` reports, per binary flag and for sentiment: raw agreement, Cohen's kappa, positive and negative agreement,
Gwet's AC1, the 2x2 confusion table and 95% percentile-bootstrap intervals (resampling reviews). Nothing is invented:
without two completed sheets `score` refuses to run.
"""
import csv, pathlib, random, sys
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLAGS = ("defect", "counterfeit", "safety", "not_as_described", "quality", "delivery")
OUT = ROOT / "research" / "agreement"
COLS = ["id", "stars", "product", "review_text", "sentiment", "flags", "confidence"]


def make(seed: int = 2026):
    OUT.mkdir(exist_ok=True)
    rng = random.Random(seed)
    test = [r for r in csv.DictReader(open(ROOT / "evaluation/annotated/test_v3.csv", encoding="utf-8-sig")) if r["confidence"].lower() == "high"]
    train = {r["id"]: r for r in csv.DictReader(open(ROOT / "evaluation/annotated/train_v3.csv", encoding="utf-8-sig"))}
    random_part = rng.sample(test, 150)
    chosen_ids = {r["id"] for r in random_part}
    ambiguous = []
    queue = list(csv.DictReader(open(ROOT / "research/annotation_audit_queue.csv", encoding="utf-8-sig")))
    for q in sorted(queue, key=lambda q: (-int(q["priority"]), q["id"])):
        if q["id"] in train and q["id"] not in chosen_ids and int(q["priority"]) >= 2:
            ambiguous.append(train[q["id"]]); chosen_ids.add(q["id"])
        if len(ambiguous) >= 90:
            break
    rare = [r for r in train.values() if r["id"] not in chosen_ids and any(f in r["flags"] for f in ("safety", "counterfeit", "delivery"))]
    rng.shuffle(rare)
    ambiguous += rare[: 150 - len(ambiguous)]
    rows = [(r, "random") for r in random_part] + [(r, "ambiguous_or_rare") for r in ambiguous]
    key = [{"id": r["id"], "stratum": s} for r, s in rows]
    for name, order_seed in (("A", 1), ("B", 2)):
        shuffled = rows[:]; random.Random(order_seed).shuffle(shuffled)
        with open(OUT / f"sheet_{name}.csv", "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh); w.writerow(COLS)
            for r, _ in shuffled:
                w.writerow([r["id"], r["stars"], " ".join(r["product"].split()), r["review_text"], "", "", ""])
    with open(OUT / "strata_key.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "stratum"]); w.writeheader(); w.writerows(key)
    with open(ROOT / "research" / "annotator_agreement_template.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh); w.writerow(COLS + ["annotator"])
        for r, _ in rows[:5]:
            w.writerow([r["id"], r["stars"], " ".join(r["product"].split()), r["review_text"][:80], "", "", "", "A or B"])
    print(f"{len(rows)} reviews: {sum(1 for _, s in rows if s == 'random')} random, {sum(1 for _, s in rows if s != 'random')} ambiguous/rare -> {OUT}")


def kappa(a: np.ndarray, b: np.ndarray) -> float:
    po = (a == b).mean(); pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float((po - pe) / (1 - pe)) if pe < 1 else float("nan")


def ac1(a: np.ndarray, b: np.ndarray) -> float:
    po = (a == b).mean(); pi = (a.mean() + b.mean()) / 2; pe = 2 * pi * (1 - pi)
    return float((po - pe) / (1 - pe)) if pe < 1 else float("nan")


def stats(a: np.ndarray, b: np.ndarray) -> dict:
    both = int(((a == 1) & (b == 1)).sum()); neither = int(((a == 0) & (b == 0)).sum()); a_only = int(((a == 1) & (b == 0)).sum()); b_only = int(((a == 0) & (b == 1)).sum())
    pos = 2 * both / (2 * both + a_only + b_only) if 2 * both + a_only + b_only else float("nan")
    neg = 2 * neither / (2 * neither + a_only + b_only) if 2 * neither + a_only + b_only else float("nan")
    return {"n": len(a), "raw_agreement": float((a == b).mean()), "kappa": kappa(a, b), "gwet_ac1": ac1(a, b), "positive_agreement": pos, "negative_agreement": neg,
            "confusion": {"both_yes": both, "A_only": a_only, "B_only": b_only, "both_no": neither}}


def boot(a, b, fn, n=1000, seed=0):
    rng = np.random.default_rng(seed); vals = []
    for _ in range(n):
        i = rng.integers(0, len(a), len(a)); v = fn(a[i], b[i])
        if v == v: vals.append(v)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if vals else (float("nan"), float("nan"))


def score(path_a, path_b):
    A = {r["id"]: r for r in csv.DictReader(open(path_a, encoding="utf-8-sig"))}
    B = {r["id"]: r for r in csv.DictReader(open(path_b, encoding="utf-8-sig"))}
    ids = [i for i in A if i in B and A[i]["flags"].strip() and B[i]["flags"].strip()]
    if len(ids) < 30:
        sys.exit(f"Only {len(ids)} reviews are labelled in both sheets; agreement needs two completed independent sheets.")
    strata = {r["id"]: r["stratum"] for r in csv.DictReader(open(OUT / "strata_key.csv", encoding="utf-8-sig"))} if (OUT / "strata_key.csv").exists() else {}
    vec = lambda R, f, i: 1 if f in R[i]["flags"].replace(" ", "").split(";") else 0
    for label, sel in (("ALL", ids), ("random", [i for i in ids if strata.get(i) == "random"]), ("ambiguous_or_rare", [i for i in ids if strata.get(i) == "ambiguous_or_rare"])):
        if len(sel) < 20:
            continue
        print(f"\n== {label} ({len(sel)} reviews) ==")
        for f in FLAGS:
            a = np.array([vec(A, f, i) for i in sel]); b = np.array([vec(B, f, i) for i in sel])
            s = stats(a, b); lo, hi = boot(a, b, kappa)
            print(f"{f:17} agree {s['raw_agreement']:.3f}  kappa {s['kappa']:.3f} [{lo:.2f},{hi:.2f}]  AC1 {s['gwet_ac1']:.3f}  pos-agree {s['positive_agreement']:.3f}  neg-agree {s['negative_agreement']:.3f}  {s['confusion']}")
        sa = [A[i]["sentiment"].strip().lower() for i in sel]; sb = [B[i]["sentiment"].strip().lower() for i in sel]
        raw = float(np.mean([x == y for x, y in zip(sa, sb)])); classes = sorted(set(sa) | set(sb))
        pe = sum((sa.count(c) / len(sa)) * (sb.count(c) / len(sb)) for c in classes)
        print(f"{'sentiment':17} agree {raw:.3f}  kappa {(raw - pe) / (1 - pe) if pe < 1 else float('nan'):.3f}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "make":
        make()
    elif len(sys.argv) == 4 and sys.argv[1] == "score":
        score(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
