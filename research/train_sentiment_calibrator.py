"""Train the optional sentiment calibrator on the TRAINING file and save the artifact (run with the APP's Python, scikit-learn 1.9.0).

    backend\.venv\Scripts\python.exe research\train_sentiment_calibrator.py
"""
import hashlib, json, pathlib, sys
import joblib, numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import CACHE, ROOT, load
CL = ("negative", "neutral", "positive")
tr, te = load("train_v3"), load("test_v3"); SP = json.load(open(CACHE / "sentiment_probs.json"))
dense = lambda rows: np.array([SP[r["id"]] + [r["stars"] == s for s in range(1, 6)] for r in rows], dtype=float)
y = np.array([CL.index(r["sentiment"].strip().lower()) for r in tr])
vw = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True); vc = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
X = hstack([vw.fit_transform([r["text"] for r in tr]), vc.fit_transform([r["text"] for r in tr]), csr_matrix(dense(tr))]).tocsr()
clf = LogisticRegression(C=2.0, class_weight="balanced", max_iter=3000).fit(X, y)
Xe = hstack([vw.transform([r["text"] for r in te]), vc.transform([r["text"] for r in te]), csr_matrix(dense(te))]).tocsr()
ye = np.array([CL.index(r["sentiment"].strip().lower()) for r in te]); pe = clf.predict(Xe)
f1 = [2 * ((pe == c) & (ye == c)).sum() / (2 * ((pe == c) & (ye == c)).sum() + ((pe == c) & (ye != c)).sum() + ((pe != c) & (ye == c)).sum()) for c in range(3)]
out = ROOT / "research" / "artifacts"; out.mkdir(exist_ok=True)
path = out / "sentiment_calibrator_v1.joblib"
joblib.dump({"word": vw, "char": vc, "classifier": clf, "classes": CL}, path, compress=3)
manifest = {"artifact": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "trained_on_rows": len(tr), "scikit_learn": __import__("sklearn").__version__,
            "historical_test_macro_f1": round(float(np.mean(f1)), 3), "historical_test_per_class_f1": dict(zip(CL, [round(float(x), 3) for x in f1])),
            "wired_by_default": False, "enable_with_env": "DEFAKETIVE_SENTIMENT_CALIBRATOR", "size_bytes": path.stat().st_size}
json.dump(manifest, open(out / "sentiment_calibrator_v1.json", "w"), indent=1); print(manifest)
