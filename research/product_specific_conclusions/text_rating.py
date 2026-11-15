"""Blind sheets for judging the WORDS of a product conclusion (old generic text vs new product-specific text), and the scoring.

    python research/product_specific_conclusions/text_rating.py make [--before-rev deployment]
    python research/product_specific_conclusions/text_rating.py score sheetA_done.csv sheetB_done.csv

This is level 3b of research/product_conclusion_evaluation_protocol.md: not "is the card (Well reviewed ... Not recommended)
right", which research/conclusion_eval.py already covers, but "is what the card SAYS faithful, relevant, complete, clear,
consistent with the hazards and useful". It reuses the products and the reviews file of that protocol, so annotators who read
the reviews once can rate both questions.

`make` writes to research/product_specific_conclusions/rating/:
  sheet_A.csv, sheet_B.csv  the same products, different order, two anonymous texts per product (which is old and which is new
                            is random per product and is not shown), empty rating columns
  key_private.csv           which text was old and which new; keep it from the annotators
`score` refuses to run unless two sheets with at least MIN_PRODUCTS products rated by both annotators are given. Nothing is
invented: with no filled sheets there are no results.

Ratings, per text, 1 (worst) to 5 (best):
  factual         the numbers and plain facts are right (how many reviews, what share was positive, which complaint)
  faithful        every claim about the product is supported by the reviews the annotator read (nothing invented)
  relevant        it talks about this kind of product and what reviewers actually said about it, not generic advice
  sentiment       the mood described matches the reviews (not "mostly negative" for a mostly neutral product, and so on)
  safety          safety and authenticity reports are neither hidden nor overstated, and are not presented as verified
  clear           easy to read for an ordinary online shopper on a phone
  recommendation  the overall assessment (Well reviewed ... Not recommended) is appropriate for what the reviews show
Plus, per text, unsupported (yes/no): "does it say anything the reviews do not support?" and, per product, preferred (1, 2 or same).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
OUT = HERE / "rating"
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(HERE))

CRITERIA = ("factual", "faithful", "relevant", "sentiment", "safety", "clear", "recommendation")
MIN_PRODUCTS = 30
SHEET_COLS = ["product_id", "name"] + [f"{c}_{n}" for n in (1, 2) for c in CRITERIA] + ["unsupported_1", "unsupported_2", "preferred", "note"]
TEXT_COLS = ["product_id", "name", "assessment_shown", "text_1", "text_2"]  # the assessment is the same under both texts (the decision is unchanged)


def make(before_rev: str) -> None:
    import dashboard_utils as new
    from before_after import load_old

    old = load_old(before_rev)
    seed = ROOT / "backend" / "seed" / "saved_products.json.gz"
    by_link = {item["product"]["link"]: item["product"] for item in json.load(gzip.open(seed, "rt", encoding="utf-8"))}
    manifest = list(csv.DictReader(open(ROOT / "research" / "conclusion_eval" / "manifest_private.csv", encoding="utf-8-sig")))
    sheet_rows, key_rows = [], []
    rng = random.Random(11)
    for row in manifest:
        product = by_link.get(row["link"])
        if not product:
            continue
        before, after = old.badge_view(product)["conclusion"], new.badge_view(product, aspects=True)["conclusion"]
        if not before or not after:
            continue
        texts = [("old", f"{before['lead']} {before['summary']}"), ("new", f"{after['lead']} {after['summary']}")]
        rng.shuffle(texts)
        sheet_rows.append({"product_id": row["product_id"], "name": product["name"][:100], "assessment_shown": after["assessment"], "text_1": texts[0][1], "text_2": texts[1][1]})
        key_rows.append({"product_id": row["product_id"], "text_1": texts[0][0], "text_2": texts[1][0], "decision": after["decision"]})
    OUT.mkdir(exist_ok=True)
    for label, seed_value in (("A", 1), ("B", 2)):
        order = list(range(len(sheet_rows)))
        random.Random(seed_value).shuffle(order)
        with open(OUT / f"sheet_{label}.csv", "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=TEXT_COLS + SHEET_COLS[2:])
            writer.writeheader()
            for i in order:
                writer.writerow({**sheet_rows[i], **{c: "" for c in SHEET_COLS[2:]}})
    with open(OUT / "key_private.csv", "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["product_id", "text_1", "text_2", "decision"])
        writer.writeheader()
        writer.writerows(key_rows)
    print(f"wrote {len(sheet_rows)} products to {OUT}")


def _read(path: Path) -> dict[str, dict[str, str]]:
    with open(path, encoding="utf-8-sig") as fh:
        return {row["product_id"]: row for row in csv.DictReader(fh)}


def _complete(row: dict[str, str]) -> bool:
    return all(row.get(f"{c}_{n}", "").strip() in "12345" and row.get(f"{c}_{n}", "").strip() for c in CRITERIA for n in (1, 2)) and row.get("unsupported_1", "").strip().lower() in ("yes", "no") and row.get("unsupported_2", "").strip().lower() in ("yes", "no")


def weighted_kappa(a: list[int], b: list[int], categories: int = 5) -> float:
    n = len(a)
    observed = [[0] * categories for _ in range(categories)]
    for x, y in zip(a, b):
        observed[x - 1][y - 1] += 1
    rows = [sum(r) for r in observed]
    cols = [sum(observed[i][j] for i in range(categories)) for j in range(categories)]
    weight = lambda i, j: ((i - j) / (categories - 1)) ** 2
    obs = sum(weight(i, j) * observed[i][j] for i in range(categories) for j in range(categories)) / n
    exp = sum(weight(i, j) * rows[i] * cols[j] for i in range(categories) for j in range(categories)) / (n * n)
    return 1.0 if exp == 0 else 1 - obs / exp


def score(path_a: Path, path_b: Path) -> dict:
    a, b, key = _read(path_a), _read(path_b), _read(OUT / "key_private.csv")
    both = [pid for pid in key if pid in a and pid in b and _complete(a[pid]) and _complete(b[pid])]
    if len(both) < MIN_PRODUCTS:
        raise SystemExit(f"Only {len(both)} products are completely rated by both annotators; at least {MIN_PRODUCTS} are needed. Nothing is scored.")

    def version_scores(sheet: dict[str, dict[str, str]], pid: str, criterion: str) -> dict[str, int]:
        k = key[pid]
        return {k["text_1"]: int(sheet[pid][f"{criterion}_1"]), k["text_2"]: int(sheet[pid][f"{criterion}_2"])}

    result: dict = {"products": len(both), "criteria": {}}
    rng = random.Random(5)
    for criterion in CRITERIA:
        per = {"old": [], "new": []}
        diffs = []
        for pid in both:
            sa, sb = version_scores(a, pid, criterion), version_scores(b, pid, criterion)
            for version in ("old", "new"):
                per[version].append((sa[version] + sb[version]) / 2)
            diffs.append((sa["new"] + sb["new"]) / 2 - (sa["old"] + sb["old"]) / 2)
        boot = sorted(statistics.fmean(rng.choices(diffs, k=len(diffs))) for _ in range(2000))
        agree = [version_scores(a, pid, criterion)[v] for pid in both for v in ("old", "new")], [version_scores(b, pid, criterion)[v] for pid in both for v in ("old", "new")]
        result["criteria"][criterion] = {
            "old_mean": round(statistics.fmean(per["old"]), 2),
            "new_mean": round(statistics.fmean(per["new"]), 2),
            "mean_difference_new_minus_old": round(statistics.fmean(diffs), 2),
            "difference_95_percent_interval": [round(boot[50], 2), round(boot[1949], 2)],
            "annotator_weighted_kappa": round(weighted_kappa(*agree), 2),
        }
    for version in ("old", "new"):
        flagged = []
        for pid in both:
            k = key[pid]
            for sheet in (a, b):
                column = "unsupported_1" if k["text_1"] == version else "unsupported_2"
                flagged.append(sheet[pid][column].strip().lower() == "yes")
        result[f"{version}_text_with_an_unsupported_claim"] = round(sum(flagged) / len(flagged), 3)
    prefs = {"new": 0, "old": 0, "same": 0}
    for pid in both:
        k = key[pid]
        for sheet in (a, b):
            choice = sheet[pid]["preferred"].strip().lower()
            prefs["same" if choice == "same" else (k["text_1"] if choice == "1" else k["text_2"] if choice == "2" else "same")] += 1
    result["preferred"] = prefs
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    make_parser = sub.add_parser("make")
    make_parser.add_argument("--before-rev", default="deployment")
    score_parser = sub.add_parser("score")
    score_parser.add_argument("sheet_a", type=Path)
    score_parser.add_argument("sheet_b", type=Path)
    args = parser.parse_args()
    if args.command == "make":
        make(args.before_rev)
    else:
        print(json.dumps(score(args.sheet_a, args.sheet_b), indent=1))


if __name__ == "__main__":
    main()
