"""Leakage audit of the Phase 2 data: the dev pool and the neutral candidate pool against the frozen test, against each other, and against the training corpus; plus product overlap.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/phase2_leakage_audit.py
Texts and products only; no labels, no model. Writes phase2/phase2_leakage_audit.json.
"""
import csv, json, pathlib, sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

X = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(X))
import xdata  # noqa: E402

rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8-sig")))
ft = rd(X / "annotation/final_test_sheet_A.csv"); dv = rd(X / "annotation/dev_pool_sheet.csv"); nc = rd(X / "annotation/neutral_candidate_pool.csv")
corpus = json.load(open(X / "data/head/corpus_meta.json"))
pm = {r["sheet_id"]: r for r in csv.DictReader(open(X / "annotation/PRIVATE_id_map.csv", encoding="utf-8"))}
nm = {r["id"]: r for r in csv.DictReader(open(X / "annotation/PRIVATE_neutral_candidate_map.csv", encoding="utf-8"))}
fc = {r["id"]: r["text"] for r in xdata.load_firecs("train")}
mk = {r["id"]: r["text"] for r in xdata.load_marketplace()["market_train_v3"]}
pool = {r["id"]: r["review_text"] for r in rd("D:/cvc-annotations/evaluation/annotation_batch_ai_direct/assembled/annotations.csv")}
train_texts = [fc.get(m["id"]) or mk.get(m["id"]) or pool.get(m["id"], "") for m in corpus]


def near(a, b):
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1).fit(a + b)
    A, B = vec.transform(a), vec.transform(b)
    best = np.zeros(A.shape[0])
    for s in range(0, A.shape[0], 1000):
        best[s:s + 1000] = (A[s:s + 1000] @ B.T).max(axis=1).toarray().ravel()
    return int((best >= 0.9).sum())


def exact(a, b):
    nb = {xdata.norm_text(t) for t in b}
    return sum(xdata.norm_text(t) in nb for t in a)


F = [r["review_text"] for r in ft]; D = [r["review_text"] for r in dv]; N = [r["review_text"] for r in nc]
res = {"dev_pool_vs_frozen_test": {"exact": exact(D, F), "near": near(D, F)}, "neutral_candidates_vs_frozen_test": {"exact": exact(N, F), "near": near(N, F)},
       "neutral_candidates_vs_dev_pool": {"exact": exact(N, D), "near": near(N, D)}, "neutral_candidates_vs_training_corpus": {"exact": exact(N, train_texts)},
       "dev_pool_vs_training_corpus": {"exact": exact(D, train_texts), "near": near(D, train_texts)}}
fl = {pm[r["id"]]["product_link"] for r in ft}; dl = {pm[r["id"]]["product_link"] for r in dv}
nl = {nm[r["id"]]["group"] for r in nc if nm[r["id"]]["source"] == "production_db"}
res["product_overlap"] = {"frozen_test_and_dev_pool": len(fl & dl), "frozen_test_and_neutral_candidates": len(fl & nl), "dev_pool_and_neutral_candidates": len(dl & nl)}
json.dump(res, open(X / "phase2/phase2_leakage_audit.json", "w"), indent=1)
print(json.dumps(res, indent=1))
