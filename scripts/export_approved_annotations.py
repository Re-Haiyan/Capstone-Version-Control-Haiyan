"""Validate human-approved annotations and export each split separately.

Does not train a model; test candidates never enter training exports.
"""
import argparse
import csv
import json
from pathlib import Path

ASPECTS = {"delivery", "packaging", "seller_service", "price", "quality", "functionality"}
LABELS = {"positive", "negative", "neutral", "mixed", "unclear"}
SPLITS = {"train", "validation", "test_candidate", "legacy_exposed"}


def validate(row):
    if row["annotation_status"] != "approved":
        return None
    if row["human_sentiment"] not in LABELS or not row["reviewer"].strip() or not row["reviewed_at"].strip():
        raise ValueError(f"{row['id']}: approval requires human label, reviewer and review date")
    if row["split"] not in SPLITS:
        raise ValueError(f"{row['id']}: invalid split")
    aspects = json.loads(row["human_aspects"])
    if not isinstance(aspects, list):
        raise ValueError(f"{row['id']}: human_aspects must be a JSON list (use [] when none)")
    for item in aspects:
        if item.get("aspect") not in ASPECTS or item.get("label") not in LABELS:
            raise ValueError(f"{row['id']}: invalid aspect or label")
        span = item.get("span")
        if (not isinstance(span, list) or len(span) != 2 or
                any(type(n) is not int for n in span) or
                not 0 <= span[0] < span[1] <= len(row["review_text"]) or
                row["review_text"][span[0]:span[1]] != item.get("text")):
            raise ValueError(f"{row['id']}: evidence must match exact character offsets")
    return {"id": row["id"], "text": row["review_text"], "sentiment": row["human_sentiment"],
            "aspects": aspects, "group_id": row["group_id"], "split": row["split"],
            "reviewer": row["reviewer"], "reviewed_at": row["reviewed_at"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new directory.")
    groups, approved, ids = {}, [], set()
    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["id"] in ids:
                raise ValueError("Duplicate review ID")
            ids.add(row["id"])
            previous = groups.setdefault(row["group_id"], row["split"])
            if previous != row["split"]:
                raise ValueError("A duplicate group crosses dataset splits")
            item = validate(row)
            if item:
                approved.append(item)
    if not approved:
        parser.error("No human-approved records. Proposals cannot be exported as training truth.")
    args.output.mkdir(parents=True)
    for split in sorted(SPLITS):
        with (args.output / f"{split}.jsonl").open("w", encoding="utf-8") as handle:
            for row in approved:
                if row["split"] == split:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Exported {len(approved)} human-approved records into separate split files.")


if __name__ == "__main__":
    main()
