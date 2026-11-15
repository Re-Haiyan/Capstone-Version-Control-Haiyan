"""Reproducible AI-only *descriptive* evaluation. No human reference is implied.

Usage:
  python research/product_specific_conclusions/ai_annotation/gpt6_qa_20261115/ai_only_audit.py
  python research/product_specific_conclusions/ai_annotation/gpt6_qa_20261115/ai_only_audit.py --json

The GPT-6 card annotator saw the system output and sampled review excerpts.
Its labels are not independent ground truth. In particular, card agreement is
NOT accuracy. Flag totals are a QA review queue, not verified error rates.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent.parent / "human_eval_pack"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def audit() -> dict:
    cards = read_csv(HERE / "card_preannotations_ai.csv")
    texts = read_csv(HERE / "summary_triage_ai.csv")
    system_rows = read_csv(PACK / "words_sheet_A.csv")

    # Refuse silent row dropping, double counting, or label substitution.
    system = {r["product_id"]: r for r in system_rows}
    card_ids = [r["product_id"] for r in cards]
    if len(system) != 35 or len(system_rows) != 35 or len(card_ids) != 35:
        raise ValueError("Unexpected pack size: expected exactly 35 products")
    if len(set(card_ids)) != 35 or set(card_ids) != set(system):
        raise ValueError("Card product IDs must exactly equal the locked evaluation pack")

    summary_ids = [r["summary_id"] for r in texts]
    expected_summaries = {f"{pid}-T{i}" for pid in system for i in (1, 2)}
    if len(texts) != 70 or len(set(summary_ids)) != 70 or set(summary_ids) != expected_summaries:
        raise ValueError("Expected exactly two summary triage rows per product")

    disagreements = []
    matches = 0
    classes = Counter()
    confidence = Counter()
    safety_yes = 0
    counterfeit_yes = 0
    for card in sorted(cards, key=lambda r: r["product_id"]):
        pid = card["product_id"]
        declared = system[pid]["assessment_shown"]
        provisional = card["assessment"]
        classes[provisional] += 1
        confidence[card["confidence"]] += 1
        safety_yes += card["serious_safety_concern"].lower() == "yes"
        counterfeit_yes += card["counterfeit_concern"].lower() == "yes"
        if provisional == declared:
            matches += 1
        else:
            disagreements.append({
                "product_id": pid,
                "system_assessment": declared,
                "ai_provisional_assessment": provisional,
                "ai_confidence": card["confidence"],
            })

    # Both wordings share a per-product issue flag. Product and summary counts
    # are reported separately so an issue is not mistaken for two observations.
    flags_by_product = {}
    per_summary_priority = Counter()
    for row in texts:
        pid = row["product_id"]
        per_summary_priority[row["priority"]] += 1
        if pid in flags_by_product:
            if (flags_by_product[pid]["priority"] != row["priority"] or
                    flags_by_product[pid]["issue_codes"] != row["issue_codes"]):
                raise ValueError(f"Risk flags differ across two text variants for {pid}")
        else:
            flags_by_product[pid] = {
                "priority": row["priority"],
                "issue_codes": row["issue_codes"],
            }

    product_priorities = Counter(row["priority"] for row in flags_by_product.values())
    safety_suspect = sorted(
        pid for pid, row in flags_by_product.items()
        if "SUSPECT_UNSUPPORTED_SAFETY" in row["issue_codes"].split(";")
    )

    return {
        "evaluation_type": "AI-assisted non-blind descriptive quality audit",
        "is_independent_human_evaluation": False,
        "human_annotators": 0,
        "reference_quality": "Provisional GPT-6 judgments; selected excerpts; system output was visible",
        "total_products": len(cards),
        "total_system_summary_texts_triaged": len(texts),
        "card_agreement": {
            "matches": matches,
            "total": len(cards),
            "fraction": matches / len(cards),
            "not_accuracy": True,
            "disagreements": disagreements,
        },
        "ai_card_assessment_distribution": dict(sorted(classes.items())),
        "ai_card_confidence_distribution": dict(sorted(confidence.items())),
        "ai_card_safety_yes": safety_yes,
        "ai_card_counterfeit_yes": counterfeit_yes,
        "summary_triage_priorities_by_product": dict(sorted(product_priorities.items())),
        "summary_triage_priorities_by_text": dict(sorted(per_summary_priority.items())),
        "suspected_unsupported_safety_products": safety_suspect,
        "verified_safety_error_count": None,
        "factual_accuracy": None,
        "claim_precision": None,
        "feature_recall": None,
        "word_quality_mean": None,
        "note": ("Counts reflect AI QA flags, not confirmed mistakes or independent "
                 "reference labels. Historical Phase 3 metrics are separate."),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print structured descriptive results")
    args = parser.parse_args()
    result = audit()
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    agreement = result["card_agreement"]
    print("AI-ASSISTED, NON-BLIND: descriptive audit only; NOT human validation")
    print(f"Products: {result['total_products']} | Summaries triaged: {result['total_system_summary_texts_triaged']}")
    print(f"Card agreement with system: {agreement['matches']}/{agreement['total']} "
          f"({agreement['fraction']:.1%}); NOT accuracy")
    print("Disagreements:", ", ".join(d["product_id"] for d in agreement["disagreements"]))
    print("Safety-risk review queue, by product:", result["summary_triage_priorities_by_product"])
    print("Safety 'yes' in AI cards:", result["ai_card_safety_yes"],
          "| Counterfeit concerns 'yes':", result["ai_card_counterfeit_yes"])
    print("No independent ground truth, no validated P/R/F1 or 1–5 word ratings.")


if __name__ == "__main__":
    main()
