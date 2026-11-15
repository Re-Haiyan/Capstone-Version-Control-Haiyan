"""Neutral-focused strategy comparison for the sentiment head (training data only; the frozen test and the already-scored results are not touched).

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/neutral_strategies.py

Data: the optimisation corpus of optimize_head.py (FiReCS train, marketplace team labels, AI-pool labels; frozen-test matches already removed). Features: the shipped encoder's
768-d embedding (cached). Development validation (separate, never trained on in that comparison): the 36 held-out marketplace products of splits.json plus 10% of the pool's
annotation groups (seed 11). FiReCS rows are used for training only (the encoder has seen their texts, so FiReCS validation would be inflated). Grouped 5-fold cross-validation is
also reported for stability. Selection (provisional, see the report): macro F1 on the marketplace slice of the development validation. Strategies:
 S0 baseline; S1 class-weighted; S2 balanced resampling of the training fold; S3 neutral hard-example mining (inner 3-fold out-of-fold: neutral rows predicted non-neutral get weight 3);
 S4 per-class bias calibration (bias chosen on an inner 20% grouped split of the training fold); S5 = S1 + S3 + S4.
Logistic head versus full fine-tuning: full fine-tuning is NOT run (about 2 hours of CPU per run and the labels do not yet follow one neutral definition; see the report).
Writes results/neutral_strategies.json.
"""
import collections, csv, json, pathlib, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

X = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(X))
import xdata, metrics_x, neutral_candidates  # noqa: E402

L = xdata.LABELS
meta = json.load(open(X / "data/head/corpus_meta.json"))
E = np.load(X / "data/head/corpus_emb.npy")[:, :768]
y = np.array([L.index(m["label"]) for m in meta]); src = np.array([m["source"] for m in meta]); grp = np.array([m["group"] for m in meta]); ids = [m["id"] for m in meta]
splits = json.load(open(xdata.DATA / "splits.json"))
rng = np.random.default_rng(11)
pool_groups = sorted({g for g, s in zip(grp, src) if s == "ai_pool"})
dev_pool_groups = set(rng.choice(pool_groups, int(0.10 * len(pool_groups)), replace=False))
market_val = set(splits["market_val"])
dev = np.array([(i in market_val) or (s == "ai_pool" and g in dev_pool_groups) for i, s, g in zip(ids, src, grp)])
train_idx, dev_idx = np.where(~dev)[0], np.where(dev)[0]


def fit(Xt, yt, w=None, C=0.003, cw=None):
    m = make_pipeline(StandardScaler(), LogisticRegression(C=C, class_weight=cw, max_iter=2000))
    m.fit(Xt, yt, logisticregression__sample_weight=w)
    return m


def predict_logp(m, Xs):
    return np.log(np.clip(m.predict_proba(Xs), 1e-9, 1))


def run(strategy, tr, te, C=0.003):
    """Fit on rows `tr` (indices), return log-probabilities for rows `te`. Everything that tunes (mining, bias) happens INSIDE `tr`."""
    Xt, yt, gt = E[tr], y[tr], grp[tr]
    w, cw, bias = None, None, np.zeros(3)
    if strategy in ("S1", "S5"):
        cw = "balanced"
    if strategy == "S2":
        r = np.random.default_rng(3)
        n = max(np.bincount(yt))
        pick = np.concatenate([r.choice(np.where(yt == k)[0], n, replace=True) for k in range(3)])
        Xt, yt = Xt[pick], yt[pick]
    if strategy in ("S3", "S5"):
        oof = np.zeros(len(yt), dtype=int)
        for a, b in StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=5).split(Xt, yt, gt):
            oof[b] = fit(Xt[a], yt[a], C=C, cw=cw).predict(Xt[b])
        w = np.where((yt == 1) & (oof != 1), 3.0, 1.0)
    m = fit(Xt, yt, w=w, C=C, cw=cw)
    if strategy in ("S4", "S5"):
        a, b = next(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=9).split(E[tr], y[tr], grp[tr]))
        inner = fit(E[tr][a], y[tr][a], C=C, cw=cw)
        lp = predict_logp(inner, E[tr][b])
        best = -1
        for b1 in np.arange(-1, 2.01, 0.25):
            for b2 in np.arange(-1, 1.01, 0.25):
                f = metrics_x.macro(y[tr][b], (lp + np.array([b2, b1, 0])).argmax(1))
                if f > best + 1e-9:
                    best, bias = f, np.array([b2, b1, 0])
    return predict_logp(m, E[te]) + bias, bias


def table(yy, pp):
    s = metrics_x.summarize(yy, pp)
    c = s["classes"]
    return {"n": int(len(yy)), "accuracy": s["accuracy"], "macro_f1": s["macro_f1"], "weighted_f1": s["weighted_f1"], "classes": c, "confusion": s["confusion"],
            "macro_precision": float(np.mean([c[k]["precision"] for k in L])), "macro_recall": float(np.mean([c[k]["recall"] for k in L]))}


def main():
    out = {"dev_rows": int(len(dev_idx)), "train_rows": int(len(train_idx)), "dev_by_source": {s: int(((src == s) & dev).sum()) for s in ("firecs", "market_team", "ai_pool")},
           "dev_label_distribution": {s: {l: int(((src == s) & dev & (y == k)).sum()) for k, l in enumerate(L)} for s in ("market_team", "ai_pool")}, "strategies": {}}
    strategies = ["S0", "S1", "S2", "S3", "S4", "S5"]
    folds = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=7).split(E, y, grp))
    for s in strategies:
        for C in (0.003, 0.03):
            lp, bias = run(s, train_idx, dev_idx, C)
            pred = lp.argmax(1)
            res = {"C": C, "bias": bias.tolist(), "dev_all": table(y[dev_idx], pred),
                   "dev_market": table(y[dev_idx][src[dev_idx] == "market_team"], pred[src[dev_idx] == "market_team"]),
                   "dev_ai_pool": table(y[dev_idx][src[dev_idx] == "ai_pool"], pred[src[dev_idx] == "ai_pool"])}
            oof = np.zeros(len(y), dtype=int)
            for tr, te in folds:
                oof[te] = run(s, tr, te, C)[0].argmax(1)
            res["cv_all"] = table(y, oof)
            res["cv_market"] = table(y[src == "market_team"], oof[src == "market_team"])
            res["cv_ai_pool"] = table(y[src == "ai_pool"], oof[src == "ai_pool"])
            res["cv_firecs"] = table(y[src == "firecs"], oof[src == "firecs"])
            out["strategies"][f"{s}_C{C}"] = res
            if s == "S0" and C == 0.003:
                out["_oof_s0"] = oof.tolist()
            m = res["dev_market"]
            print(f"{s} C={C}: dev market macroF1 {m['macro_f1']:.3f} neutral P/R/F1 {m['classes']['neutral']['precision']:.2f}/{m['classes']['neutral']['recall']:.2f}/{m['classes']['neutral']['f1']:.2f} | dev pool mF1 {res['dev_ai_pool']['macro_f1']:.3f} | CV market mF1 {res['cv_market']['macro_f1']:.3f} neutral F1 {res['cv_market']['classes']['neutral']['f1']:.2f}", flush=True)
    # neutral failure analysis on out-of-fold predictions of the baseline (training data only)
    texts = {}
    for r in xdata.load_firecs("train"):
        texts[r["id"]] = r["text"]
    for r in xdata.load_marketplace()["market_train_v3"]:
        texts[r["id"]] = r["text"]
    pool = {r["id"]: r["review_text"] for r in csv.DictReader(open(neutral_candidates_pool(), encoding="utf-8-sig"))}
    texts.update(pool)
    oof = np.array(out.pop("_oof_s0"))
    fail = collections.defaultdict(collections.Counter); examples = collections.defaultdict(list)
    for i in np.where((y == 1) & (oof != 1))[0]:
        t = texts.get(ids[i], "")
        key = f"{src[i]}: neutral predicted {L[oof[i]]}"
        fail[key]["rows"] += 1
        for c in neutral_candidates.cues(t):
            fail[key]["cue:" + c] += 1
        if len(examples[key]) < 5:
            examples[key].append(" ".join(t.split())[:200])
    out["neutral_failures_baseline_oof"] = {k: dict(v) for k, v in fail.items()}
    out["neutral_failure_examples"] = dict(examples)
    json.dump(out, open(X / "results/neutral_strategies.json", "w"), indent=1)


def neutral_candidates_pool():
    return "D:/cvc-annotations/evaluation/annotation_batch_ai_direct/assembled/annotations.csv".replace("annotations.csv", "annotations.csv")


if __name__ == "__main__":
    main()
