"""Active-learning simulation on the labelled pool: does choosing which reviews to label beat choosing at random?

    D:\\defaketive-train\\Scripts\\python.exe research\\al_simulation.py

Per seed: 20% of products are held out for evaluation (product-disjoint). From the rest, 500 random rows are the starting
labelled set; a batch of N more rows is then selected by a strategy and added (one-shot batch), a sparse model
(word+char TF-IDF, logistic regression, class-weighted, fixed threshold 0.5, no tuning) is retrained and scored on the
held-out products (macro F1 over the five flags). Strategies: random; uncertainty (model probability near 0.5);
disagreement (the deployed rules versus the model); mix (the proposed 200-review allocation scaled: 35% disagreement,
25% rare-label words, 25% uncertain, 15% random). The rules' decisions on training rows were error-tuned, so the
disagreement signal is optimistic; this is a simulation on existing labels, not a replacement for a real labelling round.
"""
import json, pathlib, re, sys
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import FLAGS5, ROOT, load, prf, rules_predictions

train = load("train_v3"); Y = np.array([r["y"][:5] for r in train]); texts = [r["text"] for r in train]
R = rules_predictions("train"); rules = np.array([R[r["id"]]["pred"] for r in train])
RARE = re.compile(r"usok|smok|sunog|burn|sumabog|pumutok|spark|rash|pantal|allerg|expired|panis|amag|uod|nagtae|nagsuka|choke|fake|peke|not original|hindi original|imitation|scam", re.I)
rare_hit = np.array([bool(RARE.search(t)) for t in texts])
products = sorted({r["product"] for r in train}); pidx = {p: i for i, p in enumerate(products)}
prod_of = np.array([pidx[r["product"]] for r in train])


def fit_predict(tr_idx, te_idx):
    vw = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True); vc = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
    Xtr = hstack([vw.fit_transform([texts[i] for i in tr_idx]), vc.fit_transform([texts[i] for i in tr_idx])]).tocsr()
    mk = lambda ids: hstack([vw.transform([texts[i] for i in ids]), vc.transform([texts[i] for i in ids])]).tocsr()
    P = np.zeros((len(te_idx), 5)); Xte = mk(te_idx)
    for k in range(5):
        if Y[tr_idx, k].sum() < 2:
            continue
        P[:, k] = LogisticRegression(C=4.0, class_weight="balanced", max_iter=2000, solver="liblinear").fit(Xtr, Y[tr_idx, k]).predict_proba(Xte)[:, 1]
    return P


def macro(te_idx, P):
    return float(np.mean([prf(Y[te_idx, k], (P[:, k] >= 0.5).astype(int))["f1"] for k in range(5)]))


def select(strategy, n, pool, P_pool, rng):
    pool = np.array(pool)
    if strategy == "random":
        return list(rng.choice(pool, n, replace=False))
    unc = 1 - np.abs(2 * P_pool - 1); unc_score = unc.mean(axis=1)
    dis = np.abs(rules[pool] - (P_pool >= 0.5).astype(int)).sum(axis=1).astype(float)
    if strategy == "uncertainty":
        return list(pool[np.argsort(-unc_score)[:n]])
    if strategy == "disagreement":
        order = np.lexsort((-unc_score, -dis)); return list(pool[order[:n]])
    chosen = []
    def take(order, count):
        for j in order:
            if len(chosen) >= len(set(chosen)) + count and False: break
        got = 0
        for j in order:
            if pool[j] not in chosen:
                chosen.append(pool[j]); got += 1
            if got >= count: break
    take(np.lexsort((-unc_score, -dis)), int(n * 0.35))
    take(np.argsort(-(rare_hit[pool] * 1.0 + unc_score * 0.01)), int(n * 0.25))
    take(np.argsort(-unc_score), int(n * 0.25))
    rest = [j for j in rng.permutation(len(pool)) if pool[j] not in chosen]
    for j in rest[: n - len(chosen)]:
        chosen.append(pool[j])
    return chosen[:n]


results = {}
for seed in range(5):
    rng = np.random.default_rng(seed); order = rng.permutation(len(products)); hold = set(order[: len(products) // 5])
    eval_idx = [i for i in range(len(train)) if prod_of[i] in hold]; pool_all = [i for i in range(len(train)) if prod_of[i] not in hold]
    start = list(rng.choice(pool_all, 500, replace=False)); pool = [i for i in pool_all if i not in set(start)]
    P0 = fit_predict(start, pool)
    results.setdefault("start_500", []).append(macro(eval_idx, fit_predict(start, eval_idx)))
    for n in (100, 200, 400):
        for strategy in ("random", "uncertainty", "disagreement", "mix"):
            picked = select(strategy, n, pool, P0, np.random.default_rng(seed * 10 + n))
            results.setdefault(f"{strategy}_{n}", []).append(macro(eval_idx, fit_predict(start + picked, eval_idx)))
    print("seed", seed, "done", flush=True)
summary = {k: {"mean": round(float(np.mean(v)), 4), "sd": round(float(np.std(v)), 4), "values": [round(x, 3) for x in v]} for k, v in results.items()}
json.dump(summary, open(ROOT / "research" / "results" / "al_simulation.json", "w"), indent=1)
print(f"{'':16} {'+100':>14} {'+200':>14} {'+400':>14}\nstart (500 rows): {summary['start_500']['mean']:.3f} +- {summary['start_500']['sd']:.3f}")
for s in ("random", "uncertainty", "disagreement", "mix"):
    print(f"{s:16}" + "".join(f"{summary[f'{s}_{n}']['mean']:.3f} +- {summary[f'{s}_{n}']['sd']:.3f}  " for n in (100, 200, 400)))
