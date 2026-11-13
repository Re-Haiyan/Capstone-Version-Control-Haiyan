"""Score the checker on the labelled non-gadget batch, product title included (the way the app runs it).

    backend/.venv/Scripts/python.exe evaluation/score_nongadget.py evaluation/label_batch_nongadget.csv
    ... --no-category        read every review as the old checker did, with no product category (for comparison)
    ... --split test         score only the half kept back for testing (tune the rules on --split dev)
    ... --misses             also list every false positive and false negative

The file is the batch after labelling: columns id, stars, product, review_text, sentiment, flags, confidence.
flags is ';'-separated from defect, counterfeit, safety, not_as_described, quality, or "none".
Only rows labelled confidence=high are scored, as in score.py. The key file (same name + _key.csv) says each row's
category, group, source (random or keyword) and split.
"""
import argparse
import collections
import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))

FLAGS = ("defect", "counterfeit", "safety", "not_as_described", "quality")
GOLD_VALUES = set(FLAGS) | {"none", ""}


def predicted_flags(analysis):
    tags = set(analysis.get("review_tags") or []) | set(analysis.get("review_extra_tags") or [])
    return {flag for flag in FLAGS if flag in tags}


def table(title, counts):
    print(f"\n{title}")
    print(f"  {'label':17} {'n+':>4} {'tp':>4} {'fp':>4} {'fn':>4}   precision  recall   F1")
    for flag in FLAGS:
        c = counts[flag]
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        precision = tp / (tp + fp) if tp + fp else float("nan")
        recall = tp / (tp + fn) if tp + fn else float("nan")
        f1 = 2 * precision * recall / (precision + recall) if precision == precision and recall == recall and precision + recall else float("nan")
        note = "   (fewer than 5 positives: do not read the score)" if tp + fn < 5 else ""
        print(f"  {flag:17} {tp + fn:>4} {tp:>4} {fp:>4} {fn:>4}   {precision:9.2f} {recall:6.2f} {f1:5.2f}{note}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("batch")
    parser.add_argument("--split", choices=("dev", "test"))
    parser.add_argument("--no-category", action="store_true")
    parser.add_argument("--misses", action="store_true")
    args = parser.parse_args()

    path = pathlib.Path(args.batch)
    key_path = path.with_name(path.stem + "_key.csv")
    key = {r["id"]: r for r in csv.DictReader(open(key_path, encoding="utf-8-sig"))}
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    unlabelled = [r for r in rows if not r["flags"].strip() or not r["sentiment"].strip()]
    if unlabelled:
        print(f"{len(unlabelled)} of {len(rows)} rows have no sentiment or flags yet and are skipped.")
    rows = [r for r in rows if r["flags"].strip() and r["sentiment"].strip() and r["confidence"].strip().lower() == "high"]
    for r in rows:
        bad = set(r["flags"].replace(" ", "").split(";")) - GOLD_VALUES
        if bad:
            sys.exit(f"{r['id']}: unknown flag {sorted(bad)}; use {', '.join(FLAGS)} or none")
    if args.split:
        rows = [r for r in rows if key[r["id"]]["split"] == args.split]
    if not rows:
        sys.exit("No labelled high-confidence rows to score.")

    from defaketive_sentiment import product_category, registry

    product_category.PRODUCT_CATEGORY_OFF = args.no_category
    model = registry.load_model()
    overall = {flag: collections.Counter() for flag in FLAGS}
    by_group: dict[str, dict] = collections.defaultdict(lambda: {flag: collections.Counter() for flag in FLAGS})
    right = 0
    misses = []
    for row in rows:
        listing = {"name": row["product"]}
        analysis = model.analyze_batch([row["review_text"]], [int(row["stars"])], listing=listing)[0]
        right += analysis.get("label") == row["sentiment"]
        gold = {f for f in row["flags"].replace(" ", "").split(";") if f in FLAGS}
        predicted = predicted_flags(analysis)
        group = key[row["id"]]["group"]
        for flag in FLAGS:
            outcome = ("tp" if flag in predicted else "fn") if flag in gold else ("fp" if flag in predicted else "tn")
            overall[flag][outcome] += 1
            by_group[group][flag][outcome] += 1
            if outcome in ("fn", "fp"):
                misses.append(f"{flag} {outcome} [{key[row['id']]['category']}] {row['review_text'][:110]}")

    mode = "no category (old behaviour)" if args.no_category else "with the product category"
    print(f"{path.name}: {len(rows)} high-confidence rows, {mode}" + (f", split {args.split}" if args.split else ""))
    print(f"sentiment accuracy {right}/{len(rows)} = {right / len(rows):.3f}")
    table("ALL", overall)
    for group in sorted(by_group):
        table(f"group {group}", by_group[group])
    if args.misses:
        print("\n" + "\n".join(misses))


main()
