"""Fits the two prespecified Phase 4 head candidates on ALL three-class policy-v1 rows (dev pool + 3,000 neutral candidates; Claude labels) and locks them BEFORE any further scoring.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/phase4_fit_and_lock.py

P4A = v1 rows only, logistic head C 0.003, balanced class weights (best mean macro F1 on the product-grouped development split).
P4B = policy-filtered old corpus (FiReCS neutral excluded) + v1 rows, no class weights (the best candidate that keeps the broader corpus; development split R5).
Neither uses the frozen test, the Phase 3 confirmation set or held-out v2. Writes research/artifacts/sentiment_head_v3_p4a.joblib / _p4b.joblib and phase4_lock.json.
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
    assert json.load(open(p3.CACHE / "v1_ids.json")) == [r["id"] for r in rows]
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
    idx = [i for i, r in enumerate(rows) if r["label"] in L]
    Xv = EV[idx]; yv = np.array([L.index(rows[i]["label"]) for i in idx])
    out = {"locked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "rule": "Fitted on all three-class v1 rows and locked before any scoring of the Phase 3 confirmation set with a Phase 4 model; selection evidence is the product-grouped development split (results/phase4_experiments.json).",
           "annotator_of_v1_rows": "Claude (claude-sonnet-5-5), policy v1; one annotator; not ChatGPT; no human review"}
    for key, name, (Xt, yt), cw, cfg in (
            ("P4A", "sentiment_head_v3_p4a.joblib", (Xv, yv), "balanced", "v1 rows only, C 0.003, balanced"),
            ("P4B", "sentiment_head_v3_p4b.joblib", (np.vstack([EC[keep], Xv]), np.concatenate([yc[keep], yv])), None, "filtered corpus without FiReCS neutral + v1 rows, C 0.003, no class weights")):
        m = make_pipeline(StandardScaler(), LogisticRegression(C=0.003, class_weight=cw, max_iter=3000)).fit(Xt, yt)
        art = xdata.ROOT / "research/artifacts" / name
        joblib.dump({"pipeline": m, "classes": L, "config": f"{key}: {cfg}", "encoder": "shipped ONNX int8 defaketive-xlmr-firecs-v1-onnx-int8-e04da4c2"}, art)
        out[key] = {"artifact": f"research/artifacts/{name}", "sha256": xdata.sha256(art), "config": cfg, "training_rows": int(len(yt)), "training_labels": {l: int((yt == k).sum()) for k, l in enumerate(L)}}
        print(key, out[key])
    out["confirmation_set_used_in_training_or_selection"] = False
    out["frozen_test_and_heldout_v2_used"] = False
    out["shipped_model_unchanged"] = True
    json.dump(out, open(X / "phase4_lock.json", "w"), indent=1)


if __name__ == "__main__":
    main()
