# Model comparison: existing model against the experimental candidates

Sources: `results/metrics__*.json`, `results/tables.md` (all rows and intervals), `results/paired__*.json`, `results/calibration__*.json`, `results/onnx_benchmark.json`. **Three evidence levels are kept apart.** *Historical*: FiReCS test (published labels, used to gate the shipped model) and `test_v3` (team labels, inspected). *Development*: the marketplace and FiReCS validation splits used to select epochs and candidates. *Independent final test*: the frozen 400-review sheet, **unlabelled, so NOT YET VERIFIED** for every model. Marketplace labels are team-supplied and unverified.

## 1. Candidates

| Tag | What it is | Selected epoch | Marketplace validation macro F1 |
|---|---|---:|---:|
| `onnx_int8` (existing) | the shipped model | n/a | 0.619 |
| `cardiff_fp32` | the public base checkpoint, zero-shot | n/a | 0.635 |
| `b_firecs_s1` | public base fine-tuned on FiReCS only (reproduces the original recipe class) | 2 | 0.643 |
| `c1_mix_ce_s1/s2/s3` | FiReCS + marketplace, plain loss, 3 seeds | 2 / 1 / 1 | 0.659 / 0.669 / 0.676 |
| `c2_mix_weighted_s1` | FiReCS + marketplace, class-weighted loss | 2 | 0.665 |
| `d1_mix_ce_rep2_s1` | FiReCS + marketplace repeated twice per epoch | 1 | **0.685** |

By the selection rule fixed in advance (highest marketplace validation macro F1) the **best experimental model is `d1_mix_ce_rep2_s1`** (checkpoint `D:/defaketive-train/xlmr/d1_mix_ce_rep2_s1/best`, outside the repository). `c2_mix_weighted_s1` is the runner-up and keeps FiReCS better (0.840 against 0.823). The differences among `c1`, `c2` and `d1` are within seed noise (see 3).

## 2. The required comparison (existing model against `d1`)

| Measurement | Existing model | Best experimental model (`d1`) | Change | Evidence level |
|---|---:|---:|---:|---|
| FiReCS accuracy | 0.833 | 0.822 | -0.011 | historical (published labels) |
| FiReCS macro F1 | 0.833 | 0.823 | **-0.010** (paired 95% interval -0.022 to +0.000, row bootstrap) | historical |
| Marketplace macro F1, historical benchmark (`test_v3`, 846) | 0.570 | 0.684 | **+0.114** (paired product bootstrap +0.064 to +0.163) | historical, team labels, inspected |
| Marketplace macro F1, validation (495) | 0.619 | 0.685 | +0.066 | development (the selection set) |
| Marketplace macro F1, older 150 team-labelled rows | 0.836 | 0.727 | **-0.108** (-0.196 to -0.025) | historical, unverified |
| Negative F1 (`test_v3`) | 0.739 | 0.798 | +0.059 | historical |
| Neutral F1 (`test_v3`) | 0.186 | 0.431 | +0.245 | historical |
| Positive F1 (`test_v3`) | 0.784 | 0.823 | +0.039 | historical |
| Negative recall (`test_v3`) | 0.667 | 0.783 | +0.116 | historical |
| **Independent final test (400 reviews), any metric** | **NOT YET VERIFIED** | **NOT YET VERIFIED** | n/a | unlabelled |
| Inference latency, median (this PC, 1 thread) | 35.3 ms | 33.7 ms (same architecture and pruning, per-channel int8 export of `c2`) | -1.6 ms | measured on an artifact of the **`c2`** candidate, not of `d1` |
| Inference latency, median (the VM, 1 thread, outside the service) | 42.7 ms | 41.0 ms | -1.7 ms | same |
| Peak RAM of the model process (VM) | 187 to 190 MB | 262 MB | +72 MB | same |
| Model size on disk | 95.2 MB | 114.7 MB | +19.5 MB | same |

**Targets.** Primary (0.80 macro F1 and 0.80 per class on a fresh, independently human-labelled marketplace test): **not achieved and not verifiable**; the best number on any marketplace set the model has not been fitted to is 0.684 (historical benchmark), with neutral F1 0.43 (far below 0.80). Secondary (maintain or improve the original model's FiReCS macro F1): the original 0.846 could not be reproduced as an artifact; against the shipped int8 (0.833) the experimental models are +0.007 (`c2`), +0.004 (`c1`, seed 1), -0.010 (`d1`); `b_firecs_s1` reaches 0.844. **Met by `c2` and `c1` within noise, not met by `d1`.**

## 3. Run-to-run variation (the "lucky seed" check)

`c1` was run with three seeds. Marketplace validation macro F1 0.659, 0.669, 0.676 (spread 0.017); historical benchmark 0.669, 0.646, 0.668 (spread 0.023, neutral F1 0.333 to 0.424); FiReCS test 0.837, 0.834, 0.838; the older 150 rows 0.731, 0.735, 0.781. **A single-seed difference below about 0.02 is not evidence.** `c2` (0.680) and `d1` (0.684) on the benchmark sit within this spread of the `c1` mean (0.661); only the combination of three configurations all above the deployed model by 0.07 to 0.11 is a stable finding.

## 4. What actually improved, and what it cost

* Adding marketplace-labelled reviews (with FiReCS kept) raised the historical-benchmark macro F1 by about 0.10 to 0.11 for every configuration, neutral F1 from 0.19 to 0.33 to 0.44, and negative recall from 0.67 to 0.74 to 0.78. Fine-tuning on FiReCS alone moved it only to 0.611. The public base checkpoint, never fine-tuned, already scores 0.637 on the benchmark: **the FiReCS fine-tuning that makes the shipped model good on FiReCS (0.639 to 0.833) costs it marketplace neutral and negative-recall performance.**
* The same candidates **lose 0.09 to 0.11** on the older 150 team-labelled rows (paired intervals exclude zero), where the shipped model is at 0.836. The two label files define "neutral" differently; no model can be ranked "better on marketplace" until a verified policy and verified labels exist (`limitations.md` 2).
* Calibration (fitted on the validation split only): the shipped model is strongly over-confident on marketplace data (best temperature 3.0, expected calibration error 0.28 on the benchmark, 0.07 after scaling); the candidates are far better calibrated (ECE 0.10 to 0.13, temperature 1.65). Temperature scaling does not change a label. A neutral-bias decision rule (+0.9 to +1.2 on the neutral log-probability) raised benchmark macro F1 to 0.686 (`c2`) and 0.693 (`c1`) and neutral F1 to 0.50, **but lowered negative recall from 0.767 to 0.717 (`c2`) and from 0.775 to 0.713 (`c1`)**, which the brief singles out as the error to avoid: not adopted.

## 5. Provisional status

The numbers above are measured and reproducible, but they say how well each model agrees with unverified labels. No candidate is shown to generalise better. See `final_recommendation.md`.
