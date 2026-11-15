"""Leakage audit of the frozen 400-review final test (reads texts only; no model is run, no labels of the returned sheets are read).

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/leakage_audit.py
Compares the frozen texts and their products with every corpus that fed training, validation, calibration, selection, vocabulary pruning, active learning or earlier
experiments, by exact normalised text, near duplicates (character TF-IDF cosine >= 0.9) and product. Writes final_human_evaluation/leakage_audit.json.
"""
import csv, glob, json, pathlib, sqlite3, sys, collections
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
X = pathlib.Path(__file__).resolve().parent; ROOT = X.parent.parent
sys.path.insert(0, str(X))
import xdata  # noqa: E402
frozen = list(csv.DictReader(open(X / "annotation" / "final_test_sheet_A.csv", encoding="utf-8-sig")))
pm = {r["sheet_id"]: r for r in csv.DictReader(open(X / "annotation" / "PRIVATE_id_map.csv", encoding="utf-8"))}
ftexts = [r["review_text"] for r in frozen]; fnorm = [xdata.norm_text(t) for t in ftexts]
fprod = {" ".join(r["product"].lower().split()) for r in frozen}
flinks = {pm[r["id"]]["product_link"] for r in frozen}
splits = json.load(open(xdata.DATA / "splits.json"))
fc = {r["id"]: r for r in xdata.load_firecs("train")}; mk = {r["id"]: r for r in xdata.load_marketplace()["market_train_v3"]}
M = xdata.load_marketplace()
corpora = {
    "FiReCS train (fine-tuning and validation texts of every candidate)": [r["text"] for r in fc.values()],
    "FiReCS test (gate of the shipped model)": [r["text"] for r in xdata.load_firecs("test")],
    "marketplace training rows used to fine-tune candidates (market_train split)": [mk[i]["text"] for i in splits["market_train"]],
    "marketplace validation split (candidate selection, calibration, bias rule)": [mk[i]["text"] for i in splits["market_val"]],
    "market_test_v3 (historical benchmark)": [r["text"] for r in M["market_test_v3"]],
    "market_fresh + market_fresh2 (folded into train_v3)": [r["text"] for k in ("market_fresh", "market_fresh2") for r in M[k]],
    "older team-labelled 300 (gold_labels_200 + heldout_labels_100)": [r["text"] for k in ("market_gold200", "market_heldout100") for r in M[k]],
    "review_pool_10000 (AI 'direct' annotations exist for these; also the active-learning pool)": [r["review_text"] for r in csv.DictReader(open(ROOT / "evaluation/review_pool_10000.csv", encoding="utf-8-sig"))],
    "conclusion_eval/product_reviews.csv (product-conclusion study)": [r.get("review") or "" for r in csv.DictReader(open(ROOT / "research/conclusion_eval/product_reviews.csv", encoding="utf-8-sig"))],
    "fresh_eval_sheet.csv (earlier fresh evaluation)": [r.get("review_text") or "" for r in csv.DictReader(open(ROOT / "research/fresh_eval/fresh_eval_sheet.csv", encoding="utf-8-sig"))],
    "al_pool.csv (active learning candidates)": [r.get("review_text") or "" for r in csv.DictReader(open(ROOT / "research/cache/al_pool.csv", encoding="utf-8-sig"))],
    "annotation dev pool sheet (different products, to be labelled for training)": [r["review_text"] for r in csv.DictReader(open(X / "annotation/dev_pool_sheet.csv", encoding="utf-8-sig"))],
}
manual = pathlib.Path("C:/Users/cabal/Downloads/manual_marketplace_reviews.csv")
if manual.exists():
    rows = list(csv.DictReader(open(manual, encoding="utf-8-sig")))
    k = next((c for c in ("review_text", "review", "text", "content") if rows and c in rows[0]), None)
    if k:
        corpora["Downloads/manual_marketplace_reviews.csv (an unrelated manual file)"] = [r[k] for r in rows]
res = {}
for name, texts in corpora.items():
    texts = [t for t in texts if t]
    if not texts:
        res[name] = {"corpus_rows": 0, "note": "no text found"}
        continue
    n = {xdata.norm_text(t) for t in texts}
    exact = sum(f in n for f in fnorm)
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1).fit(ftexts + texts)
    A = vec.transform(ftexts); B = vec.transform(texts)
    best = np.zeros(A.shape[0])
    for s in range(0, A.shape[0], 200):
        best[s:s + 200] = (A[s:s + 200] @ B.T).max(axis=1).toarray().ravel()
    res[name] = {"corpus_rows": len(texts), "frozen_exact_text_matches": int(exact), "frozen_near_duplicates_cosine_ge_0.9": int((best >= 0.9).sum())}
# product overlap against every labelled file (titles) and against the app's local database (links)
titles = collections.Counter()
for k, rows in M.items():
    for r in rows:
        if r["product"] and " ".join(r["product"].lower().split()) in fprod:
            titles[k] += 1
res["_product_title_overlap_with_labelled_files"] = dict(titles)
local = sqlite3.connect(f"file:{ROOT / 'backend/defaketive.db'}?mode=ro", uri=True)
local_links = {l for (l,) in local.execute("select link from products")}
res["_frozen_products_also_in_the_local_database_used_by_conclusion_impact_and_prune_vocab"] = len(flinks & local_links)
res["_frozen_products"] = len(flinks)
res["_note_prune_vocab"] = "prune_vocab.py read the review text (no labels) of the whole production database copy, which contains every frozen-test review; it chose which tokenizer pieces to keep for the pruned artifacts only"
json.dump(res, open(X / "final_human_evaluation" / "leakage_audit.json", "w"), indent=1)
print(json.dumps(res, indent=1))
