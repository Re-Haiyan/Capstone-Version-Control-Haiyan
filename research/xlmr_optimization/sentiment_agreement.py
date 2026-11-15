"""Sentiment annotation workflow: validate a completed sheet, score two independent sheets, build the adjudication sheet.

    python research/xlmr_optimization/sentiment_agreement.py check  annotation/final_test_sheet_A_done.csv --blank annotation/final_test_sheet_A.csv --annotator A01 --policy v1
    python research/xlmr_optimization/sentiment_agreement.py score  annotation/final_test_sheet_A_done.csv annotation/final_test_sheet_B_done.csv
    python research/xlmr_optimization/sentiment_agreement.py adjudication  A_done.csv B_done.csv   (writes adjudication_sheet.csv: only the disagreements)

check   allowed values (sentiment: positive | negative | neutral | mixed | unclear; confidence: high | low), review text unchanged against the blank
        sheet, rows missing a label; with --annotator and --policy it appends a line (UTC time, annotator, policy, rows, SHA-256) to
        annotation/provenance_log.csv. It never changes the file and never fills a label.
score   Cohen's kappa (with a percentile bootstrap interval), raw agreement, per-class agreement and the confusion table, on the reviews BOTH
        completed (refuses below 30). Reported for the 5 labels and for the 3-class mapping (mixed and unclear are not collapsed
        automatically: they are shown separately and the 3-class table drops them, with the count of dropped rows).
adjudication  one row per disagreement with both labels and rationales, EMPTY final_label / adjudicator / rule / date fields. The original
        sheets are never modified: the adjudicated label lives only in its own file.
Nothing in this script labels a review.
"""
import csv, datetime, hashlib, pathlib, random, sys
import numpy as np

ALLOWED = {"sentiment": {"positive", "negative", "neutral", "mixed", "unclear"}, "confidence": {"high", "low"}}
ANN = pathlib.Path(__file__).resolve().parent / "annotation"


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8-sig")))


def check(done, blank=None, annotator=None, policy=None):
    rows = read(done)
    problems, completed, low = [], 0, 0
    ref = {r["id"]: r for r in read(blank)} if blank else {}
    for r in rows:
        s, c = r["sentiment"].strip().lower(), r["confidence"].strip().lower()
        if ref:
            if r["id"] not in ref:
                problems.append(f"{r['id']}: not in the blank sheet")
            elif r["review_text"] != ref[r["id"]]["review_text"]:
                problems.append(f"{r['id']}: review text was edited")
        if not s:
            continue
        if s not in ALLOWED["sentiment"]:
            problems.append(f"{r['id']}: sentiment '{s}' is not allowed"); continue
        if c not in ALLOWED["confidence"]:
            problems.append(f"{r['id']}: confidence '{c}' must be high or low"); continue
        completed += 1
        low += c == "low"
    if ref:
        missing = set(ref) - {r["id"] for r in rows}
        if missing:
            problems.append(f"{len(missing)} rows of the blank sheet are missing from this file")
    print(f"{len(rows)} rows, {completed} completed, {low} marked low confidence, {len(problems)} problems")
    for p in problems[:30]:
        print("  ", p)
    if problems:
        return 1
    if annotator and policy:
        log = ANN / "provenance_log.csv"
        new = not log.exists()
        with open(log, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["utc_time", "annotator_id", "policy_version", "file", "rows_completed", "rows_low_confidence", "sha256"])
            w.writerow([datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), annotator, policy, pathlib.Path(done).name, completed, low, hashlib.sha256(open(done, "rb").read()).hexdigest()])
        print("recorded in", log)
    return 0


def kappa(a, b, labels):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((sum(x == l for x in a) / n) * (sum(y == l for y in b) / n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def both(path_a, path_b):
    A = {r["id"]: r for r in read(path_a) if r["sentiment"].strip()}
    B = {r["id"]: r for r in read(path_b) if r["sentiment"].strip()}
    ids = sorted(set(A) & set(B))
    return A, B, ids


def score(path_a, path_b):
    A, B, ids = both(path_a, path_b)
    if len(ids) < 30:
        sys.exit(f"Only {len(ids)} reviews are completed in both sheets: at least 30 are needed. Nothing reported.")
    a = [A[i]["sentiment"].strip().lower() for i in ids]; b = [B[i]["sentiment"].strip().lower() for i in ids]
    labels = sorted(ALLOWED["sentiment"])
    rng = random.Random(0)
    boots = []
    for _ in range(1000):
        idx = [rng.randrange(len(ids)) for _ in ids]
        boots.append(kappa([a[i] for i in idx], [b[i] for i in idx], labels))
    print(f"reviews completed by both: {len(ids)}")
    print(f"5-label: raw agreement {np.mean([x == y for x, y in zip(a, b)]):.3f}, Cohen's kappa {kappa(a, b, labels):.3f} (95% {np.percentile(boots, 2.5):.3f} to {np.percentile(boots, 97.5):.3f})")
    keep = [i for i, (x, y) in enumerate(zip(a, b)) if x in ("positive", "negative", "neutral") and y in ("positive", "negative", "neutral")]
    a3, b3 = [a[i] for i in keep], [b[i] for i in keep]
    print(f"3-class (positive/negative/neutral only; {len(ids) - len(keep)} rows with mixed or unclear dropped): n={len(keep)}, raw {np.mean([x == y for x, y in zip(a3, b3)]):.3f}, kappa {kappa(a3, b3, ['negative', 'neutral', 'positive']):.3f}")
    print("per class (annotator A labelled it: share where B agrees):")
    for l in labels:
        n = sum(x == l for x in a)
        if n:
            print(f"  {l:<9} A={n:<4} B agrees {sum(x == l and y == l for x, y in zip(a, b)) / n:.3f}")
    print("confusion (rows A, columns B):", labels)
    for l in labels:
        print(f"  {l:<9}", [sum(x == l and y == m for x, y in zip(a, b)) for m in labels])


def adjudication(path_a, path_b):
    A, B, ids = both(path_a, path_b)
    out = ANN / "adjudication_sheet.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "product", "review_text", "label_A", "rationale_A", "label_B", "rationale_B", "final_label", "adjudicator_id", "rule_or_reason", "policy_version", "date"])
        n = 0
        for i in ids:
            if A[i]["sentiment"].strip().lower() != B[i]["sentiment"].strip().lower():
                w.writerow([i, A[i]["product"], A[i]["review_text"], A[i]["sentiment"], A[i]["rationale"], B[i]["sentiment"], B[i]["rationale"], "", "", "", "", ""])
                n += 1
    print(f"{n} disagreements of {len(ids)} written to {out}; the original sheets are untouched")


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    opts = {a: args[i + 1] for i, a in enumerate(args) if a.startswith("--")}
    files = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or not args[i - 1].startswith("--"))]
    if cmd == "check":
        sys.exit(check(files[0], opts.get("--blank"), opts.get("--annotator"), opts.get("--policy")))
    elif cmd == "score":
        score(*files[:2])
    elif cmd == "adjudication":
        adjudication(*files[:2])
