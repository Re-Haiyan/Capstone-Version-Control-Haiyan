"""Scores the LOCKED second model (sentiment_head_v1) once on the frozen 400-review test against the AI-assisted reference sets (Team Label 1, Team Label 2, and the reviews where they agree).
Same subsets and metrics as score_provisional.py (all; excluding delivery-only; excluding reviews present in earlier AI- or team-labelled files). Reads the cached frozen embeddings; nothing is fitted.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/score_head.py
"""
import csv, json, pathlib, sys
import joblib
import numpy as np

X = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(X))
import xdata, metrics_x  # noqa: E402

L = xdata.LABELS
OUT = X / "final_human_evaluation"
DOWN = pathlib.Path("C:/Users/cabal/Downloads")
lock = json.load(open(OUT / "model_selection_lock.json"))
art = xdata.ROOT / "research/artifacts/sentiment_head_v1.joblib"
assert xdata.sha256(art) == lock["prespecified_second_model"]["artifact_sha256"], "the head is not the locked artifact"
head = joblib.load(art)
frozen = list(csv.DictReader(open(X / "annotation/final_test_sheet_A.csv", encoding="utf-8-sig")))
ids = [r["id"] for r in frozen]
texts = [r["review_text"] for r in frozen]
E = np.load(X / "data/head/frozen_emb.npy")
pred = head["pipeline"].predict(E[:, :768])
A = {r["id"]: r for r in csv.DictReader(open(DOWN / "team_label_1_final_test_sheet_A_v1.csv", encoding="utf-8-sig"))}
B = {r["id"]: r for r in csv.DictReader(open(DOWN / "team_label_2_final_test_sheet_B_v1.csv", encoding="utf-8-sig"))}
pm = {r["sheet_id"]: r for r in csv.DictReader(open(X / "annotation/PRIVATE_id_map.csv", encoding="utf-8"))}
tags = lambda r: {t.strip() for t in r["tags"].split(";") if t.strip()}
prior = set()
for path in ("evaluation/review_pool_10000.csv", "research/fresh_eval/fresh_eval_sheet.csv", "research/cache/al_pool.csv"):
    n = {xdata.norm_text(r["review_text"]) for r in csv.DictReader(open(xdata.ROOT / path, encoding="utf-8-sig"))}
    prior |= {i for i, t in zip(ids, texts) if xdata.norm_text(t) in n}
index = {i: k for k, i in enumerate(ids)}
products = {i: pm[i]["product_link"] for i in ids}


def score(label_of, rows):
    keep = [i for i in rows if label_of(i) in L]
    y = np.array([L.index(label_of(i)) for i in keep]); p = np.array([pred[index[i]] for i in keep])
    s = metrics_x.summarize(y, p); c = s["classes"]
    return {"n_scored": len(keep), "accuracy": s["accuracy"], "macro_precision": float(np.mean([c[k]["precision"] for k in L])), "macro_recall": float(np.mean([c[k]["recall"] for k in L])), "macro_f1": s["macro_f1"],
            "weighted_f1": s["weighted_f1"], "macro_f1_ci95_product_bootstrap": metrics_x.boot(y, p, [products[i] for i in keep]), "classes": c, "confusion_rows_true_cols_pred": s["confusion"]}


sources = {"sheet_A": lambda i: A[i]["sentiment"], "sheet_B": lambda i: B[i]["sentiment"], "A_and_B_agree": lambda i: A[i]["sentiment"] if A[i]["sentiment"] == B[i]["sentiment"] else ""}
subsets = {"all": ids, "excluding_delivery_only": [i for i in ids if "delivery-only" not in tags(A[i]) and "delivery-only" not in tags(B[i])], "excluding_prior_labelled_reviews": [i for i in ids if i not in prior]}
res = {s: {k: score(fn, v) for k, v in subsets.items()} for s, fn in sources.items()}
res["_notes"] = {"status": "AI-assisted reference standard (ChatGPT), not independently verified ground truth; no human adjudication yet", "model": "sentiment_head_v1", "artifact_sha256": lock["prespecified_second_model"]["artifact_sha256"]}
json.dump(res, open(OUT / "provisional_head_metrics.json", "w"), indent=1)
with open(OUT / "provisional_head_predictions.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "pred"]); [w.writerow([i, L[int(p)]]) for i, p in zip(ids, pred)]
for s in sources:
    for k, v in res[s].items():
        c = v["classes"]
        print(f"{s:<14} {k:<34} n={v['n_scored']:<4} acc {v['accuracy']:.3f} mP {v['macro_precision']:.3f} mR {v['macro_recall']:.3f} mF1 {v['macro_f1']:.3f} wF1 {v['weighted_f1']:.3f} ({v['macro_f1_ci95_product_bootstrap'][0]:.3f}-{v['macro_f1_ci95_product_bootstrap'][1]:.3f}) | F1 neg {c['negative']['f1']:.3f} neu {c['neutral']['f1']:.3f} pos {c['positive']['f1']:.3f}")
