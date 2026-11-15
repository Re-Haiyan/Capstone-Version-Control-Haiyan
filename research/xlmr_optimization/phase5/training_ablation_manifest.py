"""Phase 5 research-only manifest for uncertainty-aware TRAINING ABLATIONS.

Creates data-selection/weight alternatives without ever changing labels or
touching tests, confirmation sets, predictions, production weights or product
decisions. The Phase 4 validation protocol MUST be rebuilt separately.
"""
import argparse
import collections
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THREE = {"negative", "neutral", "positive"}


def make_manifest(root: Path):
    import label_quality_audit
    audit = label_quality_audit
    rows = (
        audit.audit_pair(root, "dev", "dev_pool_sheet.csv",
                         "dev_pool_sheet_ai_v1.csv", 400)
        + audit.audit_pair(root, "candidates", "neutral_candidate_pool.csv",
                           "neutral_candidate_pool_ai_v1.csv", 3000)
    )
    first = {}
    for path in (
        root / "annotation" / "ai_labelled" / "dev_pool_sheet_ai_v1.csv",
        root / "annotation" / "ai_labelled" / "neutral_candidate_pool_ai_v1.csv",
    ):
        first.update(audit.read(path))
    second = audit.read(root / "phase5" / "gpt6_second_ai_labels_v1.csv")
    # A disagreement is a reason to *review*, not proof Claude is wrong.
    disputes = {
        rid for rid, new in second.items()
        if rid in first and first[rid]["sentiment"] != new["sentiment"]
    }
    if len(second) != 140 or len(disputes) != 71:
        raise ValueError("The locked 140-review disagreement baseline has changed")
    manifest = []
    for r in rows:
        class_ok = r["label"] in THREE
        ambiguous_tag_shape = ("tag_list_s4_boundary" in r["flags"]
                               or "positive_tag_list_s4_boundary" in r["flags"])
        is_disputed = r["id"] in disputes
        # Proposed EXPERIMENTAL training weights only. No revised label is made.
        # Under policy v1, the disputed tag lists could be genuine buyer choices
        # OR source-generated descriptors; neither is established as fact.
        sensitive_weight = (
            0.0 if not class_ok or is_disputed
            else 0.25 if ambiguous_tag_shape
            else 1.0
        )
        entry = {
            "id": r["id"], "split": r["split"], "claude_v1_label": r["label"],
            "language_hint": r["language"],
            "category": "disagreement" if is_disputed else ("tag_shape_uncertain" if ambiguous_tag_shape else "ordinary"),
            "review_required": int(is_disputed or "check_unread_tail" in r["flags"]),
            "three_class_eligible": int(class_ok),
            "baseline_weight": 1.0 if class_ok else 0.0,
            "exclude_disagreement_weight": 1.0 if class_ok and not is_disputed else 0.0,
            "s4_downweight_sensitivity_weight": sensitive_weight,
        }
        manifest.append(entry)
    return manifest


def summarize(rows):
    variants = ("baseline_weight", "exclude_disagreement_weight", "s4_downweight_sensitivity_weight")
    data = {
        "sample": len(rows),
        "not_reference_labels": "All labels remain frozen Claude v1 labels. GPT-6 flags only affect proposed experimental weight/selection.",
        "scope": "development rows only; no final test or Phase 3 confirmation",
        "risk_buckets": dict(collections.Counter(r["category"] for r in rows)),
        "weights": {},
    }
    for variant in variants:
        eff = collections.Counter()
        count = collections.Counter()
        for r in rows:
            val = float(r[variant])
            if val:
                eff[r["claude_v1_label"]] += val
                count[r["claude_v1_label"]] += 1
        data["weights"][variant] = {
            "active_examples_by_label": dict(sorted(count.items())),
            "effective_examples_by_label": {k: round(v,2) for k,v in sorted(eff.items())},
            "total_nonzero_rows": sum(count.values()),
        }
    return data


def main(out_dir: Path, root: Path = ROOT):
    rows = make_manifest(root)
    report = summarize(rows)
    out_dir.mkdir(parents=True,exist_ok=True)
    output=out_dir/"training_ablation_manifest.csv"
    with output.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (out_dir/"training_ablation_counts.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return report


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",type=Path,default=Path("/tmp/phase5-training-ablation"))
    args=ap.parse_args()
    main(args.out_dir)
