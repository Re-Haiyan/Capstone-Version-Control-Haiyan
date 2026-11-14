"""Weak supervision: audit the rule files as labeling functions and test whether weak labels help.

    D:\\defaketive-train\\Scripts\\python.exe research\\weak_supervision.py

Labeling functions (LFs): every row of the shared and group addition files (all.add.tsv, group_*.add.tsv) votes POSITIVE
for its flag when its regular expression matches; one PRAISE function votes NEGATIVE (4-5 stars, praise words, no
complaint word) for every flag; everything else abstains. Per LF: coverage, precision and recall against the HUMAN labels
of the training file, conflicts, and highly correlated pairs (Jaccard on the rows they fire on, which must not be counted
as independent evidence). A precision-weighted vote combines them. Experiment: does adding weak-labelled UNLABELLED
reviews (from research/cache/al_pool.csv) to the gold training rows improve a sparse model on held-out PRODUCTS?
Weak labels keep their provenance: every added row is marked weak=1 and the LF names that voted are recorded.
"""
import collections, csv, json, pathlib, re, sys
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import FLAGS5, ROOT, grouped_folds, load, prf

CAT = ROOT / "backend/sentiment-analysis/defaketive_sentiment/lexicons/categories"
train = load("train_v3"); Y = np.array([r["y"][:5] for r in train]); texts = [r["text"].casefold() for r in train]
lfs = []  # (name, flag, compiled regex)
for path in sorted(CAT.glob("*.add.tsv")):
    for n, line in enumerate(l for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")):
        cols = line.split("\t") + [""] * 4
        term, label = cols[0].strip(), cols[1].strip()
        if label in FLAGS5:
            try:
                lfs.append((f"{path.name}#{n}", label, re.compile(rf"(?<!\w)(?:{term})(?!\w)")))
            except re.error:
                pass
COMPLAINT = re.compile(r"hindi (?:gumana|gumagana)|di (?:gumana|gumagana)|not working|doesn.t work|sira|basag|broken|defect|peke|fake|mali|wrong|kulang|missing|pangit|poor|bad|scam|damag|leak|yupi|dent|scratch|usok|sunog|rash|allerg|expired|panis|disappoint|nadismaya")
PRAISE = re.compile(r"maganda|ganda|bagay|sulit|worth|love|recommend|galing|satisfied|great|good|nice|perfect|thank|salamat|ayos")
stars = np.array([r["stars"] for r in train])
neg_vote = np.array([bool(stars[i] >= 4 and PRAISE.search(texts[i]) and not COMPLAINT.search(texts[i])) for i in range(len(train))])
fires = {name: np.array([bool(rx.search(t)) for t in texts]) for name, _f, rx in lfs}
rows = []
for name, flag, _rx in lfs:
    k = FLAGS5.index(flag); f = fires[name]
    if f.sum() == 0:
        continue
    tp = int((f & (Y[:, k] == 1)).sum()); rows.append({"lf": name, "flag": flag, "coverage": int(f.sum()), "precision": round(tp / f.sum(), 3), "recall": round(tp / max(Y[:, k].sum(), 1), 3)})
rows.sort(key=lambda r: (r["flag"], -r["coverage"]))
negp = {FLAGS5[k]: round(float(1 - Y[neg_vote, k].mean()), 3) for k in range(5)}
# correlated LF pairs (same flag, Jaccard >= 0.8)
corr = []
names = [r["lf"] for r in rows]
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if dict((r["lf"], r["flag"]) for r in rows)[a] == dict((r["lf"], r["flag"]) for r in rows)[b]:
            inter = (fires[a] & fires[b]).sum(); union = (fires[a] | fires[b]).sum()
            if union and inter / union >= 0.8:
                corr.append({"a": a, "b": b, "jaccard": round(float(inter / union), 3)})
# conflicts: positive LF fires on a row where the praise LF votes negative
conflicts = {f: int(sum(1 for r in rows if r["flag"] == f and (fires[r["lf"]] & neg_vote).any())) for f in FLAGS5}
# precision-weighted vote per flag
def weak_votes(text_list, star_list):
    t = [x.casefold() for x in text_list]; fire = {name: np.array([bool(rx.search(x)) for x in t]) for name, _f, rx in lfs}
    praise = np.array([bool(s >= 4 and PRAISE.search(x) and not COMPLAINT.search(x)) for x, s in zip(t, star_list)])
    out = np.zeros((len(t), 5)); provenance = [[] for _ in t]
    for r in rows:
        k = FLAGS5.index(r["flag"]); w = np.log(max(r["precision"], 0.05) / max(1 - r["precision"], 0.05))
        out[fire[r["lf"]], k] += max(w, 0.0)
        for i in np.where(fire[r["lf"]])[0]: provenance[i].append(r["lf"])
    out[praise, :] -= 2.0
    return out, praise, provenance
score_tr, _, _ = weak_votes([r["text"] for r in train], stars)
weak_pred = (score_tr > 0.5).astype(int); weak_eval = {f: prf(Y[:, k], weak_pred[:, k]) for k, f in enumerate(FLAGS5)}
abstain = float(((score_tr == 0).all(axis=1)).mean())

# experiment: gold-only versus gold + weak-labelled unlabelled reviews (grouped CV, evaluation on gold rows only)
pool = list(csv.DictReader(open(ROOT / "research/cache/al_pool.csv", encoding="utf-8-sig")))
score_pool, praise_pool, prov = weak_votes([r["review_text"] for r in pool], [int(r["stars"]) for r in pool])
decisive = [i for i in range(len(pool)) if (score_pool[i] > 2.0).any() or praise_pool[i]]
weak_texts = [pool[i]["review_text"] for i in decisive]; weak_Y = np.array([[1 if score_pool[i, k] > 2.0 else 0 for k in range(5)] for i in decisive])
folds = grouped_folds(train, 5, seed=0); results = collections.defaultdict(list)
def fit_eval(extra_X_texts, extra_Y, tr, te):
    tx = [train[i]["text"] for i in tr] + list(extra_X_texts); ty = np.vstack([Y[tr], extra_Y]) if len(extra_Y) else Y[tr]
    vw = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True); vc = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
    Xa = hstack([vw.fit_transform(tx), vc.fit_transform(tx)]).tocsr(); Xb = hstack([vw.transform([train[i]["text"] for i in te]), vc.transform([train[i]["text"] for i in te])]).tocsr()
    return [prf(Y[te][:, k], (LogisticRegression(C=4.0, class_weight="balanced", max_iter=2000, solver="liblinear").fit(Xa, ty[:, k]).predict_proba(Xb)[:, 1] >= 0.5).astype(int))["f1"] for k in range(5)]
rng = np.random.default_rng(0)
for a, b in folds:
    results["gold_only"].append(fit_eval([], np.zeros((0, 5)), a, b))
    for n in (500, 2000):
        pick = rng.choice(len(decisive), min(n, len(decisive)), replace=False)
        results[f"gold+weak_{n}"].append(fit_eval([weak_texts[i] for i in pick], weak_Y[pick], a, b))
summary = {k: {"macro_f1": round(float(np.mean(v)), 4), "per_flag": [round(float(x), 3) for x in np.mean(v, axis=0)]} for k, v in results.items()}
out = {"labeling_functions": len(rows), "per_lf": rows, "praise_lf_negative_precision": negp, "correlated_pairs_jaccard>=0.8": corr[:40], "n_correlated_pairs": len(corr),
       "praise_conflicts_per_flag": conflicts, "weighted_vote_vs_gold_on_train": {f: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in weak_eval[f].items()} for f in FLAGS5},
       "abstain_rate_on_train": round(abstain, 3), "pool_decisive_rows": len(decisive), "experiment_cv_macro_f1": summary}
json.dump(out, open(ROOT / "research" / "results" / "weak_supervision.json", "w"), indent=1)
print(f"{len(rows)} labeling functions that fire; {len(corr)} correlated pairs; abstain on {abstain:.0%} of training rows")
print("weighted vote vs human labels (train):", {f: (round(weak_eval[f]['precision'], 2), round(weak_eval[f]['recall'], 2)) for f in FLAGS5})
print("top LFs by coverage:", [(r["lf"], r["flag"], r["coverage"], r["precision"]) for r in sorted(rows, key=lambda r: -r["coverage"])[:8]])
print("experiment (grouped CV macro F1, 5 flags):", {k: v["macro_f1"] for k, v in summary.items()}, "pool decisive rows:", len(decisive))
