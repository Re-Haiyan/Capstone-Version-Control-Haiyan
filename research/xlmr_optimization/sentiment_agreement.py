"""Sentiment annotation workflow for policy v1: validate a completed sheet, score two independent sheets, build the adjudication sheet.

    python research/xlmr_optimization/sentiment_agreement.py check  annotation/final_test_sheet_A_done.csv --blank annotation/final_test_sheet_A.csv --annotator A01 --policy v1
    python research/xlmr_optimization/sentiment_agreement.py score  annotation/final_test_sheet_A_done.csv annotation/final_test_sheet_B_done.csv
    python research/xlmr_optimization/sentiment_agreement.py adjudication  A_done.csv B_done.csv   (writes adjudication_sheet.csv: only the disagreements)

Columns the annotator fills: sentiment (positive | neutral | negative | mixed | unclear), tags (any of mixed; delivery-only; no-opinion), positive_aspect,
negative_aspect, confidence (high | low), rationale. Rules checked (annotation_policy.md, v1):
  * `mixed` in sentiment means neither polarity dominates and requires the tag mixed; a dominated mixed review has the dominant polarity in sentiment plus the tag mixed.
  * the tag mixed requires both aspect fields; neutral + mixed is not allowed; the tag no-opinion needs sentiment neutral or unclear.
check   allowed values, review text unchanged against the blank sheet, missing rows, the rules above; with --annotator and --policy it appends a line (UTC time,
        annotator, policy, rows, SHA-256) to annotation/provenance_log.csv. It never changes the file and never fills a label.
score   on the reviews BOTH completed (refuses below 30): Cohen's kappa with a percentile bootstrap interval and per-class agreement for the three-class labels
        (rows both marked positive/neutral/negative), reported with and without delivery-only reviews; the separate mixed set (reviews either annotator marked
        mixed in sentiment, and agreement on the mixed tag); agreement on the delivery-only and no-opinion tags. A review is one unit: shares never exceed 100%.
adjudication  one row per disagreement in sentiment or in any tag, with both annotators' answers and EMPTY final fields. The originals are never modified.
Nothing in this script labels a review.
"""
import csv, datetime, hashlib, pathlib, random, sys
import numpy as np

SENT = {"positive", "neutral", "negative", "mixed", "unclear"}
THREE = ("negative", "neutral", "positive")
TAGS = {"mixed", "delivery-only", "no-opinion"}
CONF = {"high", "low"}
ANN = pathlib.Path(__file__).resolve().parent / "annotation"


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8-sig")))


def tags_of(r):
    return {t.strip().lower() for t in (r.get("tags") or "").split(";") if t.strip()}


def row_problems(r):
    s, c, tg = r["sentiment"].strip().lower(), r["confidence"].strip().lower(), tags_of(r)
    p = []
    if s not in SENT:
        return [f"{r['id']}: sentiment '{s}' is not allowed"]
    if c not in CONF:
        p.append(f"{r['id']}: confidence '{c}' must be high or low")
    if not tg <= TAGS:
        p.append(f"{r['id']}: unknown tag(s) {sorted(tg - TAGS)}")
    if s == "mixed" and "mixed" not in tg:
        p.append(f"{r['id']}: sentiment mixed needs the tag mixed")
    if "mixed" in tg and not (r.get("positive_aspect", "").strip() and r.get("negative_aspect", "").strip()):
        p.append(f"{r['id']}: the tag mixed needs both positive_aspect and negative_aspect")
    if "mixed" in tg and s == "neutral":
        p.append(f"{r['id']}: neutral and mixed together are not allowed (mixed means two clear opposite evaluations)")
    if "no-opinion" in tg and s not in ("neutral", "unclear"):
        p.append(f"{r['id']}: the tag no-opinion needs sentiment neutral or unclear")
    return p


def check(done, blank=None, annotator=None, policy=None):
    rows = read(done)
    problems, completed, low = [], 0, 0
    ref = {r["id"]: r for r in read(blank)} if blank else {}
    for r in rows:
        if ref:
            if r["id"] not in ref:
                problems.append(f"{r['id']}: not in the blank sheet")
            elif r["review_text"] != ref[r["id"]]["review_text"]:
                problems.append(f"{r['id']}: review text was edited")
        if not r["sentiment"].strip():
            continue
        bad = row_problems(r)
        problems += bad
        if not bad:
            completed += 1
            low += r["confidence"].strip().lower() == "low"
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
    return A, B, sorted(set(A) & set(B))


def report_three(A, B, ids, title):
    keep = [i for i in ids if A[i]["sentiment"].strip().lower() in THREE and B[i]["sentiment"].strip().lower() in THREE]
    if len(keep) < 10:
        print(f"{title}: only {len(keep)} reviews, not reported")
        return
    a = [A[i]["sentiment"].strip().lower() for i in keep]
    b = [B[i]["sentiment"].strip().lower() for i in keep]
    rng = random.Random(0)
    boots = []
    for _ in range(1000):
        idx = [rng.randrange(len(keep)) for _ in keep]
        boots.append(kappa([a[i] for i in idx], [b[i] for i in idx], THREE))
    print(f"{title}: n={len(keep)}, raw agreement {np.mean([x == y for x, y in zip(a, b)]):.3f}, Cohen's kappa {kappa(a, b, THREE):.3f} (95% {np.percentile(boots, 2.5):.3f} to {np.percentile(boots, 97.5):.3f})")
    for l in THREE:
        n = sum(x == l for x in a)
        if n:
            print(f"    {l:<9} A={n:<4} B agrees {sum(x == l and y == l for x, y in zip(a, b)) / n:.3f}")
    print("    confusion (rows A, columns B):", THREE)
    for l in THREE:
        print(f"      {l:<9}", [sum(x == l and y == m for x, y in zip(a, b)) for m in THREE])


def score(path_a, path_b):
    A, B, ids = both(path_a, path_b)
    if len(ids) < 30:
        sys.exit(f"Only {len(ids)} reviews are completed in both sheets: at least 30 are needed. Nothing reported.")
    print(f"reviews completed by both: {len(ids)} (each review is one unit; no percentage below can exceed 100%)")
    report_three(A, B, ids, "three-class, all reviews")
    no_deliv = [i for i in ids if "delivery-only" not in tags_of(A[i]) and "delivery-only" not in tags_of(B[i])]
    report_three(A, B, no_deliv, "three-class, EXCLUDING delivery-only (either annotator's tag)")
    mixed_set = [i for i in ids if A[i]["sentiment"].strip().lower() == "mixed" or B[i]["sentiment"].strip().lower() == "mixed"]
    print(f"separate mixed evaluation set (either annotator: neither polarity dominates): {len(mixed_set)} reviews; both agree: {sum(A[i]['sentiment'].strip().lower() == B[i]['sentiment'].strip().lower() == 'mixed' for i in mixed_set)}")
    for tag in sorted(TAGS):
        a = [tag in tags_of(A[i]) for i in ids]
        b = [tag in tags_of(B[i]) for i in ids]
        print(f"tag {tag:<14} A={sum(a):<4} B={sum(b):<4} raw agreement {np.mean([x == y for x, y in zip(a, b)]):.3f}, kappa {kappa(a, b, [True, False]):.3f}")
    unclear = [i for i in ids if "unclear" in (A[i]["sentiment"].strip().lower(), B[i]["sentiment"].strip().lower())]
    print(f"reviews either annotator marked unclear: {len(unclear)}")


def adjudication(path_a, path_b):
    A, B, ids = both(path_a, path_b)
    out = ANN / "adjudication_sheet.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "product", "review_text", "label_A", "tags_A", "positive_aspect_A", "negative_aspect_A", "rationale_A", "label_B", "tags_B", "positive_aspect_B", "negative_aspect_B", "rationale_B",
                    "final_label", "final_tags", "adjudicator_id", "rule_or_reason", "policy_version", "date"])
        n = 0
        for i in ids:
            if A[i]["sentiment"].strip().lower() != B[i]["sentiment"].strip().lower() or tags_of(A[i]) != tags_of(B[i]):
                a, b = A[i], B[i]
                w.writerow([i, a["product"], a["review_text"], a["sentiment"], a["tags"], a["positive_aspect"], a["negative_aspect"], a["rationale"],
                            b["sentiment"], b["tags"], b["positive_aspect"], b["negative_aspect"], b["rationale"], "", "", "", "", "", ""])
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
