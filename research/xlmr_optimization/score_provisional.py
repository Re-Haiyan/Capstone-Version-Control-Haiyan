"""PROVISIONAL scoring of the LOCKED model (the shipped ONNX int8, model_selection_lock.json) on the frozen 400-review test, against the two returned sheets.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/score_provisional.py

NOT the official final evaluation: the returned sheets have unverified provenance (annotation_provenance.md) and no A03 adjudication exists. The labels used are
(1) sheet A, (2) sheet B, (3) only the reviews on which A and B give the same three-class label. Only the locked model is scored, once; no candidate is scored and nothing
here selects, tunes or thresholds anything. Mixed (no dominant polarity) and unclear rows are excluded from the three-class scores and counted. Every score is also given
excluding delivery-only reviews (either sheet's tag) and excluding reviews that appear in earlier AI- or team-labelled files (sensitivity analysis fixed in the lock).
Writes final_human_evaluation/provisional_*.json/csv.
"""
import csv, hashlib, json, pathlib, sys
import numpy as np

X = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(X))
import xdata, metrics_x, inference  # noqa: E402

OUT = X / "final_human_evaluation"
DOWN = pathlib.Path("C:/Users/cabal/Downloads")
def main():
    frozen = list(csv.DictReader(open(X / "annotation/final_test_sheet_A.csv", encoding="utf-8-sig")))
    A = {r["id"]: r for r in csv.DictReader(open(DOWN / "team_label_1_final_test_sheet_A_v1.csv", encoding="utf-8-sig"))}
    B = {r["id"]: r for r in csv.DictReader(open(DOWN / "team_label_2_final_test_sheet_B_v1.csv", encoding="utf-8-sig"))}
    pm = {r["sheet_id"]: r for r in csv.DictReader(open(X / "annotation/PRIVATE_id_map.csv", encoding="utf-8"))}
    lock = json.load(open(OUT / "model_selection_lock.json"))
    assert lock["selected_model"].startswith("the shipped model") and not lock["final_test_scored"]
    ids = [r["id"] for r in frozen]
    texts = [r["review_text"] for r in frozen]
    P = inference.probs_onnx(texts)  # one review at a time, 1 thread per worker: the locked configuration
    pred = P.argmax(1)
    with open(OUT / "provisional_predictions_shipped_model.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "p_neg", "p_neu", "p_pos", "pred"])
        for i, p in zip(ids, P):
            w.writerow([i, *[f"{v:.6f}" for v in p], xdata.LABELS[int(p.argmax())]])
    L = xdata.LABELS
    tags = lambda r: {t.strip() for t in r["tags"].split(";") if t.strip()}
    # prior-label rows: exact normalised text present in the pool, fresh_eval or al_pool
    prior = set()
    for path, col in (("evaluation/review_pool_10000.csv", "review_text"), ("research/fresh_eval/fresh_eval_sheet.csv", "review_text"), ("research/cache/al_pool.csv", "review_text")):
        n = {xdata.norm_text(r[col]) for r in csv.DictReader(open(xdata.ROOT / path, encoding="utf-8-sig"))}
        prior |= {i for i, t in zip(ids, texts) if xdata.norm_text(t) in n}
    products = {i: pm[i]["product_link"] for i in ids}
    index = {i: k for k, i in enumerate(ids)}


    def score(label_of, subset_name, rows):
        keep = [i for i in rows if label_of(i) in L]
        y = np.array([L.index(label_of(i)) for i in keep]); p = np.array([pred[index[i]] for i in keep])
        s = metrics_x.summarize(y, p)
        cls = s["classes"]
        macro_p = float(np.mean([cls[c]["precision"] for c in L])); macro_r = float(np.mean([cls[c]["recall"] for c in L]))
        ci = metrics_x.boot(y, p, [products[i] for i in keep])
        return {"subset": subset_name, "n_scored": len(keep), "accuracy": s["accuracy"], "macro_precision": macro_p, "macro_recall": macro_r, "macro_f1": s["macro_f1"], "weighted_f1": s["weighted_f1"],
                "macro_f1_ci95_product_bootstrap": ci, "classes": cls, "confusion_rows_true_cols_pred": s["confusion"]}


    results = {}
    agree = [i for i in ids if A[i]["sentiment"] == B[i]["sentiment"] and A[i]["sentiment"] in L]
    sources = {"sheet_A": lambda i: A[i]["sentiment"], "sheet_B": lambda i: B[i]["sentiment"], "A_and_B_agree": lambda i: A[i]["sentiment"] if A[i]["sentiment"] == B[i]["sentiment"] else ""}
    subsets = {"all": ids, "excluding_delivery_only": [i for i in ids if "delivery-only" not in tags(A[i]) and "delivery-only" not in tags(B[i])],
               "excluding_prior_labelled_reviews": [i for i in ids if i not in prior]}
    for sname, fn in sources.items():
        results[sname] = {k: score(fn, k, v) for k, v in subsets.items()}
    results["_notes"] = {"status": "PROVISIONAL: labels are team-supplied and of unverified provenance; no adjudication; not the official final evaluation", "model": lock["model_file_sha256"],
                         "prior_labelled_reviews_in_frozen_test": len(prior), "mixed_sheet_A": sum(A[i]["sentiment"] == "mixed" for i in ids), "mixed_sheet_B": sum(B[i]["sentiment"] == "mixed" for i in ids),
                         "unclear_A": sum(A[i]["sentiment"] == "unclear" for i in ids), "unclear_B": sum(B[i]["sentiment"] == "unclear" for i in ids), "A_and_B_agree_three_class": len(agree),
                         "predictions_sha256": hashlib.sha256(open(OUT / "provisional_predictions_shipped_model.csv", "rb").read()).hexdigest()}
    json.dump(results, open(OUT / "provisional_test_metrics.json", "w"), indent=1)
    with open(OUT / "provisional_classification_report.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["label_source", "subset", "n_scored", "class", "precision", "recall", "f1", "support", "accuracy", "macro_precision", "macro_recall", "macro_f1", "weighted_f1", "macro_f1_ci95_low", "macro_f1_ci95_high"])
        for sname in sources:
            for k, v in results[sname].items():
                for c in L:
                    cl = v["classes"][c]
                    w.writerow([sname, k, v["n_scored"], c, f"{cl['precision']:.3f}", f"{cl['recall']:.3f}", f"{cl['f1']:.3f}", cl["support"], f"{v['accuracy']:.3f}", f"{v['macro_precision']:.3f}", f"{v['macro_recall']:.3f}", f"{v['macro_f1']:.3f}", f"{v['weighted_f1']:.3f}", f"{v['macro_f1_ci95_product_bootstrap'][0]:.3f}", f"{v['macro_f1_ci95_product_bootstrap'][1]:.3f}"])
    with open(OUT / "provisional_confusion_matrices.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["label_source", "subset", "true", *["pred_" + c for c in L]])
        for sname in sources:
            for k, v in results[sname].items():
                for i, c in enumerate(L):
                    w.writerow([sname, k, c, *v["confusion_rows_true_cols_pred"][i]])
    for sname in sources:
        for k, v in results[sname].items():
            c = v["classes"]
            print(f"{sname:<14} {k:<34} n={v['n_scored']:<4} acc {v['accuracy']:.3f} macroF1 {v['macro_f1']:.3f} ({v['macro_f1_ci95_product_bootstrap'][0]:.3f}-{v['macro_f1_ci95_product_bootstrap'][1]:.3f}) | F1 neg {c['negative']['f1']:.3f} neu {c['neutral']['f1']:.3f} pos {c['positive']['f1']:.3f} | support {[c[x]['support'] for x in L]}")
    print(results["_notes"])



if __name__ == "__main__":
    main()
