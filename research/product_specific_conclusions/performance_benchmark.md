# Performance benchmark

Every number comes from `benchmark.py` (results in `performance_results_*.json`; rerun to reproduce). **No isolated staging environment
matching production exists in this environment**, so **no staging benchmark was performed** and none of these figures should be quoted as one.
What was measured where is in §1.

## 1. What was measured, and where

| Measurement | Where | Status |
|---|---|---|
| Latency, memory, CPU, scaling, simultaneous readers | this Windows PC (12 logical CPUs), Python 3.11.9 | measured (`performance_results_local.json`) |
| The same, in the **VM's runtime** (Python 3.12, NumPy 2.4.6, scikit-learn 1.9.0, joblib 1.5.3, onnxruntime 1.31.0, pinned to what the VM reports) limited to **2 logical CPUs** | this PC | **emulation**: the right runtime and CPU *count*, but this PC's faster cores and no other load. Not a staging benchmark (`performance_results_py312_2cpu_emulated.json`) |
| A pure-CPU regex micro-benchmark | the VM, read-only, lowest priority | measured, indicative only (§2) |
| The feature itself on the VM or on a staging copy | VM / staging | **not measured**: it would need the code on a machine of the VM's size; nothing was deployed, as instructed |
| Any load against production | production | **deliberately not done** |

Why there is no staging run: there is no Docker or WSL on this PC, no staging VM was provided, and running experimental code on the production VM is excluded.
**To produce a real staging benchmark**: provision a VM like production (2 vCPUs, 3.8 GB, Ubuntu with Python 3.12), check out this branch, install `backend/requirements.txt`,
and run `python research/product_specific_conclusions/benchmark.py --cpus 2 --tag staging`. It touches no database and no model, takes about five minutes, and writes
`performance_results_staging.json`. Compare it with the two files here.

The review-analysis pipeline (sentiment model and hazard checker) is untouched: `git diff` against `deployment` for `backend/sentiment-analysis`, `accounts.py` and `data_store.py`
is empty (recorded in the result files), and the plain verdict path costs the same as before (median about 0.3 ms per product). The conclusion's evidence is computed only when a
**single product page** is opened; list pages, cards and exports do not pay for it.

## 2. The VM, read-only

| | |
|---|---|
| Commit running | `2c6e056` (contains the product-category commit `b18898c`); clean working tree; service active |
| Machine | 2 vCPUs (AMD EPYC 7763), 3.8 GB RAM; Python 3.12.3 in its virtual environment |
| Micro-benchmark (120,000 regex searches, best of 3, `nice -n 19`) | **VM 0.139 s** versus **this PC 0.330 s** (Python 3.11.9) |

On this one kind of work the VM was about 2.4 times faster than this PC (a different Python version and CPU generation). It is a micro-benchmark on a machine that also serves visitors,
so it supports "the VM is unlikely to be much slower for this feature" and nothing more precise.

## 3. Results

### Cold start (a fresh Python process, median of 5)

| | local, Python 3.11 | Python 3.12, 2 CPUs (emulated) |
|---|---|---|
| Import the modules and compile the rules | 0.34 s | 0.39 s |
| Then read one product (150 reviews) | 13 ms | 19 ms |
| Heavy modules loaded (numpy, scikit-learn, joblib, onnxruntime) | none | none |

### The 182 saved products (21,878 reviews)

| | local median / p95 / max | Python 3.12, 2 CPUs: median / p95 / max |
|---|---|---|
| plain verdict, as before | 0.34 ms | 0.31 ms |
| with reasons, first read | **72 ms** / **256 ms** / 431 ms | **72 ms** / **249 ms** / 413 ms |
| with reasons, read again (cached) | 1.1 ms / 2.8 ms | 1.0 ms / 2.4 ms |

CPU time was 0.97 of wall time: single-threaded and CPU-bound, so limiting to 2 CPUs changes nothing here (as expected).

### Real non-electronics products (21 products, median 224 reviews) — first read, median

apparel 119 to 122 ms, appliance 91 to 123 ms, food 117 to 130 ms, hair 126 to 146 ms, skin 115 to 119 ms (ranges: the two runs).

### Large review sets (real reviews repeated with distinct text, so none is a duplicate)

| Reviews | Time (3.11 / 3.12) | Peak extra memory |
|---|---|---|
| 100 | 0.067 / 0.064 s | 87 / 81 KiB |
| 300 | 0.22 / 0.22 s | 151 / 143 KiB |
| 1,000 | 0.69 / 0.70 s | 280 / 265 KiB |
| 3,000 | 1.8 / 1.8 s | 656 / 622 KiB |

About 0.6 ms per review, linear. A review is read up to 5,000 characters; one 20,000-character review costs about 70 ms.

### Several readers at once (first reads, threads in one process)

| Simultaneous | Throughput | Median | p95 (3.11 / 3.12) |
|---|---|---|---|
| 1 | about 9 per s | 83 to 88 ms | 258 / 255 ms |
| 2 | about 9.5 per s | 155 to 160 ms | 481 / 498 ms |
| 4 | about 9 per s | 335 to 337 ms | 1.08 / 1.13 s |
| 8 | about 9 per s | 580 to 640 ms | 2.2 / 2.3 s |

Python threads in one process do not run Python code in parallel, so throughput stays near 9 uncached first reads per second and **latency grows with the queue**. This matters only for a
burst of *uncached* product pages (for example just after a restart); a cached page is about 1 ms. The production server's own worker model (the number of processes) decides how much
this applies; it was not changed or measured.

### Memory

Reading one product needs about 80 to 150 KiB extra at its peak (up to about 650 KiB for 3,000 reviews). The cache of all 182 saved products holds about 3.9 MiB (small results only,
not the reviews), limited to 256 products. The benchmark process's own peak was about 450 MiB, which is the saved pool and the analysed sample loaded for the test, not the feature.

### Payload

The product-detail response gains about 7.5 KB (median) and at most 17 KB of conclusion JSON, **only on the product page**.

## 4. What this does and does not show

- The feature is light: tens to low hundreds of milliseconds per product, no model loaded, no change to the analysis pipeline, cold start about half a second, the same on Python 3.12 as 3.11.
- It does **not** show the VM's latency with the live service and the sentiment models resident in the same process, nor behaviour under real traffic.
- The honest risk is **bursts of uncached first reads**. If it matters: persist the result when a product is analysed (not built; it needs a model-version bump and a database decision), or warm the cache after a restart.

## Rerun 2026-11-15 (local, emulated 2 CPUs; staging still pending)

`performance_results_local_rerun.json`: first read median 34.8 ms, p95 129.5 ms, max 208 ms (182 saved products); cached 0.58 ms median; real non-electronics 49 to 71 ms median per profile; plain verdict without reasons 0.19 ms; 8 simultaneous first reads
median 306 ms, p95 1,190 ms (one process, queueing); peak memory 448.6 MiB (benchmark process); cold start 162 ms import, no heavy library loaded. No errors. The earlier run (72 ms / 256 ms / 1 ms) and this one were taken on the same PC at different times
and differ by about 2x: treat both as "this PC under variable load". **Neither is a staging or VM measurement.** The staging procedure is unchanged: `benchmark.py --cpus 2 --tag staging` on a machine of production's size.

Staging procedure: `staging_procedure.md` (pending; no staging environment).
