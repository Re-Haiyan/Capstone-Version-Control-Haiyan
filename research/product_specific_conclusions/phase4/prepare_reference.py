"""Phase 4: privacy-preserving, source-locked blind annotation packets.

This does NOT increase model accuracy or use previous frozen test labels.
Run only after *accepted* D3/V3/F2 real-review intake and source-rights review.
No F2 vault file or previously scored review is opened by this script.

python research/product_specific_conclusions/phase4/prepare_reference.py \
    --intake-dir /restricted/phase4/development \
    --out-dir /restricted/phase4/reviewer_packets \
    [--include-v3]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
INPUT_FIELDS = (
    "review_id", "product_hash", "category", "group", "language", "stars",
    "source_kind", "source_id", "collection_date", "review_text",
)
BLIND_FIELDS = (
    "review_id", "category", "group", "language", "review_text",
    "features", "confidence", "rationale", "reviewer_id",
    "reviewer_type", "policy_version",
)
TARGETS = {"D3": 300, "V3": 150, "F2": 200}
REVIEWERS = ("A", "B")


class PacketError(ValueError):
    pass


def outside_repo(path: Path) -> bool:
    resolved = path.resolve()
    repo = REPO.resolve()
    return resolved != repo and repo not in resolved.parents


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path, split: str) -> list[dict[str, str]]:
    if not path.is_file():
        raise PacketError(f"Required accepted {split} intake file not found")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if tuple(fields) != INPUT_FIELDS:
            raise PacketError(f"{split} columns differ from Phase 4 intake contract")
        rows = list(reader)
    if not rows:
        raise PacketError(f"Empty {split} intake")
    seen: set[str] = set()
    for r in rows:
        if None in r or r.get(None) is not None:
            raise PacketError(f"{split} contains malformed CSV rows")
        rid = r["review_id"]
        if not rid or rid in seen:
            raise PacketError(f"{split} contains blank/duplicate review IDs")
        seen.add(rid)
        if not r["review_text"].strip() or not r["product_hash"].strip():
            raise PacketError(f"{split} contains empty source review/product ID")
        if r["stars"] not in ("1", "2", "3", "4", "5"):
            raise PacketError(f"{split} invalid stars field")
        if r["source_kind"] not in {"authorized_export", "licensed_dataset", "team_owned"}:
            raise PacketError(f"{split} unknown source_kind")
    return rows


def validate_intake(intake_dir: Path, include_v3=False):
    if not outside_repo(intake_dir):
        raise PacketError("Intake files must stay outside the public repository")
    manifest_path = intake_dir / "manifest.json"
    if not manifest_path.is_file():
        raise PacketError("Missing Phase 4 intake manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("phase") != "4" or not manifest.get("research_ready", False):
        raise PacketError("Only accepted research-ready Phase 4 source can be assigned")
    if manifest.get("targets") != TARGETS or any(
        manifest.get("counts", {}).get(s, 0) < n for s, n in TARGETS.items()
    ):
        raise PacketError("Intake manifest does not meet D3/V3/F2 preregistered quotas")
    # Deliberately do NOT read F2 file; F2 stays in its separate sealed vault.
    dev = read_rows(intake_dir / "D3.csv", "D3")
    val = read_rows(intake_dir / "V3.csv", "V3")
    if len(dev) != manifest["counts"]["D3"] or len(val) != manifest["counts"]["V3"]:
        raise PacketError("Actual development/validation counts differ from manifest")
    if len({r["review_id"] for r in dev + val}) != len(dev) + len(val):
        raise PacketError("A review occurs in both D3 and V3")
    if {r["product_hash"] for r in dev} & {r["product_hash"] for r in val}:
        raise PacketError("Product-group leakage between development and validation")
    result = {"D3": dev}
    if include_v3:
        result["V3"] = val
    return result, {
        "input_manifest_sha256": sha256(manifest_path),
        "input_D3_sha256": sha256(intake_dir / "D3.csv"),
        "input_V3_sha256": sha256(intake_dir / "V3.csv"),
        "intake_counts": dict(manifest["counts"]),
        "intake_product_counts": dict(manifest.get("product_counts", {})),
        "rights_review": "Not independently verified by software; require separate source-rights ledger",
    }


def blind_row(row: dict[str, str]) -> dict[str, str]:
    # Stars, source IDs and prior model outputs must not bias reviewer labels.
    return {
        "review_id": row["review_id"], "category": row["category"],
        "group": row["group"], "language": row["language"],
        "review_text": row["review_text"],
        "features": "", "confidence": "", "rationale": "",
        "reviewer_id": "", "reviewer_type": "", "policy_version": "",
    }


def planned_packets(datasets: dict[str, list[dict[str, str]]]):
    plan: dict[str, list[dict[str, str]]] = {}
    for split, rows in datasets.items():
        for reviewer in REVIEWERS:
            ordered = sorted(rows, key=lambda r: r["review_id"])
            # Separate, deterministic orders for independent reviewer packets.
            key = hashlib.sha256(f"phase4-{split}-{reviewer}-20261115".encode()).digest()
            random.Random(int.from_bytes(key[:8], "big")).shuffle(ordered)
            plan[f"{split}_reviewer_{reviewer}_BLIND.csv"] = [blind_row(r) for r in ordered]
    return plan


def private_write(path: Path, rows: list[dict[str, str]]):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BLIND_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build(intake_dir: Path, out_dir: Path, include_v3=False, dry_run=False):
    if not outside_repo(out_dir) or not outside_repo(intake_dir):
        raise PacketError("Input and output MUST be outside the public Git repository")
    if out_dir.exists():
        raise PacketError("Output exists; refusing to overwrite reviewer work")
    if intake_dir.resolve() == out_dir.resolve() or (
        intake_dir.resolve() in out_dir.resolve().parents or
        out_dir.resolve() in intake_dir.resolve().parents
    ):
        raise PacketError("Source and reviewer output must be separate directories")
    data, provenance = validate_intake(intake_dir, include_v3)
    plan = planned_packets(data)
    report = {
        "schema": "phase4_independent_blind_reference_packets_v1",
        "status": "BLANK; 0 annotated reviews; NO model accuracy asserted",
        "source_sha256": provenance,
        "packet_row_counts": {name: len(rows) for name, rows in plan.items()},
        "split_product_counts": {
            split: len({r["product_hash"] for r in rows}) for split, rows in data.items()
        },
        "reviewer_fields": list(BLIND_FIELDS),
        "reviewer_role": "Separate A/B annotators, human preferred. AI allowed only with explicit AI provenance.",
        "v3_access": "Validation packet requires --include-v3 and must stay sealed from model developer",
        "f2_access": "F2 sealed vault NOT opened or copied",
        "privacy": "No review text or completed sheets in public GitHub or CI artifacts",
        "limits": "A manifest's rights attestation is not legal verification; verify source-rights ledger separately.",
    }
    if dry_run:
        return report
    out_dir.mkdir(parents=True, mode=0o700)
    for filename, rows in plan.items():
        private_write(out_dir / filename, rows)
    fd = os.open(str(out_dir / "packet_provenance.json"),
                 os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
        file.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--include-v3", action="store_true",
                        help="Prepare a separately restricted V3 packet; never show to candidate developer")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = build(args.intake_dir, args.out_dir, args.include_v3, args.dry_run)
    print(json.dumps({
        "status": result["status"], "packet_row_counts": result["packet_row_counts"],
        "split_product_counts": result["split_product_counts"],
        "v3": result["v3_access"], "f2": result["f2_access"],
    }, indent=2))


if __name__ == "__main__":
    main()
