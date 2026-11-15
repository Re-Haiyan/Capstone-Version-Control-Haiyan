"""Score an extractor version on an annotated Phase 3 split. Reads only the annotated sheet and the manifest; never the locked pack.

    python research/product_specific_conclusions/phase3/eval_extractor.py --impl <dir holding aspects.py and aspect_profiles.py> --split D1 [--errors out.csv]

`--impl` defaults to backend/. Reports precision, recall, F1 and the counts for T0 (all kinds), T1 (product), T2 (service), T3 (trust),
by profile and by language, with the time per review. `--errors` writes the mis-extractions: do that for D1 only (D2 and F are not to be inspected).
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
KINDS = {"T0": None, "T1": "product", "T2": "service", "T3": "trust"}


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    f = 2 * p * r / (p + r) if tp else (0.0 if tp + fp + fn else float("nan"))
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3)}


def run(impl: Path, split: str, errors: Path | None = None) -> dict:
    sys.path.insert(0, str(impl))
    sys.path.insert(1, str(ROOT / "backend"))
    import aspects  # noqa: E402
    import aspect_profiles  # noqa: E402

    manifest = {r["item_id"]: r for r in csv.DictReader(open(HERE / "data" / "data_manifest.csv", encoding="utf-8-sig"))}
    rows = list(csv.DictReader(open(HERE / "annotated" / f"sheet_{split}_annotated.csv", encoding="utf-8-sig")))
    counts = {name: collections.Counter() for name in KINDS}
    by_profile = collections.defaultdict(lambda: collections.Counter())
    by_language = collections.defaultdict(lambda: collections.Counter())
    bad = []
    start = time.perf_counter()
    for r in rows:
        m = manifest[r["item_id"]]
        result = aspects.extract([{"comment_id": r["item_id"], "content": r["review_text"], "rating": r["stars"]}], m["category"] or None, m["group"] or None)
        kinds = {a.id: a.kind for a in aspect_profiles.aspects_for(m["category"] or None, m["group"] or None)}
        system = {(row["id"], pol) for row, pol, _ in aspects.iter_claims(result)}
        ref = set() if r["features"] == "none" else {tuple(x.split(":")) for x in r["features"].split(";")}
        for a, p in ref | system:
            kind = kinds[a]  # every aspect is in the profile (the labels were validated against it)
            outcome = "tp" if (a, p) in ref and (a, p) in system else "fn" if (a, p) in ref else "fp"
            for name, wanted in KINDS.items():
                if wanted is None or wanted == kind:
                    counts[name][outcome] += 1
            by_profile[m["profile"]][outcome] += 1
            by_language[m["language"]][outcome] += 1
            if outcome != "tp":
                bad.append({"item_id": r["item_id"], "outcome": outcome, "aspect": a, "polarity": p, "profile": m["profile"], "stars": r["stars"], "text": r["review_text"][:300]})
    elapsed = time.perf_counter() - start
    if errors:
        with open(errors, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(bad[0].keys()) if bad else ["item_id"])
            w.writeheader()
            w.writerows(bad)
    return {
        "split": split, "impl": str(impl), "rules_version": aspects.ASPECT_RULES_VERSION, "reviews": len(rows),
        "tasks": {k: prf(c["tp"], c["fp"], c["fn"]) for k, c in counts.items()},
        "by_profile": {k: {"reviews": sum(1 for r in rows if manifest[r["item_id"]]["profile"] == k), **prf(c["tp"], c["fp"], c["fn"])} for k, c in sorted(by_profile.items())},
        "by_language": {k: {"reviews": sum(1 for r in rows if manifest[r["item_id"]]["language"] == k), **prf(c["tp"], c["fp"], c["fn"])} for k, c in sorted(by_language.items())},
        "ms_per_review": round(1000 * elapsed / max(1, len(rows)), 2),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--impl", type=Path, default=ROOT / "backend")
    parser.add_argument("--split", required=True, choices=["D1", "D2", "F"])
    parser.add_argument("--errors", type=Path, default=None)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()
    out = run(args.impl, args.split, args.errors)
    text = json.dumps(out, indent=1)
    if args.json:
        args.json.write_text(text, encoding="utf-8")
    print(text)
