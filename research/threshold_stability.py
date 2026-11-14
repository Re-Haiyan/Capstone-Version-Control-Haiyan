"""How stable is the single per-flag threshold? Re-choose it on 300 product-bootstrap resamples of the out-of-fold
predictions (sparse model) and report the spread. A wide spread means the threshold is not identified by the data.

    D:\defaketive-train\Scripts\python.exe research\threshold_stability.py
"""
import json, pathlib, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import CACHE, FLAGS5, ROOT, best_threshold, load, prf
tr = load("train_v3"); Y = np.array([r["y"] for r in tr]); oof = np.load(CACHE / "oof_tfidf.npy")
products = sorted({r["product"] for r in tr}); idx = {p: [] for p in products}
for i, r in enumerate(tr): idx[r["product"]].append(i)
rng = np.random.default_rng(0); out = {}
for k, f in enumerate(FLAGS5):
    ths = []
    for _ in range(300):
        pick = rng.choice(len(products), len(products)); sel = np.concatenate([idx[products[j]] for j in pick])
        ths.append(best_threshold(Y[sel, k], oof[sel, k]))
    q = np.percentile(ths, [10, 50, 90]); full = best_threshold(Y[:, k], oof[:, k])
    f_full = prf(Y[:, k], (oof[:, k] >= full).astype(int))["f1"]; f_med = prf(Y[:, k], (oof[:, k] >= q[1]).astype(int))["f1"]
    out[f] = {"threshold_full": full, "bootstrap_p10_median_p90": [round(float(x), 2) for x in q], "f1_at_full": round(f_full, 3), "f1_at_median": round(f_med, 3)}
    print(f"{f:17} threshold {full:.2f}  bootstrap p10/median/p90 {q[0]:.2f}/{q[1]:.2f}/{q[2]:.2f}  F1 at chosen {f_full:.3f}")
json.dump(out, open(ROOT / "research" / "results" / "threshold_stability.json", "w"), indent=1)
