"""Phase 4: neutral recovery on a NEW product-grouped development split built from every policy-v1 row (dev pool 400 + all 3,000 neutral candidates), all labelled by Claude (not ChatGPT).

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/phase4_experiments.py

What is NOT touched: the frozen 400-review test, the Phase 3 confirmation set (200 rows, kept as a clean check), held-out v2. Nothing here is scored on them; no configuration is selected on them.
Development protocol: 5-fold StratifiedGroupKFold by product (rows of one product never straddle train and validation), repeated with 3 fixed split seeds (11, 12, 13); the training part of each
fold = the policy-filtered old corpus (same rule as Phase 3: feature-list-shaped marketplace/AI-pool rows and rows equal to a v1 review removed) + the v1 rows of the training folds.
Reported: pooled out-of-fold metrics per seed (mean and spread across seeds), the natural-distribution subset (dev-pool rows only: the candidate pool is a biased sample by construction), and the
tag-list vs opinion-bearing split. Mixed and unclear rows are counted but kept out of the three-class scores. The locked Phase 3 artifacts (T0, T7) are scored on the rows they never saw.
A two-stage pipeline (binary no-opinion detector, then the three-class head for the rest) is compared with the one-stage head on identical folds; its binary F1 is NOT presented as three-class F1.
Writes results/phase4_experiments.json and results/phase4_false_neutral.json.
"""
import collections, csv, json, pathlib, re, sys
import joblib
import numpy as np

X = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(X))
import xdata, metrics_x, neutral_candidates, optimize_head, phase3_experiments as p3  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import StratifiedGroupKFold  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

L = xdata.LABELS
A = X / "annotation"
CACHE = X / "data" / "head"
SEEDS = (11, 12, 13)
LUKEWARM = re.compile(r"\b(ok(?:ay)?(?: lang| lng| naman| nmn)?|pwede na|so-?so|sakto lang|sakto|medyo|not bad|average|fine|decent|goods? lang|mid)\b", re.I)


def fit(Xt, yt, C=0.003, cw=None, w=None):
    m = make_pipeline(StandardScaler(), LogisticRegression(C=C, class_weight=cw, max_iter=3000))
    m.fit(Xt, yt, logisticregression__sample_weight=w)
    return m


def tab(y, p):
    s = metrics_x.summarize(np.asarray(y), np.asarray(p)); c = s["classes"]
    return {"n": int(len(y)), "accuracy": s["accuracy"], "macro_precision": float(np.mean([c[k]["precision"] for k in L])), "macro_recall": float(np.mean([c[k]["recall"] for k in L])),
            "macro_f1": s["macro_f1"], "weighted_f1": s["weighted_f1"], "classes": c, "confusion": s["confusion"]}


def main():
    rows = p3.v1_rows()
    ids = json.load(open(CACHE / "v1_ids.json"))
    assert ids == [r["id"] for r in rows], "annotation changed since embedding: rerun phase3_experiments.py embed"
    EV = np.load(CACHE / "v1_emb.npy")[:, :768]
    meta = json.load(open(CACHE / "corpus_meta.json")); EC = np.load(CACHE / "corpus_emb.npy")[:, :768]
    yc = np.array([L.index(m["label"]) for m in meta]); srcc = np.array([m["source"] for m in meta])
    fc = {r["id"]: r["text"] for r in xdata.load_firecs("train")}; mk = {r["id"]: r["text"] for r in xdata.load_marketplace()["market_train_v3"]}
    pool = {r["id"]: r["review_text"] for r in csv.DictReader(open(optimize_head.POOL_AI, encoding="utf-8-sig"))}
    textc = [fc.get(m["id"]) or mk.get(m["id"]) or pool.get(m["id"], "") for m in meta]
    listshape = np.array(["feature_list" in neutral_candidates.cues(t) for t in textc])
    v1_norm = {xdata.norm_text(r["text"]) for r in rows}
    in_v1 = np.array([xdata.norm_text(t) in v1_norm for t in textc])
    keep_policy = ~(((srcc == "market_team") | (srcc == "ai_pool")) & listshape) & ~in_v1
    mask_no_fneu = keep_policy & ~((srcc == "firecs") & (yc == 1))
    lang = {}
    for f in ("neutral_candidate_pool_ai_v1.csv", "dev_pool_sheet_ai_v1.csv"):
        for r in csv.DictReader(open(A / "ai_labelled" / f, encoding="utf-8-sig")):
            lang[r["id"]] = r["language_hint"]

    idx3 = [i for i, r in enumerate(rows) if r["label"] in L]
    R = [rows[i] for i in idx3]
    Xv = EV[idx3]; y = np.array([L.index(r["label"]) for r in R]); g = np.array([r["group"] for r in R])
    noop = np.array(["no-opinion" in r["tags"] for r in R], dtype=int)
    is_dev = np.array([r["set"] == "dev_pool" for r in R]); overlap = np.array([r["overlap_with_old_corpus"] for r in R])
    shape = np.array(["feature_list" in neutral_candidates.cues(r["text"]) for r in R])
    out = {"annotator": "Claude (claude-sonnet-5-5) via Claude Code; recorded as Claude, not ChatGPT; one annotator, no human review", "policy": "v1",
           "rows": {"all_v1_rows": len(rows), "three_class": len(R), "mixed": sum(r["label"] == "mixed" for r in rows), "unclear": sum(r["label"] == "unclear" for r in rows),
                    "labels_three_class": {l: int((y == k).sum()) for k, l in enumerate(L)}, "dev_pool_rows": int(is_dev.sum()), "candidate_rows": int((~is_dev).sum()),
                    "products": int(len(set(g))), "no_opinion_tagged": int(noop.sum())},
           "split_seeds": list(SEEDS), "untouched": ["frozen 400-review test", "Phase 3 confirmation set (200)", "held-out v2 (not built)"]}
    print(out["rows"], flush=True)

    lock = json.load(open(X / "phase3_lock.json"))
    t0 = joblib.load(xdata.ROOT / lock["T0"]["artifact"])["pipeline"]; t7 = joblib.load(xdata.ROOT / lock["T7"]["artifact"])["pipeline"]
    p_t0 = t0.predict(Xv); p_t7 = t7.predict(Xv)
    # rows the locked models never saw: T0 saw the 73 dev rows that were in the old corpus; T7 also trained on the 200 early candidate rows
    early = {r["id"] for r in rows if r["set"] == "neutral_candidates" and re.fullmatch(r"N\d{4}", r["id"])}
    early_ids = set()
    for b in (1, 2, 30, 45):
        for r in csv.DictReader(open(A / "chatgpt_batches" / f"neutral_candidates_batch_{b:02d}.csv", encoding="utf-8-sig")):
            early_ids.add(r["id"])
    seen_t7 = np.array([r["id"] in early_ids for r in R])
    clean = ~overlap & ~seen_t7
    out["locked_phase3_models_on_unseen_v1_rows"] = {"rows": int(clean.sum()), "labels": {l: int((y[clean] == k).sum()) for k, l in enumerate(L)},
                                                     "T0_sentiment_head_v1": tab(y[clean], p_t0[clean]), "T7": tab(y[clean], p_t7[clean]),
                                                     "T0_natural_distribution_dev_pool": tab(y[clean & is_dev], p_t0[clean & is_dev]), "T7_natural_distribution_dev_pool": tab(y[clean & is_dev], p_t7[clean & is_dev])}
    for k in ("T0_sentiment_head_v1", "T7"):
        t = out["locked_phase3_models_on_unseen_v1_rows"][k]
        print(f"locked {k} on {t['n']} unseen v1 rows: acc {t['accuracy']:.3f} macroF1 {t['macro_f1']:.3f} neutral F1 {t['classes']['neutral']['f1']:.2f}", flush=True)

    def base_train(kind):
        m = {"filtered": keep_policy, "no_firecs_neutral": mask_no_fneu, "v1_only": np.zeros(len(yc), bool)}[kind]
        return EC[m], yc[m]

    def cfg_fn(name):
        # returns function(train_idx, test_idx) -> predictions
        def run(tr, te):
            if name == "R1 v1 rows only, balanced":
                Xt, yt = Xv[tr], y[tr]; return fit(Xt, yt, cw="balanced").predict(Xv[te])
            kind = "filtered" if name.startswith("R3") else "no_firecs_neutral"
            Xc, ycc = base_train(kind)
            Xt = np.vstack([Xc, Xv[tr]]); yt = np.concatenate([ycc, y[tr]])
            if name.startswith("R4"):  # cap the weight of tag-list no-opinion neutrals (duplication check)
                w = np.concatenate([np.ones(len(ycc)), np.where(noop[tr] == 1, 0.3, 1.0)])
                return fit(Xt, yt, cw="balanced", w=w).predict(Xv[te])
            if name.startswith("R5"):  # old-corpus + v1, no class weights
                return fit(Xt, yt, cw=None).predict(Xv[te])
            if name.startswith("R6"):  # two-stage: no-opinion detector (v1 rows) then the three-class head
                det = fit(Xv[tr], noop[tr], C=0.03, cw="balanced")
                head = fit(Xt, yt, cw="balanced")
                pn = det.predict_proba(Xv[te])[:, 1]; ph = head.predict(Xv[te])
                return np.where(pn >= 0.5, 1, ph)
            if name.startswith("R7"):  # two-stage, head trained only on rows that are not no-opinion
                det = fit(Xv[tr], noop[tr], C=0.03, cw="balanced")
                keep = np.concatenate([np.ones(len(ycc), bool), noop[tr] == 0])
                head = fit(Xt[keep], yt[keep], cw="balanced")
                pn = det.predict_proba(Xv[te])[:, 1]; ph = head.predict(Xv[te])
                return np.where(pn >= 0.5, 1, ph)
            return fit(Xt, yt, cw="balanced").predict(Xv[te])  # R2 (T7 recipe retrained)
        return run

    names = ["R1 v1 rows only, balanced", "R2 T7 recipe retrained on v1 folds (filtered corpus, no FiReCS neutral, balanced)", "R3 R2 with FiReCS neutral kept",
             "R4 R2 with no-opinion tag-list rows down-weighted to 0.3", "R5 R2 without class weights", "R6 two-stage: no-opinion detector, else R2 head",
             "R7 two-stage: detector, head trained without no-opinion rows"]
    res = {n: {"seeds": {}} for n in names}
    oof_keep = {}
    for s in SEEDS:
        folds = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=s).split(Xv, y, g))
        leak = max(len(set(g[tr]) & set(g[te])) for tr, te in folds)
        assert leak == 0, "product leakage between folds"
        for n in names:
            oof = np.zeros(len(y), dtype=int); f = cfg_fn(n)
            for tr, te in folds:
                oof[te] = f(tr, te)
            t = tab(y, oof)
            t["natural_distribution_dev_pool"] = tab(y[is_dev], oof[is_dev]); t["tag_list_shaped_rows"] = tab(y[shape], oof[shape]) if shape.sum() else None
            t["opinion_rows_not_tag_list"] = tab(y[~shape], oof[~shape])
            res[n]["seeds"][str(s)] = t
            if s == SEEDS[0]:
                oof_keep[n] = oof
            print(f"seed {s} {n[:60]:60} acc {t['accuracy']:.3f} macroF1 {t['macro_f1']:.3f} F1 neg/neu/pos {t['classes']['negative']['f1']:.2f}/{t['classes']['neutral']['f1']:.2f}/{t['classes']['positive']['f1']:.2f} | natural-dist mF1 {t['natural_distribution_dev_pool']['macro_f1']:.3f}", flush=True)
    for n in names:
        sd = res[n]["seeds"]
        def ms(key, sub=None):
            v = [(sd[s][sub][key] if sub else sd[s][key]) for s in sd]
            return [float(np.mean(v)), float(np.std(v))]
        res[n]["summary_mean_std_over_split_seeds"] = {"accuracy": ms("accuracy"), "macro_precision": ms("macro_precision"), "macro_recall": ms("macro_recall"), "macro_f1": ms("macro_f1"), "weighted_f1": ms("weighted_f1"),
                                                      "natural_distribution_macro_f1": ms("macro_f1", "natural_distribution_dev_pool"),
                                                      "f1_per_class": {k: [float(np.mean([sd[s]["classes"][k]["f1"] for s in sd])), float(np.std([sd[s]["classes"][k]["f1"] for s in sd]))] for k in L},
                                                      "precision_per_class": {k: float(np.mean([sd[s]["classes"][k]["precision"] for s in sd])) for k in L},
                                                      "recall_per_class": {k: float(np.mean([sd[s]["classes"][k]["recall"] for s in sd])) for k in L}}
    # binary no-opinion detector, reported on its own task (not three-class)
    det_res = {}
    for s in SEEDS:
        folds = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=s).split(Xv, y, g))
        o = np.zeros(len(y), dtype=int)
        for tr, te in folds:
            o[te] = fit(Xv[tr], noop[tr], C=0.03, cw="balanced").predict(Xv[te])
        tp = int(((noop == 1) & (o == 1)).sum()); fp = int(((noop == 0) & (o == 1)).sum()); fn = int(((noop == 1) & (o == 0)).sum())
        pr = tp / max(1, tp + fp); rc = tp / max(1, tp + fn)
        det_res[str(s)] = {"precision": pr, "recall": rc, "f1": 2 * pr * rc / max(1e-9, pr + rc), "tp": tp, "fp": fp, "fn": fn, "positives": int(noop.sum())}
    out["no_opinion_detector_binary"] = {"seeds": det_res, "note": "binary task only; this F1 is not a three-class score"}
    out["configs"] = res
    # product-level bootstrap interval for the best retrained head, seed 11
    best = max(names, key=lambda n: res[n]["summary_mean_std_over_split_seeds"]["macro_f1"][0])
    out["best_on_development_by_mean_macro_f1"] = best
    out["best_macro_f1_ci95_product_bootstrap_seed11"] = metrics_x.boot(y, oof_keep[best], list(g), n=500)
    # false-neutral analysis (R2, seed 11)
    oof = oof_keep[names[1]]
    fn_out = {"model": names[1], "split_seed": SEEDS[0]}
    cm = tab(y, oof)["confusion"]; fn_out["confusion_rows_true_neg_neu_pos"] = cm
    def bucket(i):
        r = R[i]; t = r["text"]
        return {"language": lang.get(r["id"], "?"), "tag_list_shape": bool(shape[i]), "no_opinion_tag": bool(noop[i]), "lukewarm_words": bool(LUKEWARM.search(t)), "low_confidence": r["conf"] == "low",
                "has_numeric_ratings": bool(re.search(r"\b\d{1,3}\s*(?:/\s*10+|out of|%)|:\s*\d{1,2}\b", t))}
    for key, (a, b) in {"neutral_to_positive": (1, 2), "positive_to_neutral": (2, 1), "neutral_to_negative": (1, 0), "negative_to_neutral": (0, 1)}.items():
        sel = np.where((y == a) & (oof == b))[0]
        c = collections.Counter()
        for i in sel:
            for k, v in bucket(i).items():
                c[f"{k}={v}"] += 1
        fn_out[key] = {"count": int(len(sel)), "of_true_class": int((y == a).sum()), "features": dict(sorted(c.items())),
                       "examples": [{"id": R[i]["id"], "text": R[i]["text"][:220], "true_tags": R[i]["tags"], "set": R[i]["set"]} for i in sel[:12]]}
    fn_out["natural_distribution_neutral_to_positive_vs_positive_to_neutral"] = {
        "neutral_to_positive": int(((y == 1) & (oof == 2) & is_dev).sum()), "positive_to_neutral": int(((y == 2) & (oof == 1) & is_dev).sum()), "dev_pool_neutral": int(((y == 1) & is_dev).sum()), "dev_pool_positive": int(((y == 2) & is_dev).sum())}
    by_lang = {}
    for lg in sorted(set(lang.get(r["id"], "?") for r in R)):
        m = np.array([lang.get(r["id"], "?") == lg for r in R])
        if m.sum() >= 30:
            t = tab(y[m], oof[m]); by_lang[lg] = {"n": t["n"], "accuracy": t["accuracy"], "neutral_f1": t["classes"]["neutral"]["f1"], "macro_f1": t["macro_f1"], "labels": {l: int((y[m] == k).sum()) for k, l in enumerate(L)}}
    fn_out["by_language_hint"] = by_lang
    json.dump(out, open(X / "results/phase4_experiments.json", "w"), indent=1)
    json.dump(fn_out, open(X / "results/phase4_false_neutral.json", "w"), indent=1)
    print("best:", best, out["best_macro_f1_ci95_product_bootstrap_seed11"])


if __name__ == "__main__":
    main()
