"""Exploratory, historical-only five-label score for the CURRENT runtime model.

This script never changes models, thresholds, labels, source data or caches.
The 846-row historical set has been inspected during model development and its
annotation provenance is unverified. These numbers are NOT independent evidence
of an 80% target; do not use them to tune the checker.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from defaketive_sentiment import registry  # noqa: E402

FLAGS = ("defect", "counterfeit", "safety", "not_as_described", "quality")


def score_current() -> dict:
    source = ROOT / "evaluation" / "annotated" / "test_v3.csv"
    with source.open(encoding="utf-8-sig", newline="") as file:
        rows = [
            row for row in csv.DictReader(file)
            if (row.get("confidence") or "").casefold() == "high"
            and (row.get("flags") or "").strip()
        ]
    # Do not silently omit rows if the historical set changes.
    if len(rows) != 846:
        raise RuntimeError(f"Historical evaluation changed: expected 846, found {len(rows)}")
    model = registry.load_model()
    counts = {flag: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for flag in FLAGS}
    for row in rows:
        gold = {x.strip().casefold() for x in row["flags"].split(";")}
        unexpected_gold = gold - set(FLAGS) - {"none", "delivery"}
        if unexpected_gold:
            raise ValueError(f"Unexpected historical label group: {sorted(unexpected_gold)}")
        result = model.analyze(row["review_text"], float(row["stars"]), listing={"name": row["product"]})
        prediction = set(result["review_tags"]) | set(result.get("review_extra_tags") or ())
        for flag in FLAGS:
            actual = flag in gold
            pred = flag in prediction
            key = "tp" if actual and pred else "fp" if pred else "fn" if actual else "tn"
            counts[flag][key] += 1
    per = {}
    for flag, entry in counts.items():
        tp, fp, fn = entry["tp"], entry["fp"], entry["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.
        recall = tp / (tp + fn) if tp + fn else 0.
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.
        per[flag] = {**entry, "support": tp + fn, "precision": round(precision, 4),
                     "recall": round(recall, 4), "f1": round(f1, 4)}
    macro = sum(per[f]["f1"] for f in FLAGS) / len(FLAGS)
    tp = sum(per[f]["tp"] for f in FLAGS)
    fp = sum(per[f]["fp"] for f in FLAGS)
    fn = sum(per[f]["fn"] for f in FLAGS)
    micro = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.
    return {
        "historical_only": True,
        "independently_validated": False,
        "release_approved": False,
        "label_provenance": "team supplied, unverified",
        "use_for_model_selection": False,
        "rows": len(rows),
        "model_version": model.model_version,
        "model_choice": registry.configured_hazard(),
        "per_class": per,
        "macro_f1": round(macro, 4),
        "micro_f1": round(micro, 4),
    }


if __name__ == "__main__":
    # Printing aggregate counts/metrics and model version only; no text, IDs,
    # listing titles or individual predictions leave this research job.
    print(json.dumps(score_current(), sort_keys=True, indent=2))
