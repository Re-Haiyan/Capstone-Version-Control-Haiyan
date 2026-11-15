"""Candidate reviews for NEUTRAL (no-opinion) annotation under policy v1: a transparent heuristic prioritises WHICH reviews are sent to the annotator; the labels come only from
the annotator (nothing here assigns a label, and a candidate is not assumed to be neutral).

    D:/defaketive-train/Scripts/python.exe research/xlmr_optimization/neutral_candidates.py

Sources: the production-database copy (read only) and the 10,000-review pool (its test_candidate split excluded). Exclusions, applied before selection: any text equal to or
near (character TF-IDF cosine >= 0.9) a frozen-test or dev-pool review, any text already in the training corpus (so no row is duplicated), products of the frozen test and
the dev pool, duplicates inside the candidates. Diversity: at most 25 reviews per product. Writes annotation/neutral_candidate_pool.csv (id N0001..) and
phase2/neutral_sources_report.json. Cues (regular expressions): list of 3 or more short claims without first-person words, "not yet used / will update", very short factual text.
"""
import collections, csv, glob, json, pathlib, re, sqlite3, sys
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

X = pathlib.Path(__file__).resolve().parent
ROOT = X.parent.parent
sys.path.insert(0, str(X))
import xdata, metrics_x  # noqa: E402

FIRST = re.compile(r"\b(?:i|ako|ko|akin|namin|nagamit|nabili|nakuha|sakin|sa akin|my|me|we|nag-?order|order ko)\b", re.I)
NOT_YET = re.compile(r"\b(?:not yet|yet to|haven'?t (?:tried|used|tested)|di ko pa|hindi ko pa|will update|update (?:ko|later)|to be updated|wala pa)\b", re.I)
SEG = re.compile(r"[^.!?,;]+")


def cues(text):
    out = []
    segs = [s.strip() for s in SEG.findall(text) if s.strip()]
    if len(segs) >= 3 and all(len(s.split()) <= 12 for s in segs) and not FIRST.search(text):
        out.append("feature_list")
    if NOT_YET.search(text):
        out.append("not_yet_used")
    if len(text.split()) <= 4 and not FIRST.search(text):
        out.append("very_short")
    return out


def main():
    ft = [r["review_text"] for r in csv.DictReader(open(X / "annotation/final_test_sheet_A.csv", encoding="utf-8-sig"))]
    dev = [r["review_text"] for r in csv.DictReader(open(X / "annotation/dev_pool_sheet.csv", encoding="utf-8-sig"))]
    pm = {r["sheet_id"]: r for r in csv.DictReader(open(X / "annotation/PRIVATE_id_map.csv", encoding="utf-8"))}
    block_links = {r["product_link"] for r in pm.values()}
    corpus = json.load(open(X / "data/head/corpus_meta.json"))
    fc = {r["id"]: r["text"] for r in xdata.load_firecs("train")}
    mk = {r["id"]: r["text"] for r in xdata.load_marketplace()["market_train_v3"]}
    pool_ai = {r["id"]: r for r in csv.DictReader(open("D:/cvc-annotations/evaluation/annotation_batch_ai_direct/assembled/annotations.csv", encoding="utf-8-sig"))}
    seen_norm = {xdata.norm_text(fc.get(m["id"]) or mk.get(m["id"]) or pool_ai.get(m["id"], {}).get("review_text", "")) for m in corpus}
    block_norm = {xdata.norm_text(t) for t in ft + dev}
    cands = []
    db = glob.glob("D:/defaketive-backups/predeploy-*/defaketive.db")[0]
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    names = {l: n for l, n in con.execute("select link, name from products")}
    for key, link, text in con.execute("select review_key, product_link, content from reviews where length(content) >= 3"):
        if link not in block_links and text:
            cands.append({"source": "production_db", "ref": key, "product": names.get(link, ""), "group": link, "text": text.strip()})
    for r in pool_ai.values():
        if r["original_split"] != "test_candidate":
            cands.append({"source": "review_pool_10000", "ref": r["id"], "product": "", "group": r["group_id"], "text": r["review_text"].strip()})
    stats = {"candidates_before_exclusions": len(cands), "removed": collections.Counter()}
    keep, seen = [], set()
    for c in cands:
        n = xdata.norm_text(c["text"])
        if not n or n in block_norm:
            stats["removed"]["equal to a frozen-test or dev-pool review"] += 1; continue
        if n in seen_norm:
            stats["removed"]["already in the training corpus"] += 1; continue
        if n in seen:
            stats["removed"]["duplicate among candidates"] += 1; continue
        seen.add(n); keep.append(c)
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2).fit(ft + dev)
    blk = vec.transform(ft + dev)
    texts = [c["text"] for c in keep]
    best = np.zeros(len(keep))
    for s in range(0, len(keep), 2000):
        best[s:s + 2000] = (vec.transform(texts[s:s + 2000]) @ blk.T).max(axis=1).toarray().ravel()
    keep = [c for c, b in zip(keep, best) if b < 0.9] if len(keep) else keep
    stats["removed"]["near duplicate (cosine >= 0.9) of a frozen-test or dev-pool review"] = int((best >= 0.9).sum())
    for c in keep:
        c["cues"] = cues(c["text"])
    by_cue = collections.Counter(k for c in keep for k in c["cues"])
    cue_rows = [c for c in keep if c["cues"]]
    cue_rows.sort(key=lambda c: (-len(c["cues"]), c["text"]))
    per = collections.Counter(); chosen = []
    for c in cue_rows:
        if per[c["group"]] < 25:
            per[c["group"]] += 1; chosen.append(c)
        if len(chosen) >= 3000:
            break
    out = X / "annotation/neutral_candidate_pool.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "product", "category_group", "platform", "language_hint", "review_text", "sentiment", "tags", "positive_aspect", "negative_aspect", "confidence", "rationale"])
        for i, c in enumerate(chosen, 1):
            w.writerow([f"N{i:04d}", " ".join(c["product"].split())[:140], "", c["source"], metrics_x.lang_of(c["text"]), c["text"].replace("\r", " ").replace("\n", " "), "", "", "", "", "", ""])
    with open(X / "annotation/PRIVATE_neutral_candidate_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["id", "source", "ref", "group", "cues"])
        for i, c in enumerate(chosen, 1):
            w.writerow([f"N{i:04d}", c["source"], c["ref"], c["group"], ";".join(c["cues"])])
    rep = {"candidates_before_exclusions": stats["candidates_before_exclusions"], "removed": dict(stats["removed"]), "usable_after_exclusions": len(keep), "usable_with_a_cue": len(cue_rows), "cue_counts": dict(by_cue),
           "selected_for_annotation": len(chosen), "selected_by_source": dict(collections.Counter(c["source"] for c in chosen)), "selected_by_cue": dict(collections.Counter(k for c in chosen for k in c["cues"])),
           "products_represented": len({c["group"] for c in chosen}), "language_hint": dict(collections.Counter(metrics_x.lang_of(c["text"]) for c in chosen)),
           "note": "Cues only prioritise what is sent to the annotator. The share of these reviews that policy v1 labels neutral is UNKNOWN until they are annotated; 3,000 candidates do not guarantee 1,500 neutral rows."}
    json.dump(rep, open(X / "phase2/neutral_sources_report.json", "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
