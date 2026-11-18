#!/usr/bin/env python3
"""Evaluate opt-in category sentiment suggestions without activating them.

This is a *historical, non-independent research pilot*. Its labels are
team-supplied SILVER with unverified provenance. Probability cache may not
be cryptographically bound to current deployed ONNX. Results cannot qualify
a production sentiment correction. No raw review text is logged or exported.

Expected columns: id, stars, product, review_text, sentiment, flags, confidence.
A proposal is scored as an actual replacement *offline only*, on all rows,
not just cases it changes, versus the frozen XLM-R cached probabilities.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import math
import os
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/sentiment-analysis"))
from defaketive_sentiment import category_sentiment  # noqa: E402

LABELS = ("negative", "neutral", "positive")
CACHE = ROOT / "research/cache/sentiment_probs.json"


def score(gold: list[str], predicted: list[str]) -> dict:
    if not gold or len(gold) != len(predicted):
        raise ValueError("Cannot compute valid evaluation without paired predictions")
    counts = {}
    for label in LABELS:
        tp = sum(a == label and b == label for a, b in zip(gold, predicted))
        fp = sum(a != label and b == label for a, b in zip(gold, predicted))
        fn = sum(a == label and b != label for a, b in zip(gold, predicted))
        p = tp / (tp + fp) if tp + fp else 0
        r = tp / (tp + fn) if tp + fn else 0
        counts[label] = {
            "precision": round(p, 4), "recall": round(r, 4),
            "f1": round(2 * p * r / (p + r), 4) if p + r else 0,
            "support": sum(x == label for x in gold),
        }
    return {
        "n": len(gold),
        "accuracy": round(sum(a == b for a, b in zip(gold, predicted)) / len(gold), 4),
        "macro_f1": round(sum(v["f1"] for v in counts.values()) / len(LABELS), 4),
        "by_class": counts,
    }


def bootstrap(rows: list[dict], repetitions: int = 400) -> list[float] | None:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["product_key"]].append(row)
    if len(groups) < 15:
        return None
    names = sorted(groups)
    rng = random.Random(20261118)
    deltas = []
    for _ in range(repetitions):
        picked = [rng.choice(names) for _ in names]
        sample = [row for key in picked for row in groups[key]]
        gold = [r["gold"] for r in sample]
        baseline = score(gold, [r["baseline"] for r in sample])["macro_f1"]
        proposed = score(gold, [r["proposed"] for r in sample])["macro_f1"]
        deltas.append(proposed - baseline)
    deltas.sort()
    return [round(deltas[int(p * (len(deltas) - 1))], 4) for p in (.025, .5, .975)]


def evaluate(dataset: str, probabilities: dict) -> dict:
    source = ROOT / "evaluation/annotated" / f"{dataset}.csv"
    rows: list[dict] = []
    events = Counter()
    source_count = 0
    os.environ[category_sentiment.ENV] = "shadow"
    with source.open(encoding="utf-8-sig", newline="") as f:
        for item in csv.DictReader(f):
            if str(item.get("confidence", "")).strip().lower() != "high" or not str(item.get("flags", "")).strip():
                continue
            source_count += 1
            key = item["id"]
            raw = probabilities.get(key)
            if not isinstance(raw, list) or len(raw) != 3 or any(not isinstance(v, (int,float)) or not math.isfinite(v) or v < 0 or v > 1 for v in raw):
                raise RuntimeError(f"Unverifiable XLM-R cache entry: {key}")
            gold = item["sentiment"].strip().lower()
            if gold not in LABELS:
                raise RuntimeError(f"Invalid sentiment reference at {key}")
            title = " ".join(item["product"].split())
            baseline = LABELS[max(range(3), key=lambda n: raw[n])]
            suggestion = category_sentiment.suggest(item["review_text"], {"name": title}, baseline)
            proposed = baseline
            reason = None
            if suggestion is not None and suggestion["candidate_label"] != baseline:
                proposed = suggestion["candidate_label"]
                reason = suggestion["rule"]
                events["changed_total"] += 1
                events["rule:" + reason] += 1
                events["baseline_correct_changed"] += int(baseline == gold and proposed != gold)
                events["baseline_wrong_fixed"] += int(baseline != gold and proposed == gold)
                events["both_wrong_changed"] += int(baseline != gold and proposed != gold)
                events["negative_gold_lost"] += int(gold == "negative" and baseline == "negative" and proposed != "negative")
                events["negative_gold_gained"] += int(gold == "negative" and baseline != "negative" and proposed == "negative")
            rows.append({
                "product_key": title.casefold(), "gold": gold,
                "baseline": baseline, "proposed": proposed,
                "rule": reason,
            })
    if not rows or len(rows) != source_count:
        raise RuntimeError("Incomplete paired evaluation")
    gold = [r["gold"] for r in rows]
    original = score(gold, [r["baseline"] for r in rows])
    candidate = score(gold, [r["proposed"] for r in rows])
    ci = bootstrap(rows)
    return {
        "rows": len(rows),
        "distinct_product_titles": len({r["product_key"] for r in rows}),
        "raw_xlmr": original,
        "hypothetical_rule_override": candidate,
        "macro_f1_delta": round(candidate["macro_f1"]-original["macro_f1"],4),
        "paired_product_bootstrap_macro_f1_delta_ci95": ci,
        "review_changes": dict(sorted(events.items())),
        "changes_rate": round(events["changed_total"]/len(rows), 4),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not CACHE.is_file():
        raise SystemExit("Missing historic XLM-R probability cache")
    probability = json.loads(CACHE.read_text(encoding="utf-8"))
    report = {
        "mode": "research_only_hypothetical_not_deployed",
        "label_provenance": "team_supplied_silver_unverified",
        "xlmr_probability_cache_provenance": "not_encoder_sha_bound",
        "independent_holdout": False,
        "automatic_correction_qualified": False,
        "reason_not_qualified": "No untouched human-adjudicated reference, verified probabilities, or paired safety approval",
        "training_oof_development_not_fresh": evaluate("train_v3", probability),
        "previously_inspected_historical_test_descriptive": evaluate("test_v3", probability),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("CATEGORY_SENTIMENT_RULE_AUDIT=" + json.dumps({
        "trained_historical": {
            "macro_f1_delta": report["training_oof_development_not_fresh"]["macro_f1_delta"],
            "changes": report["training_oof_development_not_fresh"]["review_changes"],
            "interval": report["training_oof_development_not_fresh"]["paired_product_bootstrap_macro_f1_delta_ci95"],
        },
        "historical_descriptive": {
            "macro_f1_delta": report["previously_inspected_historical_test_descriptive"]["macro_f1_delta"],
            "changes": report["previously_inspected_historical_test_descriptive"]["review_changes"],
            "interval": report["previously_inspected_historical_test_descriptive"]["paired_product_bootstrap_macro_f1_delta_ci95"],
        },
        "production_allowed": False,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
