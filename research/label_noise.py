"""Confident-learning audit of the training labels (Cleanlab), product-grouped out-of-fold predictions.

    D:\\defaketive-train\\Scripts\\python.exe research\\label_noise.py

Per binary flag: out-of-fold probabilities from two rule-independent models (word+char TF-IDF logistic regression and
logistic regression on frozen multilingual-e5-small embeddings, unweighted so probabilities are usable), averaged;
Cleanlab ranks suspected label issues. The deployed rules are shown next to each suspect for context only: they are
NOT used as evidence that a human label is wrong. Nothing is relabelled. Writes research/suspected_label_errors.csv.
"""
import csv, json, pathlib, sys
import numpy as np
from cleanlab.filter import find_label_issues
from cleanlab.rank import get_label_quality_scores
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import CACHE, FLAGS6, ROOT, grouped_folds, load, rules_predictions

train = load("train_v3"); Y = np.array([r["y"] for r in train]); folds = grouped_folds(train, 5, seed=1)
E = np.load(CACHE / "emb_e5-small_ctx0.npy")[: len(train)]
rules = rules_predictions("train")
audit_ids = {}
for q in csv.DictReader(open(ROOT / "research/annotation_audit_queue.csv", encoding="utf-8-sig")):
    audit_ids.setdefault(q["id"], []).append(q["suspected_inconsistency"])

texts = [r["text"] for r in train]
P_tfidf = np.zeros(Y.shape); P_emb = np.zeros(Y.shape)
for tr, te in folds:
    vw = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True); vc = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
    Xtr = hstack([vw.fit_transform([texts[i] for i in tr]), vc.fit_transform([texts[i] for i in tr])]).tocsr()
    Xte = hstack([vw.transform([texts[i] for i in te]), vc.transform([texts[i] for i in te])]).tocsr()
    for k in range(len(FLAGS6)):
        P_tfidf[te, k] = LogisticRegression(C=4.0, max_iter=2000, solver="liblinear").fit(Xtr, Y[tr][:, k]).predict_proba(Xte)[:, 1]
        P_emb[te, k] = LogisticRegression(C=4.0, max_iter=3000).fit(E[tr], Y[tr][:, k]).predict_proba(E[te])[:, 1]
P = (P_tfidf + P_emb) / 2
rows, summary = [], {}
for k, f in enumerate(FLAGS6):
    labels = Y[:, k]; probs = np.stack([1 - P[:, k], P[:, k]], axis=1)
    issues = find_label_issues(labels, probs, filter_by="prune_by_noise_rate", return_indices_ranked_by="self_confidence")
    quality = get_label_quality_scores(labels, probs)
    summary[f] = {"positives": int(labels.sum()), "suspected_issues": int(len(issues)),
                  "suspected_positive_labels_that_may_be_negative": int(sum(labels[i] == 1 for i in issues)),
                  "suspected_negative_labels_that_may_be_positive": int(sum(labels[i] == 0 for i in issues))}
    for rank, i in enumerate(issues):
        r = train[i]
        kind = "labelled yes, model says no (possible false label)" if labels[i] == 1 else "labelled no, model says yes (possible missed label)"
        if r["id"] in audit_ids:
            kind += "; also in the adjudication queue: " + audit_ids[r["id"]][0]
        pri = "high" if (rank < 25 or r["id"] in audit_ids) else ("medium" if rank < 80 else "low")
        rows.append({"id": r["id"], "flag": f, "product": r["product"][:60], "review_text": r["text"].replace("\n", " ")[:280], "original_label": int(labels[i]),
                     "predicted_probability": round(float(P[i, k]), 3), "label_quality_score": round(float(quality[i]), 3), "deployed_rules_say": int(rules[r["id"]]["pred"][k]) if k < 5 else "",
                     "suspected_issue": kind, "review_priority": pri})
rows.sort(key=lambda x: (x["review_priority"] != "high", x["review_priority"] != "medium", x["label_quality_score"]))
with open(ROOT / "research" / "suspected_label_errors.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
json.dump(summary, open(ROOT / "research" / "results" / "label_noise_summary.json", "w"), indent=1)
print(json.dumps(summary, indent=1)); print(len(rows), "rows written")
