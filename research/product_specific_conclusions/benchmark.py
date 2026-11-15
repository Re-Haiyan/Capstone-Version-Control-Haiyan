"""Latency, CPU and memory of the product-specific conclusion.

    python research/product_specific_conclusions/benchmark.py [--cpus 2] [--tag local] [--real PATH]

Standard library only, so the SAME script runs on Windows here and on a Linux staging VM later:

    python research/product_specific_conclusions/benchmark.py --cpus 2 --tag staging

It never touches a database, a model or a service. It measures: cold start in a fresh process; the first read of every saved
product and its cached re-read; real non-electronics products when `--real` points at the analysed sample; review sets of
growing size; several simultaneous readers; CPU time against wall time; peak memory; and the cost the existing plain verdict
path pays (it should pay nothing).

--cpus N limits this process to its first N logical CPUs, to EMULATE a small server. An emulation is not a measurement of the
real server (its CPU is slower per core, and it runs other work): the machine, the date and `emulated_cpus` are written into
the results so the two are never confused. Results: performance_results_<tag>.json.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import gc
import gzip
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))


def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q * (len(values) - 1))))]


def stats(seconds):
    return {"n": len(seconds), "median_ms": round(statistics.median(seconds) * 1000, 2), "p95_ms": round(pct(seconds, 0.95) * 1000, 2), "max_ms": round(max(seconds) * 1000, 2)}


def limit_cpus(count: int) -> int:
    """Restrict this process to its first `count` logical CPUs (Linux and Windows). Returns the count in force."""
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, set(range(count)))
        return len(os.sched_getaffinity(0))
    if sys.platform == "win32":
        import ctypes

        kernel = ctypes.windll.kernel32
        kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), (1 << count) - 1)
        return count
    return os.cpu_count() or 1


def peak_memory_mib() -> float | None:
    """Peak resident memory of this process, in MiB."""
    try:
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(peak / (1024 if sys.platform != "darwin" else 1048576), 1)
    except ImportError:
        pass
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        kernel, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return None
        return round(counters.PeakWorkingSetSize / 1048576, 1)
    return None


def cold_start(runs: int = 5) -> dict:
    """A fresh Python process: import the module and read one product's reviews. This is what the first product page pays."""
    script = (
        "import sys, time, json\n"
        "t0 = time.perf_counter()\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "import aspects\n"
        "t1 = time.perf_counter()\n"
        "aspects.extract([{'comment_id': str(i), 'content': 'Ang lambot ng buhok ko, sobrang bango. Hindi gumagana ang pump pero ok naman', 'rating': 4} for i in range(150)], 'haircare', None)\n"
        "t2 = time.perf_counter()\n"
        "print(json.dumps({'import_s': t1 - t0, 'first_read_s': t2 - t1, 'heavy': [m for m in ('numpy', 'sklearn', 'joblib', 'onnxruntime') if m in sys.modules]}))\n"
    )
    out = []
    for _ in range(runs):
        ran = subprocess.run([sys.executable, "-I", "-c", script, str(ROOT / "backend")], capture_output=True, text=True)
        out.append(json.loads(ran.stdout))
    return {
        "runs": runs,
        "import_ms_median": round(statistics.median(o["import_s"] for o in out) * 1000),
        "first_read_150_reviews_ms_median": round(statistics.median(o["first_read_s"] for o in out) * 1000),
        "heavy_modules_loaded": sorted({m for o in out for m in o["heavy"]}),
    }


def load_real(path: Path | None) -> list[dict]:
    path = path or HERE / "cache" / "analysed_nongadget.json.gz"
    if not path.is_file():
        return []
    return json.load(gzip.open(path, "rt", encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpus", type=int, default=0, help="emulate a server with this many logical CPUs")
    parser.add_argument("--tag", default="local")
    parser.add_argument("--real", type=Path, default=None)
    args = parser.parse_args()
    emulated = limit_cpus(args.cpus) if args.cpus else None

    result: dict = {
        "tag": args.tag,
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "machine": f"{platform.system()} {platform.release()}, Python {platform.python_version()}, {platform.processor() or platform.machine()}, {os.cpu_count()} logical CPUs",
        "emulated_cpus": emulated,
        "note": "An emulated CPU limit is not a measurement of the real server." if emulated else "Not emulated: this machine's own CPUs.",
        "cold_start": cold_start(),
    }
    import aspect_profiles as ap
    import aspects
    import dashboard_utils as du

    products = [item["product"] for item in json.load(gzip.open(ROOT / "backend" / "seed" / "saved_products.json.gz", "rt", encoding="utf-8"))]
    du.badge_view(products[0], aspects=True)  # warm the lazy imports, so the figures below are the steady state
    aspects.clear_cache()

    plain, cold, warm = [], [], []
    for p in products:
        t = time.perf_counter(); du.badge_view(p); plain.append(time.perf_counter() - t)
    wall0, cpu0 = time.perf_counter(), time.process_time()
    for p in products:
        t = time.perf_counter(); du.badge_view(p, aspects=True); cold.append(time.perf_counter() - t)
    wall, cpu = time.perf_counter() - wall0, time.process_time() - cpu0
    for p in products:
        t = time.perf_counter(); du.badge_view(p, aspects=True); warm.append(time.perf_counter() - t)
    result["saved_electronics_182"] = {
        "products": len(products),
        "reviews": sum(len(p["comments"]) for p in products),
        "plain_verdict_as_before": stats(plain),
        "with_reasons_first_read": stats(cold),
        "with_reasons_cached": stats(warm),
        "cpu_seconds_over_wall_seconds_for_all_first_reads": round(cpu / wall, 2),
    }

    real = load_real(args.real)
    if real:
        by: dict[str, list[float]] = {}
        sizes = []
        for p in real:
            aspects.clear_cache()
            profile = ap.profile_key(du.product_category_of(p), du.product_group(p))
            t = time.perf_counter(); du.badge_view(p, aspects=True); by.setdefault(profile, []).append(time.perf_counter() - t)
            sizes.append(len(p["comments"]))
        result["real_non_electronics"] = {"products": len(real), "reviews_per_product_median": statistics.median(sizes), "first_read_by_profile": {k: stats(v) for k, v in sorted(by.items())}}

    # review sets of growing size: real reviews, repeated with distinct ids and slightly changed text so none is a duplicate
    pool = [c for p in (real or products) for c in p["comments"] if isinstance(c.get("content"), str)]
    scaling = {}
    for size in (100, 300, 1000, 3000):
        comments = [{**pool[i % len(pool)], "comment_id": f"s{i}", "content": f"{pool[i % len(pool)]['content']} ({i})"} for i in range(size)]
        runs = []
        for _ in range(3):
            aspects.clear_cache()
            t = time.perf_counter(); aspects.extract(comments, "haircare", None); runs.append(time.perf_counter() - t)
        gc.collect(); tracemalloc.start(); aspects.extract(comments, "haircare", None); peak = tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
        scaling[str(size)] = {"seconds_median": round(statistics.median(runs), 3), "peak_extra_memory_kib": round(peak / 1024)}
    result["review_set_size"] = scaling

    # several readers at once, every one reading a product not yet cached
    simultaneous = {}
    work = (products * 2)[:80]
    for workers in (1, 2, 4, 8):
        aspects.clear_cache()

        def one(p):
            t = time.perf_counter(); du.badge_view(dict(p, link=p["link"] + f"#{time.perf_counter_ns()}"), aspects=True); return time.perf_counter() - t

        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(workers) as pool_:
            latencies = list(pool_.map(one, work))
        total = time.perf_counter() - started
        simultaneous[str(workers)] = {"requests": len(latencies), "throughput_per_second": round(len(latencies) / total, 1), **stats(latencies)}
    result["simultaneous_first_reads_threads"] = {"note": "One Python process, threads: the GIL means no speed-up is expected; the figures show queueing, not parallel work.", **simultaneous}

    # the review-analysis pipeline is untouched: nothing in it is imported or changed by this feature
    diff = subprocess.run(["git", "diff", "--stat", "deployment", "--", "backend/sentiment-analysis", "backend/accounts.py", "backend/data_store.py"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    result["existing_pipeline"] = {"files_changed_in_analysis_models_or_data_store_vs_deployment": diff or "none", "plain_verdict_per_product_median_ms": stats(plain)["median_ms"]}
    result["peak_memory_mib_of_this_process"] = peak_memory_mib()

    out = HERE / f"performance_results_{args.tag}.json"
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
