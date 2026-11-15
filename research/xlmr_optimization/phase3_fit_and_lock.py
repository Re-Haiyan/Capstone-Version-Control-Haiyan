"""Fits the prespecified Phase 3 configuration T7 on its training data only and writes research/xlmr_optimization/phase3_lock.json BEFORE the confirmation set is built or annotated.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/phase3_fit_and_lock.py

T7 = policy-v1-filtered corpus (older-rubric feature-list-shaped rows excluded; FiReCS neutral excluded as an alternative-convention class) + the 200 v1 neutral-candidate rows annotated by Claude
(three-class only), logistic head C 0.003 with balanced class weights, on the shipped encoder's embedding. The dev-pool rows used to compare configurations are NOT in its training data.
T0 = the locked sentiment_head_v1 artifact (old corpus). Both are scored once on the confirmation set; the confirmation set selects nothing.
"""
import csv, datetime, json, pathlib, sys
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

X = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(X))
import xdata, neutral_candidates, optimize_head, phase3_experiments as p3  # noqa: E402

L = xdata.LABELS


def main():
    rows = p3.v1_rows()
    ids = json.load(open(p3.CACHE / "v1_ids.json"))
    assert ids == [r["id"] for r in rows]
    EV = np.load(p3.CACHE / "v1_emb.npy")[:, :768]
    meta = json.load(open(p3.CACHE / "corpus_meta.json")); EC = np.load(p3.CACHE / "corpus_emb.npy")[:, :768]
    yc = np.array([L.index(m["label"]) for m in meta]); srcc = np.array([m["source"] for m in meta])
    fc = {r["id"]: r["text"] for r in xdata.load_firecs("train")}; mk = {r["id"]: r["text"] for r in xdata.load_marketplace()["market_train_v3"]}
    pool = {r["id"]: r["review_text"] for r in csv.DictReader(open(optimize_head.POOL_AI, encoding="utf-8-sig"))}
    text = [fc.get(m["id"]) or mk.get(m["id"]) or pool.get(m["id"], "") for m in meta]
    shape = np.array(["feature_list" in neutral_candidates.cues(t) for t in text])
    v1n = {xdata.norm_text(r["text"]) for r in rows}
    in_v1 = np.array([xdata.norm_text(t) in v1n for t in text])
    keep = ~(((srcc == "market_team") | (srcc == "ai_pool")) & shape) & ~in_v1 & ~((srcc == "firecs") & (yc == 1))
    cand = [i for i, r in enumerate(rows) if r["set"] == "neutral_candidates" and r["label"] in L]
    Xt = np.vstack([EC[keep], EV[cand]]); yt = np.concatenate([yc[keep], [L.index(rows[i]["label"]) for i in cand]])
    m = make_pipeline(StandardScaler(), LogisticRegression(C=0.003, class_weight="balanced", max_iter=3000)).fit(Xt, yt)
    art = xdata.ROOT / "research/artifacts/sentiment_head_v2_t7.joblib"
    joblib.dump({"pipeline": m, "classes": L, "config": "T7: v1-filtered corpus, FiReCS neutral excluded, +200 v1 candidate rows, C 0.003, balanced weights", "encoder": "shipped ONNX int8 defaketive-xlmr-firecs-v1-onnx-int8-e04da4c2"}, art)
    lock = {"locked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "rule": "Written before the confirmation set was built or annotated. Each locked configuration is scored once on it; the set selects nothing and nothing is tuned afterwards.",
            "T0": {"artifact": "research/artifacts/sentiment_head_v1.joblib", "sha256": xdata.sha256(xdata.ROOT / "research/artifacts/sentiment_head_v1.joblib")},
            "T7": {"artifact": "research/artifacts/sentiment_head_v2_t7.joblib", "sha256": xdata.sha256(art), "training_rows": int(len(yt)), "training_labels": {l: int((yt == k).sum()) for k, l in enumerate(L)},
                   "v1_rows_in_training": len(cand), "dev_pool_rows_in_training": 0,
                   "selection_note": "T7 was chosen among eight configurations on the 303-row policy-v1 dev validation (Claude-annotated); its dev score is therefore optimistic; the confirmation set is the unbiased check"},
            "selection_evidence": "results/phase3_experiments.json", "shipped_model_unchanged": True, "frozen_test_and_heldout_v2_used": False}
    json.dump(lock, open(X / "phase3_lock.json", "w"), indent=1)
    print(lock["T7"])


if __name__ == "__main__":
    main()
