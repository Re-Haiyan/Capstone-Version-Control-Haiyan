"""Phase 6D: compare 200 *locked* GPT-6 AI labels with Claude v1 development labels.

Scores AI-to-AI annotation consistency only. No model inference, human gold,
automatic relabeling, previously scored confirmation/frozen test or deployment.
Customer review text is NOT exported in any CI artifact.

Run: python research/xlmr_optimization/phase6_annotation/phase6d_audit.py \
    --output /tmp/phase6d-ai-agreement
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import annotation_quality as qa

CLASSES = ("negative", "neutral", "positive", "mixed", "unclear")
BATCHES = tuple(HERE / f"phase6d_gpt6_random200_batch0{i}.csv" for i in range(1, 6))
COMBINED = HERE / "phase6d_gpt6_random200_v1.csv"
ROSTER = HERE / "phase6d_random200_ids.csv"
EXPECTED = 200


def label_agreement(a: list[str], b: list[str]) -> dict:
    if not a or len(a) != len(b):
        raise ValueError("Unmatched or empty annotation lists")
    if any(x not in CLASSES for x in a + b):
        raise ValueError("Invalid sentiment")
    n = len(a)
    matrix = [
        [sum(left == r and right == c for left, right in zip(a, b)) for c in CLASSES]
        for r in CLASSES
    ]
    matching = sum(matrix[i][i] for i in range(len(CLASSES)))
    row = [sum(r) for r in matrix]
    col = [sum(matrix[i][j] for i in range(len(CLASSES))) for j in range(len(CLASSES))]
    pe = sum(x*y for x, y in zip(row, col)) / (n*n)
    po = matching / n
    return {
        "n": n, "matching": matching,
        "raw_agreement": round(po, 6),
        "cohens_kappa": round((po-pe)/(1-pe), 6) if pe < 1 else None,
        "labels": list(CLASSES),
        "matrix_rows_claude_columns_gpt6": matrix,
        "claude_counts": dict(zip(CLASSES, row)),
        "gpt6_counts": dict(zip(CLASSES, col)),
    }


def confidence_interval(pairs: list[tuple[str, str]], trials=1000) -> dict:
    """Simple pairwise bootstrap CI, sampling only from the selected dev pool.

    This does NOT repair shared AI bias, unapproved S4 rules or prior exposure.
    """
    if not pairs:
        raise ValueError("No label pairs")
    rng = random.Random(20261115)
    kappas, agreements = [], []
    for _ in range(trials):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        scored = label_agreement([a for a, _ in sample], [b for _, b in sample])
        agreements.append(scored["raw_agreement"])
        if scored["cohens_kappa"] is not None:
            kappas.append(scored["cohens_kappa"])
    def interval(xs):
        if not xs:
            return None
        xs.sort()
        return [xs[int(0.025*(len(xs)-1))], xs[int(0.975*(len(xs)-1))]]
    return {
        "method": "seeded 1000-pair bootstrap; interval describes this selected development sample only",
        "raw_agreement_95pct": interval(agreements),
        "kappa_95pct": interval(kappas),
    }


def source_rows():
    qa.verify_protected()
    original = {}
    claude = {}
    for split, source_name, ai_name, count in qa.SPLITS:
        src = qa.read_csv(ROOT/"annotation"/source_name)
        labelled = qa.read_csv(ROOT/"annotation"/"ai_labelled"/ai_name)
        qa.validate_pair(src, labelled, split, count)
        original.update(src)
        claude.update(labelled)
    return original, claude


def load():
    roster = qa.read_csv(ROSTER)
    combined = qa.read_csv(COMBINED)
    if len(roster) != EXPECTED or set(roster) != set(combined):
        raise ValueError(f"Expected exactly {EXPECTED} preselected review IDs and labels")
    batches = {}
    for b in BATCHES:
        individual = qa.read_csv(b)
        if len(individual) != 40:
            raise ValueError(f"{b.name}: expected 40 reviewed rows")
        if set(batches) & set(individual):
            raise ValueError("An annotation ID occurs in multiple batches")
        batches.update(individual)
    if set(batches) != set(combined):
        raise ValueError("The consolidated sheet differs from the five locked batches")
    for rid, row in batches.items():
        if combined[rid] != row:
            raise ValueError(f"{rid}: combined annotation altered locked batch values")
    original, claude = source_rows()
    seen_prior = set(qa.read_csv(ROOT/"phase5"/"gpt6_second_ai_labels_v1.csv"))
    seen_prior |= set(qa.read_csv(HERE/"phase6b_gpt6_second_ai_v1.csv"))
    if not set(roster) <= set(original) or not set(roster) <= set(claude):
        raise ValueError("Random review roster has IDs not in original development source")
    dataset = []
    for rid in roster:
        row = combined[rid]
        first = claude[rid]
        orig = original[rid]
        tags = [t.strip().lower() for t in row["tags"].split(";") if t.strip()]
        if row.get("sentiment") not in qa.LABELS or row.get("confidence") not in qa.CONFIDENCE:
            raise ValueError(f"{rid}: invalid label/confidence")
        if len(tags) != len(set(tags)) or not set(tags) <= qa.TAGS:
            raise ValueError(f"{rid}: invalid/duplicate tags")
        if row.get("reviewer_id") != "GPT6_PHASE6D_20261115" or row.get("reviewer_type") != "ai" or row.get("policy_version") != "v1":
            raise ValueError(f"{rid}: incorrect GPT-6 AI provenance")
        if row["sentiment"] == "mixed" and "mixed" not in tags:
            raise ValueError(f"{rid}: undominated mixed requires mixed tag")
        if "mixed" in tags and (row["sentiment"] not in ("positive", "negative", "mixed")
                              or not row["positive_aspect"].strip()
                              or not row["negative_aspect"].strip()):
            raise ValueError(f"{rid}: Mixed requires both aspects")
        if "no-opinion" in tags and row["sentiment"] not in ("neutral", "unclear"):
            raise ValueError(f"{rid}: no-opinion conflicts with sentiment")
        if not row.get("rationale", "").strip():
            raise ValueError(f"{rid}: no annotation rationale")
        dataset.append({
            "id": rid,
            "sample_position": int(roster[rid]["sample_position"]),
            "split": "dev" if rid.startswith("D") else "candidates",
            "language": orig["language_hint"].strip().lower(),
            "claude_label": first["sentiment"],
            "gpt6_label": row["sentiment"],
            "claude_tags": first["tags"],
            "gpt6_tags": row["tags"],
            "gpt6_confidence": row["confidence"],
            "claude_confidence": first["confidence"],
            "gpt6_rationale": row["rationale"],
            "previous_gpt6_exposure": rid in seen_prior,
            "template_like_heuristic": bool(qa.shape(orig["review_text"])["list_shape"]),
        })
    if sorted(r["sample_position"] for r in dataset) != list(range(1, EXPECTED+1)):
        raise ValueError("Invalid or repeated random sample positions")
    return sorted(dataset, key=lambda r: r["sample_position"])


def summarize(rows):
    full = label_agreement([r["claude_label"] for r in rows], [r["gpt6_label"] for r in rows])
    without_exposure = [r for r in rows if not r["previous_gpt6_exposure"]]
    by_source = {}
    for key in ("dev", "candidates"):
        sample = [r for r in rows if r["split"] == key]
        by_source[key] = label_agreement([r["claude_label"] for r in sample], [r["gpt6_label"] for r in sample])
    by_language = {}
    for key in sorted(set(r["language"] for r in rows)):
        sample = [r for r in rows if r["language"] == key]
        by_language[key] = {
            "n": len(sample),
            "claude": dict(collections.Counter(r["claude_label"] for r in sample)),
            "gpt6": dict(collections.Counter(r["gpt6_label"] for r in sample)),
            "agree": sum(r["claude_label"] == r["gpt6_label"] for r in sample),
        }
    by_template = {}
    for key in (True, False):
        sample = [r for r in rows if r["template_like_heuristic"] == key]
        by_template[str(key).lower()] = label_agreement(
            [r["claude_label"] for r in sample], [r["gpt6_label"] for r in sample]
        ) if sample else {"n": 0}
    disagreements = [r for r in rows if r["claude_label"] != r["gpt6_label"]]
    transitions = collections.Counter(f"{r['claude_label']} -> {r['gpt6_label']}" for r in rows)
    report = {
        "purpose": "Development-only AI annotation agreement, NOT human gold or model F1",
        "sources": {
            "locked_roster_git_blob": qa.git_blob_sha(ROSTER),
            "gpt6_combined_git_blob": qa.git_blob_sha(COMBINED),
            "original_Claude_policy": "v1 unchanged",
            "rows": 200, "reannotator": "GPT-6 ChatGPT, AI, not human",
            "old_annotator": "Claude Sonnet 5.5, AI, not human",
        },
        "all": full,
        "bootstrap": confidence_interval([(r["claude_label"], r["gpt6_label"]) for r in rows]),
        "no_prior_gpt6_overlap": label_agreement(
            [r["claude_label"] for r in without_exposure],
            [r["gpt6_label"] for r in without_exposure]
        ),
        "prior_gpt6_overlap_count": len(rows)-len(without_exposure),
        "by_source": by_source,
        "by_language_hint": by_language,
        "by_template_heuristic": by_template,
        "transitions": dict(sorted(transitions.items())),
        "disagreements": len(disagreements),
        "claude_neutral_to_gpt6_positive": sum(
            r["claude_label"] == "neutral" and r["gpt6_label"] == "positive" for r in rows
        ),
        "gpt6_low_confidence": sum(r["gpt6_confidence"] == "low" for r in rows),
        "clear_provenance": [
            "200 GPT-6 labels locked across five commits before fetching original Claude labels",
            "13 of the 200 previously appeared in GPT-6 reviews; not fully blind",
            "No human label identity or agreement is claimed",
            "S4 buyer-selected marketplace tag status remains unresolved",
            "Random sampling is only within a Neutral-enriched development pool, not the marketplace population",
            "Low-confidence templated Positive disagreements must NOT automatically overwrite Claude Neutrals",
            "No original annotation, frozen test, confirmation set, model or production code is changed",
        ],
    }
    return report, disagreements


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/tmp/phase6d-ai-agreement"))
    args = parser.parse_args()
    records = load()
    report, disagreements = summarize(records)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/"ai_agreement_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    keys = ["id","sample_position","split","language","claude_label","gpt6_label",
            "claude_tags","gpt6_tags","claude_confidence","gpt6_confidence",
            "gpt6_rationale","previous_gpt6_exposure","template_like_heuristic","status"]
    with (args.output/"proposed_only_disagreements.csv").open("w",newline="",encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        for r in disagreements:
            writer.writerow({**r, "status": "proposed_not_adjudicated"})
    print(json.dumps({
        "n": report["all"]["n"],
        "agreement": report["all"]["raw_agreement"],
        "kappa": report["all"]["cohens_kappa"],
        "disagreements": report["disagreements"],
        "claude_neutral_to_gpt6_positive": report["claude_neutral_to_gpt6_positive"],
        "prior_gpt6_overlap": report["prior_gpt6_overlap_count"],
    }, indent=2))
    print("No training labels corrected, no human gold claimed.")


if __name__ == "__main__":
    main()
