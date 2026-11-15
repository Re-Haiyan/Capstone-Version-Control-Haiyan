"""Scores the two LOCKED Phase 3 configurations (phase3_lock.json: T0 = sentiment_head_v1, T7) once on the frozen confirmation set (annotation/confirm_v1_manifest.json), Claude-annotated under policy v1.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/score_confirm.py
Artifact hashes are checked against the lock; nothing is fitted or tuned here. Three-class rows only (mixed and unclear are counted and kept apart). Reports all rows, the cue and no-cue strata,
and an estimate re-weighted to the usable population (cue rows were over-sampled). The reference is AI-assisted (Claude), not independent human ground truth. Writes results/phase3_confirmation.json.
"""
import csv, json, pathlib, sys
import joblib
import numpy as np

X = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(X))
import xdata, metrics_x, optimize_head  # noqa: E402

L = xdata.LABELS
A = X / "annotation"


def main():
    lock = json.load(open(X / "phase3_lock.json"))
    arts = {}
    for k in ("T0", "T7"):
        p = xdata.ROOT / lock[k]["artifact"]
        assert xdata.sha256(p) == lock[k]["sha256"], f"{k} artifact differs from the lock"
        arts[k] = joblib.load(p)["pipeline"]
    man = json.load(open(A / "confirm_v1_manifest.json"))
    assert xdata.sha256(A / "confirm_v1_sheet.csv") == man["sheet_sha256"], "the frozen sheet changed"
    rows = list(csv.DictReader(open(A / "ai_labelled/confirm_v1_sheet_ai_v1.csv", encoding="utf-8-sig")))
    pm = {r["id"]: r for r in csv.DictReader(open(A / "PRIVATE_confirm_map.csv", encoding="utf-8"))}
    E = optimize_head.embed_all([r["review_text"] for r in rows])[:, :768]
    keep = [i for i, r in enumerate(rows) if r["sentiment"] in L]
    y = np.array([L.index(rows[i]["sentiment"]) for i in keep]); grp = [pm[rows[i]["id"]]["product_link"] for i in keep]
    stratum = np.array([pm[rows[i]["id"]]["stratum"] for i in keep]); w = np.array([float(pm[rows[i]["id"]]["weight"]) for i in keep])
    out = {"rows": len(rows), "three_class_rows": len(keep), "mixed": sum(r["sentiment"] == "mixed" for r in rows), "unclear": sum(r["sentiment"] == "unclear" for r in rows),
           "labels": {l: int((y == k).sum()) for k, l in enumerate(L)}, "reference": "AI-assisted (Claude, policy v1); not independent human ground truth", "models": {}}
    for k, m in arts.items():
        p = m.predict(E[keep])
        def tab(sel):
            s = metrics_x.summarize(y[sel], p[sel]); c = s["classes"]
            return {"n": int(sel.sum()), "accuracy": s["accuracy"], "macro_precision": float(np.mean([c[x]["precision"] for x in L])), "macro_recall": float(np.mean([c[x]["recall"] for x in L])), "macro_f1": s["macro_f1"],
                    "weighted_f1": s["weighted_f1"], "classes": c, "confusion": s["confusion"]}
        allr = tab(np.ones(len(y), dtype=bool))
        allr["macro_f1_ci95_product_bootstrap"] = metrics_x.boot(y, p, grp, n=500)
        # population-weighted macro F1 (weights of the sampling plan)
        f1w = []
        for c in range(3):
            tp = w[(y == c) & (p == c)].sum(); fp = w[(y != c) & (p == c)].sum(); fn = w[(y == c) & (p != c)].sum()
            pr = tp / (tp + fp) if tp + fp else 0; rc = tp / (tp + fn) if tp + fn else 0
            f1w.append(2 * pr * rc / (pr + rc) if pr + rc else 0)
        out["models"][k] = {"all": allr, "cue_stratum": tab(stratum == "cue"), "no_cue_stratum": tab(stratum == "no_cue"), "population_weighted_macro_f1": float(np.mean(f1w)), "population_weighted_f1_per_class": dict(zip(L, map(float, f1w)))}
        c = allr["classes"]
        print(f"{k}: n={allr['n']} acc {allr['accuracy']:.3f} mP {allr['macro_precision']:.3f} mR {allr['macro_recall']:.3f} mF1 {allr['macro_f1']:.3f} ({allr['macro_f1_ci95_product_bootstrap'][0]:.3f}-{allr['macro_f1_ci95_product_bootstrap'][1]:.3f}) wF1 {allr['weighted_f1']:.3f} | F1 neg {c['negative']['f1']:.3f} neu {c['neutral']['f1']:.3f} pos {c['positive']['f1']:.3f} | neutral P/R {c['neutral']['precision']:.2f}/{c['neutral']['recall']:.2f} | popW mF1 {np.mean(f1w):.3f}")
    json.dump(out, open(X / "results/phase3_confirmation.json", "w"), indent=1)
    print({k: out[k] for k in ("rows", "three_class_rows", "mixed", "unclear", "labels")})


if __name__ == "__main__":
    main()
