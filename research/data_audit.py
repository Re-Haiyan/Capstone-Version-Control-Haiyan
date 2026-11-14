"""Data audit: duplicates, near-duplicates, product overlap between splits, and conflicting labels.

    D:\\defaketive-train\\Scripts\\python.exe research\\data_audit.py

Writes research/data_audit.json and prints a summary. Reads only the labelled files, never model output.
"""
import csv, json, pathlib, re, collections
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLAGS = ("defect", "counterfeit", "safety", "not_as_described", "quality", "delivery")


def load(name):
    key = {r["id"]: r for r in csv.DictReader(open(ROOT / "evaluation/annotated" / f"{name}_key.csv", encoding="utf-8-sig"))}
    rows = []
    for r in csv.DictReader(open(ROOT / "evaluation/annotated" / f"{name}.csv", encoding="utf-8-sig")):
        if r["confidence"].strip().lower() != "high" or not r["flags"].strip():
            continue
        r["product"] = " ".join(r["product"].split())
        r["gold"] = sorted(f for f in r["flags"].replace(" ", "").split(";") if f in FLAGS)
        r["category"] = key.get(r["id"], {}).get("category", "")
        r["group"] = key.get(r["id"], {}).get("group", "")
        rows.append(r)
    return rows


norm = lambda t: re.sub(r"\W+", " ", t.casefold()).strip()
train, test = load("train_v3"), load("test_v3")
out = {"train_rows": len(train), "test_rows": len(test)}
out["train_products"] = len({r["product"] for r in train}); out["test_products"] = len({r["product"] for r in test})
out["product_overlap"] = len({r["product"] for r in train} & {r["product"] for r in test})

# exact duplicates inside and across splits
tn = collections.defaultdict(list)
for r in train: tn[norm(r["review_text"])].append(("train", r))
for r in test: tn[norm(r["review_text"])].append(("test", r))
dups = {k: v for k, v in tn.items() if len(v) > 1}
out["exact_duplicate_texts"] = len(dups)
out["exact_duplicates_across_splits"] = sum(1 for v in dups.values() if {s for s, _ in v} == {"train", "test"})
conflicts = [v for v in dups.values() if len({tuple(r["gold"]) for _, r in v}) > 1]
out["exact_duplicate_label_conflicts"] = len(conflicts)
out["conflict_examples"] = [[{"id": r["id"], "split": s, "gold": r["gold"], "text": r["review_text"][:100]} for s, r in v] for v in conflicts[:15]]

# near duplicates train <-> test (character n-gram cosine)
vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)
X = vec.fit_transform([norm(r["review_text"]) for r in train + test])
Xtr, Xte = X[: len(train)], X[len(train):]
sims = (Xte @ Xtr.T).tocsr()
near = []
for i in range(sims.shape[0]):
    row = sims.getrow(i)
    if row.nnz:
        j = int(row.indices[row.data.argmax()]); s = float(row.data.max())
        if s >= 0.90: near.append((s, test[i]["id"], train[j]["id"], test[i]["product"] != train[j]["product"]))
out["near_duplicate_test_vs_train_cos>=0.90"] = len(near)
out["near_duplicate_examples"] = [{"cos": round(s, 3), "test_id": a, "train_id": b, "different_product": d} for s, a, b, d in sorted(near, reverse=True)[:15]]

# near-duplicate label disagreement inside train (cos >= 0.85, different labels)
S = (Xtr @ Xtr.T).tocsr(); disagree = 0; pairs = 0
for i in range(S.shape[0]):
    row = S.getrow(i)
    for j, v in zip(row.indices, row.data):
        if j > i and v >= 0.85:
            pairs += 1
            disagree += train[i]["gold"] != train[j]["gold"]
out["train_near_duplicate_pairs_cos>=0.85"] = pairs
out["train_near_duplicate_pairs_label_disagree"] = disagree

# class balance
for name, rows in (("train", train), ("test", test)):
    c = collections.Counter(f for r in rows for f in r["gold"])
    out[f"{name}_positives"] = {f: c[f] for f in FLAGS}
    out[f"{name}_rows_by_group"] = dict(collections.Counter(r["group"] for r in rows))
    out[f"{name}_products_per_flag"] = {f: len({r["product"] for r in rows if f in r["gold"]}) for f in FLAGS}
json.dump(out, open(ROOT / "research" / "data_audit.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if "examples" not in k}, indent=1))
