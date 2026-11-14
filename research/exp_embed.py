"""Experiment B: frozen multilingual sentence embeddings + regularised logistic regression, product-grouped CV.

    D:\\defaketive-train\\Scripts\\python.exe research\\exp_embed.py

Encoders (licences checked): intfloat/multilingual-e5-small (MIT, needs the "query: " prefix),
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (Apache-2.0).
Input variants: review alone; category + title + review; plus structured features (stars, group one-hot, rule flags).
Selection is by out-of-fold F1 on the training file; the historical test file is scored once at the end.
"""
import json, pathlib, sys, time
import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import CACHE, FLAGS5, FLAGS6, ROOT, best_threshold, grouped_folds, load, model_text, prf, product_bootstrap_f1, rules_predictions

torch.set_num_threads(10)
OUT = ROOT / "research" / "results"; OUT.mkdir(exist_ok=True)
train, test = load("train_v3"), load("test_v3")
Y = np.array([r["y"] for r in train]); Yt = np.array([r["y"] for r in test])
folds = grouped_folds(train, 5, seed=0)
ENCODERS = {"e5-small": ("intfloat/multilingual-e5-small", "query: "), "minilm": ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "")}
groups = sorted({r["group"] for r in train + test})


def embed(name, ctx):
    path = CACHE / f"emb_{name}_ctx{int(ctx)}.npy"
    if path.exists():
        return np.load(path)
    model_id, prefix = ENCODERS[name]
    model = SentenceTransformer(model_id, device="cpu"); model.max_seq_length = 160
    texts = [prefix + model_text(r, ctx) for r in train + test]
    t0 = time.time(); E = model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    print(f"  embedded {len(texts)} texts with {name} ctx={int(ctx)} in {time.time() - t0:.0f}s ({(time.time() - t0) / len(texts) * 1000:.1f} ms/text)", flush=True)
    np.save(path, E.astype(np.float32)); return E


def structured(rows, rules):
    out = []
    for r in rows:
        v = [r["stars"] / 5.0] + [1.0 if r["group"] == g else 0.0 for g in groups]
        v += [float(x) for x in rules[r["id"]]["pred"]]
        out.append(v)
    return np.array(out, dtype=np.float32)


rules_tr, rules_te = rules_predictions("train"), rules_predictions("test")
S_tr, S_te = structured(train, rules_tr), structured(test, rules_te)
results, oof_store = {}, {}
for enc in ENCODERS:
    for ctx in (False, True):
        E = embed(enc, ctx); Etr, Ete = E[: len(train)], E[len(train):]
        for extra in ("emb", "emb+struct"):
            for C in (0.5, 2.0, 8.0):
                X = Etr if extra == "emb" else np.hstack([Etr, S_tr])
                oof = np.zeros(Y.shape); t0 = time.time()
                for tr, te in folds:
                    for k in range(len(FLAGS6)):
                        clf = LogisticRegression(C=C, class_weight="balanced", max_iter=3000)
                        clf.fit(X[tr], Y[tr][:, k]); oof[te, k] = clf.predict_proba(X[te])[:, 1]
                name = f"{enc}|ctx={int(ctx)}|{extra}|C={C}"
                per = {}
                for k, f in enumerate(FLAGS6):
                    t = best_threshold(Y[:, k], oof[:, k]); per[f] = {**prf(Y[:, k], (oof[:, k] >= t).astype(int)), "threshold": t}
                results[name] = {"per_flag": per, "macro_f1": float(np.mean([per[f]["f1"] for f in FLAGS6]))}
                oof_store[name] = oof
                print(f"{name:42} macroF1={results[name]['macro_f1']:.3f} " + " ".join(f"{f[:4]}={per[f]['f1']:.2f}" for f in FLAGS6), flush=True)

best = {f: max(results, key=lambda n: results[n]["per_flag"][f]["f1"]) for f in FLAGS6}
np.save(CACHE / "oof_embed.npy", np.stack([oof_store[best[f]][:, k] for k, f in enumerate(FLAGS6)], axis=1))
hist, test_prob = {}, np.zeros(Yt.shape)
for k, f in enumerate(FLAGS6):
    enc, ctx, extra, C = best[f].split("|"); ctx = ctx == "ctx=1"; C = float(C.split("=")[1])
    E = embed(enc, ctx); Etr, Ete = E[: len(train)], E[len(train):]
    Xtr = Etr if extra == "emb" else np.hstack([Etr, S_tr]); Xte = Ete if extra == "emb" else np.hstack([Ete, S_te])
    clf = LogisticRegression(C=C, class_weight="balanced", max_iter=3000).fit(Xtr, Y[:, k]); p = clf.predict_proba(Xte)[:, 1]
    test_prob[:, k] = p; thr = results[best[f]]["per_flag"][f]["threshold"]; pred = (p >= thr).astype(int)
    s = prf(Yt[:, k], pred); lo, hi = product_bootstrap_f1(test, pred, k, n_boot=500)
    hist[f] = {"config": best[f], "threshold": thr, **s, "f1_ci95_product_bootstrap": [round(lo, 3), round(hi, 3)]}
    print(f"historical test {f:17} {best[f]:40} F1 {s['f1']:.2f} (P {s['precision']:.2f} R {s['recall']:.2f}) CI [{lo:.2f},{hi:.2f}]")
np.save(CACHE / "test_prob_embed.npy", test_prob)
json.dump({"cv": results, "best_per_flag": best, "historical_test": hist}, open(OUT / "exp_embed.json", "w"), indent=1)
