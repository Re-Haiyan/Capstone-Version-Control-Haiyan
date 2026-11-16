"""Experiment: does title category improve a light calibrator over original XLM-R?

Training/evaluation inputs are the repository's HISTORICAL team-supplied
SILVER sentiment labels. Provenance is unverified (annotation_provenance.md).
The old 846-row test set has been inspected before: it is descriptive ONLY.
No release/qualification claim can be made from this experiment.

Train and select on product-disjoint OOF folds in train_v3, with no text
vectorizer fitted on validation rows. Compare unchanged XLM-R predictions,
generic calibrated XLM-R and category-conditioned calibrated XLM-R on exactly
the same reviews. A missing/mismatched probability is a HARD ERROR.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, accuracy_score
from sklearn.model_selection import StratifiedGroupKFold

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
from common import load  # noqa: E402
from defaketive_sentiment.category_adapter import (  # noqa: E402
    CLASSES, REVISION, context_features, model_features, title_category
)

CACHE = ROOT / "research" / "cache" / "sentiment_probs.json"
SOURCE_MANIFEST = ROOT / "backend" / "sentiment-analysis" / "models" / "sentiment_onnx" / "xlmr_firecs_v1" / "manifest.json"
CATEGORY_SOURCE = ROOT / "backend" / "sentiment-analysis" / "defaketive_sentiment" / "product_category.py"


def read_rows(name, probabilities):
    rows = load(name)
    missing = [r["id"] for r in rows if r["id"] not in probabilities]
    if missing:
        raise ValueError(f"{len(missing)} {name} labels lack XLM-R probabilities: STOP, no imputation")
    for r in rows:
        raw = probabilities[r["id"]]
        if len(raw) != 3 or not np.isfinite(raw).all() or any(x < 0 or x > 1 for x in raw):
            raise ValueError("invalid cached XLM-R probability for " + r["id"])
        if r["sentiment"] not in CLASSES:
            raise ValueError("unexpected sentiment label in " + r["id"])
    return rows


def inputs(rows, cache):
    texts = [r["text"] for r in rows]
    titles = [r["product"] for r in rows]
    stars = [r["stars"] for r in rows]
    probs = np.asarray([cache[r["id"]] for r in rows], dtype=float)
    y = np.asarray([CLASSES.index(r["sentiment"]) for r in rows], dtype=int)
    return texts, titles, stars, probs, y


def feature_bundle(train, test, cache, include_category):
    tx, titles, stars, probs, _ = inputs(train, cache)
    ex, etitles, estars, eprobs, _ = inputs(test, cache)
    word = TfidfVectorizer(analyzer="word", ngram_range=(1, 2),
                           min_df=2, max_features=22000, sublinear_tf=True)
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5),
                           min_df=2, max_features=30000, sublinear_tf=True)
    xt_word = word.fit_transform(tx)
    xe_word = word.transform(ex)
    xt_char = char.fit_transform(tx)
    xe_char = char.transform(ex)
    def dense(star_values, raw_probs):
        onehot = [[float(int(star) == i) for i in range(1, 6)] for star in star_values]
        return csr_matrix(np.column_stack((raw_probs, np.asarray(onehot, dtype=float))))
    xt_parts = [xt_word, xt_char, dense(stars, probs)]
    xe_parts = [xe_word, xe_char, dense(estars, eprobs)]
    context = DictVectorizer(sparse=True)
    category_counts = Counter(title_category(t)[0] for t in titles)
    supported = {c for c, n in category_counts.items() if c != "other" and n >= 50}
    if include_category:
        xt_context = [context_features(t, title, supported) for t, title in zip(tx, titles)]
        xe_context = [context_features(t, title, supported) for t, title in zip(ex, etitles)]
        xt_parts.append(context.fit_transform(xt_context))
        xe_parts.append(context.transform(xe_context))
    return (
        hstack(xt_parts, format="csr"),
        hstack(xe_parts, format="csr"),
        (word, char, context, supported)
    )


def fit_predict(train, test, cache, include_category):
    xt, xe, bundle = feature_bundle(train, test, cache, include_category)
    _, _, _, _, y = inputs(train, cache)
    classifier = LogisticRegression(
        C=2.0, class_weight="balanced", max_iter=1100, solver="lbfgs"
    )
    classifier.fit(xt, y)
    return classifier.predict(xe), (classifier, bundle)


def score(y, pred):
    f1 = f1_score(y, pred, labels=range(3), average=None, zero_division=0)
    return {
        "rows": int(len(y)), "accuracy": round(float(accuracy_score(y, pred)), 4),
        "macro_f1": round(float(f1.mean()), 4),
        "per_class_f1": {c: round(float(v), 4) for c, v in zip(CLASSES, f1)},
    }


def paired_interval(rows, gold, baseline, candidate, reps=400, seed=2026):
    """Cluster bootstrap for macro-F1 difference; never review-row bootstrap."""
    group_idx = defaultdict(list)
    for i, row in enumerate(rows):
        group_idx[" ".join(row["product"].lower().split())].append(i)
    groups = sorted(group_idx)
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(reps):
        sample = rng.choice(len(groups), size=len(groups), replace=True)
        ids = np.concatenate([group_idx[groups[j]] for j in sample])
        b = f1_score(gold[ids], baseline[ids], labels=range(3), average="macro", zero_division=0)
        c = f1_score(gold[ids], candidate[ids], labels=range(3), average="macro", zero_division=0)
        values.append(float(c - b))
    return [round(float(np.percentile(values, pct)), 4) for pct in (2.5, 50, 97.5)]


def evaluate(name, rows, cache, generic=None, category=None):
    _, _, _, p, y = inputs(rows, cache)
    base = p.argmax(axis=1)
    result = {"raw_xlmr": score(y, base)}
    if generic is not None:
        result["generic_calibrator"] = score(y, generic)
    if category is not None:
        result["category_calibrator"] = score(y, category)
        result["paired_category_minus_raw_ci95"] = paired_interval(rows, y, base, category)
        if generic is not None:
            result["paired_category_minus_generic_ci95"] = paired_interval(rows, y, generic, category)
        result["by_group"] = {}
        by_group = defaultdict(list)
        for i, row in enumerate(rows):
            _, group = title_category(row["product"])
            by_group[group].append(i)
        for group, ids in sorted(by_group.items()):
            if len(ids) >= 30:
                result["by_group"][group] = {
                    "rows": len(ids), "baseline_macro_f1": score(y[ids], base[ids])["macro_f1"],
                    "category_macro_f1": score(y[ids], category[ids])["macro_f1"],
                }
        result["candidate_changed_labels"] = int((category != base).sum())
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="", help="metrics JSON only; never raw reviews")
    parser.add_argument("--write-candidate", default="", help="local research artifact only; never GitHub upload")
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()
    if not CACHE.is_file() or not SOURCE_MANIFEST.is_file():
        raise SystemExit("missing cached XLM-R probabilities or pinned encoder manifest")
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    train = read_rows("train_v3", cache)
    historical = read_rows("test_v3", cache)
    _, _, _, _, y = inputs(train, cache)
    if len(train) < 200 or len(set(row["product"] for row in train)) < 20:
        raise SystemExit("insufficient historical training labels/products")
    train_titles = {" ".join(row["product"].lower().split()) for row in train}
    test_titles = {" ".join(row["product"].lower().split()) for row in historical}
    overlaps = sorted(train_titles & test_titles)
    if overlaps:
        raise SystemExit(f"product leakage between historical train and test: {len(overlaps)} titles")
    groups = [" ".join(row["product"].lower().split()) for row in train]
    folds = StratifiedGroupKFold(n_splits=args.folds, shuffle=True, random_state=2026)
    predictions = {
        "generic": np.full(len(train), -1, dtype=int),
        "category": np.full(len(train), -1, dtype=int),
    }
    for fold_number, (tr, val) in enumerate(folds.split(np.zeros(len(train)), y, groups), start=1):
        fit = [train[i] for i in tr]
        target = [train[i] for i in val]
        for name, enabled in (("generic", False), ("category", True)):
            pred, _ = fit_predict(fit, target, cache, enabled)
            predictions[name][val] = pred
        print(f"Completed training-only, product-disjoint fold {fold_number}/{args.folds}", flush=True)
    if any((v < 0).any() for v in predictions.values()):
        raise SystemExit("cross-validation did not score every training review")
    cv = evaluate("train_oof", train, cache, predictions["generic"], predictions["category"])
    hist_pred = {}
    for name, enabled in (("generic", False), ("category", True)):
        hist_pred[name], _ = fit_predict(train, historical, cache, enabled)
    historic = evaluate("historical_test", historical, cache, hist_pred["generic"], hist_pred["category"])
    original = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    report = {
        "purpose": "research_only_not_independent_gold",
        "labels": "team_supplied_unverified_provenance_silver",
        "historical_test_status": "previously_inspected_for_development_not_an_independent_gate",
        "encoder_manifest_sha256": original["files"]["model.onnx"],
        "cached_probabilities_provenance": "not_cryptographically_bound_to_this_encoder",
        "train_products": len(train_titles),
        "historical_products": len(test_titles),
        "train_rows": len(train),
        "historical_rows": len(historical),
        "category_detection": {
            "source": "runtime_title_classifier_not_manual_evaluation_key",
            "other_count": sum(title_category(x["product"])[0] == "other" for x in train),
        },
        "train_oof": cv,
        "historical_test_descriptive": historic,
        "qualified_for_integration": False,
        "enable_production_predictions": False,
    }
    print("CATEGORY_ADAPTER_METRICS=" + json.dumps(report, separators=(",", ":"), sort_keys=True), flush=True)
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.write_candidate:
        # This still is an UNQUALIFIED model: no live switch exists.
        import joblib
        classifier, (word, char, context, supported) = fit_predict(train, historical[:1], cache, True)[1]
        artifact = Path(args.write_candidate)
        artifact.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "revision": REVISION, "classes": CLASSES, "word": word, "char": char,
            "context_vectorizer": context, "supported_categories": sorted(supported),
            "classifier": classifier,
        }, artifact, compress=3)
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        manifest = {
            "revision": REVISION, "stage": "research_shadow",
            "qualified_for_integration": False,
            "artifact_sha256": digest,
            "base_encoder_sha256": original["files"]["model.onnx"],
            "training_labels_provenance": "silver_unverified",
            "probability_cache_provenance": "unverified",
            "train_oof_category_macro_f1": cv["category_calibrator"]["macro_f1"],
            "train_oof_generic_macro_f1": cv["generic_calibrator"]["macro_f1"],
            "historical_test_category_macro_f1": historic["category_calibrator"]["macro_f1"],
            "source_code_sha256": hashlib.sha256(CATEGORY_SOURCE.read_bytes()).hexdigest(),
            "production_activation_allowed": False,
        }
        artifact.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print("Local-only research adapter written, NOT qualified:", artifact)


if __name__ == "__main__":
    main()
