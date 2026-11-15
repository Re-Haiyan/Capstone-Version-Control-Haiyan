"""Phase 5B: development-only label-quality sensitivity using a lexical classifier.

NOT XLM-RoBERTa, NOT an independent test, NOT product-ID disjoint.
The actual Phase 4 embedding caches and product URL maps are not in GitHub.
Never reads frozen final test, Phase 3 confirmation or heldout v2.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "phase5"))
import label_quality_audit as qa
import training_ablation_manifest as ta

LABELS = ("negative", "neutral", "positive")
SEEDS = (11, 12, 13)
VARIANTS = ("baseline_weight", "exclude_disagreement_weight", "s4_downweight_sensitivity_weight")


def normalized_title(title):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", title).lower(), re.UNICODE))


def load_data(root=ROOT):
    manifest = ta.make_manifest(root)
    source = {}
    for name in ("dev_pool_sheet.csv", "neutral_candidate_pool.csv"):
        source.update(qa.read(root / "annotation" / name))
    audited = {}
    for split, original, labelled, n in qa.PAIRS:
        audited.update({r["id"]: r for r in qa.audit_pair(root, split, original, labelled, n)})
    second = qa.read(root / "phase5" / "gpt6_second_ai_labels_v1.csv")
    reviewed_groups = {normalized_title(source[rid]["product"]) for rid in second
                       if normalized_title(source[rid]["product"])}
    rows, dropped = [], Counter()
    for m in manifest:
        if not m["three_class_eligible"]:
            dropped["mixed_or_unclear"] += 1
            continue
        s = source[m["id"]]
        group = normalized_title(s["product"])
        if not group:
            dropped["no_product_title"] += 1
            continue
        rows.append({
            "text": s["review_text"], "label": m["claude_v1_label"],
            "group": group, "split": m["split"],
            "language": s["language_hint"].lower().strip(),
            "tag_shape": audited[m["id"]]["tag_shape"],
            "reviewed_group": group in reviewed_groups,
            "weights": {v: float(m[v]) for v in VARIANTS},
        })
    if len(rows) < 1000 or len(reviewed_groups) < 30:
        raise RuntimeError("Insufficient known-title groups to evaluate")
    stats = {
        "source_annotation_rows": len(manifest),
        "rows_with_three_class_and_product_title": len(rows),
        "dropped": dict(dropped),
        "distinct_normalized_title_groups": len({r["group"] for r in rows}),
        "second_ai_reviewed_title_groups_excluded_from_evaluation": len(reviewed_groups),
        "unreviewed_evaluation_rows": sum(not r["reviewed_group"] for r in rows),
    }
    return rows, stats


def scores(gold, pred):
    if len(gold) != len(pred):
        raise ValueError("prediction and reference lengths differ")
    if not gold:
        return {"n": 0, "macro_f1": None, "support": {}, "classes": {}}
    p, r, f, s = precision_recall_fscore_support(gold, pred, labels=LABELS, zero_division=0)
    return {
        "n": len(gold),
        "accuracy": float(accuracy_score(gold, pred)),
        "macro_f1": float(np.mean(f)),
        "support": {k: int(v) for k, v in zip(LABELS, s)},
        "classes": {k: {"precision": float(a), "recall": float(b), "f1": float(c)}
                    for k, a, b, c in zip(LABELS, p, r, f)},
        "confusion": confusion_matrix(gold, pred, labels=LABELS).tolist(),
    }


def subsets(rows):
    idx = [i for i, r in enumerate(rows) if not r["reviewed_group"]]
    return {
        "all_unreviewed": idx,
        "natural_dev_unreviewed": [i for i in idx if rows[i]["split"] == "dev"],
        "non_tag_unreviewed": [i for i in idx if not rows[i]["tag_shape"]],
        "english_unreviewed": [i for i in idx if rows[i]["language"] == "english"],
        "filipino_unreviewed": [i for i in idx if rows[i]["language"] == "filipino"],
        "taglish_unreviewed": [i for i in idx if rows[i]["language"] == "taglish"],
        "filipino_taglish_unreviewed": [i for i in idx if rows[i]["language"] in ("filipino", "taglish")],
    }


def compare(rows, seeds=SEEDS, folds=5):
    texts = np.asarray([r["text"] for r in rows])
    gold = np.asarray([r["label"] for r in rows])
    groups = np.asarray([r["group"] for r in rows])
    masks = subsets(rows)
    weights = {v: np.asarray([r["weights"][v] for r in rows]) for v in VARIANTS}
    output = {"seeds": list(seeds), "labels": list(LABELS), "per_seed": {}}
    for seed in seeds:
        splits = list(StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed).split(texts, gold, groups))
        predictions = {v: np.empty(len(rows), dtype=object) for v in VARIANTS}
        filled = np.zeros(len(rows), dtype=int)
        for train, valid in splits:
            if set(groups[train]) & set(groups[valid]):
                raise AssertionError("Normalized title leakage")
            features = FeatureUnion([
                ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2,
                                         max_features=22000, sublinear_tf=True)),
                ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                         min_df=2, max_features=30000, sublinear_tf=True)),
            ])
            x_train = features.fit_transform(texts[train])
            x_valid = features.transform(texts[valid])
            for variant in VARIANTS:
                weight = weights[variant][train]
                keep = weight > 0
                if set(gold[train][keep]) != set(LABELS):
                    raise ValueError("Class lost in training-fold ablation")
                clf = LinearSVC(C=0.5, class_weight="balanced", max_iter=3000, dual="auto", random_state=seed)
                clf.fit(x_train[keep], gold[train][keep], sample_weight=weight[keep])
                predictions[variant][valid] = clf.predict(x_valid)
            filled[valid] += 1
        if not np.all(filled == 1):
            raise AssertionError("One OOF prediction required per row")
        output["per_seed"][str(seed)] = {
            variant: {name: scores(gold[ids].tolist(), predictions[variant][ids].tolist())
                      for name, ids in masks.items()}
            for variant in VARIANTS
        }
        print("seed", seed, "natural macro-F1",
              {v: round(output["per_seed"][str(seed)][v]["natural_dev_unreviewed"]["macro_f1"], 4)
               for v in VARIANTS}, flush=True)
    output["mean"] = {}
    for variant in VARIANTS:
        output["mean"][variant] = {}
        for name in masks:
            vals = [output["per_seed"][str(seed)][variant][name] for seed in seeds]
            scores_ = [x["macro_f1"] for x in vals if x["macro_f1"] is not None]
            neu = [x["classes"]["neutral"]["f1"] for x in vals if x["n"]]
            output["mean"][variant][name] = {
                "n": vals[0]["n"], "support": vals[0]["support"],
                "macro_f1": float(np.mean(scores_)) if scores_ else None,
                "neutral_f1": float(np.mean(neu)) if neu else None,
                "std_macro_f1": float(np.std(scores_)) if scores_ else None,
            }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path("/tmp/phase5b-results"))
    parser.add_argument("--seeds", nargs="+", type=int, default=list(SEEDS))
    args = parser.parse_args()
    rows, stats = load_data()
    result = compare(rows, seeds=tuple(args.seeds))
    result["data"] = stats
    result["limitations"] = [
        "Text-only lexical baseline; NO XLM-RoBERTa improvement is measured.",
        "Source marketplace product-link mappings are missing; grouping uses normalized titles only.",
        "All references are Claude-labelled development data; no independent ground truth.",
        "Exclude all GPT-6-reviewed title groups from validation; GPT-6 disagreement affects training weights only.",
        "The same validation folds compare three predeclared experimental data-weight policies.",
        "No original labels, policies, weights, deployed models, or locked tests changed.",
    ]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "sensitivity.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for variant in VARIANTS:
        nat = result["mean"][variant]["natural_dev_unreviewed"]
        non = result["mean"][variant]["non_tag_unreviewed"]
        print(variant, "natural F1", nat["macro_f1"], "neutral F1", nat["neutral_f1"],
              "non-tag F1", non["macro_f1"], flush=True)


if __name__ == "__main__":
    main()
