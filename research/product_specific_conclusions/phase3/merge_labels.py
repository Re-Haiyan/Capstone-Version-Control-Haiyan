"""Merge typed Claude-assisted labels (raw/labels_<split>.py) into annotated sheets, validating every aspect against the row's profile vocabulary.

    python research/product_specific_conclusions/phase3/merge_labels.py D1 D2        (F only after the extractor is frozen)
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))
import aspect_profiles as ap  # noqa: E402

PROVENANCE = {
    "annotator": "Claude (Claude-assisted annotation). Not ChatGPT, not a human.",
    "model_version": "Claude Sonnet 5.5 (claude-sonnet-5-5)",
    "interface": "Claude Code, VS Code extension session",
    "date": "2026-11-15",
    "policy": "annotation_process_record.md interpretation rules 1-6 (ai_annotation/claude_session_1), plus: label-prefixed prompt answers count as the reviewer's; "
              "bare thanks to a seller or rider is not a statement; the absence of a problem ('not irritating') is a positive statement",
    "human_review_of_labels": "none",
    "blindness": "labelled from review text only; the extractor was not run on these rows before labelling; "
                 "D2 extractor output is not inspected until a candidate is frozen",
}


def load(path: Path):
    spec = importlib.util.spec_from_file_location("labels", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def merge(split: str) -> None:
    labels = load(HERE / "raw" / f"labels_{split}.py")
    with open(HERE / "data" / f"sheet_{split}.csv", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    manifest = {r["item_id"]: r for r in csv.DictReader(open(HERE / "data" / "data_manifest.csv", encoding="utf-8-sig"))}
    problems = []
    for r in rows:
        num = r["item_id"].split("-")[1]
        m = manifest[r["item_id"]]
        valid = {a.id for a in ap.aspects_for(m["category"] or None, m["group"] or None)}
        pairs = []
        for token in labels.L.get(num, "").split():
            aspect, _, pol = token.partition(":")
            if aspect not in valid:
                problems.append((r["item_id"], aspect))
            pairs.append(f"{aspect}:{'positive' if pol == 'P' else 'negative'}")
        r["features"] = ";".join(dict.fromkeys(pairs)) if pairs else "none"
        r["note"] = "menu-tag list ignored" if num in labels.MENU else ""
    unknown = [n for n in labels.L if f"{split}-{n}" not in {r["item_id"] for r in rows}]
    if problems or unknown:
        raise SystemExit(f"{split}: not in the vocabulary {problems}; unknown ids {unknown}")
    out = HERE / "annotated" / f"sheet_{split}_annotated.csv"
    with open(out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(split, len(rows), "rows;", sum(r["features"] != "none" for r in rows), "with a reference feature ->", out.name)


if __name__ == "__main__":
    for s in sys.argv[1:] or ["D1", "D2"]:
        merge(s)
    prov = dict(PROVENANCE, input_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in sorted((HERE / "data").glob("sheet_*.csv")) if p.name != "sheet_F.csv"})
    (HERE / "annotated" / "provenance.json").write_text(json.dumps(prov, indent=1, ensure_ascii=False), encoding="utf-8")
