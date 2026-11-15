# ONNX compression and deployment benchmark

Candidate used: `c2_mix_weighted_s1` (the best-FiReCS candidate; `d1` has the identical architecture, so its size, speed and memory are the same, but **its accuracy under compression was not measured**). Artifacts are in `D:/defaketive-train/xlmr/c2_onnx` (outside the repository; nothing under `backend/` was changed). Scores: `results/metrics__c2_pruned_*.json`; performance: `results/onnx_benchmark.json`. Each artifact is scored one review at a time (the int8 activation scales depend on the batch). Compare scores with `c2` PyTorch FP32 (FiReCS test 0.840, benchmark 0.680, older 150 rows 0.747, older 76 rows 0.696).

## 1. Accuracy of each deployment artifact (as a distinct artifact)

| Artifact | Size | FiReCS test macro F1 | `test_v3` macro F1 (neutral F1, neg recall) | Older 150 | Older 76 | Label agreement with PyTorch FP32 (FiReCS / `test_v3`) |
|---|---:|---:|---|---:|---:|---|
| PyTorch FP32, full vocabulary (250,002 pieces) | 1,112 MB | 0.840 | 0.680 (0.443, 0.767) | 0.747 | 0.696 | n/a |
| PyTorch FP32, **vocabulary pruned** to 35,655 pieces (113 M parameters) | 454 MB | identical labels | identical labels (agreement 1.000 on `test_v3`, 150, 76 and validation) | | | 1.000 |
| ONNX FP32 (pruned) | 454 MB | 0.840 | 0.680 (0.443, 0.767) | 0.747 | 0.696 | **1.000 / 1.000** |
| ONNX int8 dynamic (pruned) | 114 MB | 0.835 | 0.662 (0.391, 0.746) | 0.691 | 0.696 | 0.944 / 0.937 |
| ONNX int8 **per-channel** (pruned) | 115 MB | 0.823 | 0.677 (0.442, 0.767) | 0.730 | 0.741 | not computed |
| ONNX int8 selective (last two layers and classifier FP32) | 157 MB | 0.833 | 0.660 (0.386, 0.742) | 0.691 | 0.709 | not computed |

Reading: pruning and the FP32 export lose nothing measurable. Plain int8 loses 0.005 on FiReCS and 0.018 on the benchmark and 0.056 on the older 150, mostly in the neutral class; per-channel int8 recovers the marketplace loss (-0.003 on the benchmark) but costs 0.017 on FiReCS; selective quantisation does not help and is larger. **There is no int8 variant that keeps every score; the choice is a trade-off to be made with verified labels.** (The shipped model was evaluated only as int8; its own FP32 was not available to measure its compression loss.)

## 2. Performance, one artifact per fresh process, ONNX Runtime with 1 intra-op thread (the production setting), 200 single reviews

| Artifact | Where | Cold start | Memory after load / peak | Latency median / p95 | Reviews per second |
|---|---|---:|---:|---:|---:|
| Deployed int8 (95.2 MB) | this PC (unloaded) | 0.53 s | 168 / 173 MB | 35.3 / 85.0 ms | 24.8 |
| Pruned int8 (114.3 MB) | this PC | 0.50 s | 199 / 204 MB | 33.5 / 81.4 ms | 25.8 |
| Pruned int8 per-channel (114.7 MB) | this PC | 0.57 s | 199 / 204 MB | 33.7 / 82.3 ms | 25.8 |
| Pruned FP32 (454 MB) | this PC | 0.94 s | 536 / 539 MB | 66.1 / 156.1 ms | 13.2 |
| Deployed int8 | **the production VM** (2 vCPU, `nice -n 19`, outside the service, two runs) | 0.37 s | 177 to 188 / 187 to 190 MB | 42.7 / 96.1 ms | 20.8 |
| Pruned int8 per-channel | **the production VM** (two runs) | 0.47 s | 261 / 262 MB | 41.0 / 92.5 ms | 21.5 |

The service was active throughout (load average 0.67 at the end of the runs, 2.2 GB of memory available); the temporary files on the VM were removed. Batch-size effects and concurrent-request stability were **not** measured: the app scores one review at a time, and a disruptive load test on the VM is outside this phase's rules.

## 3. Recommendation on the format

If a candidate were ever adopted, ship the **pruned int8** (either variant): the same speed as the shipped model (about 41 ms against 43 ms on the VM) and about 75 MB more memory in the model process (262 MB against 187 MB; the whole service is about 1.0 GB of 3.8 GB, so this fits comfortably). FP32 (454 MB, twice as slow, three times the memory) is not justified by the accuracy it recovers (0.003 to 0.02 macro F1 depending on the variant). Pruning needs the rebuilt tokenizer shipped with the model; it changes no label on the sets tested (a rare word outside the kept pieces would be segmented differently: not measured on production reviews).
