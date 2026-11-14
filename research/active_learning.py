"""Select 200 informative UNLABELLED reviews for the next annotation round (research/active_learning_candidates.csv).

    D:\\defaketive-train\\Scripts\\python.exe research\\active_learning.py <vm_reviews.json>

Pool: saved reviews (vm_reviews.json: name, rating, text) plus the scanned listings in backups/pool-scans, minus every
review already in a labelled file. 8,000 random pool reviews are scored by the deployed rules (with the product title)
and by a sparse model trained on the training file. Proposed allocation (an experiment, see research/al_simulation.py):
70 rule/model disagreements, 50 rare-label candidates, 50 uncertain and diverse, 30 random. At most 3 per product,
near-duplicates skipped. The independent annotation sheet does NOT show these columns (see research/agreement.py).
"""
import csv, glob, json, pathlib, re, subprocess, sys
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from common import CACHE, FLAGS5, ROOT, load

rng = np.random.default_rng(7)
norm = lambda t: re.sub(r"\W+", " ", t.casefold()).strip()
clean = lambda t: " ".join((t or "").split())
used = set()
for f in glob.glob(str(ROOT / "evaluation" / "**" / "*.csv"), recursive=True):
    if f.endswith("_key.csv"):
        continue
    try:
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            if r.get("review_text"):
                used.add(norm(r["review_text"]))
    except Exception:
        pass
pool, seen = [], set()
def add(name, rating, text):
    name, text = clean(name), clean(text)
    k = norm(text)
    if not (20 <= len(text) <= 500) or rating is None or k in used or k in seen:
        return
    seen.add(k); pool.append({"product": name, "stars": int(rating), "text": text})
for n, s, t in json.load(open(sys.argv[1], encoding="utf-8")):
    add(n, s, t)
for f in glob.glob(str(ROOT / "backups/pool-scans/search_*.json")):
    if f.endswith("_discovery.json"):
        continue
    for p in json.load(open(f, encoding="utf-8")):
        for c in p.get("comments") or []:
            add(p["name"], c.get("rating"), c.get("content"))
print("unlabelled pool:", len(pool))
pick = rng.choice(len(pool), min(8000, len(pool)), replace=False)
sample = [pool[i] for i in pick]
for i, r in enumerate(sample):
    r["id"] = f"AL{i:05d}"
with open(CACHE / "al_pool.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh); w.writerow(["id", "stars", "product", "review_text", "sentiment", "flags", "confidence"])
    for r in sample:
        w.writerow([r["id"], r["stars"], r["product"], r["text"], "", "none", "high"])
subprocess.run([str(ROOT / "backend/.venv/Scripts/python.exe"), str(ROOT / "training/rules_eval.py"), str(CACHE / "al_pool.csv"), str(CACHE / "al_rules.json"), "6"], check=True, env={**__import__("os").environ, "PYTHONUTF8": "1"})
rules = json.load(open(CACHE / "al_rules.json"))
R = np.array([rules[r["id"]]["pred"] for r in sample])

train = load("train_v3"); Y = np.array([r["y"][:5] for r in train])
vw = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True); vc = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
Xtr = hstack([vw.fit_transform([r["text"] for r in train]), vc.fit_transform([r["text"] for r in train])]).tocsr()
Xp = hstack([vw.transform([r["text"] for r in sample]), vc.transform([r["text"] for r in sample])]).tocsr()
P = np.stack([LogisticRegression(C=4.0, class_weight="balanced", max_iter=2000, solver="liblinear").fit(Xtr, Y[:, k]).predict_proba(Xp)[:, 1] for k in range(5)], axis=1)
unc = 1 - np.abs(2 * P - 1); unc_mean = unc.mean(axis=1)
dis = np.abs(R - (P >= 0.5).astype(int)); dis_total = dis.sum(axis=1)
RARE = {"safety": re.compile(r"usok|smok|sunog|burn|sumabog|pumutok|spark|rash|pantal|allerg|expired|panis|amag|uod|nagtae|nagsuka|choke|nabilaukan|matalim|namaga", re.I),
        "counterfeit": re.compile(r"fake|peke|not original|hindi original|imitation|replica|scam|di original|hindi totoo", re.I)}
rare_flag = [next((f for f, rx in RARE.items() if rx.search(r["text"])), None) for r in sample]
cv = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True); C = cv.fit_transform([norm(r["text"]) for r in sample])
chosen, per_product, rows = [], {}, []
def take(order, count, reason):
    got = 0
    for i in order:
        if i in chosen or per_product.get(sample[i]["product"], 0) >= 3:
            continue
        if chosen and (C[i] @ C[chosen].T).max() >= 0.8:
            continue
        chosen.append(i); per_product[sample[i]["product"]] = per_product.get(sample[i]["product"], 0) + 1; got += 1
        k = int(np.argmax(dis[i])) if dis[i].sum() else int(np.argmax(unc[i]))
        flag = FLAGS5[k] if reason != "rare_label_candidate" else (rare_flag[i] or FLAGS5[k])
        rows.append({"review_id": sample[i]["id"], "product": sample[i]["product"][:70], "review_text": sample[i]["text"], "reason_selected": reason,
                     "priority": {"rule_model_disagreement": 1, "rare_label_candidate": 2, "uncertain_diverse": 3, "random_representative": 4}[reason],
                     "model_uncertainty": round(float(unc_mean[i]), 3), "relevant_flag": flag, "annotation_status": "unlabelled"})
        if got >= count:
            break
take(np.lexsort((-unc_mean, -dis_total)), 70, "rule_model_disagreement")
take([i for i in np.argsort(-unc_mean) if rare_flag[i]], 50, "rare_label_candidate")
take(np.argsort(-unc_mean), 50, "uncertain_diverse")
take(rng.permutation(len(sample)), 30, "random_representative")
with open(ROOT / "research" / "active_learning_candidates.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows), "candidates;", {k: sum(1 for r in rows if r["reason_selected"] == k) for k in ("rule_model_disagreement", "rare_label_candidate", "uncertain_diverse", "random_representative")}, "products:", len({r["product"] for r in rows}))
