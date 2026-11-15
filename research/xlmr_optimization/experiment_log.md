# Experiment log

Every run is reproducible with the scripts in this folder (`splits.py`, `finetune.py`, `inference.py`, `metrics_x.py`); run arguments, per-epoch validation results and timings are in `runs/*.json` and `runs/*.log`; every score is in `results/metrics__*.json`. Environment: CPU only (12 threads), Python in `D:/defaketive-train` (torch 2.15.0+cpu, transformers 5.23.0, scikit-learn 1.9.1, onnxruntime 1.32.0). Starting checkpoint for all fine-tuning: the public `cardiffnlp/twitter-xlm-roberta-base-sentiment` snapshot `48de035c...` (SHA-256 of `model.safetensors` `0c0d65e6a3ff...`, `results/inventory.json`). Fixed settings: maximum length 128, batch 16, AdamW with weight decay 0.01, 6% warm-up and linear decay, gradient clipping 1.0, word-embedding table frozen (as in the earlier flag-model runs: far faster, no accuracy claim is made about it), length-grouped batches, 2 epochs, the better epoch kept by **marketplace validation macro F1** (rule fixed before the runs). Splits (`data/splits.json`): FiReCS validation = 10% of FiReCS train (732 rows), marketplace validation = 36 held-out products of `train_v3` (495 rows); the marketplace training rows are the other 267 products (3,135 rows, deduplicated by product and text). `market_test_v3` (historical benchmark) and FiReCS test are never read during training or selection.

## Fine-tuning runs

| Run | mix / loss / lr / epochs / seed | rows | before: market val, FiReCS val (macro F1) | epoch results: market val macro F1 (neutral F1, neg recall) / FiReCS val | selected epoch | minutes |
|---|---|---:|---|---|---:|---:|
| b_firecs_s1 | firecs / ce / 2e-05 / 2 / 1 | 6608 | 0.635, 0.647 | e1: 0.625 (0.29, 0.71) / 0.823; e2: 0.643 (0.34, 0.68) / 0.856 | 2 | 31 |
| c1_mix_ce_s1 | firecs+market / ce / 2e-05 / 2 / 1 | 9743 | 0.635, 0.647 | e1: 0.618 (0.24, 0.77) / 0.835; e2: 0.659 (0.35, 0.79) / 0.847 | 2 | 53 |
| c1_mix_ce_s2 | firecs+market / ce / 2e-05 / 2 / 2 | 9743 | 0.635, 0.647 | e1: 0.669 (0.35, 0.81) / 0.846; e2: 0.663 (0.35, 0.80) / 0.847 | 1 | 43 |
| c1_mix_ce_s3 | firecs+market / ce / 2e-05 / 2 / 3 | 9743 | 0.635, 0.647 | e1: 0.676 (0.41, 0.77) / 0.858; e2: 0.661 (0.36, 0.78) / 0.850 | 1 | 49 |
| c2_mix_weighted_s1 | firecs+market / weighted / 2e-05 / 2 / 1 | 9743 | 0.635, 0.647 | e1: 0.637 (0.29, 0.77) / 0.841; e2: 0.665 (0.37, 0.79) / 0.849 | 2 | 58 |
| d1_mix_ce_rep2_s1 | firecs+market / ce / 2e-05 / 2 / 1, repeat 2 | 12878 | 0.635, 0.647 | e1: 0.685 (0.40, 0.81) / 0.837; e2: 0.675 (0.40, 0.81) / 0.842 | 1 | 73 |


Experiments and what was and was not run:

| Experiment | Status | Result |
|---|---|---|
| A. Existing checkpoint | Done | `baseline_results.md` (deployed int8 reproduced on FiReCS exactly; the FP32 fine-tuned original is missing) |
| B. Neutral-class optimisation | Done: class-weighted loss (`c2`), marketplace over-sampling (`d1`); balanced sampling and focal loss **not run** (the weighted and over-sampled runs already moved neutral F1 from 0.19 to 0.43 to 0.44 on the benchmark, and seed noise (0.65 to 0.67) is larger than the differences that further variants could show) | `model_comparison.md` |
| B'. Re-fine-tune on FiReCS only (`b_firecs_s1`) | Done | reproduces the original recipe class: FiReCS test macro F1 0.844 against the historical 0.846 |
| C. Marketplace fine-tuning from the public base checkpoint with FiReCS kept in the mixture (`c1`, `c2`, `d1`) | Done; **continuing from the missing fine-tuned checkpoint was impossible** | FiReCS test stays within -0.01 to +0.007 of the deployed model; benchmark macro F1 rises by 0.10 to 0.11 |
| D. Hyper-parameter search | **Minimal**: learning rate, epochs, dropout, weight decay, warm-up and sequence length were not varied (about 50 minutes per run on this CPU); the two variants that were varied are the loss weighting and the marketplace repeat; the C1 configuration has 3 seeds | seed spread of C1: market validation 0.659 / 0.669 / 0.676, benchmark 0.669 / 0.646 / 0.668 |
| E. Domain-adaptive pretraining | **Not run** (no established permission for a corpus, a CPU masked-language-model pass over about 100,000 reviews is many hours, and the bottleneck found is the labels, not the encoder) | n/a |
| F. Calibration and decision rule | Done (`calibrate.py`, `results/calibration__*.json`) | temperature scaling removes most of the over-confidence of the deployed model on marketplace data (ECE 0.28 to 0.07 on the benchmark) but never changes a label; a neutral-bias decision rule raises neutral F1 and lowers negative recall (see `model_comparison.md`). The existing recalibrator (`research/sentiment_calibration_review.md`) was not re-run. |
| G. ONNX optimisation | Done for the C2 candidate: vocabulary pruning, ONNX FP32, plain int8, per-channel int8, selective int8 | `onnx_benchmark.md` |
| Product conclusions | Done for C2 and D1 | `conclusion_impact.md` |

Not claimed anywhere: that any marketplace figure is accuracy (the labels are unverified), that a difference below about 0.02 macro F1 is real (seed noise), or that any result was measured on the frozen final test (it is unlabelled).
