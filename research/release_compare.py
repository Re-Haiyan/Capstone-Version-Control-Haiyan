"""Run the review pipeline of ANY checkout on the labelled reviews, with every experimental switch cleared, and save the outputs.

    backend\\.venv\\Scripts\\python.exe research\\release_compare.py <checkout_root> <out.json> [workers]

The same script (from the release candidate) is pointed at the production commit's checkout and at the candidate, so the two outputs
differ only by the code under test. All DEFAKETIVE_* environment variables are removed first, so this measures defaults.
Output per review id: review_tags, review_extra_tags, sentiment label, whether the review carries a `review_evidence` key.
"""
import csv, json, multiprocessing as mp, os, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent.parent
_model = None
_root = None


def init(root):
    global _root
    _root = pathlib.Path(root)
    for key in [k for k in os.environ if k.startswith("DEFAKETIVE_")]:
        del os.environ[key]
    sys.path.insert(0, str(_root / "backend" / "sentiment-analysis"))


def work(rows):
    global _model
    if _model is None:
        from defaketive_sentiment import registry
        _model = registry.load_model()
    out = {}
    for r in rows:
        a = _model.analyze_batch([r["review_text"]], [int(r["stars"])], listing={"name": r["product"]})[0]
        out[r["id"]] = {"tags": sorted(a.get("review_tags") or []), "extra": sorted(a.get("review_extra_tags") or []), "label": a.get("label"),
                        "has_evidence_key": "review_evidence" in a, "keys": sorted(a.keys())}
    return out


if __name__ == "__main__":
    root, dst = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    rows = []
    for name in ("train_v3", "test_v3"):
        rows += [dict(r, split=name) for r in csv.DictReader(open(HERE / "evaluation/annotated" / f"{name}.csv", encoding="utf-8-sig")) if r["confidence"].lower() == "high" and r["flags"].strip()]
    result = {}
    with mp.Pool(n, initializer=init, initargs=(root,)) as pool:
        for part in pool.imap_unordered(work, [rows[i::n * 4] for i in range(n * 4)]):
            result.update(part)
    json.dump({"root": str(root), "rows": len(result), "reviews": result}, open(dst, "w"))
    print(len(result), "reviews analysed from", root)
