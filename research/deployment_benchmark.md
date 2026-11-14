# Deployment benchmark

Measured with `research/bench_deploy.py` on the real pipeline (`registry.load_model`, product title as listing context) over 320 reviews from the labelled test file. The VM run used the code deployed there (commit `d74589a`; the research branch's rule changes are text-file and small-regex changes that do not alter model size or the ONNX path). The script ran from `/tmp`, so the deployed repository was not modified. Raw output: `research/results/bench_vm.json`, `research/results/bench_local.json`.

| Measure | Azure VM (2 vCPU, Linux, the production constraint) | Training PC (12 threads, Windows) |
|---|---|---|
| Cold start (load + first call) | 2.3 s | 7.8 s |
| RSS after load | 370 MB | not measured (no psutil on Windows) |
| Peak RSS | 377 MB (of 3.8 GB) | not measured |
| Single review, median | **62 ms** | 122 ms |
| Single review, 95th percentile | 133 ms | 289 ms |
| Batch of 200 reviews | 13.9 s (**14.4 reviews/s**) | 26.2 s (7.6 reviews/s) |
| Model files on disk | 100.3 MB (sentiment ONNX 95.2 MB; four joblib classifiers 4.5 MB) | same |

Interpretation (not over-claimed):

* A scan of 1,000 reviews (five star levels of 200) is about 70 seconds of analysis on the VM at the measured rate; one 200-review level is about 14 seconds. These are CPU-bound on the two cores and were measured with the site otherwise idle.
* The PC is slower than the VM in this benchmark, which is unexpected for a 12-thread machine. Likely causes (not investigated): thread over-subscription and Windows process start costs. It does not matter for production but means PC timings must not be used to judge VM capacity.
* **Per-component timing was not profiled**, so the source of the 62 ms is not attributed.

## Candidates considered for production

| Candidate | Size | Cost | Production compatible? | Decision |
|---|---|---|---|---|
| Sparse word+char logistic regression (per flag) | about 1 to 2 MB each | about 0.002 ms/review inference | Yes (scikit-learn is already on the VM, same version) | Not adopted: no reliable gain over the rules |
| e5-small embeddings + logistic regression | 118M-parameter encoder | 12.7 ms/text on 10 CPU threads in PyTorch | **No** as is: PyTorch is not on the VM and no ONNX export exists | Not adopted |
| Sentiment calibrator (TF-IDF + logistic regression over the sentiment probabilities and stars) | 1.47 MB | 2.4 ms/review (PC), joblib artifact, scikit-learn 1.9.0 (same as VM) | **Yes** | Built, opt-in, off by default (see `evaluation_report.md`) |
| Fine-tuned XLM-R base (previous session) | 278M parameters | seconds per review without quantization work | Needs an ONNX int8 export and was not better than the rules | Not adopted |

Not measured: CPU utilization over a full scan, thread-count sweeps on the VM, and the effect of quantizing a second transformer. None was needed because no heavier model was adopted.
