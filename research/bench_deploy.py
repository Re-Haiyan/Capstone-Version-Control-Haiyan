"""CPU deployment benchmark of the review pipeline: cold start, peak memory, latency, throughput, full-scan time.

    python research/bench_deploy.py <reviews.csv> [out.json]       (the app's Python; works on Windows and Linux)

reviews.csv needs columns stars, product, review_text. Measures with the real pipeline (registry.load_model, listing context),
one review at a time and in batches, and a "full scan" of 200 reviews.
"""
import csv, json, os, pathlib, platform, sys, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend" / "sentiment-analysis"))


def rss_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1e6
    except Exception:
        try:
            for line in open("/proc/self/status"):
                if line.startswith("VmRSS"):
                    return int(line.split()[1]) / 1e3
        except OSError:
            pass
        return -1.0  # no psutil and no /proc (Windows without psutil): memory is measured on the Linux VM instead


def peak_mb():
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e3
    except Exception:
        try:
            import psutil
            return psutil.Process().memory_info().peak_wset / 1e6
        except Exception:
            return -1.0


rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8-sig")))
t0 = time.time(); rss0 = rss_mb()
from defaketive_sentiment import registry
model = registry.load_model()
model.analyze_batch([rows[0]["review_text"]], [int(rows[0]["stars"])], listing={"name": rows[0]["product"]})  # warm-up call
cold = time.time() - t0
out = {"platform": platform.platform(), "cpus": os.cpu_count(), "cold_start_seconds": round(cold, 2), "rss_after_load_mb": round(rss_mb(), 1), "rss_before_mb": round(rss0, 1)}
lat = []
for r in rows[1:101]:
    t = time.time(); model.analyze_batch([r["review_text"]], [int(r["stars"])], listing={"name": r["product"]}); lat.append((time.time() - t) * 1000)
lat.sort(); out["single_review_ms"] = {"median": round(lat[len(lat) // 2], 1), "p95": round(lat[int(len(lat) * 0.95)], 1), "mean": round(sum(lat) / len(lat), 1)}
batch = rows[101:301]
t = time.time(); model.analyze_batch([r["review_text"] for r in batch], [int(r["stars"]) for r in batch], listing={"name": batch[0]["product"]}); dt = time.time() - t
out["batch_200_seconds"] = round(dt, 2); out["batch_reviews_per_second"] = round(len(batch) / dt, 1)
out["peak_rss_mb"] = round(peak_mb(), 1); out["rss_end_mb"] = round(rss_mb(), 1)
sizes = {}
for p in (ROOT / "backend/sentiment-analysis/models").rglob("*"):
    if p.is_file() and p.stat().st_size > 100_000:
        sizes[str(p.relative_to(ROOT / "backend/sentiment-analysis/models"))] = round(p.stat().st_size / 1e6, 2)
out["model_artifacts_mb"] = sizes; out["model_total_mb"] = round(sum(sizes.values()), 1)
cal = ROOT / "research/artifacts/sentiment_calibrator_v1.joblib"
try:
    from defaketive_sentiment.sentiment_calibration import SentimentCalibrator
    if cal.is_file():
        c = SentimentCalibrator.load(cal); t = time.time()
        for r in rows[:100]:
            c.predict(r["review_text"], int(r["stars"]), [0.3, 0.3, 0.4])
        out["sentiment_calibrator_ms_per_review"] = round((time.time() - t) * 10, 2); out["sentiment_calibrator_mb"] = round(cal.stat().st_size / 1e6, 2)
except ImportError:
    out["sentiment_calibrator"] = "module not present in this checkout"
print(json.dumps(out, indent=1))
if len(sys.argv) > 2:
    json.dump(out, open(sys.argv[2], "w"), indent=1)
