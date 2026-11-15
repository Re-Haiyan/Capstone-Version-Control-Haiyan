"""Exact-quotation check of the release candidate: every quoted span must equal its slice of the original review.

    backend\\.venv\\Scripts\\python.exe research\\release_checks.py [workers]

(1) All labelled reviews: for each `keyword_span` in `review_evidence`, review[review_start:review_end] == span text, and the sentence
offsets agree (sentence text[start:end] == span text). (2) Real saved Lazada reviews (10 products, up to 300 reviews each): the same,
plus the highlight ranges the app serves in each badge's evidence quotes (`badge_view`) lie inside the quoted text and cover real
characters. Switches are cleared first. Writes research/results/release_evidence_quotes.json.
"""
import csv, json, multiprocessing as mp, os, pathlib, random, sqlite3, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
for key in [k for k in os.environ if k.startswith("DEFAKETIVE_")]:
    del os.environ[key]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
_model = None


def check(items):
    global _model
    if _model is None:
        from defaketive_sentiment import registry
        _model = registry.load_model()
    res = {"reviews": 0, "spans": 0, "bad_review_offset": 0, "bad_sentence_offset": 0, "no_review_offset": 0, "empty_text": 0, "examples": []}
    for text, stars, product in items:
        a = _model.analyze_batch([text], [int(stars)], listing={"name": product})[0]
        res["reviews"] += 1
        sentences = {int(s.get("index", i)): s for i, s in enumerate(a["sentences"])}
        for flag, entry in a["review_evidence"].items():
            for sp in entry["spans"]:
                res["spans"] += 1
                s = sentences.get(sp["sentence"], {})
                raw = s.get("text_raw", "")
                if not sp["text"].strip():
                    res["empty_text"] += 1
                if raw[sp["start"]:sp["end"]] != sp["text"]:
                    res["bad_sentence_offset"] += 1
                    res["examples"].append(("sentence", flag, sp["text"], raw[sp["start"]:sp["end"]]))
                if sp["review_start"] is None:
                    res["no_review_offset"] += 1
                elif text[sp["review_start"]:sp["review_end"]] != sp["text"]:
                    res["bad_review_offset"] += 1
                    res["examples"].append(("review", flag, sp["text"], text[sp["review_start"]:sp["review_end"]]))
    return res


def merge(parts):
    out = {k: 0 for k in ("reviews", "spans", "bad_review_offset", "bad_sentence_offset", "no_review_offset", "empty_text")}; out["examples"] = []
    for p in parts:
        for k in out:
            if k == "examples":
                out[k] += p[k][:5]
            else:
                out[k] += p[k]
    out["examples"] = out["examples"][:10]
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    labelled = []
    for name in ("train_v3", "test_v3"):
        labelled += [(r["review_text"], r["stars"], r["product"]) for r in csv.DictReader(open(ROOT / "evaluation/annotated" / f"{name}.csv", encoding="utf-8-sig")) if r["confidence"].lower() == "high" and r["flags"].strip()]
    con = sqlite3.connect(str(ROOT / "backend" / "defaketive.db")); saved, products = [], []
    for raw, platform in con.execute("select raw_json, platform from products where raw_json is not null"):
        p = json.loads(raw)
        if "Lazada" in platform and isinstance(p.get("comments"), list) and len(p["comments"]) >= 40:
            products.append(p)
    random.Random(21).shuffle(products)
    for p in products[:10]:
        for c in [c for c in p["comments"] if isinstance(c, dict) and str(c.get("content") or "").strip()][:300]:
            saved.append((str(c["content"]), c.get("rating") or 3, p.get("name") or ""))
    out = {}
    with mp.Pool(n) as pool:
        for name, items in (("labelled_reviews", labelled), ("saved_lazada_reviews", saved)):
            out[name] = merge(pool.imap_unordered(check, [items[i::n * 4] for i in range(n * 4)]))
    # the highlight ranges the app serves
    import dashboard_utils
    from defaketive_sentiment.analyze_reviews import analyze_product_json
    from defaketive_sentiment.registry import load_model
    served = {"products": 0, "quotes": 0, "highlights": 0, "highlight_outside_quote": 0, "highlight_empty": 0}
    import copy
    analysed = analyze_product_json(copy.deepcopy(products[:10]), load_model())
    for product in analysed:
        view = dashboard_utils.badge_view(product); served["products"] += 1
        for badge in view.get("badges") or []:
            for quote in badge.get("evidence") or []:
                served["quotes"] += 1
                text = str(quote.get("text") or "")
                for h in quote.get("highlights") or quote.get("terms") or []:
                    rng = h if isinstance(h, (list, tuple)) else h.get("span")
                    if not rng:
                        continue
                    served["highlights"] += 1
                    if not (0 <= rng[0] < rng[1] <= len(text)):
                        served["highlight_outside_quote"] += 1
                    elif not text[rng[0]:rng[1]].strip():
                        served["highlight_empty"] += 1
    out["served_to_the_app"] = served
    json.dump(out, open(ROOT / "research" / "results" / "release_evidence_quotes.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))
