"""Cache the deployed sentiment model's probabilities (negative, neutral, positive) for the labelled rows.
    backend\.venv\Scripts\python.exe research\sentiment_probs.py [workers]
"""
import csv, json, multiprocessing as mp, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))
_model = None
def work(rows):
    global _model
    if _model is None:
        from defaketive_sentiment import registry
        _model = registry.load_model()
    out = {}
    for r in rows:
        a = _model.analyze_batch([r["review_text"]], [int(r["stars"])], listing={"name": r["product"]})[0]
        p = a["sentiment"]["probabilities"]; out[r["id"]] = [p["negative"], p["neutral"], p["positive"]]
    return out
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6; result = {}
    for name in ("train_v3", "test_v3"):
        rows = [r for r in csv.DictReader(open(ROOT / "evaluation/annotated" / f"{name}.csv", encoding="utf-8-sig")) if r["confidence"].lower() == "high" and r["flags"].strip()]
        with mp.Pool(n) as pool:
            for part in pool.imap_unordered(work, [rows[i::n * 4] for i in range(n * 4)]): result.update(part)
    json.dump(result, open(ROOT / "research" / "cache" / "sentiment_probs.json", "w")); print(len(result))
