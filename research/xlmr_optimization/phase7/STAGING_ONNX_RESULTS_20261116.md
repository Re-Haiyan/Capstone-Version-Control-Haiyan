# Phase 7 research-only INT8 ONNX staging build: measured results

Source: GitHub Actions run 43774281914 (completed successfully, Nov 16, 2026, Philippine time).
Artifact: phase7-onnx-research-staging-only (7-day retention).
Branch: research/phase7-staging-export-20261116.
No customer data in artifact, no VM modifications, no production model replacement.

## Conversion correctness (same AI-assisted development set of 50 reviews)

- Locked Phase 7 PyTorch candidate: macro-F1 = 1.0000 on development validation only.
- New INT8 ONNX candidate: macro-F1 = 0.9811 on the **same** 50 development rows.
- 49 of 50 predictions match the source checkpoint.
- ONNX output tensors (logits and hidden_states) present, embedding width = 768.
- Artifact ONNX model size: 265.97 MiB, up from approximately 90.7 MiB for current deployed ONNX model.
- The model is explicitly marked qualified_for_integration=false, eligible_for_deployment=false.
- Source URL: https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan/actions/runs/43774281914

## Isolated CPU memory diagnostic (GitHub Ubuntu runner, NOT the actual Azure VM)

The exporter PyTorch process was fully exited before benchmarking. The separate
ONNX-only test used the ONNX Runtime single-thread configuration and 49 original
synthetic input strings (no marketplace reviews).

- Process RSS before model load: 62.70 MiB.
- Process RSS after ONNX session creation: **582.48 MiB**.
- Peak process RSS: **585.59 MiB**.
- Incremental process resident memory: **522.89 MiB**.
- Session load: 0.76 s.
- Synthetic-input median latency: 6.06 ms/review.
- Synthetic-input p95 latency: 7.55 ms/review.

**Blocking implication:** The candidate alone exceeded 512 MiB RSS on the test
runner. If the actual Azure VM has only 512 MiB physical RAM, it cannot safely
run this artifact in the current application; the web server, database, Caddy
and hazard checker also need memory. VM physical memory has not been measured
from this environment. A 1 GiB VM may also be uncomfortably tight depending
on available memory and production workload. Memory cannot be inferred from
the ONNX file size alone. A more aggressive model slimming/pruning study is
needed before considering the same-class free-tier host, or the VM must be
sized and benchmarked appropriately.

## Non-memory release blockers

The existing hazard_classifier_v6 manifest pins the original sentiment ONNX
SHA (e04da4c268bc8ab94e27da2e0fb4206f38dadc43e9cfb52050818a5bb40c3478).
It uses original model's sentiment predictions to gate defect detections; simply
swapping ONNX files would disable badge analysis or miscalibrate safety logic.
Do not change the expected hash to bypass this requirement.

No independent product-disjoint, human-reviewed 0.80 macro-F1 has been shown.
The earlier ChatGPT-labelled exploratory 47-case evaluation yielded Phase 7
macro-F1 0.9029 but the neutral class was mostly templated no-opinion reviews
and the only natural Filipino neutral was misclassified. This sample is
neither a production certification nor a statistically decisive comparison.

## Release decision

**DO NOT ACTIVATE PHASE 7 ON THE PRODUCTION VM.**

A model with an unresolved safety/defect-gating dependency and an unverified
memory budget should remain in research staging. Next steps are to perform
aggressive vocabulary pruning / quantization experiments, check real VM free
memory using the read-only checker, and rerun a complete hazard + sentiment +
product-conclusion evaluation on properly human-validated unseen products.

No production deployment, service restart, or database mutation occurred.
