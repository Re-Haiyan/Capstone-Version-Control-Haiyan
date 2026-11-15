"""Builds the Phase 3 CONFIRMATION set: 200 reviews never used in training, selection or validation of any Phase 3 configuration, frozen BEFORE it is annotated and before any configuration is scored on it.

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/build_confirm_set.py

Source: the production-database copy (read only). Excluded before sampling: products of the frozen test, the dev pool and the ANNOTATED neutral-candidate rows (the unannotated candidates and the old training corpora's products are NOT blocked by product, because almost every production product is in them; texts are always disjoint); texts equal to or near (cosine >= 0.9) any frozen-test, dev-pool, candidate,
training-corpus or v1-labelled review; duplicates. Sampling (seed 20261116): 100 reviews with at least one neutral-oriented cue (feature list, not-yet-used, very short) and 100 without a cue, at most 4 per product.
The cue split exists so that neutral reviews are present; weights are recorded (cue rows are over-represented). Writes annotation/confirm_v1_sheet.csv, annotation/chatgpt_batches/confirm_v1_batch_01..04.csv (blind: no stars, no predictions, no labels),
annotation/PRIVATE_confirm_map.csv (git-ignored) and annotation/confirm_v1_manifest.json (hashes, plan, frozen time). Nothing is labelled here.
"""
import csv, datetime, glob, hashlib, json, pathlib, random, sqlite3, sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

X = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(X))
import xdata, metrics_x, neutral_candidates as nc  # noqa: E402

A = X / "annotation"
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8-sig")))


def main():
    blocked_sheets = [rd(A / "final_test_sheet_A.csv"), rd(A / "dev_pool_sheet.csv"), rd(A / "neutral_candidate_pool.csv")]
    blocked_text = [r["review_text"] for s in blocked_sheets for r in s]
    meta = json.load(open(X / "data/head/corpus_meta.json"))
    fc = {r["id"]: r["text"] for r in xdata.load_firecs("train")}; mk = {r["id"]: r["text"] for r in xdata.load_marketplace()["market_train_v3"]}
    pool = {r["id"]: r["review_text"] for r in rd("D:/cvc-annotations/evaluation/annotation_batch_ai_direct/assembled/annotations.csv")}
    blocked_text += [fc.get(m["id"]) or mk.get(m["id"]) or pool.get(m["id"], "") for m in meta]
    bn = {xdata.norm_text(t) for t in blocked_text if t}
    pm = {r["sheet_id"]: r for r in csv.DictReader(open(A / "PRIVATE_id_map.csv", encoding="utf-8"))}
    cm = {r["id"]: r for r in csv.DictReader(open(A / "PRIVATE_neutral_candidate_map.csv", encoding="utf-8"))}
    annotated = {r["id"] for r in rd(A / "ai_labelled/neutral_candidate_pool_ai_v1.csv")}  # only candidates that were annotated (and may be trained on) block their products
    blocked_links = {r["product_link"] for r in pm.values()} | {cm[i]["group"] for i in annotated if cm[i]["source"] == "production_db"}
    db = glob.glob("D:/defaketive-backups/predeploy-*/defaketive.db")[0]
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    names = {l: n for l, n in con.execute("select link, name from products")}
    rows = con.execute("select review_key, product_link, content from reviews where length(content) >= 3").fetchall()
    random.Random(20261116).shuffle(rows)
    seen, keep, removed = set(), [], {"blocked product": 0, "equal to a blocked text": 0, "duplicate": 0}
    for key, link, text in rows:
        if link in blocked_links:
            removed["blocked product"] += 1; continue
        n = xdata.norm_text(text or "")
        if not n or n in bn:
            removed["equal to a blocked text"] += 1; continue
        if n in seen:
            removed["duplicate"] += 1; continue
        seen.add(n); keep.append({"key": key, "link": link, "product": names.get(link, ""), "text": text.strip(), "cues": nc.cues(text.strip())})
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2).fit(blocked_text[:30000])
    B = vec.transform([t for t in blocked_text if t])
    best = np.zeros(len(keep)); T = [k["text"] for k in keep]
    for s in range(0, len(keep), 2000):
        best[s:s + 2000] = (vec.transform(T[s:s + 2000]) @ B.T).max(axis=1).toarray().ravel()
    removed["near duplicate (cosine >= 0.9)"] = int((best >= 0.9).sum())
    keep = [k for k, b in zip(keep, best) if b < 0.9]
    rng = random.Random(7); per = {}; pick = []
    for want, cond in ((100, True), (100, False)):
        cell = [k for k in keep if bool(k["cues"]) == cond]; rng.shuffle(cell); n = 0
        for k in cell:
            if per.get(k["link"], 0) < 4:
                per[k["link"]] = per.get(k["link"], 0) + 1; k["stratum"] = "cue" if cond else "no_cue"; pick.append(k); n += 1
            if n >= want:
                break
    cue_pop = sum(1 for k in keep if k["cues"]); pop = len(keep)
    for k in pick:
        k["weight"] = round(((cue_pop if k["stratum"] == "cue" else pop - cue_pop) / pop) / 0.5, 4)
    rng.shuffle(pick)
    for i, k in enumerate(pick, 1):
        k["sid"] = f"C{i:03d}"
    cols = ["id", "product", "category_group", "platform", "language_hint", "review_text", "sentiment", "tags", "positive_aspect", "negative_aspect", "confidence", "rationale"]
    with open(A / "confirm_v1_sheet.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(cols)
        for k in pick:
            w.writerow([k["sid"], " ".join(k["product"].split())[:140], "", "production_db", metrics_x.lang_of(k["text"]), k["text"].replace("\r", " ").replace("\n", " "), "", "", "", "", "", ""])
    for b in range(4):
        with open(A / "chatgpt_batches" / f"confirm_v1_batch_{b + 1:02d}.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f); w.writerow(["id", "product", "language_hint", "review_text"])
            for k in pick[b * 50:(b + 1) * 50]:
                w.writerow([k["sid"], " ".join(k["product"].split())[:140], metrics_x.lang_of(k["text"]), k["text"].replace("\r", " ").replace("\n", " ")])
    with open(A / "PRIVATE_confirm_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["id", "review_key", "product_link", "stratum", "weight", "cues"])
        for k in sorted(pick, key=lambda k: k["sid"]):
            w.writerow([k["sid"], k["key"], k["link"], k["stratum"], k["weight"], ";".join(k["cues"])])
    manifest = {"frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "rule": "Frozen before annotation and before any Phase 3 configuration is scored on it. Configurations are locked in phase3_lock.json first; this set is scored once per locked configuration and chooses nothing.",
                "source_database_sha256": xdata.sha256(db), "reviews": len(pick), "products": len({k["link"] for k in pick}), "usable_population_after_exclusions": pop, "removed": removed,
                "by_stratum": {s: sum(k["stratum"] == s for k in pick) for s in ("cue", "no_cue")}, "sheet_sha256": xdata.sha256(A / "confirm_v1_sheet.csv"), "labels_in_files": 0}
    json.dump(manifest, open(A / "confirm_v1_manifest.json", "w"), indent=1)
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
