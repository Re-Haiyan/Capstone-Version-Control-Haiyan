"""Labels the unique review texts of the 60 impact-study products with a locked head artifact (for conclusion_impact.py), caching the shipped encoder's embeddings once.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/phase4_head_labels.py <artifact name under research/artifacts> <candidate name>

The embeddings are cached in data/head/impact_emb.npy (git-ignored). Output: results/candidate_labels__<candidate name>.json (text -> label), the format conclusion_impact.py `impact` reads.
Nothing is saved to the database, the shipped model is not touched.
"""
import json, pathlib, sys
import joblib
import numpy as np

X = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(X))
import xdata, optimize_head, conclusion_impact  # noqa: E402

LABELS = conclusion_impact.LABELS


def main():
    art, name = sys.argv[1], sys.argv[2]
    products = conclusion_impact.sample_products(60)
    texts = sorted({str(c.get("content") or "") for p in products for c in p["comments"] if isinstance(c, dict)})
    cache = X / "data" / "head" / "impact_emb.npy"; key = X / "data" / "head" / "impact_texts.json"
    if cache.exists() and json.load(open(key)) == texts:
        E = np.load(cache)
    else:
        E = optimize_head.embed_all(texts)[:, :768]; np.save(cache, E); json.dump(texts, open(key, "w"))
    pipe = joblib.load(xdata.ROOT / "research/artifacts" / art)["pipeline"]
    pred = pipe.predict(E)
    json.dump({t: LABELS[int(p)] for t, p in zip(texts, pred)}, open(X / "results" / f"candidate_labels__{name}.json", "w"))
    print(name, len(texts), "texts labelled; shares", {LABELS[k]: round(float((pred == k).mean()), 3) for k in range(3)})


if __name__ == "__main__":
    main()
