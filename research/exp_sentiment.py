"""Can the sentiment output be improved cheaply? Product-grouped CV on the training rows; historical test scored once.

    D:\defaketive-train\Scripts\python.exe research\exp_sentiment.py

(a) the deployed model's argmax; (b) logistic regression on its 3 probabilities + stars; (c) (b) plus word+char TF-IDF
of the review text. Selection is by out-of-fold macro F1 on the training file only.
"""
import json, pathlib, sys
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import CACHE, ROOT, grouped_folds, load
CL = ("negative", "neutral", "positive")
tr, te = load("train_v3"), load("test_v3"); SP = json.load(open(CACHE / "sentiment_probs.json"))
yt = np.array([CL.index(r["sentiment"].strip().lower()) for r in tr]); ye = np.array([CL.index(r["sentiment"].strip().lower()) for r in te])
def macro(y, p):
    f = []
    for c in range(3):
        tp = ((p == c) & (y == c)).sum(); fp = ((p == c) & (y != c)).sum(); fn = ((p != c) & (y == c)).sum()
        f.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return float(np.mean(f)), [round(x, 3) for x in f]
def base(rows): return np.array([SP[r["id"]] + [r["stars"] == s for s in range(1, 6)] for r in rows], dtype=float)
Btr, Bte = base(tr), base(te)
folds = grouped_folds(tr, 5, seed=0)
res = {"deployed_argmax": {"cv": macro(yt, Btr[:, :3].argmax(1)), "test": macro(ye, Bte[:, :3].argmax(1))}}
for name, text in (("probs+stars", False), ("probs+stars+text", True)):
    oof = np.zeros(len(tr), dtype=int)
    for a, b in folds:
        if text:
            vw = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True); vc = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
            Xa = hstack([vw.fit_transform([tr[i]["text"] for i in a]), vc.fit_transform([tr[i]["text"] for i in a]), csr_matrix(Btr[a])]).tocsr()
            Xb = hstack([vw.transform([tr[i]["text"] for i in b]), vc.transform([tr[i]["text"] for i in b]), csr_matrix(Btr[b])]).tocsr()
        else:
            Xa, Xb = Btr[a], Btr[b]
        oof[b] = LogisticRegression(C=2.0, class_weight="balanced", max_iter=3000).fit(Xa, yt[a]).predict(Xb)
    if text:
        vw = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True); vc = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
        Xa = hstack([vw.fit_transform([r["text"] for r in tr]), vc.fit_transform([r["text"] for r in tr]), csr_matrix(Btr)]).tocsr()
        Xe = hstack([vw.transform([r["text"] for r in te]), vc.transform([r["text"] for r in te]), csr_matrix(Bte)]).tocsr()
    else:
        Xa, Xe = Btr, Bte
    pe = LogisticRegression(C=2.0, class_weight="balanced", max_iter=3000).fit(Xa, yt).predict(Xe)
    res[name] = {"cv": macro(yt, oof), "test": macro(ye, pe)}
json.dump(res, open(ROOT / "research" / "results" / "exp_sentiment.json", "w"), indent=1)
for k, v in res.items(): print(f"{k:22} CV macro F1 {v['cv'][0]:.3f} {v['cv'][1]}   historical test {v['test'][0]:.3f} {v['test'][1]}")
