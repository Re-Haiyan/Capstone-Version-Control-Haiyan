"""Phase 6B: compare a separately committed GPT-6 review with original Claude v1.

This script produces a **proposed-only** overlay for every disagreement.
It NEVER rewrites labels, changes model weights, loads any frozen test,
or converts cross-AI disagreement into verified human ground truth.

python research/xlmr_optimization/phase6_annotation/compare_phase6b.py --output /tmp/phase6b
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import annotation_quality as qa

LABELS = ("negative", "neutral", "positive", "mixed", "unclear")
REVIEW_IDS = 54
# Manual triage of full-text high-salience claims. This is a REVIEW PRIORITY,
# not verified correctness and not permission to replace any training label.
CLEAR_EVIDENCE_PRIORITY = {
    "N2459": "explicit defective charger after under one month, bad-buy verdict",
    "N2372": "power bank drained while charging a phone by 8 percent",
    "N1025": "first-person headset performance and microphone evaluation",
    "N1682": "personal observation of fast smartphone performance",
}


def agreement(a: list[str], b: list[str], labels=LABELS):
    if not a or len(a) != len(b):
        raise ValueError("Inconsistent pair lengths")
    if any(x not in labels for x in (*a, *b)):
        raise ValueError("Invalid sentiment")
    n = len(a)
    matrix = [
        [sum(x == lx and y == ly for x, y in zip(a, b)) for ly in labels]
        for lx in labels
    ]
    correct = sum(matrix[i][i] for i in range(len(labels)))
    observed = correct / n
    r = [sum(row) for row in matrix]
    c = [sum(row[j] for row in matrix) for j in range(len(labels))]
    chance = sum(x * y for x, y in zip(r, c)) / (n*n)
    return {
        "count": n, "agreed": correct,
        "raw_agreement": round(observed, 6),
        "cohens_kappa": round((observed-chance)/(1-chance), 6) if chance < 1 else None,
        "labels": list(labels),
        "confusion_rows_claude_columns_gpt6": matrix,
        "original_claude_counts": dict(zip(labels, r)),
        "new_gpt6_counts": dict(zip(labels, c)),
    }


def tags(row):
    return {t.strip().lower() for t in row.get("tags", "").split(";") if t.strip()}


def compare():
    qa.verify_protected()
    roster = qa.read_csv(HERE/"phase6b_blind_ids.csv")
    second_path = HERE/"phase6b_gpt6_second_ai_v1.csv"
    second = qa.read_csv(second_path)
    if set(roster) != set(second) or len(roster) != REVIEW_IDS:
        raise ValueError("Phase 6B roster and separately locked second labels differ")
    ai_rows, _ = qa.annotate()
    original = {r["id"]: r for r in ai_rows}
    rows = []
    for rid in roster:
        a = original[rid]
        b = second[rid]
        predicted_label = b.get("sentiment", "").strip().lower()
        if predicted_label not in LABELS:
            raise ValueError(f"{rid}: invalid second-AI label")
        if b.get("confidence") not in qa.CONFIDENCE:
            raise ValueError(f"{rid}: invalid confidence")
        if not b.get("rationale", "").strip():
            raise ValueError(f"{rid}: missing rationale")
        if b.get("reviewer_type") != "ai" or b.get("reviewer_id") != "GPT6_20261115_PHASE6B":
            raise ValueError(f"{rid}: incorrect second-AI provenance")
        if b.get("policy_version") != "v1":
            raise ValueError(f"{rid}: second-AI policy cannot be changed in this run")
        bt = tags(b)
        if not bt <= qa.TAGS:
            raise ValueError(f"{rid}: invalid tags")
        if predicted_label == "mixed" and "mixed" not in bt:
            raise ValueError(f"{rid}: Mixed label requires mixed tag")
        if "mixed" in bt and (predicted_label not in ("negative", "positive", "mixed")
                             or not b.get("positive_aspect", "").strip()
                             or not b.get("negative_aspect", "").strip()):
            raise ValueError(f"{rid}: Mixed requires valid label and both aspects")
        if "no-opinion" in bt and predicted_label not in ("neutral", "unclear"):
            raise ValueError(f"{rid}: inconsistent no-opinion tag")
        ca, gb = a["label"], predicted_label
        oldtags, newtags = tags(a), bt
        change = "sentiment" if ca != gb else ("tags" if oldtags != newtags else "none")
        rows.append({
            "id": rid, "split": a["split"], "language": a["language"],
            "claude_v1_sentiment": ca,
            "gpt6_v1_sentiment": gb,
            "claude_v1_tags": ";".join(sorted(oldtags)),
            "gpt6_v1_tags": ";".join(sorted(newtags)),
            "gpt6_v1_confidence": b["confidence"],
            "gpt6_v1_positive_aspect": b["positive_aspect"],
            "gpt6_v1_negative_aspect": b["negative_aspect"],
            "gpt6_v1_rationale": b["rationale"],
            "change_type": change,
            "priority_for_human_adjudication": (
                "evidence_high" if rid in CLEAR_EVIDENCE_PRIORITY else "other_disagreement"
            ) if change != "none" else "",
            "why_prioritized": CLEAR_EVIDENCE_PRIORITY.get(rid, ""),
            "status": "proposed_not_adjudicated" if change != "none" else "second_ai_agrees_unverified",
            "human_final_label": "", "human_reviewer_id": "", "human_policy_version": "",
        })
    a = [r["claude_v1_sentiment"] for r in rows]
    b = [r["gpt6_v1_sentiment"] for r in rows]
    diag = agreement(a,b)
    changes = collections.Counter(r["change_type"] for r in rows)
    by_language = {
        key: {
            "n": sum(r["language"] == key for r in rows),
            "different_sentiment": sum(r["language"] == key and r["change_type"]=="sentiment" for r in rows),
        }
        for key in sorted({r["language"] for r in rows})
    }
    three = [r for r in rows if r["claude_v1_sentiment"] in LABELS[:3] and r["gpt6_v1_sentiment"] in LABELS[:3]]
    return {
        "method": "additional AI-to-AI agreement on a risk-selected, partly blind development sample",
        "provenance": {
            "original": "Claude Sonnet 5.5, policy v1, 2026-11-15",
            "second": "ChatGPT GPT-6, policy v1, 2026-11-15",
            "blindness_limit": "Original Claude per-ID labels not fetched during second pass; some may have appeared in earlier conversation context",
            "second_AI_sha256": hashlib.sha256(second_path.read_bytes()).hexdigest(),
        },
        "five_class": diag,
        "three_class_both": agreement(
            [r["claude_v1_sentiment"] for r in three],
            [r["gpt6_v1_sentiment"] for r in three], LABELS[:3]
        ),
        "change_types": dict(changes),
        "by_language": by_language,
        "clear_evidence_review_priorities": CLEAR_EVIDENCE_PRIORITY,
        "overlays": [r for r in rows if r["change_type"] != "none"],
        "limits": [
            "This is AI-assisted annotation, not human adjudication or a verified gold standard.",
            "The selected 54 are risk-enriched; agreement cannot estimate overall error rate.",
            "The separate GPT-6 run is partly blind, not strictly independent.",
            "Template list origin remains uncertain under S4; low-confidence opinions are NOT auto-corrections.",
            "No frozen final tests/used confirmation/heldout-v2 evaluated.",
            "Do not auto-apply proposed overlays to training, model selection or production.",
        ],
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("/tmp/phase6b-comparison"))
    args=parser.parse_args()
    result=compare()
    args.output.mkdir(parents=True,exist_ok=True)
    csv_cols=["id","split","language","claude_v1_sentiment","gpt6_v1_sentiment",
              "claude_v1_tags","gpt6_v1_tags","gpt6_v1_confidence",
              "gpt6_v1_positive_aspect","gpt6_v1_negative_aspect","gpt6_v1_rationale",
              "change_type","priority_for_human_adjudication","why_prioritized",
              "status","human_final_label","human_reviewer_id","human_policy_version"]
    with (args.output/"proposed_annotation_overlay.csv").open("w",newline="",encoding="utf-8") as file:
        writer=csv.DictWriter(file,fieldnames=csv_cols)
        writer.writeheader()
        writer.writerows(result.pop("overlays"))
    (args.output/"agreement_report.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"n":result["five_class"]["count"],
                      "agreement":result["five_class"]["raw_agreement"],
                      "kappa":result["five_class"]["cohens_kappa"],
                      "changes":result["change_types"],
                      "overlays":sum(v for k,v in result["change_types"].items() if k!="none")},indent=2))
    print("Proposals only; 0 original labels changed.")


if __name__=="__main__":
    main()
