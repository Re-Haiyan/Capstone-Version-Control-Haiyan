"""Phase 6C: local-only, two-reviewer sentiment adjudication gate.

This is a provenance and quality-control tool, NOT a source of human labels.
It never reads the frozen tests or Phase 3 confirmation and never mutates
Claude/GPT-6 annotations, model artifacts or production code.

First, give two independently briefed reviewers copies of the SAME locally
exported BLIND review CSV. After each separately completes their copy:

python adjudication_gate.py prepare --blind priority_blind_review.csv \
  --reviewer-a completed_A.csv --reviewer-b completed_B.csv --out-dir /private/phase6c

Then pass /private/phase6c/adjudication_sheet.csv to a DISTINCT adjudicator.
It shows reviewer disagreements and their reasons (as frozen policy v1 permits).
After the adjudicator fills it:

python adjudication_gate.py finalize --blind priority_blind_review.csv \
  --reviewer-a completed_A.csv --reviewer-b completed_B.csv \
  --completed /private/phase6c/adjudication_sheet_completed.csv \
  --out-dir /private/phase6c_final

Outputs are proposed, provenance-traceable decisions, NOT independently
verified human ground truth; personhood and identity are self-declared.
Never upload reviewer sheets or raw review texts to PUBLIC GitHub Actions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import review_submission as submissions

LABELS = ("negative", "neutral", "positive", "mixed", "unclear")
FIELDS = ("sentiment", "tags", "positive_aspect", "negative_aspect")
BLIND_FIELDS = ("id", "split", "product", "platform", "language_hint", "review_text")
ADJUDICATOR_FIELDS = (
    "final_sentiment", "final_tags", "final_positive_aspect", "final_negative_aspect",
    "final_confidence", "adjudication_rationale", "evidence_quote",
    "adjudicator_id", "adjudicator_type", "policy_version", "adjudication_date",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError(f"{path.name}: duplicated column names")
        rows = list(reader)
    if not rows or any(not r.get("id") for r in rows):
        raise ValueError(f"{path.name}: missing IDs or empty file")
    if len(rows) != len({r["id"] for r in rows}):
        raise ValueError(f"{path.name}: repeated ID")
    if any(None in r or r.get(None) is not None for r in rows):
        raise ValueError(f"{path.name}: malformed CSV")
    return {r["id"]: r for r in rows}


def validate_blind(blind: dict[str, dict[str, str]]) -> None:
    for rid, row in blind.items():
        if any(row.get(k, "").strip() for k in ("sentiment", "tags", "confidence", "rationale")):
            raise ValueError(f"{rid}: source packet is not blind")
        if not set(BLIND_FIELDS) <= set(row):
            raise ValueError(f"{rid}: source packet missing fields")


def checked_reviewer(
    blind_path: Path, submission_path: Path, blind: dict,
    allow_partial: bool = False
) -> tuple[str, dict[str, dict[str, str]]]:
    submitted = read_csv(submission_path)
    if not set(submitted) <= set(blind):
        raise ValueError("Review submitted an unknown review ID")
    # A labelled CSV must contain the SAME IDs as the assigned blank packet.
    # Partial work is never silently discarded.
    if not allow_partial and set(submitted) != set(blind):
        raise ValueError("Reviewer packet has missing IDs; use --allow-partial to acknowledge")
    parsed = submissions.parse(blind_path, submission_path)
    answers = {r["id"]: r for r in parsed}
    if not answers:
        raise ValueError("Reviewer has no completed annotations")
    if not allow_partial and set(answers) != set(blind):
        raise ValueError("Reviewer has blank annotations; use --allow-partial to acknowledge")
    names = {r["reviewer_id"] for r in parsed}
    if len(names) != 1:
        raise ValueError("One completed reviewer packet must have one reviewer ID")
    identity = names.pop()
    for row in parsed:
        if row["reviewer_type_self_reported"] != "human":
            raise ValueError("Independent human-review workflow cannot use an AI-submitted packet")
        if row["policy_version"] != "v1":
            raise ValueError("Approved policy v1 required; unapproved v2 draft not accepted")
    return identity, answers


def agreement(a: list[str], b: list[str]) -> dict:
    if not a or len(a) != len(b):
        raise ValueError("Agreement inputs must be nonempty matched labels")
    if any(v not in LABELS for v in (*a, *b)):
        raise ValueError("Unexpected sentiment class")
    matrix = [[sum(x == left and y == right for x, y in zip(a, b))
               for right in LABELS] for left in LABELS]
    n = len(a)
    matched = sum(matrix[i][i] for i in range(len(LABELS)))
    counts_a = [sum(row) for row in matrix]
    counts_b = [sum(matrix[j][i] for j in range(len(LABELS))) for i in range(len(LABELS))]
    expected = sum(x * y for x, y in zip(counts_a, counts_b)) / (n*n)
    observed = matched / n
    return {
        "pairs": n, "identical_sentiment": matched,
        "raw_sentiment_agreement": round(observed, 6),
        "cohens_kappa_five_class": round((observed-expected)/(1-expected), 6) if expected < 1 else None,
        "labels": list(LABELS),
        "confusion_rows_reviewer_A_columns_reviewer_B": matrix,
    }


def normal_tags(s: str) -> str:
    return ";".join(sorted({v.strip().lower() for v in s.split(";") if v.strip()}))


def is_disputed(a: dict, b: dict) -> list[str]:
    differences = []
    if a["sentiment"] != b["sentiment"]:
        differences.append("sentiment")
    if normal_tags(a["tags"]) != normal_tags(b["tags"]):
        differences.append("tags")
    if a["positive_aspect"].strip() != b["positive_aspect"].strip() or \
       a["negative_aspect"].strip() != b["negative_aspect"].strip():
        if "mixed" in normal_tags(a["tags"]).split(";") or "mixed" in normal_tags(b["tags"]).split(";"):
            differences.append("mixed_aspect")
    if a["confidence"] == "low" or b["confidence"] == "low":
        differences.append("low_confidence")
    return differences


def prepare(blind_path: Path, a_path: Path, b_path: Path, allow_partial=False):
    blind = read_csv(blind_path)
    validate_blind(blind)
    reviewer_a, a = checked_reviewer(blind_path, a_path, blind, allow_partial)
    reviewer_b, b = checked_reviewer(blind_path, b_path, blind, allow_partial)
    if reviewer_a == reviewer_b:
        raise ValueError("Reviewer A and B must have distinct IDs")
    overlap = sorted(set(a) & set(b))
    if not overlap:
        raise ValueError("No reviews independently labelled by both reviewers")
    entries = []
    disagreement = Counter()
    for rid in overlap:
        left, right = a[rid], b[rid]
        reasons = is_disputed(left, right)
        if not reasons:
            continue
        disagreement.update(reasons)
        original = blind[rid]
        entry = {k: original[k] for k in BLIND_FIELDS}
        entry.update({
            "reviewer_a_id": reviewer_a, "reviewer_b_id": reviewer_b,
            "reviewer_a_sentiment": left["sentiment"], "reviewer_b_sentiment": right["sentiment"],
            "reviewer_a_tags": left["tags"], "reviewer_b_tags": right["tags"],
            "reviewer_a_positive_aspect": left["positive_aspect"],
            "reviewer_b_positive_aspect": right["positive_aspect"],
            "reviewer_a_negative_aspect": left["negative_aspect"],
            "reviewer_b_negative_aspect": right["negative_aspect"],
            "reviewer_a_confidence": left["confidence"],
            "reviewer_b_confidence": right["confidence"],
            "reviewer_a_rationale": left["rationale"],
            "reviewer_b_rationale": right["rationale"],
            "reason_for_review": ";".join(reasons),
        })
        entry.update({k: "" for k in ADJUDICATOR_FIELDS})
        entries.append(entry)
    result = {
        "schema": "phase6c_adjudication_preparation_v1",
        "policy": "v1; no S4-v2 interpretation presumed",
        "reviewer_a_id_self_reported": reviewer_a,
        "reviewer_b_id_self_reported": reviewer_b,
        "original_blank_reviews": len(blind),
        "a_completed": len(a), "b_completed": len(b),
        "both_completed": len(overlap),
        "no_pairwise_answer": len(blind) - len(overlap),
        "needs_adjudication": len(entries),
        "reasons": dict(sorted(disagreement.items())),
        "agreement": agreement([a[r]["sentiment"] for r in overlap], [b[r]["sentiment"] for r in overlap]),
        "sha256": {
            "source_blind": digest(blind_path),
            "reviewer_a": digest(a_path), "reviewer_b": digest(b_path),
        },
        "limit": (
            "Reviewer identities and roles are SELF-REPORTED; this software cannot verify persons. "
            "Only the original reviewed development packet is permitted. No final-test or "
            "confirmation scores are computed, and agreement is not model F1."
        ),
    }
    return result, entries


def validate_final_row(row: dict, original: dict, reviewers: set[str]):
    rid = original["id"]
    for key, value in original.items():
        if key in ADJUDICATOR_FIELDS:
            continue
        if row.get(key) != value:
            raise ValueError(f"{rid}: adjudication task source or reviewer evidence was changed: {key}")
    label = row.get("final_sentiment", "").strip().lower()
    if label not in LABELS:
        raise ValueError(f"{rid}: final sentiment required")
    tags = [t.strip().lower() for t in row.get("final_tags", "").split(";") if t.strip()]
    if len(tags) != len(set(tags)) or not set(tags) <= submissions.TAGS:
        raise ValueError(f"{rid}: unrecognized/duplicate tags")
    if label == "mixed" and "mixed" not in tags:
        raise ValueError(f"{rid}: mixed requires mixed tag")
    if "mixed" in tags:
        if label not in {"positive", "negative", "mixed"} or not row.get("final_positive_aspect", "").strip() or not row.get("final_negative_aspect", "").strip():
            raise ValueError(f"{rid}: mixed must have two aspects and a compatible label")
    if "no-opinion" in tags and label not in {"neutral", "unclear"}:
        raise ValueError(f"{rid}: no-opinion contradicts final sentiment")
    if row.get("final_confidence", "").strip().lower() not in {"high", "low"}:
        raise ValueError(f"{rid}: confidence missing")
    who = row.get("adjudicator_id", "").strip()
    if not who or who in reviewers:
        raise ValueError(f"{rid}: third adjudicator ID must differ from both reviewers")
    if row.get("adjudicator_type", "").strip().lower() != "human":
        raise ValueError(f"{rid}: third adjudicator must self-identify as human; not independently verified")
    if row.get("policy_version", "").strip() != "v1":
        raise ValueError(f"{rid}: approved policy v1 required")
    if not row.get("adjudication_rationale", "").strip():
        raise ValueError(f"{rid}: independent adjudication rationale required")
    quote = row.get("evidence_quote", "").strip()
    if not quote or quote not in original["review_text"]:
        raise ValueError(f"{rid}: evidence quote must be an exact span of the original review")
    raw_date = row.get("adjudication_date", "").strip()
    try:
        parsed = date.fromisoformat(raw_date)
    except ValueError:
        raise ValueError(f"{rid}: ISO 8601 adjudication date required") from None
    if parsed > date.today():
        raise ValueError(f"{rid}: adjudication date cannot be in the future")
    return {
        "id": rid, "split": original["split"],
        "final_sentiment": label,
        "final_tags": ";".join(sorted(tags)),
        "final_positive_aspect": row.get("final_positive_aspect", "").strip(),
        "final_negative_aspect": row.get("final_negative_aspect", "").strip(),
        "final_confidence": row["final_confidence"].strip().lower(),
        "adjudication_rationale": row["adjudication_rationale"].strip(),
        "evidence_quote": quote,
        "reviewer_a_id": original["reviewer_a_id"],
        "reviewer_b_id": original["reviewer_b_id"],
        "adjudicator_id_self_reported": who,
        "policy_version": "v1",
        "adjudication_date": raw_date,
        "status": "self_reported_adjudication_pending_identity_and_protocol_verification",
        "approved_for_training": "false",
    }


def finalize(blind_path: Path, a_path: Path, b_path: Path, completed_path: Path, allow_partial=False):
    report, todo = prepare(blind_path, a_path, b_path, allow_partial)
    expected = {r["id"]: r for r in todo}
    if not todo:
        raise ValueError("No differences or low-confidence rows requiring adjudication")
    actual = read_csv(completed_path)
    if set(actual) != set(expected):
        raise ValueError("Every proposed adjudication must be included, no additions or omissions")
    reviewers = {report["reviewer_a_id_self_reported"], report["reviewer_b_id_self_reported"]}
    decisions = [validate_final_row(actual[rid], expected[rid], reviewers) for rid in sorted(expected)]
    judges = {r["adjudicator_id_self_reported"] for r in decisions}
    if len(judges) != 1:
        raise ValueError("One adjudication submission must identify exactly one third adjudicator")
    return {
        "summary": {
            "rows_adjudicated_self_reported": len(decisions),
            "adjudicator_id_self_reported": next(iter(judges)),
            "source_sha256": report["sha256"],
            "adjudicator_csv_sha256": digest(completed_path),
            "training_approved": False,
            "independent_human_verification": "NOT VERIFIED BY SOFTWARE",
            "policy_version": "v1",
        },
        "rows": decisions,
    }


def write_csv(path: Path, records: list[dict], headers=None):
    if not records:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers or list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    for name in ("prepare", "finalize"):
        command = sub.add_parser(name)
        command.add_argument("--blind", type=Path, required=True)
        command.add_argument("--reviewer-a", type=Path, required=True)
        command.add_argument("--reviewer-b", type=Path, required=True)
        command.add_argument("--out-dir", type=Path, required=True)
        command.add_argument("--allow-partial", action="store_true")
        if name == "finalize":
            command.add_argument("--completed", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "prepare":
        report, todo = prepare(args.blind, args.reviewer_a, args.reviewer_b, args.allow_partial)
        (args.out_dir / "agreement_summary.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        if todo:
            write_csv(args.out_dir / "adjudication_sheet.csv", todo)
        print(json.dumps({k: report[k] for k in ("both_completed", "needs_adjudication", "agreement")}, indent=2))
        print("Original label files unchanged. Reviewer identity is self-reported; LOCAL ONLY.")
    else:
        result = finalize(args.blind, args.reviewer_a, args.reviewer_b,
                          args.completed, args.allow_partial)
        write_csv(args.out_dir / "adjudicated_proposed_only.csv", result["rows"])
        (args.out_dir / "adjudication_provenance.json").write_text(
            json.dumps(result["summary"], indent=2) + "\n", encoding="utf-8"
        )
        print(f"{len(result['rows'])} adjudications recorded as PROPOSED, not training-approved.")


if __name__ == "__main__":
    main()
