"""Scores the two LOCKED Phase 4 heads (phase4_lock.json: P4A, P4B) once on the Phase 3 confirmation set (annotation/confirm_v1_manifest.json; Claude labels, policy v1), as a NON-SELECTING check.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/score_confirm_p4.py

Honest status of this set for Phase 4: it was already scored once for T0 and T7 (Phase 3), it is AI-annotated (Claude), and it is NOT product-independent of the Phase 4 training data (the 3,000 candidates now
used for training come from nearly the same products). It is therefore an intermediate consistency check, NOT the new held-out test (that needs an authorised fresh scan). Reported: all three-class rows, and the
subset whose product has no row in the Phase 4 training data. Nothing is fitted, selected or tuned here. Writes results/phase4_confirmation.json.
"""
import csv, json, pathlib, sys
import joblib
import numpy as np

X = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(X))
import xdata, metrics_x, optimize_head, phase3_experiments as p3  # noqa: E402

L = xdata.LABELS
A = X / "annotation"


def main():
    lock = json.load(open(X / "phase4_lock.json"))
    arts = {}
    for k in ("P4A", "P4B"):
        p = xdata.ROOT / lock[k]["artifact"]
        assert xdata.sha256(p) == lock[k]["sha256"], f"{k} artifact differs from the lock"
        arts[k] = joblib.load(p)["pipeline"]
    man = json.load(open(A / "confirm_v1_manifest.json"))
    assert xdata.sha256(A / "confirm_v1_sheet.csv") == man["sheet_sha256"], "the frozen sheet changed"
    rows = list(csv.DictReader(open(A / "ai_labelled/confirm_v1_sheet_ai_v1.csv", encoding="utf-8-sig")))
    pm = {r["id"]: r for r in csv.DictReader(open(A / "PRIVATE_confirm_map.csv", encoding="utf-8"))}
    E = optimize_head.embed_all([r["review_text"] for r in rows])[:, :768]
    keep = [i for i, r in enumerate(rows) if r["sentiment"] in L]
    y = np.array([L.index(rows[i]["sentiment"]) for i in keep]); grp = np.array([pm[rows[i]["id"]]["product_link"] for i in keep])
    train_products = {r["group"] for r in p3.v1_rows() if r["label"] in L}
    # the confirmation map names products by link; the candidate map names its groups the same way (group = product link): rows whose product has no v1 training row
    free = np.array([g not in train_products for g in grp])
    out = {"rows": len(rows), "three_class_rows": len(keep), "labels": {l: int((y == k).sum()) for k, l in enumerate(L)}, "rows_with_product_unseen_in_phase4_training": int(free.sum()),
           "reference": "AI-assisted (Claude, policy v1); not independent human ground truth; set already used once in Phase 3 for T0/T7; not product-independent", "models": {}}
    for k, m in arts.items():
        p = m.predict(E[keep])
        def tab(sel):
            if sel.sum() == 0:
                return None
            s = metrics_x.summarize(y[sel], p[sel]); c = s["classes"]
            return {"n": int(sel.sum()), "labels": {l: int((y[sel] == j).sum()) for j, l in enumerate(L)}, "accuracy": s["accuracy"], "macro_precision": float(np.mean([c[x]["precision"] for x in L])),
                    "macro_recall": float(np.mean([c[x]["recall"] for x in L])), "macro_f1": s["macro_f1"], "weighted_f1": s["weighted_f1"], "classes": c, "confusion": s["confusion"]}
        allr = tab(np.ones(len(y), dtype=bool)); allr["macro_f1_ci95_product_bootstrap"] = metrics_x.boot(y, p, list(grp), n=500)
        out["models"][k] = {"all": allr, "product_unseen_subset": tab(free)}
        c = allr["classes"]
        print(f"{k}: n={allr['n']} acc {allr['accuracy']:.3f} mF1 {allr['macro_f1']:.3f} {allr['macro_f1_ci95_product_bootstrap']} | F1 neg {c['negative']['f1']:.3f} neu {c['neutral']['f1']:.3f} pos {c['positive']['f1']:.3f} | neutral P/R {c['neutral']['precision']:.2f}/{c['neutral']['recall']:.2f}")
        u = out["models"][k]["product_unseen_subset"]
        if u:
            print(f"   product-unseen subset n={u['n']} labels {u['labels']} mF1 {u['macro_f1']:.3f} neutral F1 {u['classes']['neutral']['f1']:.2f}")
    json.dump(out, open(X / "results/phase4_confirmation.json", "w"), indent=1)


if __name__ == "__main__":
    main()
