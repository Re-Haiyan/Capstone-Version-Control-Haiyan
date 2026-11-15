"""Compare pre-locked GPT-6 labels with Claude v1 labels, without changing either.

Use only after gpt6_second_ai_labels_v1.csv was committed separately.
Five-class Cohen's kappa is descriptive *AI-to-AI* agreement on a deliberately
disagreement-enriched development sample, NOT independent-human reliability
or final model accuracy. Frozen test and Phase 3 confirmation are untouched.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ("negative", "neutral", "positive", "mixed", "unclear")


def read(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows or not all(r.get("id") for r in rows):
        raise ValueError(f"{path}: empty file or missing IDs")
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate ids")
    return {r["id"]: r for r in rows}


def measure(first: list[str], second: list[str], labels=LABELS) -> dict:
    if len(first) != len(second) or not first:
        raise ValueError("Different lengths or empty label lists")
    if any(x not in labels for x in (*first, *second)):
        raise ValueError("Unexpected label")
    n = len(first)
    matrix = [[sum(a == x and b == y for a,b in zip(first,second)) for y in labels] for x in labels]
    n_agree = sum(matrix[i][i] for i in range(len(labels)))
    observed = n_agree / n
    row_sums = [sum(r) for r in matrix]
    col_sums = [sum(matrix[j][i] for j in range(len(labels))) for i in range(len(labels))]
    chance = sum(a*b for a,b in zip(row_sums,col_sums)) / (n*n)
    kappa = (observed-chance)/(1-chance) if chance<1 else None
    return {
        "n": n,
        "agreed": n_agree,
        "observed_agreement": round(observed,6),
        "cohens_kappa": round(kappa,6) if kappa is not None else None,
        "labels": list(labels),
        "confusion_rows_claude_columns_gpt6": matrix,
        "claude_counts": dict(zip(labels,row_sums)),
        "gpt6_counts": dict(zip(labels,col_sums)),
    }


def compare(root: Path, output: Path, expected_n: int = 140) -> dict:
    import label_quality_audit as audit  # local script from Phase 5
    candidates = audit.audit_pair(root, "candidates", "neutral_candidate_pool.csv",
                                  "neutral_candidate_pool_ai_v1.csv", 3000)
    dev = audit.audit_pair(root, "dev", "dev_pool_sheet.csv",
                           "dev_pool_sheet_ai_v1.csv", 400)
    queue = audit.select_queue(dev+candidates)
    roster = {(r["split"],r["id"]):r for r in queue}
    gpt_path = root/"phase5"/"gpt6_second_ai_labels_v1.csv"
    second = read(gpt_path)
    if len(queue)!=expected_n or len(second)!=expected_n or {r["id"] for r in queue}!=set(second):
        raise ValueError(f"Selection/annotation coverage mismatch; queue={len(queue)}, GPT={len(second)}")
    claude = {}
    for path in (
        root/"annotation"/"ai_labelled"/"dev_pool_sheet_ai_v1.csv",
        root/"annotation"/"ai_labelled"/"neutral_candidate_pool_ai_v1.csv",
    ):
        claude.update(read(path))
    paired=[]
    for row in queue:
        rid=row["id"]
        a=claude[rid]
        b=second[rid]
        if b.get("sentiment") not in LABELS or b.get("confidence") not in ("high","low"):
            raise ValueError("Invalid second pass values: "+rid)
        tag=set(filter(None,b.get("tags","").split(";")))
        if "no-opinion" in tag and b["sentiment"]!="neutral":
            raise ValueError("Second pass no-opinion conflicts with sentiment: "+rid)
        if b["sentiment"]=="mixed" and "mixed" not in tag:
            raise ValueError("Second pass mixed must have mixed tag: "+rid)
        paired.append({
            "id": rid, "split":row["split"], "bucket":row["bucket"],
            "language":row["language"], "claude":a["sentiment"],
            "gpt6":b["sentiment"], "claude_confidence":a.get("confidence",""),
            "gpt6_confidence":b.get("confidence",""), "gpt6_tags":b.get("tags",""),
            "gpt6_rationale":b.get("rationale",""),
        })
    all_a=[r["claude"] for r in paired]
    all_b=[r["gpt6"] for r in paired]
    result={
        "study": "Phase 5, development-only, two AI systems, second pass fixed in prior commit",
        "sources": {
            "gpt6_labels_sha256": hashlib.sha256(gpt_path.read_bytes()).hexdigest(),
            "claude_dev_sha256": hashlib.sha256((root/"annotation"/"ai_labelled"/"dev_pool_sheet_ai_v1.csv").read_bytes()).hexdigest(),
            "claude_candidates_sha256": hashlib.sha256((root/"annotation"/"ai_labelled"/"neutral_candidate_pool_ai_v1.csv").read_bytes()).hexdigest(),
        },
        "five_class": measure(all_a,all_b),
        "three_class_both_labelled": measure(
            [r["claude"] for r in paired if r["claude"] in LABELS[:3] and r["gpt6"] in LABELS[:3]],
            [r["gpt6"] for r in paired if r["claude"] in LABELS[:3] and r["gpt6"] in LABELS[:3]],
            LABELS[:3]),
        "by_bucket": {},
        "by_language": {},
        "disagreements": sum(r["claude"]!=r["gpt6"] for r in paired),
        "constraints": [
            "Sample intentionally enriched for ambiguous reviews and is NOT population representative.",
            "A second AI opinion is NOT independent-human adjudication or a corrected gold standard.",
            "Do not change Claude labels or score the frozen test with these labels.",
            "Policy S4 buyer-selected tag interpretation remains unresolved.",
        ],
    }
    for key, field in (("by_bucket","bucket"),("by_language","language")):
        for name in sorted({r[field] for r in paired}):
            group=[r for r in paired if r[field]==name]
            result[key][name]=measure([r["claude"] for r in group],[r["gpt6"] for r in group])
    output.mkdir(parents=True,exist_ok=True)
    (output/"agreement.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    differences=[r for r in paired if r["claude"]!=r["gpt6"]]
    cols=("id","split","bucket","language","claude","gpt6","claude_confidence","gpt6_confidence","gpt6_tags","gpt6_rationale")
    with (output/"disagreement_queue.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=cols)
        writer.writeheader()
        writer.writerows([{k:r[k] for k in cols} for r in differences])
    print(json.dumps({"sample":len(paired),"agreement":result["five_class"]["observed_agreement"],
                     "kappa":result["five_class"]["cohens_kappa"],
                     "disagreements":len(differences),"three_class_both":result["three_class_both_labelled"]["n"]},indent=2))
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--out-dir",type=Path,default=Path("/tmp/phase5-comparison"))
    args=p.parse_args()
    compare(args.root,args.out_dir)
