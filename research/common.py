"""Shared helpers for the research experiments: data, product-grouped folds, metrics, product-level bootstrap.

Rules: the 846-row test file is HISTORICAL (it was inspected during earlier development). Experiments here select
and tune on grouped cross-validation over the training file only; historical test numbers are reported separately
and never used to choose anything.
"""
from __future__ import annotations

import csv
import json
import pathlib
import re

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "research" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
FLAGS5 = ("defect", "counterfeit", "safety", "not_as_described", "quality")
FLAGS6 = FLAGS5 + ("delivery",)


def load(name: str) -> list[dict]:
    """High-confidence labelled rows of evaluation/annotated/<name>.csv with a 0/1 vector over FLAGS6."""
    key = {r["id"]: r for r in csv.DictReader(open(ROOT / "evaluation/annotated" / f"{name}_key.csv", encoding="utf-8-sig"))}
    rows = []
    for r in csv.DictReader(open(ROOT / "evaluation/annotated" / f"{name}.csv", encoding="utf-8-sig")):
        if r["confidence"].strip().lower() != "high" or not r["flags"].strip():
            continue
        gold = {f for f in r["flags"].replace(" ", "").split(";") if f in FLAGS6}
        k = key.get(r["id"], {})
        rows.append({"id": r["id"], "stars": int(r["stars"]), "product": " ".join(r["product"].split()), "text": r["review_text"],
                     "sentiment": r["sentiment"], "category": k.get("category", ""), "group": k.get("group", ""),
                     "y": np.array([1 if f in gold else 0 for f in FLAGS6], dtype=int)})
    return rows


def model_text(r: dict, with_context: bool = True) -> str:
    kind = r["category"].replace("_", " ") if r["category"] else "product"
    return f"{kind} | {r['product'][:100]} | {r['text']}" if with_context else r["text"]


def grouped_folds(rows: list[dict], n_splits: int = 5, seed: int = 0, flags=FLAGS6):
    """Product-grouped folds that keep the rare flags spread out (stratified on the rarest flag in each row)."""
    from sklearn.model_selection import StratifiedGroupKFold

    order = ("safety", "counterfeit", "quality", "delivery", "defect", "not_as_described")
    strat = []
    for r in rows:
        label = "none"
        for f in order:
            if r["y"][FLAGS6.index(f)]:
                label = f
                break
        strat.append(label)
    groups = [r["product"] for r in rows]
    folds = list(StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed).split(np.zeros(len(rows)), strat, groups))
    return folds


def prf(y: np.ndarray, pred: np.ndarray) -> dict:
    tp = int(((pred == 1) & (y == 1)).sum()); fp = int(((pred == 1) & (y == 0)).sum()); fn = int(((pred == 0) & (y == 1)).sum()); tn = int(((pred == 0) & (y == 0)).sum())
    p = tp / (tp + fp) if tp + fp else 0.0; r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": p, "recall": r, "f1": f, "support": tp + fn, "predicted": tp + fp}


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def product_bootstrap_f1(rows: list[dict], pred: np.ndarray, k: int, n_boot: int = 1000, seed: int = 0):
    """95% interval for F1 of flag k, resampling PRODUCTS (not reviews) with replacement."""
    rng = np.random.default_rng(seed)
    products = sorted({r["product"] for r in rows})
    index = {p: [] for p in products}
    for i, r in enumerate(rows):
        index[r["product"]].append(i)
    y = np.array([r["y"][k] for r in rows])
    scores = []
    for _ in range(n_boot):
        pick = rng.choice(len(products), len(products), replace=True)
        idx = np.concatenate([index[products[j]] for j in pick])
        s = prf(y[idx], pred[idx])
        if s["support"] > 0:
            scores.append(s["f1"])
    if not scores:
        return (0.0, 0.0)
    return (float(np.percentile(scores, 2.5)), float(np.percentile(scores, 97.5)))


def paired_bootstrap_diff(rows: list[dict], pred_a: np.ndarray, pred_b: np.ndarray, k: int, n_boot: int = 1000, seed: int = 0):
    """95% interval for F1(a) - F1(b) on the same rows, resampling products."""
    rng = np.random.default_rng(seed)
    products = sorted({r["product"] for r in rows})
    index = {p: [] for p in products}
    for i, r in enumerate(rows):
        index[r["product"]].append(i)
    y = np.array([r["y"][k] for r in rows])
    diffs = []
    for _ in range(n_boot):
        pick = rng.choice(len(products), len(products), replace=True)
        idx = np.concatenate([index[products[j]] for j in pick])
        if y[idx].sum() == 0:
            continue
        diffs.append(prf(y[idx], pred_a[idx])["f1"] - prf(y[idx], pred_b[idx])["f1"])
    return (float(np.percentile(diffs, 2.5)), float(np.mean(diffs)), float(np.percentile(diffs, 97.5)))


def best_threshold(y: np.ndarray, p: np.ndarray, grid=None, beta: float = 1.0) -> float:
    """One threshold per flag on a small predefined grid, by F-beta."""
    grid = grid if grid is not None else np.round(np.arange(0.1, 0.91, 0.05), 2)
    best, best_s = 0.5, -1.0
    for t in grid:
        s = prf(y, (p >= t).astype(int))
        pr, rc = s["precision"], s["recall"]
        f = (1 + beta ** 2) * pr * rc / (beta ** 2 * pr + rc) if pr + rc else 0.0
        if f > best_s:
            best, best_s = float(t), f
    return best


def rules_predictions(split: str) -> dict:
    """Deployed rules' flags per id: research/cache/rules_<split>.json (made by research/dump_rules_cache.py)."""
    return json.load(open(CACHE / f"rules_{split}.json"))
