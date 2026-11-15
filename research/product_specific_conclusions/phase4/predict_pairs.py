"""Generate aspect-pair predictions with a real pinned extractor, without labels.

Run baseline C3 and experimental candidate in separate checkouts; do not hand
write prediction pairs. All input/output paths must stay OUTSIDE Git. For F2,
verify the prospective freeze and actual clean Git commit before reading any
sealed review. This writes only aspect IDs/polarities, not review text.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_pairs as scoring  # noqa: E402


def _git(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                              text=True, timeout=10, check=False)
        return proc.stdout.strip() if proc.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def generate(reviews: Path, impl: Path, split: str, freeze: Path | None,
             role: str) -> tuple[list[dict], dict]:
    impl = impl.resolve()
    aspect_file, profile_file = impl / "aspects.py", impl / "aspect_profiles.py"
    if not aspect_file.is_file() or not profile_file.is_file():
        raise scoring.ScoringError("extractor directory must contain aspects.py and aspect_profiles.py")
    checkout_sha = _git(impl, "rev-parse", "HEAD")
    clean = _git(impl, "status", "--porcelain", "--untracked-files=no") == ""
    if split == "F2" and (not checkout_sha or not clean):
        raise scoring.ScoringError("F2 model must be from a clean, pinned Git checkout")
    accepted_sha = scoring.file_sha256(reviews)
    spec = scoring.check_frozen_final(freeze, accepted_sha, split)
    if spec and checkout_sha != spec[f"{role}_commit_sha"]:
        raise scoring.ScoringError("F2 model checkout SHA does not equal prospective freeze")
    allowed = scoring.load_accepted(reviews, split)
    sys.path.insert(0, str(impl))
    sys.path.insert(1, str(scoring.ROOT / "backend" / "sentiment-analysis"))
    try:
        aspects = importlib.import_module("aspects")
        profiles = importlib.import_module("aspect_profiles")
    except Exception as e:
        raise scoring.ScoringError("extractor could not be imported; verify environment") from e
    entries = []
    with reviews.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            rid = row["review_id"]
            kind = {a.id: a.kind for a in profiles.aspects_for(
                row["category"] or None, row["group"] or None
            )}
            try:
                extraction = aspects.extract(
                    [{"comment_id": rid, "content": row["review_text"],
                      "rating": row["stars"]}],
                    row["category"] or None, row["group"] or None,
                )
                pairs = sorted({
                    (kind[a["id"]], a["id"], pol) for a, pol, _ in aspects.iter_claims(extraction)
                })
            except (KeyError, TypeError, ValueError) as e:
                raise scoring.ScoringError(
                    "extractor returned an unrecognized claim; no predictions emitted"
                ) from e
            parsed = [{"kind": k, "aspect_id": a, "polarity": pol} for k, a, pol in pairs]
            scoring.parse_pairs(parsed, rid)
            entries.append({"review_id": rid, "pairs": parsed})
    if len(entries) != len(allowed):
        raise scoring.ScoringError("prediction coverage mismatch")
    code_hash = hashlib.sha256(
        (scoring.file_sha256(aspect_file) + scoring.file_sha256(profile_file)).encode()
    ).hexdigest()
    meta = {
        "phase": "4", "split": split, "role": role, "reviews": len(entries),
        "accepted_csv_sha256": accepted_sha,
        "model_checkout_sha": checkout_sha, "model_checkout_clean": clean,
        "aspect_code_combined_sha256": code_hash,
        "source": "actual extractor via aspects.extract and aspects.iter_claims",
        "labels_read": False,
        "production_adoption_approved": False,
    }
    return entries, meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reviews", required=True, type=Path)
    parser.add_argument("--split", required=True, choices=["D3", "V3", "F2"])
    parser.add_argument("--impl", required=True, type=Path)
    parser.add_argument("--role", required=True, choices=["baseline", "candidate"])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--metadata-out", required=True, type=Path)
    parser.add_argument("--freeze", type=Path)
    args = parser.parse_args()
    try:
        scoring._check_off_repo(args.reviews, args.out, args.metadata_out,
                                *([args.freeze] if args.freeze else []))
        if args.out.resolve() == args.metadata_out.resolve():
            raise scoring.ScoringError("prediction and metadata files must be distinct")
        if args.out.exists() or args.metadata_out.exists():
            raise scoring.ScoringError("refusing to overwrite any prediction or metadata")
        entries, meta = generate(args.reviews, args.impl, args.split,
                                 args.freeze, args.role)
        fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for item in entries:
                f.write(json.dumps(item, sort_keys=True) + "\n")
        meta["predictions_sha256"] = scoring.file_sha256(args.out)
        fd = os.open(args.metadata_out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, sort_keys=True)
            f.write("\n")
        print(json.dumps({"split": args.split, "role": args.role, "reviews": len(entries),
                          "model_checkout_sha": meta["model_checkout_sha"],
                          "production_adoption_approved": False}))
        return 0
    except (scoring.ScoringError, OSError) as e:
        parser.exit(2, f"Phase 4 prediction refused: {e}\n")


if __name__ == "__main__":
    raise SystemExit(main())
