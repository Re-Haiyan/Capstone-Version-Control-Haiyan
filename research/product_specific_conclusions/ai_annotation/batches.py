"""Product-level batches for the card and words sheets (the part of the evaluation that needs every review of a product read).

    python research/product_specific_conclusions/ai_annotation/batches.py make  [--size 5] [--out <folder>]
    python research/product_specific_conclusions/ai_annotation/batches.py merge <returned folder> --out <working folder>

`make` writes, per batch of products, a reading packet (every review of each product) and a blank return CSV. Card packets contain NO system
output. Words packets (written to a separate file) show the system's assessment and two texts, and may be used for a product only after its
card row has been returned: `merge` refuses a words row whose card row is missing. Nothing here fills a rating.

`merge` combines returned batch CSVs into card_sheet_A.csv / words_sheet_A.csv in a working folder (never in human_eval_pack/), checks every
value against the allowed ones, refuses duplicates, unknown products and changes to the pre-filled columns, and requires a `returned/provenance.json`
naming the annotator, model and date. Score the result with `final_eval_pack.py score <working folder>` (single_annotation_set provenance).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
sys.path.insert(0, str(RESEARCH))
import final_eval_pack as fp  # noqa: E402

PACK = fp.PACK


def rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write(path: Path, cols: list[str], data: list[dict]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(data)


def make(size: int, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    reviews: dict[str, list[dict]] = {}
    for r in rows(PACK / "reviews.csv"):
        reviews.setdefault(r["product_id"], []).append(r)
    card = rows(PACK / "card_sheet_A.csv")
    words = {r["product_id"]: r for r in rows(PACK / "words_sheet_A.csv")}
    count = 0
    for start in range(0, len(card), size):
        group = card[start:start + size]
        number = start // size + 1
        packet = [f"# Card batch {number:02d}: products {', '.join(r['product_id'] for r in group)}\n",
                  "Read every review of each product, then fill one row per product in `batch_%02d_card_return.csv` (assessment, serious_safety_concern, counterfeit_concern, main_reason, confidence), as `INSTRUCTIONS.md` section 1 says. No system output is in this file.\n" % number]
        for r in group:
            packet.append(f"\n## {r['product_id']}: {r['product']}\n")
            for review in reviews[r["product_id"]]:
                packet.append(f"({review['review_no']}) {review['stars']}*: {review['review_text']}\n")
        (out / f"batch_{number:02d}_card_packet.md").write_text("\n".join(packet), encoding="utf-8")
        write(out / f"batch_{number:02d}_card_return.csv", fp.CARD_COLS, [{c: (r[c] if c in ("product_id", "product") else "") for c in fp.CARD_COLS} for r in group])
        wpacket = [f"# Words batch {number:02d}: products {', '.join(r['product_id'] for r in group)}\n",
                   "Use only for products whose card row has been returned and merged. Rate each text 1-5 on seven dimensions and mark unsupported and safety_error, as `INSTRUCTIONS.md` section 3 says. Check numbers and statements against the product's reviews in the card packet.\n"]
        for r in group:
            w = words[r["product_id"]]
            wpacket.append(f"\n## {w['product_id']}: {w['product']}\nAssessment shown: {w['assessment_shown']}\nText 1: {w['text_1']}\nText 2: {w['text_2']}\n")
        (out / f"batch_{number:02d}_words_packet.md").write_text("\n".join(wpacket), encoding="utf-8")
        write(out / f"batch_{number:02d}_words_return.csv", fp.WORDS_COLS, [{c: (words[r["product_id"]][c] if c in fp.WORDS_COLS[:5] else "") for c in fp.WORDS_COLS} for r in group])
        count += 1
    return count


def merge(returned: Path, out: Path) -> dict:
    prov = returned / "provenance.json"
    if not prov.is_file():
        raise SystemExit("returned/provenance.json is missing: name the annotator, model version, interface, date and prompt. Nothing is merged.")
    data = json.loads(prov.read_text(encoding="utf-8"))
    for key in ("annotator", "model_version", "interface", "date", "prompt_file", "human_review_of_labels"):
        if not str(data.get(key, "")).strip():
            raise SystemExit(f"provenance.json: '{key}' is empty (write 'not recorded' if unknown). Nothing is merged.")
    out.mkdir(parents=True, exist_ok=True)
    result = {}
    for kind, cols, sheet_name, valid in (("card", fp.CARD_COLS, "card_sheet_A.csv", None), ("words", fp.WORDS_COLS, "words_sheet_A.csv", None)):
        base = {r["product_id"]: r for r in rows(PACK / sheet_name)}
        merged: dict[str, dict] = {}
        for path in sorted(returned.glob(f"batch_*_{kind}_return.csv")):
            for r in rows(path):
                pid = r["product_id"]
                if pid not in base:
                    raise SystemExit(f"{path.name}: unknown product {pid}")
                if pid in merged:
                    raise SystemExit(f"{path.name}: product {pid} returned twice")
                fixed = fp.CARD_COLS[:2] if kind == "card" else fp.WORDS_COLS[:5]
                if any(r[c] != base[pid][c] for c in fixed):
                    raise SystemExit(f"{path.name}: a pre-filled column of {pid} was changed")
                if not any(r[c].strip() for c in cols if c not in fixed):
                    continue  # an untouched row stays blank (pending), never guessed
                if kind == "card" and r["assessment"].strip() not in fp.CARDS:
                    raise SystemExit(f"{path.name}: {pid} assessment '{r['assessment']}' is not one of {fp.CARDS}")
                if kind == "words":
                    for c in fp.CRITERIA:
                        for n in (1, 2):
                            if r[f"{c}_{n}"].strip() not in {"1", "2", "3", "4", "5"}:
                                raise SystemExit(f"{path.name}: {pid} {c}_{n} must be 1 to 5")
                    for x in ("unsupported", "safety_error"):
                        for n in (1, 2):
                            if r[f"{x}_{n}"].strip().lower() not in ("yes", "no"):
                                raise SystemExit(f"{path.name}: {pid} {x}_{n} must be yes or no")
                merged[pid] = r
        if kind == "words":
            cards_done = {r["product_id"] for r in rows(out / "card_sheet_A.csv") if r["assessment"].strip()}
            missing = sorted(set(merged) - cards_done)
            if missing:
                raise SystemExit(f"words rows returned for {missing} before their card rows: the words sheet shows the system's assessment, so the card is done first. Nothing is merged.")
        write(out / sheet_name, cols, [merged.get(pid, base[pid]) for pid in base])
        result[kind] = {"products_returned": len(merged), "products_total": len(base)}
    (out / "provenance.json").write_text(json.dumps({"mode": "single_annotation_set", "annotator_A": {"label": "Team Label 1", "type": "ai_assisted", "annotator": data["annotator"], "model_version": data["model_version"], "interface": data["interface"], "dates": data["date"], "prompt_file": data["prompt_file"], "human_review_of_labels": data["human_review_of_labels"]}, "annotator_B": None}, indent=1), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("make")
    m.add_argument("--size", type=int, default=5)
    m.add_argument("--out", type=Path, default=HERE / "batches")
    g = sub.add_parser("merge")
    g.add_argument("returned", type=Path)
    g.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "make":
        print(make(args.size, args.out), "batches written to", args.out)
    else:
        print(json.dumps(merge(args.returned, args.out)))
