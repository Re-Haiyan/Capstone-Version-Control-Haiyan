"""Datasets for the XLM-R optimisation study. Nothing here changes a source file; FiReCS is restored from git history (commit 5ea027e).

Evidence classes (see research/final_research_integrity_audit.md): FiReCS = published, human-annotated by its authors (CC BY 4.0);
every marketplace file is "team-supplied labels of unverified provenance"; no independent human-verified marketplace set exists.
"""
from __future__ import annotations

import csv, hashlib, pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
X = ROOT / "research" / "xlmr_optimization"
DATA = X / "data"
LABELS = ("negative", "neutral", "positive")
FIRECS_COMMIT = "5ea027e04acc3832b9f5478695683ed4f5b6e2cf"
FIRECS_SHA = {"train": "9ca5ef80b8f93836f5966a1db8d017ebbd474e4b615468269cb0ba9d3778eb39", "test": "6c172b8a52ad5d320d445bcf2229557de103587673582767cc59f8fc42754875"}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def firecs_path(split: str) -> pathlib.Path:
    target = DATA / "firecs" / f"FiReCS_{split}_set.csv"
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        blob = subprocess.run(["git", "show", f"{FIRECS_COMMIT}:sentiment-analysis/data/firecs/FiReCS_{split}_set.csv"], cwd=ROOT, capture_output=True, check=True).stdout
        target.write_bytes(blob)
    assert sha256(target) == FIRECS_SHA[split], f"FiReCS {split} does not match the published hash"
    return target


def norm_text(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", (t or "").lower())).strip()


def load_firecs(split: str) -> list[dict]:
    rows = []
    for i, r in enumerate(csv.DictReader(open(firecs_path(split), encoding="utf-8"))):
        rows.append({"id": f"F{split[0].upper()}{i:05d}", "set": f"firecs_{split}", "text": r["review"], "label": LABELS[int(float(r["label"]))], "product": "", "stars": 0, "group": "", "conf": "published"})
    return rows


def _read(path, name, key=None):
    rows = []
    for r in csv.DictReader(open(ROOT / path, encoding="utf-8-sig")):
        if not r.get("sentiment"):
            continue
        k = (key or {}).get(r["id"], {})
        rows.append({"id": r["id"], "set": name, "text": r["review_text"], "label": r["sentiment"].strip().lower(), "product": " ".join(r.get("product", "").split()),
                     "stars": int(float(r["stars"] or 0)), "group": k.get("group", ""), "conf": r["confidence"].strip().lower()})
    return rows


def load_marketplace() -> dict[str, list[dict]]:
    """Team-supplied sentiment labels, by file (high and low confidence kept; filter on `conf`)."""
    def key(p):
        return {r["id"]: r for r in csv.DictReader(open(ROOT / p, encoding="utf-8-sig"))}
    ann = "evaluation/annotated/"
    return {
        "market_train_v3": _read(ann + "train_v3.csv", "market_train_v3", key(ann + "train_v3_key.csv")),
        "market_test_v3": _read(ann + "test_v3.csv", "market_test_v3", key(ann + "test_v3_key.csv")),
        "market_fresh": _read("evaluation/fresh/label_batch_fresh.csv", "market_fresh", key("evaluation/fresh/label_batch_fresh_key.csv")),
        "market_fresh2": _read("evaluation/fresh2/label_batch_fresh2.csv", "market_fresh2", key("evaluation/fresh2/label_batch_fresh2_key.csv")),
        "market_gold200": _read("evaluation/gold_labels_200.csv", "market_gold200"),
        "market_heldout100": _read("evaluation/heldout_labels_100.csv", "market_heldout100"),
    }
