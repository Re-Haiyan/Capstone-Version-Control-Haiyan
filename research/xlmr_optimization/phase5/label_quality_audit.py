"""Audit source fidelity and Phase 4 label distribution without model scoring.

Outputs aggregate statistics and a *non-adjudicated* review-ID queue.
No final test, Phase 3 confirmation, held-out v2 or production artifacts are read.
"""
import argparse
import collections
import csv
import hashlib
import json
import random
import re
from pathlib import Path

X = Path(__file__).resolve().parents[1]
PAIRS = [
    ("dev", "dev_pool_sheet.csv", "dev_pool_sheet_ai_v1.csv", 400),
    ("candidates", "neutral_candidate_pool.csv", "neutral_candidate_pool_ai_v1.csv", 3000),
]
ALLOWED = {"positive", "negative", "neutral", "mixed", "unclear"}
FIRST = re.compile(r"\b(?:i|ako|ko|akin|namin|nagamit|nabili|nakuha|sakin|sa akin|my|me|we|nag-?order|order ko)\b", re.I)
OPINION = re.compile(r"\b(?:i|ako|ko|nagamit|ginamit|nagustuhan|nasubukan|tried|tested|works|working|sulit|maganda|ganda|satisfied|disappointed|quality)\b", re.I)
SEG = re.compile(r"[^.!?,;]+")


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        data = list(csv.DictReader(f))
    if any(not row.get("id") for row in data) or len({row["id"] for row in data}) != len(data):
        raise ValueError("Missing/duplicate ids: " + str(path))
    return {row["id"]: row for row in data}


def audit_pair(root, split, source, labels, expected):
    base = read(root / "annotation" / source)
    annotated = read(root / "annotation" / "ai_labelled" / labels)
    if len(base) != expected or set(base) != set(annotated):
        raise ValueError(f"{split}: incomplete or unmatched IDs")
    items = []
    for rid, row in annotated.items():
        original = base[rid]
        for field in ("review_text", "product", "language_hint"):
            if original.get(field) != row.get(field):
                raise ValueError(f"{split}:{rid}: original {field} altered")
        sentiment = row.get("sentiment", "").lower().strip()
        if sentiment not in ALLOWED:
            raise ValueError(f"{split}:{rid}: invalid sentiment")
        tags = set(row.get("tags", "").lower().split(";"))
        if "no-opinion" in tags and sentiment != "neutral":
            raise ValueError(f"{split}:{rid}: inconsistent no-opinion tag")
        if row.get("confidence", "").lower() not in {"high", "low"}:
            raise ValueError(f"{split}:{rid}: missing confidence")
        text = row["review_text"]
        parts = [s.strip() for s in SEG.findall(text) if s.strip()]
        tag_shape = len(parts) >= 3 and all(len(s.split()) <= 12 for s in parts) and not FIRST.search(text)
        flags = []
        if sentiment == "neutral" and "no-opinion" in tags and len(text) > 170 and OPINION.search(text[170:]):
            flags.append("check_unread_tail")
        if sentiment == "neutral" and "no-opinion" in tags and tag_shape:
            flags.append("tag_list_s4_boundary")
        if sentiment == "positive" and tag_shape:
            flags.append("positive_tag_list_s4_boundary")
        if sentiment == "neutral" and row.get("language_hint", "").lower() in ("filipino", "taglish"):
            flags.append("undersampled_language")
        if row["confidence"].lower() == "low":
            flags.append("low_confidence")
        items.append(dict(id=rid, split=split, label=sentiment,
                          language=row.get("language_hint", "").lower(),
                          product=row["product"], flags=flags, length=len(text),
                          no_opinion="no-opinion" in tags, tag_shape=tag_shape,
                          hash=hashlib.sha256(" ".join(text.lower().split()).encode()).hexdigest()))
    return items


def select_queue(rows):
    rng = random.Random(20261115)
    requirements = [
        ("unread_tail", 30, lambda r: "check_unread_tail" in r["flags"]),
        ("neutral_tags", 30, lambda r: "tag_list_s4_boundary" in r["flags"]),
        ("positive_tags", 30, lambda r: "positive_tag_list_s4_boundary" in r["flags"]),
        ("filipino_taglish_neutral", 25, lambda r: "undersampled_language" in r["flags"]),
        ("opinion_controls", 25, lambda r: r["label"] in ("negative", "positive") and not r["tag_shape"]),
    ]
    chosen = set()
    output = []
    for bucket, count, test in requirements:
        options = sorted((r for r in rows if test(r) and r["id"] not in chosen), key=lambda r: r["id"])
        rng.shuffle(options)
        for r in options[:count]:
            chosen.add(r["id"])
            output.append(dict(id=r["id"], split=r["split"], bucket=bucket, language=r["language"],
                               flags=";".join(r["flags"]), second_label="", second_confidence="", notes=""))
    return output


def main(root, out_dir):
    rows = []
    checksums = {}
    for entry in PAIRS:
        split, raw, labelled, expected = entry
        rows.extend(audit_pair(root, *entry))
        for name, folder in [(raw, root / "annotation"), (labelled, root / "annotation" / "ai_labelled")]:
            checksums[name] = hashlib.sha256((folder / name).read_bytes()).hexdigest()
    labels = collections.Counter((r["split"], r["label"]) for r in rows)
    languages = collections.Counter((r["language"], r["label"]) for r in rows)
    flags = collections.Counter(x for r in rows for x in r["flags"])
    neu = [r for r in rows if r["label"] == "neutral"]
    neutral_noop = [r for r in neu if r["no_opinion"]]
    duplicates = collections.Counter(r["hash"] for r in rows)
    queue = select_queue(rows)
    counts = {
        "rows": len(rows), "neutral": len(neu), "neutral_no_opinion": len(neutral_noop),
        "neutral_no_opinion_share": round(len(neutral_noop) / len(neu), 5),
        "neutral_no_opinion_product_titles": len({r["product"] for r in neutral_noop}),
        "long_neutral_no_opinion": sum(r["length"] > 170 for r in neutral_noop),
        "cross_sheet_exact_duplicates_excess": sum(v - 1 for v in duplicates.values() if v > 1),
        "label_by_split": {"/".join(k): v for k, v in sorted(labels.items())},
        "label_by_language": {"/".join(k): v for k, v in sorted(languages.items())},
        "review_priorities": dict(flags), "second_annotator_queue_size": len(queue),
    }
    report = {
        "counts": counts, "source_sha256": checksums, "policy": "v1 unchanged; S4 buyer-selected tag interpretation pending",
        "annotator": "Claude Sonnet 5.5; one AI annotator, no independent human or ChatGPT labels",
        "excluded": ["frozen test", "Phase 3 confirmation", "held-out v2"],
        "limitations": [
            "Flags are heuristics, not confirmed mislabels.",
            "Source text identity does not prove the annotator saw full text.",
            "Queue IDs require a coordinator to provide blinded source text; original labels are not shown.",
            "No model F1, label agreement or independent performance is calculated.",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (out_dir / "second_annotator_ids.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "split", "bucket", "language", "flags", "second_label", "second_confidence", "notes"])
        w.writeheader()
        w.writerows(queue)
    print(json.dumps(counts, indent=2))
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=X)
    p.add_argument("--out-dir", type=Path, default=Path("/tmp/phase5-audit"))
    a = p.parse_args()
    main(a.root, a.out_dir)
