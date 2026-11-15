"""Model and dataset inventory with hashes, label distributions, duplicates, near-duplicates and product overlap (writes results/inventory.json).

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/inventory.py
"""
import collections, json, pathlib, subprocess, sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import xdata  # noqa: E402

R = xdata.ROOT
out = {"repo_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=R, capture_output=True, text=True).stdout.strip(),
       "branch": subprocess.run(["git", "branch", "--show-current"], cwd=R, capture_output=True, text=True).stdout.strip()}

# models
models = {}
onnx = R / "backend/sentiment-analysis/models/sentiment_onnx/xlmr_firecs_v1"
for f in ("model.onnx", "tokenizer.json", "manifest.json"):
    models[f"deployed_onnx_int8/{f}"] = {"bytes": (onnx / f).stat().st_size, "sha256": xdata.sha256(onnx / f)}
cal = R / "research/artifacts/sentiment_calibrator_v1.joblib"
models["experimental_calibrator_v1.joblib (disabled)"] = {"bytes": cal.stat().st_size, "sha256": xdata.sha256(cal)}
hub = pathlib.Path.home() / ".cache/huggingface/hub/models--cardiffnlp--twitter-xlm-roberta-base-sentiment"
snap = sorted((hub / "snapshots").iterdir())[0]
models["cardiffnlp/twitter-xlm-roberta-base-sentiment (public base, FP32)"] = {"snapshot": snap.name, "files": {p.name: {"bytes": p.stat().st_size, "sha256": xdata.sha256(p)} for p in snap.iterdir() if p.is_file() or p.is_symlink()}}
for v in ("v1", "v2", "v3"):
    p = R / "training/runs" / v / "model" / "model.safetensors"
    models[f"training/runs/{v}/model (HAZARD-FLAG model, not sentiment)"] = {"bytes": p.stat().st_size, "sha256": xdata.sha256(p)}
out["models"] = models

# datasets
sets = {"firecs_train": xdata.load_firecs("train"), "firecs_test": xdata.load_firecs("test"), **xdata.load_marketplace()}
files = {"firecs_train": xdata.firecs_path("train"), "firecs_test": xdata.firecs_path("test"), "market_train_v3": R / "evaluation/annotated/train_v3.csv", "market_test_v3": R / "evaluation/annotated/test_v3.csv",
         "market_fresh": R / "evaluation/fresh/label_batch_fresh.csv", "market_fresh2": R / "evaluation/fresh2/label_batch_fresh2.csv",
         "market_gold200": R / "evaluation/gold_labels_200.csv", "market_heldout100": R / "evaluation/heldout_labels_100.csv"}
ds = {}
for name, rows in sets.items():
    conf = collections.Counter(r["conf"] for r in rows)
    lab = collections.Counter(r["label"] for r in rows if r["conf"] in ("high", "published"))
    norm = [xdata.norm_text(r["text"]) for r in rows]
    ds[name] = {"file_sha256": xdata.sha256(files[name]), "rows": len(rows), "confidence": dict(conf), "labels_high_confidence": dict(lab),
                "label_share_high": {k: round(v / max(1, sum(lab.values())), 3) for k, v in lab.items()},
                "duplicate_texts_within": len(norm) - len(set(norm)), "products": len({r["product"] for r in rows if r["product"]}),
                "mean_words": round(float(np.mean([len(r["text"].split()) for r in rows])), 1)}
out["datasets"] = ds

# exact duplicates / product overlap between sets
norm_sets = {n: {xdata.norm_text(r["text"]) for r in rows} for n, rows in sets.items()}
names = list(sets)
out["exact_text_overlap"] = {f"{a} & {b}": len(norm_sets[a] & norm_sets[b]) for i, a in enumerate(names) for b in names[i + 1:] if norm_sets[a] & norm_sets[b]}
prod = {n: {r["product"] for r in rows if r["product"]} for n, rows in sets.items()}
out["product_overlap"] = {f"{a} & {b}": len(prod[a] & prod[b]) for i, a in enumerate(names) for b in names[i + 1:] if prod[a] & prod[b]}

# near duplicates (TF-IDF cosine >= 0.9) of each evaluation set against the sets it must not resemble
def near(test, train):
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2).fit([r["text"] for r in train + test])
    A = vec.transform([r["text"] for r in test]); B = vec.transform([r["text"] for r in train])
    best = np.zeros(A.shape[0])
    for s in range(0, A.shape[0], 500):
        best[s:s + 500] = (A[s:s + 500] @ B.T).max(axis=1).toarray().ravel()
    return {"rows": len(test), "with_neighbour_cosine_ge_0.9": int((best >= 0.9).sum()), "with_neighbour_cosine_ge_0.95": int((best >= 0.95).sum())}
out["near_duplicates"] = {
    "firecs_test vs firecs_train": near(sets["firecs_test"], sets["firecs_train"]),
    "market_test_v3 vs market_train_v3": near(sets["market_test_v3"], sets["market_train_v3"]),
    "market_test_v3 vs firecs_train": near(sets["market_test_v3"], sets["firecs_train"]),
    "market_fresh vs market_train_v3": near(sets["market_fresh"], sets["market_train_v3"]),
}
json.dump(out, open(xdata.X / "results" / "inventory.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("exact_text_overlap", "product_overlap", "near_duplicates")}, indent=1))
print(json.dumps({n: {k: d[k] for k in ("rows", "labels_high_confidence", "duplicate_texts_within", "products")} for n, d in ds.items()}, indent=1))
