"""Regularised stacking: a small logistic regression over the rule decision and the OUT-OF-FOLD sparse-model probability.

    D:\defaketive-train\Scripts\python.exe research\exp_stacking.py

Inputs per flag: rule decision, out-of-fold word+char TF-IDF probability (never in-sample), star rating, product group
one-hot. The rules' decisions on training rows were error-tuned, so a stacker trained on them tends to over-trust them;
the historical test (which the rules were NOT tuned on) is the check. Product-grouped CV on the training file selects
nothing here except the regularisation strength from {0.1, 1}; the historical test is scored once.
"""
import json, pathlib, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import CACHE, FLAGS5, ROOT, best_threshold, grouped_folds, load, paired_bootstrap_diff, prf, product_bootstrap_f1, rules_predictions
tr, te = load("train_v3"), load("test_v3")
Y, Yt = np.array([r["y"] for r in tr]), np.array([r["y"] for r in te])
oof = np.load(CACHE / "oof_tfidf.npy"); pt = np.load(CACHE / "test_prob_tfidf.npy")
R, Rt = rules_predictions("train"), rules_predictions("test")
groups = sorted({r["group"] for r in tr + te})
def feats(rows, rules, prob, k):
    return np.array([[rules[r["id"]]["pred"][k], prob[i, k], r["stars"] / 5.0] + [1.0 if r["group"] == g else 0.0 for g in groups] for i, r in enumerate(rows)])
folds = grouped_folds(tr, 5, seed=3); out = {}
for k, f in enumerate(FLAGS5):
    X, Xt = feats(tr, R, oof, k), feats(te, Rt, pt, k); best = None
    for C in (0.1, 1.0):
        p = np.zeros(len(tr))
        for a, b in folds:
            p[b] = LogisticRegression(C=C, class_weight="balanced", max_iter=2000).fit(X[a], Y[a, k]).predict_proba(X[b])[:, 1]
        thr = best_threshold(Y[:, k], p); s = prf(Y[:, k], (p >= thr).astype(int))["f1"]
        if best is None or s > best[0]: best = (s, C, thr)
    s, C, thr = best; clf = LogisticRegression(C=C, class_weight="balanced", max_iter=2000).fit(X, Y[:, k])
    pred = (clf.predict_proba(Xt)[:, 1] >= thr).astype(int); rule = np.array([Rt[r["id"]]["pred"][k] for r in te])
    sc = prf(Yt[:, k], pred); lo, hi = product_bootstrap_f1(te, pred, k, 500); d = paired_bootstrap_diff(te, pred, rule, k, 500)
    out[f] = {"cv_f1": round(s, 3), "C": C, "threshold": thr, "historical_test": {x: (round(v, 3) if isinstance(v, float) else v) for x, v in sc.items()}, "f1_ci95": [round(lo, 3), round(hi, 3)],
              "rules_f1": round(prf(Yt[:, k], rule)["f1"], 3), "f1_minus_rules_ci95": [round(d[0], 3), round(d[2], 3)], "coef_rule_prob_stars": [round(float(x), 2) for x in clf.coef_[0][:3]]}
    print(f"{f:17} CV {s:.2f} | historical test stack {sc['f1']:.2f} [{lo:.2f},{hi:.2f}] vs rules {out[f]['rules_f1']:.2f}  diff CI {out[f]['f1_minus_rules_ci95']}  rule-coef {out[f]['coef_rule_prob_stars'][0]}")
json.dump(out, open(ROOT / "research" / "results" / "exp_stacking.json", "w"), indent=1)
