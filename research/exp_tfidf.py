"""Experiment A: sparse text baselines (word / char / word+char TF-IDF, logistic regression), product-grouped CV.

    D:\\defaketive-train\\Scripts\\python.exe research\\exp_tfidf.py

Selection (feature set, C, threshold) is by out-of-fold F1 on the TRAINING file only. The historical test file is
scored once at the end with the selected configuration and is not used to select anything.
"""
import json, pathlib, sys, time
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import CACHE, FLAGS6, ROOT, best_threshold, grouped_folds, load, model_text, prf, product_bootstrap_f1

OUT = ROOT / "research" / "results"; OUT.mkdir(exist_ok=True)
train, test = load("train_v3"), load("test_v3")
Y = np.array([r["y"] for r in train]); Yt = np.array([r["y"] for r in test])
folds = grouped_folds(train, 5, seed=0)
print("positives per fold:", {f: [int(Y[te][:, k].sum()) for _, te in folds] for k, f in enumerate(FLAGS6)})


def features(kind, fit_texts, other_texts_list):
    vecs = []
    if kind in ("word", "word+char"):
        vecs.append(TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True, lowercase=True, token_pattern=r"(?u)\b\w+\b"))
    if kind in ("char", "word+char"):
        vecs.append(TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, lowercase=True))
    fit = hstack([v.fit_transform(fit_texts) for v in vecs]).tocsr()
    others = [hstack([v.transform(t) for v in vecs]).tocsr() for t in other_texts_list]
    return fit, others


results = {}
configs = [(kind, ctx, C) for kind in ("word", "char", "word+char") for ctx in (False, True) for C in (1.0, 4.0, 16.0)]
oof_store = {}
for kind, ctx, C in configs:
    texts = [model_text(r, ctx) for r in train]
    oof = np.zeros(Y.shape, dtype=float); t0 = time.time()
    for tr, te in folds:
        Xtr, (Xte,) = features(kind, [texts[i] for i in tr], [[texts[i] for i in te]])
        for k in range(len(FLAGS6)):
            if Y[tr][:, k].sum() < 2:
                continue
            clf = LogisticRegression(C=C, class_weight="balanced", max_iter=2000, solver="liblinear")
            clf.fit(Xtr, Y[tr][:, k]); oof[te, k] = clf.predict_proba(Xte)[:, 1]
    name = f"{kind}|ctx={int(ctx)}|C={C}"
    per = {}
    for k, f in enumerate(FLAGS6):
        t = best_threshold(Y[:, k], oof[:, k]); per[f] = {**prf(Y[:, k], (oof[:, k] >= t).astype(int)), "threshold": t}
    results[name] = {"cv_minutes": round((time.time() - t0) / 60, 2), "per_flag": per, "macro_f1": float(np.mean([per[f]["f1"] for f in FLAGS6]))}
    oof_store[name] = oof
    print(f"{name:28} macroF1={results[name]['macro_f1']:.3f} " + " ".join(f"{f[:4]}={per[f]['f1']:.2f}" for f in FLAGS6) + f"  ({results[name]['cv_minutes']} min)", flush=True)

# best configuration per flag (on OOF) -> saved for stacking / label-noise audit; scored once on the historical test
best = {}
for k, f in enumerate(FLAGS6):
    name = max(results, key=lambda n: results[n]["per_flag"][f]["f1"])
    best[f] = name
np.save(CACHE / "oof_tfidf.npy", np.stack([oof_store[best[f]][:, k] for k, f in enumerate(FLAGS6)], axis=1))
json.dump([r["id"] for r in train], open(CACHE / "oof_ids.json", "w"))
hist = {}
test_prob = np.zeros(Yt.shape)
for k, f in enumerate(FLAGS6):
    kind, ctx, C = best[f].split("|"); ctx = ctx == "ctx=1"; C = float(C.split("=")[1])
    texts = [model_text(r, ctx) for r in train]; ttexts = [model_text(r, ctx) for r in test]
    t0 = time.time(); Xtr, (Xte,) = features(kind, texts, [ttexts])
    clf = LogisticRegression(C=C, class_weight="balanced", max_iter=2000, solver="liblinear").fit(Xtr, Y[:, k])
    fit_s = time.time() - t0; t0 = time.time(); p = clf.predict_proba(Xte)[:, 1]; inf_ms = (time.time() - t0) / len(test) * 1000
    test_prob[:, k] = p; thr = results[best[f]]["per_flag"][f]["threshold"]
    pred = (p >= thr).astype(int); s = prf(Yt[:, k], pred); lo, hi = product_bootstrap_f1(test, pred, k, n_boot=500)
    hist[f] = {"config": best[f], "threshold": thr, **s, "f1_ci95_product_bootstrap": [round(lo, 3), round(hi, 3)], "fit_seconds": round(fit_s, 1), "inference_ms_per_review": round(inf_ms, 3)}
    print(f"historical test {f:17} {best[f]:26} F1 {s['f1']:.2f} (P {s['precision']:.2f} R {s['recall']:.2f}) CI [{lo:.2f},{hi:.2f}]")
np.save(CACHE / "test_prob_tfidf.npy", test_prob)
json.dump({"cv": results, "best_per_flag": best, "historical_test": hist}, open(OUT / "exp_tfidf.json", "w"), indent=1)
