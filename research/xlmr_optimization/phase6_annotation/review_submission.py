"""Validate a separately completed blind review sheet; never rewrite original labels.

A completed sheet must be generated locally using:
  annotation_quality.py --export-blind-text --output <private-dir>

Usage:
  python review_submission.py --blind-original <private-dir>/priority_blind_review.csv \
    --completed <private-dir>/priority_blind_review_completed.csv \
    --output <private-dir>/proposed_reannotation_overlay.csv

Only rows with a filled sentiment are imported. All other rows remain
unreviewed. "Human" is self-declared metadata, not independently verified.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

ALLOWED={"positive","negative","neutral","mixed","unclear"}
TAGS={"mixed","delivery-only","no-opinion"}
CONF={"high","low"}
FIELDS=("id","split","product","platform","language_hint","review_text")


def records(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        data=list(csv.DictReader(f))
    if any(not r.get("id") for r in data) or len({r["id"] for r in data})!=len(data):
        raise ValueError("Missing or duplicate review ID")
    return {r["id"]:r for r in data}


def parse(original, completed):
    expected=records(original)
    supplied=records(completed)
    if not set(supplied) <= set(expected):
        raise ValueError("Submitted row ID was not in the original blind packet")
    results=[]
    for rid,row in supplied.items():
        source=expected[rid]
        for f in FIELDS:
            if row.get(f,"") != source.get(f,""):
                raise ValueError(f"{rid}: immutable source field edited: {f}")
        label=row.get("sentiment","").strip().lower()
        if not label:
            continue
        if label not in ALLOWED:
            raise ValueError(f"{rid}: invalid sentiment")
        tags=[t.strip().lower() for t in row.get("tags","").split(";") if t.strip()]
        if len(tags)!=len(set(tags)) or not set(tags) <= TAGS:
            raise ValueError(f"{rid}: duplicate/unknown tag")
        if label=="mixed" and "mixed" not in tags:
            raise ValueError(f"{rid}: mixed needs mixed tag")
        if "mixed" in tags and (label not in {"positive","negative","mixed"}
                                 or not row.get("positive_aspect","").strip()
                                 or not row.get("negative_aspect","").strip()):
            raise ValueError(f"{rid}: mixed needs both aspects and valid sentiment")
        if "no-opinion" in tags and label not in {"neutral","unclear"}:
            raise ValueError(f"{rid}: no-opinion only for neutral/unclear")
        if row.get("confidence","").strip().lower() not in CONF:
            raise ValueError(f"{rid}: high/low confidence required")
        if not row.get("rationale","").strip():
            raise ValueError(f"{rid}: rationale required")
        who=row.get("reviewer_id","").strip()
        reviewer_type=row.get("reviewer_type","").strip().lower()
        policy=row.get("policy_version","").strip()
        if not who or reviewer_type not in {"human","ai"} or policy not in {"v1","v2-draft"}:
            raise ValueError(f"{rid}: reviewer ID/type and policy version required")
        results.append({
            "id":rid,"split":row["split"],"sentiment":label,"tags":";".join(sorted(tags)),
            "positive_aspect":row.get("positive_aspect",""),
            "negative_aspect":row.get("negative_aspect",""),
            "confidence":row["confidence"].strip().lower(),
            "rationale":row["rationale"].strip(),
            "reviewer_id":who,"reviewer_type_self_reported":reviewer_type,
            "policy_version":policy,
            "status":"proposed_not_adjudicated",
        })
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--blind-original",type=Path,required=True)
    p.add_argument("--completed",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    rows=parse(args.blind_original,args.completed)
    if not rows:
        raise ValueError("No reviewed rows submitted; nothing to import")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("w",newline="",encoding="utf-8") as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} proposed decisions validated; 0 original labels changed; NOT human gold.")


if __name__=="__main__":
    main()
