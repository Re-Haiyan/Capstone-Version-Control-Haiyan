"""Sentiment evaluation of the deployed model (XLM-R ONNX) against the team's sentiment labels.

    D:\defaketive-train\Scripts\python.exe research\sentiment_eval.py

The sentiment model was not trained on these labels, so all labelled rows are valid evaluation data. Uses the cached
deployed predictions (research/cache/rules_train.json, rules_test.json: field "sent"). Reports accuracy, macro F1,
per-class precision/recall/F1, a confusion matrix, breakdowns by star rating, by product group and by whether the review
carries a product-issue flag, and a product-bootstrap interval for macro F1.
"""
import collections, json, pathlib, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import ROOT, load, rules_predictions

CLASSES = ("negative", "neutral", "positive")


def metrics(gold, pred):
    out = {}
    for c in CLASSES:
        tp = sum(1 for g, p in zip(gold, pred) if g == c and p == c); fp = sum(1 for g, p in zip(gold, pred) if g != c and p == c); fn = sum(1 for g, p in zip(gold, pred) if g == c and p != c)
        P = tp / (tp + fp) if tp + fp else 0; R = tp / (tp + fn) if tp + fn else 0
        out[c] = {"precision": round(P, 3), "recall": round(R, 3), "f1": round(2 * P * R / (P + R) if P + R else 0, 3), "support": tp + fn}
    out["macro_f1"] = round(float(np.mean([out[c]["f1"] for c in CLASSES])), 3); out["accuracy"] = round(float(np.mean([g == p for g, p in zip(gold, pred)])), 3)
    return out


def boot_macro(rows, gold, pred, n=500):
    rng = np.random.default_rng(0); products = sorted({r["product"] for r in rows}); idx = collections.defaultdict(list)
    for i, r in enumerate(rows): idx[r["product"]].append(i)
    vals = []
    for _ in range(n):
        pick = rng.choice(len(products), len(products)); sel = np.concatenate([idx[products[j]] for j in pick])
        vals.append(metrics([gold[i] for i in sel], [pred[i] for i in sel])["macro_f1"])
    return [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)]


result = {}
for split in ("train", "test"):
    rows = load(f"{split}_v3"); preds = rules_predictions(split)
    gold = [r["sentiment"].strip().lower() for r in rows]; pred = [preds[r["id"]]["sent"] for r in rows]
    entry = {"rows": len(rows), **metrics(gold, pred), "macro_f1_ci95_product_bootstrap": boot_macro(rows, gold, pred)}
    conf = collections.Counter((g, p) for g, p in zip(gold, pred)); entry["confusion_gold_by_pred"] = {g: {p: conf[(g, p)] for p in CLASSES} for g in CLASSES}
    entry["by_stars"] = {str(s): {"rows": sum(1 for r in rows if r["stars"] == s), "accuracy": round(float(np.mean([g == p for r, g, p in zip(rows, gold, pred) if r["stars"] == s] or [0])), 3)} for s in range(1, 6)}
    entry["by_group_macro_f1"] = {g: metrics([a for r, a in zip(rows, gold) if r["group"] == g], [b for r, b in zip(rows, pred) if r["group"] == g])["macro_f1"] for g in sorted({r["group"] for r in rows})}
    flagged = [i for i, r in enumerate(rows) if r["y"][:5].sum() > 0]; clean_ = [i for i in range(len(rows)) if i not in set(flagged)]
    entry["accuracy_with_issue_flag"] = round(float(np.mean([gold[i] == pred[i] for i in flagged])), 3); entry["accuracy_without_issue_flag"] = round(float(np.mean([gold[i] == pred[i] for i in clean_])), 3)
    # sentiment toward product vs courier: reviews flagged delivery only
    deliv_only = [i for i, r in enumerate(rows) if r["y"][5] and r["y"][:5].sum() == 0]
    entry["delivery_only_reviews"] = {"rows": len(deliv_only), "accuracy": round(float(np.mean([gold[i] == pred[i] for i in deliv_only] or [0])), 3)}
    # positive text with a product issue flag (a positive review can contain a real defect)
    pos_with_issue = [i for i in flagged if gold[i] == "positive"]
    entry["positive_reviews_with_issue_flag"] = {"rows": len(pos_with_issue), "predicted_positive": sum(1 for i in pos_with_issue if pred[i] == "positive")}
    result[split] = entry
json.dump(result, open(ROOT / "research" / "results" / "sentiment_eval.json", "w"), indent=1)
for split, e in result.items():
    print(f"\n[{split}] rows {e['rows']}  accuracy {e['accuracy']}  macro F1 {e['macro_f1']} CI95 {e['macro_f1_ci95_product_bootstrap']}")
    for c in CLASSES: print("  ", c, e[c])
    print("   confusion (gold -> pred):", e["confusion_gold_by_pred"]); print("   by stars:", {k: (v['rows'], v['accuracy']) for k, v in e["by_stars"].items()})
    print("   acc with issue flag", e["accuracy_with_issue_flag"], "without", e["accuracy_without_issue_flag"], "| delivery-only:", e["delivery_only_reviews"], "| positive+issue:", e["positive_reviews_with_issue_flag"])
