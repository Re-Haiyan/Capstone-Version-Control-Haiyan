"""Evidence-first Phase 4 paired scorer. Scores supplied, complete reference
annotations against baseline and candidate predictions on EXACTLY the same
accepted new reviews. Does NOT generate labels, scrape, train, or modify a model.

All inputs must be PRIVATE/off-repository. Outputs are aggregate counts only;
no raw texts, product IDs or prediction examples are printed or written.

JSONL reference/prediction: {"review_id":"...","status":"complete",
"pairs":[{"kind":"product","aspect_id":"build_quality","polarity":"positive"}]}
Predictions omit "status". To mark no evidence, use "pairs":[] -- not a
missing annotation. See Phase 4 protocol.

For final F2, require a separately recorded pre-evaluation freeze manifest
whose source_file_sha256 equals the exact accepted F2 file. One-shot score
requires an exclusive fresh ledger path in the separate final vault.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KINDS = frozenset({"product", "service", "trust"})
POLARITIES = frozenset({"positive", "negative"})
TASKS = {"T0": None, "T1": "product", "T2": "service", "T3": "trust"}


class ScoringError(ValueError):
    pass


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _outside_repo(path: Path) -> bool:
    r, root = path.resolve(), ROOT.resolve()
    return r != root and root not in r.parents


def _check_off_repo(*paths: Path) -> None:
    for p in paths:
        if not _outside_repo(p):
            raise ScoringError("research inputs, outputs and final ledger MUST reside outside Git repository")


def load_accepted(path: Path, split: str) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"review_id", "product_hash", "language", "category", "group", "review_text"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ScoringError("accepted review CSV missing required intake columns")
        result = {}
        for row in reader:
            identifier = row["review_id"]
            if (not identifier or identifier in result or not row["product_hash"] or
                    not row["review_text"]):
                raise ScoringError("missing/duplicate accepted review ID, product hash or text")
            result[identifier] = {
                "product_hash": row["product_hash"],
                "language": row["language"],
                "category": row["category"],
            }
    if not result:
        raise ScoringError("no accepted reviews: cannot score Phase 4")
    return result


def parse_pairs(value: object, identifier: str) -> frozenset[tuple[str, str, str]]:
    if not isinstance(value, list):
        raise ScoringError(f"{identifier}: pairs must be an array, even when empty")
    seen: set[tuple[str, str, str]] = set()
    for p in value:
        if not isinstance(p, dict) or set(p) != {"kind", "aspect_id", "polarity"}:
            raise ScoringError(f"{identifier}: pair must have exact kind/aspect_id/polarity keys")
        k, a, pol = p["kind"], p["aspect_id"], p["polarity"]
        if (k not in KINDS or pol not in POLARITIES or not isinstance(a, str)
                or not a or len(a) > 100 or not all(x.isalnum() or x == "_" for x in a)):
            raise ScoringError(f"{identifier}: unrecognized pair kind, aspect ID, or polarity")
        triple = (k, a, pol)
        if triple in seen:
            raise ScoringError(f"{identifier}: duplicate pair would inflate metrics")
        seen.add(triple)
    return frozenset(seen)


def load_pairs(path: Path, review_ids: set[str], reference: bool) -> dict[str, frozenset]:
    found = {}
    with path.open("r", encoding="utf-8") as stream:
        for no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except ValueError as e:
                raise ScoringError(f"line {no}: invalid JSONL") from e
            required = {"review_id", "pairs", "status"} if reference else {"review_id", "pairs"}
            if not isinstance(value, dict) or set(value) != required:
                raise ScoringError(f"line {no}: wrong pair record keys")
            identifier = value["review_id"]
            if not isinstance(identifier, str) or identifier not in review_ids or identifier in found:
                raise ScoringError(f"line {no}: unknown/duplicate review id")
            if reference and value["status"] != "complete":
                raise ScoringError(
                    "reference labels have pending/unclear/incomplete rows; no selective exclusions allowed"
                )
            found[identifier] = parse_pairs(value["pairs"], identifier)
    if set(found) != review_ids:
        raise ScoringError(f"incomplete reference or predictions: {len(review_ids) - len(found)} review(s) absent")
    return found


def validate_provenance(path: Path, accepted_sha: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        raise ScoringError("unreadable annotation provenance") from e
    required = {"reference_type", "annotator_model", "annotation_date",
                "rubric_sha256", "accepted_csv_sha256", "blind_to_predictions"}
    if not isinstance(data, dict) or not required.issubset(data):
        raise ScoringError("annotation provenance must describe actual labeling method and input hashes")
    if data["reference_type"] != "ai_assisted":
        raise ScoringError("this exploratory scorer requires explicit ai_assisted reference provenance")
    if not data["annotator_model"] or not data["annotation_date"] or len(str(data["rubric_sha256"])) != 64:
        raise ScoringError("missing annotator model, date or full rubric hash")
    if data["accepted_csv_sha256"] != accepted_sha:
        raise ScoringError("annotation provenance is not tied to these exact accepted reviews")
    if not isinstance(data["blind_to_predictions"], bool):
        raise ScoringError("blind_to_predictions must explicitly be boolean")
    return data


def check_frozen_final(freeze: Path | None, accepted_sha: str, split: str) -> dict | None:
    if split != "F2":
        if freeze is not None:
            raise ScoringError("a final freeze is valid only for F2")
        return None
    if freeze is None:
        raise ScoringError("F2 is sealed: a prospective freeze manifest is mandatory")
    try:
        data = json.loads(freeze.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        raise ScoringError("missing/invalid final freeze manifest") from e
    required = {"accepted_csv_sha256", "candidate_commit_sha", "baseline_commit_sha",
                "rubric_sha256", "frozen_before_final_reference", "feature_policy"}
    if not isinstance(data, dict) or not required.issubset(data):
        raise ScoringError("final freeze requires accepted data, candidate, baseline and rubric provenance")
    if data["accepted_csv_sha256"] != accepted_sha or data["frozen_before_final_reference"] is not True:
        raise ScoringError("final was not prospectively frozen against this dataset")
    if (not all(isinstance(data[x], str) and len(data[x]) == 40
                and all(c in "0123456789abcdef" for c in data[x])
                for x in ("candidate_commit_sha", "baseline_commit_sha"))
            or len(str(data["rubric_sha256"])) != 64
            or data["feature_policy"] != "unchanged"):
        raise ScoringError("invalid final model/rubric freeze or policy was changed")
    return data


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else None
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": round(p, 4) if p is not None else None,
            "recall": round(r, 4) if r is not None else None,
            "f1": round(f, 4) if f is not None else None,
            "precision_ci95": wilson(tp, tp + fp),
            "recall_ci95": wilson(tp, tp + fn)}


def wilson(correct: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    z = 1.959963984540054
    p = correct / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [round(max(0, center - margin), 4), round(min(1, center + margin), 4)]


def _counter(ref: frozenset, pred: frozenset, kind: str | None = None) -> Counter:
    if kind:
        ref = frozenset(p for p in ref if p[0] == kind)
        pred = frozenset(p for p in pred if p[0] == kind)
    return Counter(tp=len(ref & pred), fp=len(pred - ref), fn=len(ref - pred))


def metrics_for(review_ids: list[str], reference: dict, predicted: dict) -> dict:
    counters = {name: Counter() for name in TASKS}
    for rid in review_ids:
        for name, kind in TASKS.items():
            counters[name].update(_counter(reference[rid], predicted[rid], kind))
    return {name: prf(c["tp"], c["fp"], c["fn"]) for name, c in counters.items()}


def _metric_delta(a: float | None, b: float | None) -> float | None:
    return round(a - b, 4) if a is not None and b is not None else None


def paired_bootstrap(ids: list[str], products: dict[str, str],
                     ref: dict, baseline: dict, candidate: dict,
                     iterations: int = 500) -> dict:
    groups = defaultdict(list)
    for rid in ids:
        groups[products[rid]].append(rid)
    keys = sorted(groups)
    if len(keys) < 2:
        return {"method": "product-cluster-bootstrap", "clusters": len(keys), "ci95": None}
    rng = random.Random(20261115)
    deltas = []
    for _ in range(iterations):
        sampled = []
        for _ in keys:
            sampled.extend(groups[keys[rng.randrange(len(keys))]])
        cur = metrics_for(sampled, ref, candidate)["T1"]["f1"]
        old = metrics_for(sampled, ref, baseline)["T1"]["f1"]
        if cur is not None and old is not None:
            deltas.append(cur - old)
    if not deltas:
        interval = None
    else:
        deltas.sort()
        interval = [round(deltas[int(0.025 * (len(deltas) - 1))], 4),
                    round(deltas[int(0.975 * (len(deltas) - 1))], 4)]
    return {"method": "product-cluster-bootstrap", "clusters": len(keys),
            "replicates_used": len(deltas), "ci95": interval}


def evaluate(accepted: dict, reference: dict, baseline: dict, candidate: dict,
             provenance: dict, split: str) -> dict:
    ids = sorted(accepted)
    p = {rid: accepted[rid]["product_hash"] for rid in ids}
    base = metrics_for(ids, reference, baseline)
    cand = metrics_for(ids, reference, candidate)
    def segments(field: str) -> dict:
        values = sorted({m[field] for m in accepted.values()})
        return {
            value or "unknown": {
                "reviews": len(related),
                "baseline": metrics_for(related, reference, baseline),
                "candidate": metrics_for(related, reference, candidate),
            }
            for value in values
            for related in [[rid for rid in ids if accepted[rid][field] == value]]
        }
    t1_delta = _metric_delta(cand["T1"]["f1"], base["T1"]["f1"])
    prec_delta = _metric_delta(cand["T1"]["precision"], base["T1"]["precision"])
    service_delta = _metric_delta(cand["T2"]["f1"], base["T2"]["f1"])
    threshold_met = all(v is not None and v >= 0.80 for v in (
        cand["T1"]["precision"], cand["T1"]["recall"], cand["T1"]["f1"]
    ))
    candidate_numeric_gate = all((
        t1_delta is not None and t1_delta >= 0.03,
        prec_delta is not None and prec_delta >= -0.03,
        service_delta is not None and service_delta >= -0.05,
    ))
    return {
        "split": split, "review_count": len(ids),
        "product_count": len(set(p.values())),
        "reference_method": "AI-assisted proxy; NOT independent or human-validated",
        "reference_model": provenance["annotator_model"],
        "reference_blind_to_predictions": provenance["blind_to_predictions"],
        "task_metrics": {"baseline": base, "candidate": cand},
        "t1_delta_f1": t1_delta,
        "t1_delta_precision": prec_delta,
        "t2_delta_f1": service_delta,
        "t1_all_three_at_least_080_on_this_proxy": threshold_met,
        "v3_numeric_candidate_gate_pass": candidate_numeric_gate if split == "V3" else None,
        "by_language": segments("language"), "by_category": segments("category"),
        "product_cluster_bootstrap_t1_f1_delta": paired_bootstrap(
            ids, p, reference, baseline, candidate
        ),
        "adoption_or_production_approved": False,
        "unverified_gates": [
            "independent accuracy not established by AI-assisted annotations",
            "unsupported claims and serious safety errors not independently adjudicated",
            "saved decisions, app performance, and staging release gates not checked",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--split", required=True, choices=["D3", "V3", "F2"])
    parser.add_argument("--reviews", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--final-ledger", type=Path)
    args = parser.parse_args()
    paths = [args.reviews, args.reference, args.baseline, args.candidate, args.provenance, args.out]
    paths.extend(x for x in (args.freeze, args.final_ledger) if x is not None)
    try:
        _check_off_repo(*paths)
        if args.split == "F2":
            if args.final_ledger is None or args.final_ledger.exists():
                raise ScoringError("F2 may be scored once only; new exclusive final-ledger path required")
            if not args.final_ledger.parent.is_dir():
                raise ScoringError("F2 final ledger parent directory must exist in protected vault")
        elif args.final_ledger is not None:
            raise ScoringError("final ledger is only for F2")
        if args.out.exists():
            raise ScoringError("refusing to overwrite a prior evaluation report")
        sha = file_sha256(args.reviews)
        freeze = check_frozen_final(args.freeze, sha, args.split)
        accepted = load_accepted(args.reviews, args.split)
        ids = set(accepted)
        prov = validate_provenance(args.provenance, sha)
        if freeze and prov["rubric_sha256"] != freeze["rubric_sha256"]:
            raise ScoringError("final rubric was changed after candidate freeze")
        ref = load_pairs(args.reference, ids, reference=True)
        base = load_pairs(args.baseline, ids, reference=False)
        cand = load_pairs(args.candidate, ids, reference=False)
        report = evaluate(accepted, ref, base, cand, prov, args.split)
        report["accepted_csv_sha256"] = sha
        report["reference_file_sha256"] = file_sha256(args.reference)
        report["baseline_file_sha256"] = file_sha256(args.baseline)
        report["candidate_file_sha256"] = file_sha256(args.candidate)
        report["freeze_present"] = freeze is not None
        encoded = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
        if args.split == "F2":
            # A local sentinel (exclusive create) prevents accidental re-scoring.
            # This cannot prevent a privileged operator deleting the ledger.
            fd = os.open(args.final_ledger, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"accepted_csv_sha256": sha, "report_sha256": hashlib.sha256(encoded).hexdigest()}, stream)
                stream.write("\n")
        fd = os.open(args.out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
        print(json.dumps({
            "split": args.split, "reviews_scored": report["review_count"],
            "reference_method": report["reference_method"],
            "t1_candidate": report["task_metrics"]["candidate"]["T1"],
            "t1_all_three_at_least_080_on_this_proxy": report["t1_all_three_at_least_080_on_this_proxy"],
            "adoption_or_production_approved": False,
        }, indent=2))
        return 0
    except (ScoringError, OSError) as e:
        parser.exit(2, f"Phase 4 score refused: {e}\n")


if __name__ == "__main__":
    raise SystemExit(main())
