"""Score the deployed rules on a labelled file in parallel and keep every prediction, so errors can be read per label.

    backend\.venv\Scripts\python.exe training\rules_eval.py evaluation\annotated\train_v3.csv out.json [workers]
"""
import csv, json, multiprocessing as mp, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
FLAGS = ("defect", "counterfeit", "safety", "not_as_described", "quality")
_model = None

def work(rows):
    global _model
    if _model is None:
        from defaketive_sentiment import registry
        _model = registry.load_model()
    out = {}
    for r in rows:
        a = _model.analyze_batch([r["review_text"]], [int(r["stars"])], listing={"name": r["product"]})[0]
        tags = set(a.get("review_tags") or []) | set(a.get("review_extra_tags") or [])
        out[r["id"]] = {"pred": [1 if f in tags else 0 for f in FLAGS], "sent": a.get("label")}
    return out

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    rows = [r for r in csv.DictReader(open(src, encoding="utf-8-sig")) if r["confidence"].lower() == "high" and r["flags"].strip()]
    chunks = [rows[i::n * 4] for i in range(n * 4)]
    result = {}
    with mp.Pool(n) as pool:
        for part in pool.imap_unordered(work, chunks): result.update(part)
    json.dump(result, open(dst, "w"))
    print(len(result), "rows scored")
