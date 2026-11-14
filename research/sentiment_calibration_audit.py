"""Audit of the sentiment calibrator: stability across product groups, shortcut learning on stars, delivery-only reviews.

    D:\\defaketive-train\\Scripts\\python.exe research\\sentiment_calibration_audit.py

All predictions for the calibrator are OUT-OF-FOLD (product-grouped 5-fold on the training file); the historical test is
scored once with a model trained on the training file. Sentiment labels are the team-supplied ones (provenance unverified).
Feature ablations decide whether the star rating is a shortcut: if "probabilities + text" matches "probabilities + text +
stars", the stars are not carrying the gain.
"""
import json, pathlib, sys
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import CACHE, ROOT, grouped_folds, load

CL = ("negative", "neutral", "positive")
tr, te = load("train_v3"), load("test_v3"); SP = json.load(open(CACHE / "sentiment_probs.json"))
y_tr = np.array([CL.index(r["sentiment"].strip().lower()) for r in tr]); y_te = np.array([CL.index(r["sentiment"].strip().lower()) for r in te])
P_tr = np.array([SP[r["id"]] for r in tr]); P_te = np.array([SP[r["id"]] for r in te])
S_tr = np.array([[r["stars"] == s for s in range(1, 6)] for r in tr], dtype=float); S_te = np.array([[r["stars"] == s for s in range(1, 6)] for r in te], dtype=float)


def macro(y, p):
    f = []
    for c in range(3):
        tp = ((p == c) & (y == c)).sum(); fp = ((p == c) & (y != c)).sum(); fn = ((p != c) & (y == c)).sum()
        f.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return float(np.mean(f)), f


def features(kind, rows_fit, rows_other, P_fit, P_other, S_fit, S_other):
    parts_fit, parts_other = [], []
    if "text" in kind:
        vw = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True); vc = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
        t_fit = [r["text"] for r in rows_fit]; t_other = [r["text"] for r in rows_other]
        parts_fit += [vw.fit_transform(t_fit), vc.fit_transform(t_fit)]; parts_other += [vw.transform(t_other), vc.transform(t_other)]
    dense_fit, dense_other = [], []
    if "probs" in kind:
        dense_fit.append(P_fit); dense_other.append(P_other)
    if "stars" in kind:
        dense_fit.append(S_fit); dense_other.append(S_other)
    if dense_fit:
        parts_fit.append(csr_matrix(np.hstack(dense_fit))); parts_other.append(csr_matrix(np.hstack(dense_other)))
    return hstack(parts_fit).tocsr(), hstack(parts_other).tocsr()


KINDS = ["probs", "probs+stars", "probs+text", "probs+stars+text", "stars", "text"]
folds = grouped_folds(tr, 5, seed=0)
out = {"ablation": {}}
oof = {}
for kind in KINDS:
    pred = np.zeros(len(tr), dtype=int)
    for a, b in folds:
        Xa, Xb = features(kind, [tr[i] for i in a], [tr[i] for i in b], P_tr[a], P_tr[b], S_tr[a], S_tr[b])
        pred[b] = LogisticRegression(C=2.0, class_weight="balanced", max_iter=3000).fit(Xa, y_tr[a]).predict(Xb)
    Xa, Xe = features(kind, tr, te, P_tr, P_te, S_tr, S_te)
    pe = LogisticRegression(C=2.0, class_weight="balanced", max_iter=3000).fit(Xa, y_tr).predict(Xe)
    oof[kind] = pred
    out["ablation"][kind] = {"cv_macro_f1": round(macro(y_tr, pred)[0], 3), "historical_test_macro_f1": round(macro(y_te, pe)[0], 3), "cv_neutral_f1": round(macro(y_tr, pred)[1][1], 3)}
deployed = P_tr.argmax(1)
out["ablation"]["deployed_argmax"] = {"cv_macro_f1": round(macro(y_tr, deployed)[0], 3), "historical_test_macro_f1": round(macro(y_te, P_te.argmax(1))[0], 3), "cv_neutral_f1": round(macro(y_tr, deployed)[1][1], 3)}

best = oof["probs+stars+text"]
# stability by product group (out-of-fold)
groups = sorted({r["group"] for r in tr}); out["by_group"] = {}
for g in groups:
    idx = [i for i, r in enumerate(tr) if r["group"] == g]
    if len(idx) < 40:
        continue
    out["by_group"][g] = {"rows": len(idx), "deployed_macro_f1": round(macro(y_tr[idx], deployed[idx])[0], 3), "calibrated_macro_f1": round(macro(y_tr[idx], best[idx])[0], 3),
                          "calibrated_neutral_f1": round(macro(y_tr[idx], best[idx])[1][1], 3)}
# distribution shift (team-supplied sentiment, deployed, calibrated)
out["shares"] = {"gold": [round(float((y_tr == c).mean()), 3) for c in range(3)], "deployed": [round(float((deployed == c).mean()), 3) for c in range(3)], "calibrated": [round(float((best == c).mean()), 3) for c in range(3)], "order": CL}
# star-contradicting reviews (5-star but negative, 1-star but positive) and delivery-only reviews
contradict = [i for i, r in enumerate(tr) if (r["stars"] >= 4 and y_tr[i] == 0) or (r["stars"] <= 2 and y_tr[i] == 2)]
deliv = [i for i, r in enumerate(tr) if r["y"][5] and r["y"][:5].sum() == 0]
out["star_contradicting"] = {"rows": len(contradict), "deployed_accuracy": round(float((deployed[contradict] == y_tr[contradict]).mean()), 3), "calibrated_accuracy": round(float((best[contradict] == y_tr[contradict]).mean()), 3)}
out["delivery_only"] = {"rows": len(deliv), "deployed_accuracy": round(float((deployed[deliv] == y_tr[deliv]).mean()), 3), "calibrated_accuracy": round(float((best[deliv] == y_tr[deliv]).mean()), 3),
                        "gold_share_positive": round(float((y_tr[deliv] == 2).mean()), 3), "calibrated_share_positive": round(float((best[deliv] == 2).mean()), 3)}
json.dump(out, open(ROOT / "research" / "results" / "sentiment_calibration_audit.json", "w"), indent=1)
print("ABLATION (CV macro F1 / historical test macro F1 / CV neutral F1)")
for k, v in out["ablation"].items():
    print(f"  {k:18} {v['cv_macro_f1']:.3f} / {v['historical_test_macro_f1']:.3f} / {v['cv_neutral_f1']:.3f}")
print("BY GROUP (OOF)  deployed -> calibrated macro F1:", {g: (v['rows'], v['deployed_macro_f1'], v['calibrated_macro_f1']) for g, v in out['by_group'].items()})
print("SHARES [neg, neu, pos]:", out["shares"])
print("STAR-CONTRADICTING:", out["star_contradicting"]); print("DELIVERY-ONLY:", out["delivery_only"])
