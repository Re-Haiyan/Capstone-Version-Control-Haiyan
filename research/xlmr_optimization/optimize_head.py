"""Optimised sentiment head on the shipped encoder: stratified, grouped cross-validation over training data only; the frozen final test is never read here.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/optimize_head.py embed     (embeddings and class probabilities of the shipped ONNX model, cached)
    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/optimize_head.py cv        (grid, out-of-fold metrics, writes results/optimized_head_cv.json and the chosen config)
    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/optimize_head.py fit       (final fit on all training rows with the chosen config; writes research/artifacts/sentiment_head_v1.joblib)

Training corpus (three label sources, kept visible by source; the source is NEVER a feature):
  FiReCS train (published, authors' labels; its neutral class is the FiReCS convention),
  marketplace train_v3 rows, deduplicated (team-supplied labels, unverified provenance),
  the 10,000-review pool with AI silver labels (positive / neutral / negative only, high or medium confidence; mixed and unclear are not three-class training rows by policy v1;
  rows whose text matches a frozen-test review exactly or at cosine >= 0.9 and the pool's own test_candidate split are removed BEFORE any model sees them).
Selection metric: pooled out-of-fold macro F1. Features: the 768-d mean last hidden layer (optionally plus the model's log-probabilities), standardised. Class weighting and C are
searched. No row is dropped for being hard. The chosen head is documented, locked and then scored once on the frozen test by score_head.py.
"""
import csv, json, multiprocessing as mp, pathlib, sys
import numpy as np

X = pathlib.Path(__file__).resolve().parent
ROOT = X.parent.parent
sys.path.insert(0, str(X))
import xdata, metrics_x  # noqa: E402

ONNX = ROOT / "backend/sentiment-analysis/models/sentiment_onnx/xlmr_firecs_v1"
CACHE = X / "data" / "head"
CACHE.mkdir(parents=True, exist_ok=True)
POOL_AI = pathlib.Path("D:/cvc-annotations/evaluation/annotation_batch_ai_direct/assembled/annotations.csv")
L = xdata.LABELS
_c = None


def _init():
    global _c
    sys.path.insert(0, str(ROOT / "backend/sentiment-analysis"))
    from defaketive_sentiment.transformer_sentiment import TransformerSentimentClassifier
    _c = TransformerSentimentClassifier(ONNX, threads=1)


def _work(texts):
    out = []
    for t in texts:
        p = _c.predict(t)["probabilities"]
        out.append(np.concatenate([_c.embed(t), [p["negative"], p["neutral"], p["positive"]]]))
    return out


def embed_all(texts, workers=8):
    chunks = [texts[i::workers * 4] for i in range(workers * 4)]
    with mp.Pool(workers, initializer=_init) as pool:
        parts = pool.map(_work, chunks)
    out = np.zeros((len(texts), 771), dtype=np.float32)
    for i, part in enumerate(parts):
        out[i::workers * 4] = np.array(part)
    return out


def frozen_texts():
    return [r["review_text"] for r in csv.DictReader(open(X / "annotation/final_test_sheet_A.csv", encoding="utf-8-sig"))]


def build_corpus():
    from sklearn.feature_extraction.text import TfidfVectorizer
    rows = []
    for r in xdata.load_firecs("train"):
        rows.append({"id": r["id"], "source": "firecs", "text": r["text"], "label": r["label"], "group": r["id"]})
    seen = set()
    for r in xdata.load_marketplace()["market_train_v3"]:
        k = (r["product"], xdata.norm_text(r["text"]))
        if r["conf"] == "high" and k not in seen:
            seen.add(k)
            rows.append({"id": r["id"], "source": "market_team", "text": r["text"], "label": r["label"], "group": "P:" + r["product"]})
    ai = [r for r in csv.DictReader(open(POOL_AI, encoding="utf-8-sig")) if r["original_split"] in ("train", "validation") and r["ai_sentiment"] in L and r["ai_confidence"] in ("high", "medium")]
    for r in ai:
        rows.append({"id": r["id"], "source": "ai_pool", "text": r["review_text"], "label": r["ai_sentiment"], "group": "G:" + r["group_id"]})
    # remove anything that matches the frozen test, before any model or statistic sees the rows
    ft = frozen_texts()
    fn = {xdata.norm_text(t) for t in ft}
    keep = [r for r in rows if xdata.norm_text(r["text"]) not in fn]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1).fit(ft + [r["text"] for r in keep])
    A = vec.transform(ft); B = vec.transform([r["text"] for r in keep])
    best = np.zeros(B.shape[0])
    for s in range(0, B.shape[0], 1000):
        best[s:s + 1000] = (B[s:s + 1000] @ A.T).max(axis=1).toarray().ravel()
    final = [r for r, b in zip(keep, best) if b < 0.9]
    info = {"rows_before": len(rows), "removed_exact_frozen_match": len(rows) - len(keep), "removed_near_duplicate_of_frozen": len(keep) - len(final), "rows_after": len(final),
            "by_source": {s: sum(r["source"] == s for r in final) for s in ("firecs", "market_team", "ai_pool")},
            "label_distribution": {s: {l: sum(r["source"] == s and r["label"] == l for r in final) for l in L} for s in ("firecs", "market_team", "ai_pool")}}
    return final, info


def main():
    cmd = sys.argv[1]
    if cmd == "embed":
        rows, info = build_corpus()
        json.dump(info, open(X / "results" / "optimized_head_corpus.json", "w"), indent=1)
        json.dump([{k: r[k] for k in ("id", "source", "label", "group")} for r in rows], open(CACHE / "corpus_meta.json", "w"))
        np.save(CACHE / "corpus_emb.npy", embed_all([r["text"] for r in rows]))
        np.save(CACHE / "frozen_emb.npy", embed_all(frozen_texts()))
        print(info)
        return
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    meta = json.load(open(CACHE / "corpus_meta.json"))
    E = np.load(CACHE / "corpus_emb.npy")
    y = np.array([L.index(m["label"]) for m in meta]); src = np.array([m["source"] for m in meta]); grp = np.array([m["group"] for m in meta])

    def feats(M, kind):
        return M[:, :768] if kind == "emb" else np.hstack([M[:, :768], np.log(np.clip(M[:, 768:], 1e-6, 1))])
    if cmd == "cv":
        folds = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=7).split(E, y, grp))
        grid = [(k, C, cw) for k in ("emb", "emb+logp") for C in (0.003, 0.01, 0.03, 0.1, 0.3) for cw in (None, "balanced")]
        res = []
        for kind, C, cw in grid:
            oof = np.zeros(len(y), dtype=int)
            F = feats(E, kind)
            for tr, te in folds:
                m = make_pipeline(StandardScaler(), LogisticRegression(C=C, class_weight=cw, max_iter=2000))
                m.fit(F[tr], y[tr]); oof[te] = m.predict(F[te])
            s = metrics_x.summarize(y, oof)
            res.append({"features": kind, "C": C, "class_weight": cw, "macro_f1": s["macro_f1"], "accuracy": s["accuracy"], "neutral_f1": s["classes"]["neutral"]["f1"], "negative_f1": s["classes"]["negative"]["f1"], "positive_f1": s["classes"]["positive"]["f1"]})
            print(res[-1], flush=True)
        best = max(res, key=lambda r: r["macro_f1"])
        kind, C, cw = best["features"], best["C"], best["class_weight"]
        F = feats(E, kind); oof = np.zeros(len(y), dtype=int)
        for tr, te in folds:
            m = make_pipeline(StandardScaler(), LogisticRegression(C=C, class_weight=cw, max_iter=2000)); m.fit(F[tr], y[tr]); oof[te] = m.predict(F[te])
        shipped = E[:, 768:].argmax(1)  # the shipped model's own decision on the same rows, for reference (no fitting involved)
        out = {"grid": res, "chosen": best, "folds": "StratifiedGroupKFold(5), groups = product (marketplace), review id (FiReCS), annotation group (pool); seed 7",
               "oof_overall": metrics_x.summarize(y, oof), "shipped_model_on_same_rows": metrics_x.summarize(y, shipped),
               "oof_by_source": {s: metrics_x.summarize(y[src == s], oof[src == s]) for s in ("firecs", "market_team", "ai_pool")},
               "shipped_by_source": {s: metrics_x.summarize(y[src == s], shipped[src == s]) for s in ("firecs", "market_team", "ai_pool")}}
        json.dump(out, open(X / "results" / "optimized_head_cv.json", "w"), indent=1)
        print("CHOSEN", best)
        return
    if cmd == "fit":
        import joblib
        cfg = json.load(open(X / "results" / "optimized_head_cv.json"))["chosen"]
        F = feats(E, cfg["features"])
        m = make_pipeline(StandardScaler(), LogisticRegression(C=cfg["C"], class_weight=cfg["class_weight"], max_iter=2000)).fit(F, y)
        (ROOT / "research/artifacts").mkdir(exist_ok=True)
        joblib.dump({"pipeline": m, "config": cfg, "classes": L, "encoder": "shipped ONNX int8 model_version defaketive-xlmr-firecs-v1-onnx-int8-e04da4c2"}, ROOT / "research/artifacts/sentiment_head_v1.joblib")
        print("saved", cfg)


if __name__ == "__main__":
    main()
