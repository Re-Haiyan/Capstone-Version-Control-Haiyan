"""Builds a NEW independently held-out evaluation set (held-out v2) from a database of FRESHLY SCANNED products, with every exclusion that protects it, and freezes it before any model
is looked at. It is not run until fresh scans exist: the production database holds no further unused products (see phase2/heldout_v2_protocol.md).

    backend/.venv/Scripts/python.exe research/xlmr_optimization/build_heldout_v2.py <scan database with the production schema> [n_reviews=400]

Exclusions (all applied before sampling): products (by link, or by normalised title) of the frozen test, the dev pool, the neutral candidate pool and every labelled file; texts equal to
or near (cosine >= 0.9) a review of any of those sets or of the training corpus; duplicates. Stratified by category group and star group; at most 6 reviews per product. Writes
annotation/heldout_v2/: sheet_A.csv and sheet_B.csv (blank, same columns as the frozen test sheets; no stars, no predictions), PRIVATE_id_map.csv (git-ignored) and
frozen_manifest.json (hashes, plan, exclusion counts, frozen timestamp, the rule: scored once, after labelling and adjudication, never used to select or tune).
Reviews are NOT labelled here.
"""
import csv, datetime, hashlib, json, pathlib, random, sqlite3, sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

X = pathlib.Path(__file__).resolve().parent
ROOT = X.parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis")); sys.path.insert(0, str(X))
from defaketive_sentiment import product_category as pc  # noqa: E402
import xdata, metrics_x  # noqa: E402

OUT = X / "annotation" / "heldout_v2"
GROUPS = {"electronics": 0.30, "home_living": 0.18, "fashion": 0.15, "beauty_health": 0.15, "food_grocery": 0.10, "automotive_tools": 0.06, "other": 0.06}
STARS = {"1-2": 0.30, "3": 0.20, "4": 0.20, "5": 0.30}
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8-sig")))


def main(db, n=400):
    OUT.mkdir(parents=True, exist_ok=True)
    blocked_text = []
    for p in ("annotation/final_test_sheet_A.csv", "annotation/dev_pool_sheet.csv", "annotation/neutral_candidate_pool.csv"):
        blocked_text += [r["review_text"] for r in rd(X / p)]
    corpus = json.load(open(X / "data/head/corpus_meta.json"))
    fc = {r["id"]: r["text"] for r in xdata.load_firecs("train")}; mk = {r["id"]: r["text"] for r in xdata.load_marketplace()["market_train_v3"]}
    pool = {r["id"]: r["review_text"] for r in rd("D:/cvc-annotations/evaluation/annotation_batch_ai_direct/assembled/annotations.csv")}
    blocked_text += [fc.get(m["id"]) or mk.get(m["id"]) or pool.get(m["id"], "") for m in corpus]
    blocked_norm = {xdata.norm_text(t) for t in blocked_text}
    blocked_links = {r["product_link"] for p in ("PRIVATE_id_map.csv", ) for r in csv.DictReader(open(X / "annotation" / p, encoding="utf-8"))}
    blocked_links |= {r["group"] for r in csv.DictReader(open(X / "annotation/PRIVATE_neutral_candidate_map.csv", encoding="utf-8")) if r["source"] == "production_db"}
    blocked_titles = {" ".join(r["product"].lower().split()) for rows in xdata.load_marketplace().values() for r in rows if r["product"]}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    products = {l: (nm, pl) for l, nm, pl in con.execute("select link, name, platform from products")}
    rows, seen, per, removed = [], set(), {}, {"blocked product": 0, "equal to a blocked text": 0, "duplicate": 0}
    allrows = con.execute("select review_key, product_link, rating, content from reviews where length(content) >= 12").fetchall()
    random.Random(20261201).shuffle(allrows)
    for key, link, rating, text in allrows:
        name, plat = products.get(link, ("", ""))
        if link in blocked_links or " ".join(name.lower().split()) in blocked_titles:
            removed["blocked product"] += 1; continue
        nt = xdata.norm_text(text)
        if nt in blocked_norm:
            removed["equal to a blocked text"] += 1; continue
        if nt in seen or rating is None:
            removed["duplicate"] += 1; continue
        if per.get(link, 0) >= 6:
            continue
        seen.add(nt); per[link] = per.get(link, 0) + 1
        g = pc.group_of(pc.classify_listing({"name": name})); g = g if g in GROUPS else "other"
        rows.append({"key": key, "link": link, "stars": int(rating), "text": text.strip(), "group": g, "platform": plat, "product": name})
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1).fit(blocked_text[:20000] + [r["text"] for r in rows])
    B = vec.transform([t for t in blocked_text if t]); best = np.zeros(len(rows))
    A = vec.transform([r["text"] for r in rows])
    for s in range(0, len(rows), 1000):
        best[s:s + 1000] = (A[s:s + 1000] @ B.T).max(axis=1).toarray().ravel()
    rows = [r for r, b in zip(rows, best) if b < 0.9]
    removed["near duplicate (cosine >= 0.9) of a blocked text"] = int((best >= 0.9).sum())
    sb = lambda s: "1-2" if s <= 2 else str(s)
    rng = random.Random(7); picked, used = [], set()
    for g, gq in GROUPS.items():
        for k, sq in STARS.items():
            cell = [r for r in rows if r["group"] == g and sb(r["stars"]) == k and r["key"] not in used]
            rng.shuffle(cell); take = cell[: round(n * gq * sq)]; picked += take; used |= {r["key"] for r in take}
    rest = [r for r in rows if r["key"] not in used]; rng.shuffle(rest)
    picked = (picked + rest[: max(0, n - len(picked))])[:n]
    for i, r in enumerate(sorted(picked, key=lambda r: r["key"]), 1):
        r["sid"] = f"H{i:03d}"
    cols = ["id", "product", "category_group", "platform", "language_hint", "review_text", "sentiment", "tags", "positive_aspect", "negative_aspect", "confidence", "rationale"]
    for name, seed in (("sheet_A.csv", 1), ("sheet_B.csv", 2)):
        rr = list(picked); random.Random(seed).shuffle(rr)
        with open(OUT / name, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(cols)
            for r in rr:
                w.writerow([r["sid"], " ".join(r["product"].split())[:140], r["group"], r["platform"], metrics_x.lang_of(r["text"]), r["text"].replace("\r", " ").replace("\n", " "), "", "", "", "", "", ""])
    with open(OUT / "PRIVATE_id_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["sheet_id", "review_key", "product_link", "stars", "category_group", "platform"])
        for r in sorted(picked, key=lambda r: r["sid"]):
            w.writerow([r["sid"], r["key"], r["link"], r["stars"], r["group"], r["platform"]])
    manifest = {"frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "rule": "Frozen before any model is looked at. Scored once, after labelling and adjudication; never used to select, tune or threshold.",
                "source_database_sha256": xdata.sha256(db), "reviews": len(picked), "products": len({r["link"] for r in picked}), "removed": removed,
                "by_group": {g: sum(r["group"] == g for r in picked) for g in GROUPS}, "by_star": {k: sum(sb(r["stars"]) == k for r in picked) for k in STARS},
                "sheet_sha256": {n: xdata.sha256(OUT / n) for n in ("sheet_A.csv", "sheet_B.csv", "PRIVATE_id_map.csv")}, "human_or_ai_labels_in_files": 0}
    json.dump(manifest, open(OUT / "frozen_manifest.json", "w"), indent=1)
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 400)
