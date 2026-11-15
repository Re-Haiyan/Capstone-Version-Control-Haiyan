"""Provenance forensics for returned annotation sheets (NO model predictions are read; no model is scored).

    python research/xlmr_optimization/provenance_forensics.py <sheet A done> <sheet B done> <blank A> <blank B>

Checks file metadata, id/text identity against the frozen blanks (matching by id), row order, encoding and line endings, rationale diversity and templating, annotation time budget,
relation of the labels to the hidden star rating (read from the private map, only for this audit), duplicate files, and whether any other file on this machine shares the returned
sheets' content. Evidence of how a sheet was produced is reported; it is never proof by itself.
"""
import collections, csv, glob, hashlib, json, os, pathlib, re, sys, datetime
import numpy as np
X = pathlib.Path(__file__).resolve().parent
ROOT = X.parent.parent
done = [pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])]
blank = [pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])]
out = {}
pm = {r["sheet_id"]: r for r in csv.DictReader(open(X / "annotation" / "PRIVATE_id_map.csv", encoding="utf-8"))}
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
for name, d, b in (("A", done[0], blank[0]), ("B", done[1], blank[1])):
    raw = open(d, "rb").read()
    rows = list(csv.DictReader(open(d, encoding="utf-8-sig"))); brows = list(csv.DictReader(open(b, encoding="utf-8-sig")))
    ids = [r["id"] for r in rows]
    info = {"file": d.name, "sha256": sha(d), "bytes": len(raw), "mtime_local": datetime.datetime.fromtimestamp(d.stat().st_mtime).isoformat(timespec="seconds"),
            "ctime_local": datetime.datetime.fromtimestamp(d.stat().st_ctime).isoformat(timespec="seconds"),
            "bom": raw[:3] == b"\xef\xbb\xbf", "crlf_lines": raw.count(b"\r\n"), "lf_only_lines": raw.count(b"\n") - raw.count(b"\r\n"),
            "rows": len(rows), "duplicate_ids": len(ids) - len(set(ids)), "ids_equal_blank_set": set(ids) == {r["id"] for r in brows}, "row_order_equals_blank_order": ids == [r["id"] for r in brows],
            "columns_equal_blank": list(rows[0].keys()) == list(brows[0].keys())}
    bt = {r["id"]: r for r in brows}
    changed = [r["id"] for r in rows if any(r[c] != bt[r["id"]][c] for c in ("product", "category_group", "platform", "language_hint", "review_text") if r["id"] in bt)]
    info["rows_with_edited_non_label_columns"] = len(changed)
    rat = [r["rationale"].strip() for r in rows]
    c = collections.Counter(rat)
    info["rationale_distinct"] = len(c); info["rationale_most_common"] = c.most_common(5)
    info["rationale_words_mean"] = round(float(np.mean([len(x.split()) for x in rat])), 1)
    first = collections.Counter(" ".join(x.lower().split()[:3]) for x in rat)
    info["rationale_first_three_words_top"] = first.most_common(6)
    stars = np.array([int(pm[r["id"]]["stars"]) for r in rows]); lab = [r["sentiment"] for r in rows]
    tab = {s: dict(collections.Counter(l for l, st in zip(lab, stars) if st == s)) for s in (1, 2, 3, 4, 5)}
    info["labels_by_hidden_stars"] = tab
    info["confidence_low"] = sum(r["confidence"] == "low" for r in rows)
    out[name] = info
# relation between the two sheets
A = {r["id"]: r for r in csv.DictReader(open(done[0], encoding="utf-8-sig"))}; B = {r["id"]: r for r in csv.DictReader(open(done[1], encoding="utf-8-sig"))}
same_rat = sum(A[i]["rationale"].strip() == B[i]["rationale"].strip() for i in A)
same_aspects = sum(1 for i in A if (A[i]["positive_aspect"].strip(), A[i]["negative_aspect"].strip()) == (B[i]["positive_aspect"].strip(), B[i]["negative_aspect"].strip()) and (A[i]["positive_aspect"].strip() or A[i]["negative_aspect"].strip()))
mixed_ids = [i for i in A if "mixed" in A[i]["tags"]]
out["between_sheets"] = {"identical_rationale_text_rows": same_rat, "mixed_tag_rows_A": len(mixed_ids), "mixed_rows_with_identical_aspects": same_aspects,
                         "identical_tag_strings": sum(A[i]["tags"] == B[i]["tags"] for i in A), "identical_confidence": sum(A[i]["confidence"] == B[i]["confidence"] for i in A),
                         "identical_sentiment": sum(A[i]["sentiment"] == B[i]["sentiment"] for i in A)}
# does the same ordering/field pattern appear in any other file on this machine?
texts = {r["review_text"] for r in csv.DictReader(open(blank[0], encoding="utf-8-sig"))}
hits = []
for pattern in ("C:/Users/cabal/Downloads/**/*.csv", str(ROOT / "**/*.csv")):
    for f in glob.glob(pattern, recursive=True):
        if "node_modules" in f or ".venv" in f or pathlib.Path(f).resolve() in [p.resolve() for p in done + blank]:
            continue
        try:
            rr = list(csv.DictReader(open(f, encoding="utf-8-sig")))
        except Exception:
            continue
        k = next((c for c in ("review_text", "review", "text", "content") if rows and c in (rr[0] if rr else {})), None) if (rows := rr) else None
        if k:
            n = sum(r.get(k, "") in texts for r in rr)
            if n >= 5:
                hits.append((f, n))
out["other_files_sharing_frozen_test_texts"] = hits
out["same_file_hash_as_other_file"] = [f for f in glob.glob("C:/Users/cabal/Downloads/*.csv") if pathlib.Path(f).name not in (done[0].name, done[1].name) and sha(f) in (out["A"]["sha256"], out["B"]["sha256"])]
json.dump(out, open(X / "final_human_evaluation" / "_forensics.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False)[:6000])
