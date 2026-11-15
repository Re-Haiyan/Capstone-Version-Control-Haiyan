"""Generate Hazard Checker predictions for a rights-cleared evaluation pack locally.

Reference CSV must have review_id,product_id,review_text,product_name,stars,
rights_confirmed. Writes *only* review_id and predicted_flags; never review
text or model output containing excerpts. Use with research/hazard_80_gate.py
on new product-disjoint data. Never run against sealed final evaluation after
any model/threshold selection step.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))

from defaketive_sentiment import registry  # noqa: E402

VALID = {"defect", "counterfeit", "safety", "not_as_described", "quality"}


def generate(reference: Path, output: Path, *, model_choice: str = "learned") -> tuple[int, str]:
    if output.resolve() == reference.resolve():
        raise ValueError("Do not overwrite the reference CSV")
    with reference.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"review_id", "product_id", "review_text", "product_name", "stars", "rights_confirmed"}
        fields = set(reader.fieldnames or [])
        if not required.issubset(fields):
            raise ValueError(f"Missing fields: {sorted(required - fields)}")
        rows = [dict(r) for r in reader]
    if not rows:
        raise ValueError("No rows to score")
    ids = [r["review_id"].strip() for r in rows]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError("review_id must be nonblank and unique")
    if any((r.get("rights_confirmed") or "").strip().casefold() not in {"yes", "true", "1"}
           for r in rows):
        raise ValueError("All evaluation rows must have confirmed usage rights")
    if any(not (r.get("product_id") or "").strip()
           or not (r.get("product_name") or "").strip()
           or not (r.get("review_text") or "").strip()
           for r in rows):
        raise ValueError("All rows need product_id, product_name, and review_text")
    stars = []
    for r in rows:
        rating = float(r["stars"])
        if not 1 <= rating <= 5:
            raise ValueError("stars must be between 1 and 5")
        stars.append(rating)
    if model_choice not in ("learned", "keywords"):
        raise ValueError("model_choice must be 'learned' or 'keywords'")
    # The registry chooses the same application model code as the production
    # path, but no deployment or live database is accessed here.
    os.environ[registry.HAZARD_ENVIRONMENT_VARIABLE] = model_choice
    registry.clear_cache()
    model = registry.load_model()
    outputs = []
    for row, star in zip(rows, stars):
        prediction = model.analyze(
            row["review_text"], star, listing={"name": row["product_name"]}
        )
        flags = set(prediction.get("review_tags") or ()) | set(prediction.get("review_extra_tags") or ())
        unknown = flags - VALID
        if unknown:
            raise ValueError(f"Model returned unrecognized labels: {sorted(unknown)}")
        outputs.append({"review_id": row["review_id"], "predicted_flags": "|".join(sorted(flags))})
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError("Refusing to replace existing predictions; select a new output path")
    with output.open("x", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["review_id", "predicted_flags"])
        writer.writeheader()
        writer.writerows(outputs)
    return len(outputs), str(model.model_version)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model", choices=("learned", "keywords"), default="learned")
    args = p.parse_args()
    count, version = generate(args.reference, args.out, model_choice=args.model)
    print(f"Predictions generated: {count}; model_version: {version}; research-only, not accuracy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
