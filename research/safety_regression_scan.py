"""Unlabelled safety-regression scan: run the review pipeline of ANY checkout on saved review texts and record which reviews carry
a safety flag. Run once per checkout, then `diff` lists every review whose safety flag differs. Labels are not used at all.

    backend\\.venv\\Scripts\\python.exe research\\safety_regression_scan.py scan <checkout_root> <out.json> [n_reviews] [workers]
    backend\\.venv\\Scripts\\python.exe research\\safety_regression_scan.py diff old.json new.json out.csv

Reviews are a seeded random sample of the saved database (COMPAT_DB selects another one; SCAN_CORPUS=evaluation uses every review of evaluation/**.csv that names its product, including non-gadget categories), only reviews with text of at least 12 characters.
"""
import csv, json, multiprocessing as mp, os, pathlib, random, sqlite3, sys

HERE = pathlib.Path(__file__).resolve().parent.parent
DB = pathlib.Path(os.environ.get("COMPAT_DB") or HERE / "backend" / "defaketive.db")
_model = None


def init(root):
    for key in [k for k in os.environ if k.startswith("DEFAKETIVE_")]:
        del os.environ[key]
    sys.path.insert(0, str(pathlib.Path(root) / "backend" / "sentiment-analysis"))


def work(rows):
    global _model
    if _model is None:
        from defaketive_sentiment import registry
        _model = registry.load_model()
    out = {}
    for key, name, stars, text in rows:
        a = _model.analyze_batch([text], [int(stars)], listing={"name": name})[0]
        out[key] = {"safety": "safety" in (a.get("review_tags") or []), "tags": sorted(a.get("review_tags") or [])}
    return out


def sample_evaluation_files(n):
    """Every review of the evaluation folder that names its product, once per (product, text): non-gadget categories included."""
    import glob
    seen, rows = set(), []
    for path in sorted(glob.glob(str(HERE / "evaluation" / "**" / "*.csv"), recursive=True)):
        reader = csv.DictReader(open(path, encoding="utf-8-sig"))
        if not {"review_text", "product", "stars"} <= set(reader.fieldnames or []):
            continue
        for r in reader:
            text = (r["review_text"] or "").strip()
            key = (r["product"], text)
            if len(text) < 12 or key in seen:
                continue
            seen.add(key)
            rows.append((f"{pathlib.Path(path).name}:{r['id']}", r["product"], int(float(r["stars"] or 3)), text))
    random.Random(7).shuffle(rows)
    return rows[:n]


def sample(n):
    if os.environ.get("SCAN_CORPUS") == "evaluation":
        return sample_evaluation_files(n)
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute("select r.review_key, coalesce(p.name,''), coalesce(r.rating,3), r.content from reviews r left join products p on p.link=r.product_link "
                       "where length(r.content) >= 12").fetchall()
    random.Random(7).shuffle(rows)
    return [(k, nm, st, tx) for k, nm, st, tx in rows[:n]]


if __name__ == "__main__":
    if sys.argv[1] == "scan":
        root, dst = sys.argv[2], sys.argv[3]
        n = int(sys.argv[4]) if len(sys.argv) > 4 else 6000
        w = int(sys.argv[5]) if len(sys.argv) > 5 else 4
        rows = sample(n)
        text = {k: tx for k, _, _, tx in rows}
        res = {}
        with mp.Pool(w, initializer=init, initargs=(root,)) as pool:
            for part in pool.imap_unordered(work, [rows[i::w * 8] for i in range(w * 8)]):
                res.update(part)
        json.dump({"root": str(root), "n": len(res), "reviews": res, "text": text}, open(dst, "w", encoding="utf-8"))
        print(len(res), "reviews;", sum(1 for v in res.values() if v["safety"]), "with a safety flag")
    else:
        old = json.load(open(sys.argv[2], encoding="utf-8")); new = json.load(open(sys.argv[3], encoding="utf-8"))
        lost = [k for k in old["reviews"] if old["reviews"][k]["safety"] and not new["reviews"][k]["safety"]]
        gained = [k for k in old["reviews"] if not old["reviews"][k]["safety"] and new["reviews"][k]["safety"]]
        with open(sys.argv[4], "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["change", "review_key", "text"])
            for k in lost: w.writerow(["lost", k, old["text"][k][:600]])
            for k in gained: w.writerow(["gained", k, old["text"][k][:600]])
        print("reviews", len(old["reviews"]), "| safety flag lost", len(lost), "| gained", len(gained), "| old flagged", sum(v["safety"] for v in old["reviews"].values()), "new flagged", sum(v["safety"] for v in new["reviews"].values()))
