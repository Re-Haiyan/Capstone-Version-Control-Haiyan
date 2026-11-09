"""Create auditable machine proposals, NEVER human ground truth.

Run with backend/.venv/Scripts/python.exe scripts/annotate_reviews.py.
Output is private local data, excluded from Git. Existing outputs are refused.
"""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from defaketive_sentiment.aspects import analyze_aspects, VERSION
from defaketive_sentiment import registry


def fingerprint(text):
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = re.sub(r"[^\w]+", " ", normalized).strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def split_for(text, known):
    key = fingerprint(text)
    if key in known:
        return "legacy_exposed"
    bucket = int(key[:8], 16) % 10
    return "test_candidate" if bucket == 0 else "validation" if bucket == 1 else "train"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "evaluation/review_pool_10000.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/annotation_batch_10000")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; use a new directory to preserve annotations.")
    with args.input.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or any(not row.get("id") or not row.get("review_text", "").strip() for row in rows):
        parser.error("Every row needs an ID and nonempty review_text.")
    if len({row['id'] for row in rows}) != len(rows):
        parser.error("Review IDs must be unique.")
    known = set()
    for name in ("gold_labels_200.csv", "heldout_labels_100.csv"):
        with (ROOT / "evaluation" / name).open(encoding="utf-8-sig", newline="") as handle:
            known.update(fingerprint(row["review_text"]) for row in csv.DictReader(handle))
    model = registry.load_model().sentiment
    args.output.mkdir(parents=True)
    counts = collections.Counter()
    labels = collections.Counter()
    unique = set()
    fields = ["id", "platform", "review_text", "group_id", "split", "annotation_status",
              "proposed_sentiment", "probabilities", "proposed_aspects", "priority",
              "human_sentiment", "human_aspects", "reviewer", "reviewed_at", "notes"]
    with (args.output / "annotations.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(rows, 1):
            text = row["review_text"]
            group = fingerprint(text)
            unique.add(group)
            split = split_for(text, known)
            counts[split] += 1
            item = {"id": row["id"], "platform": row.get("platform", ""), "review_text": text,
                    "group_id": group, "split": split, "annotation_status": "pending_human_review"}
            if split == "test_candidate":
                # Keep this queue blind: no model suggestions, ratings or aspects.
                item["priority"] = "blind_annotation"
            else:
                result = model.analyze(text)  # Never use star ratings as truth.
                probabilities = (result.get("classifier") or {}).get("probabilities") or {}
                values = sorted(probabilities.values(), reverse=True)
                aspects = analyze_aspects(text)
                uncertain = len(values) < 2 or values[0] < .65 or values[0] - values[1] < .15
                item.update(proposed_sentiment=result["label"], probabilities=json.dumps(probabilities),
                            proposed_aspects=json.dumps(aspects, ensure_ascii=False),
                            priority="high" if uncertain or aspects["mixed_evidence"] else "normal")
                labels[result["label"]] += 1
            writer.writerow(item)
            if index % 500 == 0:
                handle.flush()
                print(f"Prepared {index}/{len(rows)} reviews", flush=True)
    manifest = {"rows": len(rows), "unique_normalized_texts": len(unique), "splits": dict(counts),
                "proposed_sentiment_counts": dict(labels), "human_approved": 0,
                "sentiment_version": model.model_version, "aspect_version": VERSION,
                "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
                "limitations": ["Machine proposals are not gold labels or new training truth.",
                                "Test candidates are blind, but historical training overlap is unverified.",
                                "No product IDs: product-disjoint splitting cannot be guaranteed.",
                                "Near-duplicate templates require human review before evaluation.",
                                "No trained model weights were changed."]}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
