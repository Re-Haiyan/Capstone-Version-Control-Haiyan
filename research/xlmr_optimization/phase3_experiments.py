"""Phase 3: policy-v1-consistent training data, evaluated on policy-v1 AI-assisted labels (Claude-annotated development rows). Frozen test and held-out v2: never touched.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/phase3_experiments.py embed     (embeddings of the newly annotated rows, cached)
    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/phase3_experiments.py run       (corpus audit, strategies, cross-validation, no-opinion detector)

New v1 rows (annotator: Claude, recorded as such; not ChatGPT): the 400-review dev pool and 200 neutral-candidate rows (batches 01, 02, 30, 45), mixed and unclear kept apart.
Corpus audit and the documented, policy-based exclusion (NOT a metric-driven relabelling): training rows of the older sources (marketplace team labels, AI pool) whose text has the
feature-list shape were labelled under rubrics that disagree with policy v1 S4 (21% and 1% neutral); they are EXCLUDED from v1 training instead of being relabelled. FiReCS neutral
rows are an alternative-convention class (mixed folded into neutral): compared with and without them. Rows equal to a dev-pool or candidate review, and the 73 dev-pool rows already
in the training corpus, are removed from validation / training respectively so nothing is trained on and validated on at once.
Configurations are compared on (a) the policy-v1 dev validation (dev-pool rows not in the old corpus; three-class rows only) and (b) 5-fold product-grouped cross-validation over all
eligible v1 rows (training = filtered corpus + the v1 training folds). Writes results/phase3_experiments.json.
"""
import collections, csv, json, pathlib, sys
import numpy as np

X = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(X))
import xdata, metrics_x, neutral_candidates, optimize_head  # noqa: E402

L = xdata.LABELS
A = X / "annotation"
CACHE = X / "data" / "head"


def v1_rows():
    rows = []
    pm = {r["sheet_id"]: r for r in csv.DictReader(open(A / "PRIVATE_id_map.csv", encoding="utf-8"))}
    nm = {r["id"]: r for r in csv.DictReader(open(A / "PRIVATE_neutral_candidate_map.csv", encoding="utf-8"))}
    overlap = {r["dev_pool_id"] for r in csv.DictReader(open(A / "dev_pool_overlap_with_training.csv"))}
    for r in csv.DictReader(open(A / "ai_labelled/dev_pool_sheet_ai_v1.csv", encoding="utf-8-sig")):
        rows.append({"id": r["id"], "set": "dev_pool", "text": r["review_text"], "label": r["sentiment"], "tags": r["tags"], "group": pm[r["id"]]["product_link"], "overlap_with_old_corpus": r["id"] in overlap, "conf": r["confidence"]})
    for r in csv.DictReader(open(A / "ai_labelled/neutral_candidate_pool_ai_v1.csv", encoding="utf-8-sig")):
        rows.append({"id": r["id"], "set": "neutral_candidates", "text": r["review_text"], "label": r["sentiment"], "tags": r["tags"], "group": nm[r["id"]]["group"], "overlap_with_old_corpus": False, "conf": r["confidence"]})
    return rows


def table(yy, pp):
    s = metrics_x.summarize(yy, pp)
    c = s["classes"]
    return {"n": int(len(yy)), "accuracy": s["accuracy"], "macro_f1": s["macro_f1"], "weighted_f1": s["weighted_f1"], "classes": c, "confusion": s["confusion"],
            "macro_precision": float(np.mean([c[k]["precision"] for k in L])), "macro_recall": float(np.mean([c[k]["recall"] for k in L]))}


def boot_ci(y, p, groups, n=500):
    return metrics_x.boot(np.array(y), np.array(p), groups, n=n)


def main():
    cmd = sys.argv[1]
    rows = v1_rows()
    if cmd == "embed":
        np.save(CACHE / "v1_emb.npy", optimize_head.embed_all([r["text"] for r in rows]))
        json.dump([r["id"] for r in rows], open(CACHE / "v1_ids.json", "w"))
        print(len(rows), "embedded")
        return
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    ids = json.load(open(CACHE / "v1_ids.json"))
    assert ids == [r["id"] for r in rows], "annotation files changed since the embeddings were cached: run embed again"
    EV = np.load(CACHE / "v1_emb.npy")[:, :768]
    meta = json.load(open(CACHE / "corpus_meta.json")); EC = np.load(CACHE / "corpus_emb.npy")[:, :768]
    yc = np.array([L.index(m["label"]) for m in meta]); srcc = np.array([m["source"] for m in meta]); grpc = np.array([m["group"] for m in meta])
    fc = {r["id"]: r["text"] for r in xdata.load_firecs("train")}; mk = {r["id"]: r["text"] for r in xdata.load_marketplace()["market_train_v3"]}
    pool = {r["id"]: r["review_text"] for r in csv.DictReader(open(optimize_head.POOL_AI, encoding="utf-8-sig"))}
    textc = [fc.get(m["id"]) or mk.get(m["id"]) or pool.get(m["id"], "") for m in meta]
    listshape = np.array(["feature_list" in neutral_candidates.cues(t) for t in textc])
    v1_norm = {xdata.norm_text(r["text"]) for r in rows}
    in_v1 = np.array([xdata.norm_text(t) in v1_norm for t in textc])
    out = {"annotator": "Claude (claude-sonnet-5-5) via Claude Code, recorded as Claude; not ChatGPT", "policy": "v1"}
    lab = collections.Counter((r["set"], r["label"]) for r in rows)
    out["v1_labelled_rows"] = {f"{s}: {l}": n for (s, l), n in sorted(lab.items())}
    # corpus audit
    audit = {"corpus_rows": int(len(yc))}
    for s in ("firecs", "market_team", "ai_pool"):
        m = srcc == s
        audit[s] = {"rows": int(m.sum()), "labels": {l: int((yc[m] == k).sum()) for k, l in enumerate(L)}, "feature_list_shaped_rows": int((m & listshape).sum()),
                    "feature_list_shaped_labels": {l: int((m & listshape & (yc == k)).sum()) for k, l in enumerate(L)}}
    audit["rows_equal_to_a_v1_labelled_review"] = int(in_v1.sum())
    out["corpus_audit"] = audit
    keep_policy = ~(((srcc == "market_team") | (srcc == "ai_pool")) & listshape) & ~in_v1
    out["exclusion_procedure"] = {"rule": "exclude (do not relabel) market_team and ai_pool rows with the feature-list shape (older rubrics conflict with policy v1 S4), and any corpus row equal to a v1-labelled review",
                                  "rows_excluded": int((~keep_policy).sum()), "rows_kept": int(keep_policy.sum())}
    three = lambda r: r["label"] in L
    dev_rows = [r for r in rows if r["set"] == "dev_pool" and three(r) and not r["overlap_with_old_corpus"]]
    cand_rows = [r for r in rows if r["set"] == "neutral_candidates" and three(r)]
    idx = {r["id"]: i for i, r in enumerate(rows)}
    Xd = EV[[idx[r["id"]] for r in dev_rows]]; yd = np.array([L.index(r["label"]) for r in dev_rows]); gd = [r["group"] for r in dev_rows]
    Xn = EV[[idx[r["id"]] for r in cand_rows]]; yn = np.array([L.index(r["label"]) for r in cand_rows])
    out["dev_validation"] = {"rows": len(dev_rows), "labels": {l: int((yd == k).sum()) for k, l in enumerate(L)}, "excluded_overlap_with_old_corpus": int(sum(r["overlap_with_old_corpus"] for r in rows if r["set"] == "dev_pool")),
                             "excluded_mixed_or_unclear": int(sum(1 for r in rows if r["set"] == "dev_pool" and not three(r)))}

    def fit(Xt, yt, C=0.003, cw=None, w=None):
        m = make_pipeline(StandardScaler(), LogisticRegression(C=C, class_weight=cw, max_iter=3000))
        m.fit(Xt, yt, logisticregression__sample_weight=w)
        return m

    def corpus(neutral_firecs=True, filtered=True):
        m = keep_policy.copy() if filtered else ~in_v1
        if not neutral_firecs:
            m &= ~((srcc == "firecs") & (yc == 1))
        return m

    configs = {
        "T0 previous head (old corpus, locked sentiment_head_v1 setting)": dict(mask=~in_v1, v1_train=False, cw=None),
        "T1 old corpus + class weights": dict(mask=~in_v1, v1_train=False, cw="balanced"),
        "T2 v1-filtered corpus": dict(mask=corpus(True), v1_train=False, cw=None),
        "T3 v1-filtered corpus, FiReCS neutral excluded": dict(mask=corpus(False), v1_train=False, cw=None),
        "T4 v1-filtered corpus + 200 v1 candidate rows": dict(mask=corpus(True), v1_train=True, cw=None),
        "T5 T4 + class weights": dict(mask=corpus(True), v1_train=True, cw="balanced"),
        "T6 T4 with FiReCS neutral excluded": dict(mask=corpus(False), v1_train=True, cw=None),
        "T7 T6 + class weights": dict(mask=corpus(False), v1_train=True, cw="balanced"),
    }
    res = {}
    for name, c in configs.items():
        Xt = EC[c["mask"]]; yt = yc[c["mask"]]
        if c["v1_train"]:
            Xt = np.vstack([Xt, Xn]); yt = np.concatenate([yt, yn])
        m = fit(Xt, yt, cw=c["cw"])
        p = m.predict(Xd)
        t = table(yd, p); t["macro_f1_ci95_product_bootstrap"] = boot_ci(yd, p, gd)
        t["training_rows"] = int(len(yt)); t["training_labels"] = {l: int((yt == k).sum()) for k, l in enumerate(L)}
        res[name] = {"dev_v1": t}
        print(f"{name}: dev-v1 n={t['n']} acc {t['accuracy']:.3f} macroF1 {t['macro_f1']:.3f} neutral P/R/F1 {t['classes']['neutral']['precision']:.2f}/{t['classes']['neutral']['recall']:.2f}/{t['classes']['neutral']['f1']:.2f} | train {t['training_labels']}", flush=True)
    # cross-validation over all eligible v1 rows (dev non-overlap + candidates), product-grouped; training = filtered corpus + v1 training folds
    allv1 = dev_rows + cand_rows
    Xa = np.vstack([Xd, Xn]); ya = np.concatenate([yd, yn]); ga = np.array([r["group"] for r in allv1])
    folds = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=3).split(Xa, ya, ga))
    for name in ("T0 previous head (old corpus, locked sentiment_head_v1 setting)", "T2 v1-filtered corpus", "T4 v1-filtered corpus + 200 v1 candidate rows", "T5 T4 + class weights", "T6 T4 with FiReCS neutral excluded", "T7 T6 + class weights"):
        c = configs[name]
        oof = np.zeros(len(ya), dtype=int)
        for tr, te in folds:
            Xt = EC[c["mask"]]; yt = yc[c["mask"]]
            if c["v1_train"]:
                Xt = np.vstack([Xt, Xa[tr]]); yt = np.concatenate([yt, ya[tr]])
            oof[te] = fit(Xt, yt, cw=c["cw"]).predict(Xa[te])
        t = table(ya, oof); t["macro_f1_ci95_product_bootstrap"] = boot_ci(ya, oof, list(ga))
        res[name]["cv_v1"] = t
        print(f"  CV {name}: n={t['n']} macroF1 {t['macro_f1']:.3f} neutral F1 {t['classes']['neutral']['f1']:.2f} acc {t['accuracy']:.3f}", flush=True)
    out["configs"] = res
    # separately evaluated no-opinion detector (binary), product-grouped CV on all v1 rows incl. mixed/unclear excluded
    noop = np.array(["no-opinion" in r["tags"] for r in allv1], dtype=int)
    oofn = np.zeros(len(noop), dtype=int); prob = np.zeros(len(noop))
    for tr, te in folds:
        m = fit(Xa[tr], noop[tr], C=0.03, cw="balanced"); oofn[te] = m.predict(Xa[te]); prob[te] = m.predict_proba(Xa[te])[:, 1]
    tp = int(((noop == 1) & (oofn == 1)).sum()); fp = int(((noop == 0) & (oofn == 1)).sum()); fn = int(((noop == 1) & (oofn == 0)).sum())
    pr = tp / max(1, tp + fp); rc = tp / max(1, tp + fn)
    out["no_opinion_detector_cv"] = {"rows": int(len(noop)), "positives": int(noop.sum()), "precision": pr, "recall": rc, "f1": 2 * pr * rc / max(1e-9, pr + rc), "tp": tp, "fp": fp, "fn": fn,
                                     "note": "binary no-opinion vs other, logistic on the shipped encoder embedding, product-grouped 5-fold CV over the v1-labelled rows; small and annotated by one AI annotator"}
    print("no-opinion detector CV:", out["no_opinion_detector_cv"], flush=True)
    json.dump(out, open(X / "results/phase3_experiments.json", "w"), indent=1)


if __name__ == "__main__":
    main()
