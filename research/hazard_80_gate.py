"""Strict, label-provenance-aware F1 gate for the five DeFaketive hazard flags.

Research-only. Reads a new, product-disjoint labelled reference and *separately*
generated predictions; never fits or changes a model. It cannot certify a product
as safe or authentic. CSV inputs and any review text stay local: output is
aggregate metrics only.

Required reference columns:
  review_id,product_id,review_text,true_flags,annotation_method,
  adjudicated,rights_confirmed
Required prediction columns: review_id,predicted_flags
Flags are pipe-separated (e.g. "safety|defect") or blank. Allowed annotation
methods: human_adjudicated, ai_assisted, team_silver.
Historical --exclude CSV(s) must include product_id (or product) and review_text.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

FLAGS = ("defect", "not_as_described", "counterfeit", "safety", "quality")
METHODS = {"human_adjudicated", "ai_assisted", "team_silver"}
TRUE = {"1", "yes", "true", "y"}
FALSE = {"0", "no", "false", "n", ""}
TARGET = 0.80


class GateError(ValueError):
    """The reference pack is malformed, not rights-cleared, or contaminated."""


def _read(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise GateError(f"{path.name}: missing columns {sorted(required - set(reader.fieldnames or []))}")
        return [{k: (v or "").strip() for k, v in row.items() if k is not None} for row in reader]


def _text_key(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.casefold()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _parse_flags(value: str, context: str) -> set[str]:
    if not value or value.casefold() in {"none", "no_flags", "[]"}:
        return set()
    flags = {token.strip().casefold() for token in re.split(r"[|;,]", value) if token.strip()}
    unexpected = flags - set(FLAGS)
    if unexpected:
        raise GateError(f"{context}: unknown flags {sorted(unexpected)}")
    return flags


def _boolean(value: str, context: str) -> bool:
    v = value.strip().casefold()
    if v in TRUE:
        return True
    if v in FALSE:
        return False
    raise GateError(f"{context}: expected a boolean, got {value!r}")


def _historical_keys(files: list[Path]) -> tuple[set[str], set[str]]:
    products: set[str] = set()
    texts: set[str] = set()
    if not files:
        raise GateError("At least one --exclude historical/training CSV is required")
    for file in files:
        with file.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = set(reader.fieldnames or [])
            column = "product_id" if "product_id" in fields else "product"
            if column not in fields or "review_text" not in fields:
                raise GateError(f"{file.name}: exclusion file requires product_id/product and review_text")
            for row in reader:
                product = (row.get(column) or "").strip().casefold()
                text = (row.get("review_text") or "").strip()
                if product:
                    products.add(product)
                if text:
                    texts.add(_text_key(text))
    return products, texts


def score(
    reference_file: Path,
    prediction_file: Path,
    exclusion_files: list[Path],
    *,
    target: float = TARGET,
    min_positives: int = 20,
) -> dict[str, object]:
    """Score a frozen external reference once; refuse obvious leakage.

    Human-adjudicated metrics may qualify the metric gate; AI-assisted and
    unverified team-supplied labels are descriptive, never verified accuracy.
    """
    if not 0 < target <= 1:
        raise GateError("target must be in (0,1]")
    if min_positives < 1:
        raise GateError("min_positives must be at least 1")
    known_products, known_texts = _historical_keys(exclusion_files)
    refs = _read(
        reference_file,
        {"review_id", "product_id", "review_text", "true_flags",
         "annotation_method", "adjudicated", "rights_confirmed"},
    )
    predictions = _read(prediction_file, {"review_id", "predicted_flags"})
    if not refs:
        raise GateError("reference dataset is empty")
    ids: set[str] = set()
    seen_texts: set[str] = set()
    human_adjudicated = True
    provenance: dict[str, int] = {method: 0 for method in sorted(METHODS)}
    validated: list[tuple[set[str], str]] = []
    for row in refs:
        rid = row["review_id"]
        pid = row["product_id"].casefold()
        text = row["review_text"]
        if not rid or not pid or not text:
            raise GateError("reference rows need nonempty review_id, product_id and review_text")
        if rid in ids:
            raise GateError(f"duplicate reference review_id: {rid}")
        ids.add(rid)
        key = _text_key(text)
        if key in seen_texts:
            raise GateError(f"duplicate review text in reference: {rid}")
        seen_texts.add(key)
        if pid in known_products or key in known_texts:
            raise GateError(f"historical/training overlap at review_id {rid}")
        if not _boolean(row["rights_confirmed"], f"{rid}.rights_confirmed"):
            raise GateError(f"rights not confirmed for review_id {rid}")
        method = row["annotation_method"].casefold()
        if method not in METHODS:
            raise GateError(f"{rid}: unsupported annotation_method {method!r}")
        provenance[method] += 1
        adjudicated = _boolean(row["adjudicated"], f"{rid}.adjudicated")
        human_adjudicated &= method == "human_adjudicated" and adjudicated
        validated.append((_parse_flags(row["true_flags"], rid), rid))

    pred_by_id: dict[str, set[str]] = {}
    for row in predictions:
        rid = row["review_id"]
        if not rid or rid in pred_by_id:
            raise GateError(f"missing/duplicate prediction review_id: {rid}")
        pred_by_id[rid] = _parse_flags(row["predicted_flags"], rid)
    if set(pred_by_id) != ids:
        raise GateError(
            f"prediction IDs mismatch: {len(ids - set(pred_by_id))} missing, "
            f"{len(set(pred_by_id) - ids)} unexpected"
        )

    per_class: dict[str, dict[str, float | int]] = {}
    for category in FLAGS:
        tp = fp = fn = tn = 0
        for actual, rid in validated:
            gold = category in actual
            predicted = category in pred_by_id[rid]
            tp += gold and predicted
            fp += not gold and predicted
            fn += gold and not predicted
            tn += not gold and not predicted
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
        per_class[category] = {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "support": tp + fn, "precision": round(precision, 6),
            "recall": round(recall, 6), "f1": round(f1, 6),
        }
    macro = sum(float(per_class[f]["f1"]) for f in FLAGS) / len(FLAGS)
    tp_total = sum(int(per_class[f]["tp"]) for f in FLAGS)
    fp_total = sum(int(per_class[f]["fp"]) for f in FLAGS)
    fn_total = sum(int(per_class[f]["fn"]) for f in FLAGS)
    micro = 2 * tp_total / (2 * tp_total + fp_total + fn_total) if 2 * tp_total + fp_total + fn_total else 0.0
    exact = sum(actual == pred_by_id[rid] for actual, rid in validated) / len(validated)
    enough_support = all(int(per_class[f]["support"]) >= min_positives for f in FLAGS)
    metrics_pass = (
        enough_support and macro >= target
        and all(float(per_class[f]["f1"]) >= target for f in FLAGS)
        and float(per_class["safety"]["recall"]) >= target
    )
    # The metric target on AI labels is still an *agreement* target.
    return {
        "reference_rows": len(validated),
        "distinct_products": len({row["product_id"].casefold() for row in refs}),
        "excluded_history_files": len(exclusion_files),
        "annotation_provenance_counts": provenance,
        "annotation_claims_human_adjudication": human_adjudicated,
        "independent_provenance_verified": False,
        "target": target,
        "minimum_positives_per_flag": min_positives,
        "per_class": per_class,
        "macro_f1": round(macro, 6),
        "micro_f1": round(micro, 6),
        "exact_match_accuracy": round(exact, 6),
        "sufficient_support": enough_support,
        "target_met_on_reference": metrics_pass,
        "independently_verified_target_met": False,  # CSV declarations cannot establish human provenance
        "production_release_approved": False,
        "interpretation": (
            "human adjudication is declared, not independently verified by this CSV"
            if human_adjudicated else
            "descriptive agreement with AI-assisted/unverified reference; not independent accuracy"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--exclude", type=Path, action="append", required=True,
                        help="Historical/train/validation CSV, repeated for every prior corpus")
    parser.add_argument("--out", type=Path, help="Optional aggregate-only JSON output")
    parser.add_argument("--target", type=float, default=TARGET)
    parser.add_argument("--min-positives", type=int, default=20)
    parser.add_argument("--require-pass", action="store_true",
                        help="Fail the command if the score does not meet the numeric target on its declared reference")
    args = parser.parse_args()
    try:
        report = score(args.reference, args.predictions, args.exclude,
                       target=args.target, min_positives=args.min_positives)
    except (GateError, OSError) as exc:
        parser.error(str(exc))
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 1 if args.require_pass and not report["target_met_on_reference"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
