"""Inter-annotator agreement: build independent annotation sheets, then score two completed sheets.

    python research/agreement.py make
    python research/agreement.py score  sheet_A_done.csv sheet_B_done.csv
    python research/agreement.py compare sheet_A_done.csv sheet_B_done.csv      # also against the team-supplied labels

`make` writes, in research/agreement/:
  sheet_A.csv, sheet_B.csv   the SAME 300 reviews under anonymous ids (S001..S300), shuffled differently, with empty
                             label columns. No model prediction, no existing label, no stratum, no source-revealing id.
  id_map.csv                 sheet id -> original id -> stratum. KEEP THIS AWAY FROM THE ANNOTATORS.
Strata: 150 random reviews from the historical test file and 150 ambiguous or rare-label reviews from the training file
(chosen from the adjudication queue and the safety, counterfeit and delivery positives); they are mixed in the sheets.

`score` reports, per binary flag and for sentiment, on the reviews both annotators completed: raw agreement, Cohen's kappa,
positive and negative agreement, Gwet's AC1, the 2x2 table and 95% percentile-bootstrap intervals (resampling reviews),
for all reviews, for each stratum, and for the rows both marked high confidence. A review missing a label in either sheet is
left out of that statistic; fewer than 30 reviews completed in both sheets and `score` refuses to run.

`compare` adds what the provenance audit needs: each annotator against the team-supplied labels, and the two annotators
against each other, per flag. If the supplied labels are human-quality, annotator-vs-supplied agreement should be close to
annotator-vs-annotator agreement.
"""
import csv, pathlib, random, sys
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLAGS = ("defect", "counterfeit", "safety", "not_as_described", "quality", "delivery")
OUT = ROOT / "research" / "agreement"
COLS = ["id", "stars", "product", "review_text", "sentiment", "flags", "confidence"]
MIN_COMPLETED = 30


def make(seed: int = 2026, out_dir: pathlib.Path = OUT, test_path=None, train_path=None, queue_path=None):
    out_dir.mkdir(exist_ok=True)
    rng = random.Random(seed)
    test = [r for r in csv.DictReader(open(test_path or ROOT / "evaluation/annotated/test_v3.csv", encoding="utf-8-sig")) if r["confidence"].lower() == "high"]
    train = {r["id"]: r for r in csv.DictReader(open(train_path or ROOT / "evaluation/annotated/train_v3.csv", encoding="utf-8-sig"))}
    random_part = rng.sample(test, 150)
    chosen = {r["id"] for r in random_part}
    ambiguous = []
    queue = list(csv.DictReader(open(queue_path or ROOT / "research/annotation_audit_queue.csv", encoding="utf-8-sig")))
    for q in sorted(queue, key=lambda q: (-int(q["priority"]), q["id"])):
        if q["id"] in train and q["id"] not in chosen and int(q["priority"]) >= 2:
            ambiguous.append(train[q["id"]]); chosen.add(q["id"])
        if len(ambiguous) >= 90:
            break
    rare = [r for r in train.values() if r["id"] not in chosen and any(f in r["flags"] for f in ("safety", "counterfeit", "delivery"))]
    rng.shuffle(rare)
    ambiguous += rare[: 150 - len(ambiguous)]
    items = [(r, "random") for r in random_part] + [(r, "ambiguous_or_rare") for r in ambiguous]
    rng.shuffle(items)
    # anonymous ids: the original id prefix says which file (and so which stratum) a review came from
    ids = {r["id"]: f"S{n:03d}" for n, (r, _s) in enumerate(items, start=1)}
    with open(out_dir / "id_map.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh); w.writerow(["sheet_id", "original_id", "stratum"])
        for r, s in items:
            w.writerow([ids[r["id"]], r["id"], s])
    for name, order_seed in (("A", 1), ("B", 2)):
        shuffled = items[:]; random.Random(order_seed).shuffle(shuffled)
        with open(out_dir / f"sheet_{name}.csv", "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh); w.writerow(COLS)
            for r, _s in shuffled:
                w.writerow([ids[r["id"]], r["stars"], " ".join(r["product"].split()), r["review_text"], "", "", ""])
    with open(ROOT / "research" / "annotator_agreement_template.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh); w.writerow(COLS + ["annotator"])
        for r, _s in items[:5]:
            w.writerow([ids[r["id"]], r["stars"], " ".join(r["product"].split()), r["review_text"][:80], "", "", "", "A or B"])
    n_random = sum(1 for _r, s in items if s == "random")
    print(f"{len(items)} reviews ({n_random} random, {len(items) - n_random} ambiguous/rare) -> {out_dir}")


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
        if v == v:
            vals.append(v)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if vals else (float("nan"), float("nan"))


def _read(path):
    return {r["id"]: r for r in csv.DictReader(open(path, encoding="utf-8-sig"))}


def _done(row) -> bool:
    """A review counts as annotated only when flags and sentiment are both filled in (blank means missing, not 'none')."""
    return bool(row and row.get("flags", "").strip() and row.get("sentiment", "").strip())


def _flag(row, f) -> int:
    return 1 if f in row["flags"].replace(" ", "").lower().split(";") else 0


def completed_in_both(A, B):
    return [i for i in A if i in B and _done(A[i]) and _done(B[i])]


def score(path_a, path_b, id_map_path=None, out=print):
    A, B = _read(path_a), _read(path_b)
    if set(A) != set(B):
        out(f"Warning: the sheets do not hold the same review ids ({len(set(A) ^ set(B))} differ); only shared ids are compared.")
    ids = completed_in_both(A, B)
    if len(ids) < MIN_COMPLETED:
        sys.exit(f"Only {len(ids)} reviews are fully labelled in both sheets; agreement needs at least {MIN_COMPLETED} completed by both annotators.")
    id_map_path = id_map_path or OUT / "id_map.csv"
    strata = {r["sheet_id"]: r["stratum"] for r in csv.DictReader(open(id_map_path, encoding="utf-8-sig"))} if pathlib.Path(id_map_path).exists() else {}
    groups = [("ALL completed in both sheets", ids), ("random stratum", [i for i in ids if strata.get(i) == "random"]),
              ("ambiguous/rare stratum", [i for i in ids if strata.get(i) == "ambiguous_or_rare"]),
              ("both marked high confidence", [i for i in ids if A[i]["confidence"].strip().lower() == "high" and B[i]["confidence"].strip().lower() == "high"])]
    result = {}
    for label, sel in groups:
        if len(sel) < 20:
            continue
        out(f"\n== {label} ({len(sel)} reviews) ==")
        result[label] = {}
        for f in FLAGS:
            a = np.array([_flag(A[i], f) for i in sel]); b = np.array([_flag(B[i], f) for i in sel])
            s = stats(a, b); lo, hi = boot(a, b, kappa)
            result[label][f] = {**s, "kappa_ci95": [lo, hi]}
            out(f"{f:17} agree {s['raw_agreement']:.3f}  kappa {s['kappa']:.3f} [{lo:.2f},{hi:.2f}]  AC1 {s['gwet_ac1']:.3f}  pos-agree {s['positive_agreement']:.3f}  neg-agree {s['negative_agreement']:.3f}  {s['confusion']}")
        sa = [A[i]["sentiment"].strip().lower() for i in sel]; sb = [B[i]["sentiment"].strip().lower() for i in sel]
        raw = float(np.mean([x == y for x, y in zip(sa, sb)])); classes = sorted(set(sa) | set(sb))
        pe = sum((sa.count(c) / len(sa)) * (sb.count(c) / len(sb)) for c in classes)
        out(f"{'sentiment':17} agree {raw:.3f}  kappa {(raw - pe) / (1 - pe) if pe < 1 else float('nan'):.3f}")
    return result


def compare(path_a, path_b, id_map_path=None, out=print):
    """Annotator A vs B, and each against the team-supplied labels."""
    A, B = _read(path_a), _read(path_b)
    id_map_path = id_map_path or OUT / "id_map.csv"
    mapping = {r["sheet_id"]: r["original_id"] for r in csv.DictReader(open(id_map_path, encoding="utf-8-sig"))}
    supplied = {}
    for name in ("train_v3", "test_v3"):
        for r in csv.DictReader(open(ROOT / "evaluation/annotated" / f"{name}.csv", encoding="utf-8-sig")):
            supplied[r["id"]] = r
    ids = [i for i in completed_in_both(A, B) if mapping.get(i) in supplied]
    if len(ids) < MIN_COMPLETED:
        sys.exit(f"Only {len(ids)} reviews are fully labelled in both sheets and found in the supplied labels; need at least {MIN_COMPLETED}.")
    out(f"{len(ids)} reviews labelled by both annotators and carrying a team-supplied label")
    out(f"{'flag':17} {'A vs B':>10} {'A vs supplied':>15} {'B vs supplied':>15}   (Cohen's kappa)")
    table = {}
    for f in FLAGS:
        a = np.array([_flag(A[i], f) for i in ids]); b = np.array([_flag(B[i], f) for i in ids]); s = np.array([_flag(supplied[mapping[i]], f) for i in ids])
        table[f] = {"A_vs_B": kappa(a, b), "A_vs_supplied": kappa(a, s), "B_vs_supplied": kappa(b, s)}
        out(f"{f:17} {table[f]['A_vs_B']:10.3f} {table[f]['A_vs_supplied']:15.3f} {table[f]['B_vs_supplied']:15.3f}")
    out("Reading: if the supplied labels are human-quality, the last two columns are close to the first.")
    return table


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "make":
        make()
    elif len(sys.argv) == 4 and sys.argv[1] == "score":
        score(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 4 and sys.argv[1] == "compare":
        compare(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
