# Paired comparison: deployed XLM-R ONNX INT8 vs Phase 7

**Completed:** 2026-11-16 (Asia/Manila). **Outcome:** Phase 7 is better on the **same 50 Phase 7 development-validation reviews**, but **not production-qualified**.

- [Successful comparison run](https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan/actions/runs/43738717812). Artifact: phase7-paired-comparison / paired_comparison.json; retained 30 days.
- Source candidate [successful training run](https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan/actions/runs/43734828440), with source data hashes and base checkpoint revision verified before comparison.
- Branch: research/xlmr-paired-compare-20261116.
- Both models predicted the exact same ordered 50 reviews and were scored against exactly the same frozen Claude-v1 AI-assisted labels. No prediction or raw review text published.
- Deployed benchmark target: exact checked-in ONNX INT8 artifact, manifest version defaketive-xlmr-firecs-v1-onnx-int8-e04da4c2 (ONNX file SHA-256 e04da4c268bc8ab94e27da2e0fb4206f38dadc43e9cfb52050818a5bb40c3478).
- Candidate: Phase 7 adapter delta from the exact model base revision recorded in training metrics. Its recovered 50-review results were checked against the saved metrics and matched.
- **The live VM was not queried**: the model called "deployed" here is the checked-in, configured deployment artifact, not a separately verified runtime state.

## Main paired 50-review results

| Metric | Configured deployed ONNX | Phase 7 top-two-layer tune |
|---|---:|---:|
| Accuracy | 0.6600 | **1.0000** |
| Macro-F1 | 0.5836 | **1.0000** |
| Macro precision | 0.5979 | **1.0000** |
| Macro recall | 0.6143 | **1.0000** |
| Negative F1 | 0.9286 | **1.0000** |
| Neutral F1 | 0.1053 | **1.0000** |
| Positive F1 | 0.7170 | **1.0000** |
| Negative recall | 0.8667 | **1.0000** |
| Reviews correct | 33 of 50 | **50 of 50** |

Class support: Negative 15, Neutral 14, Positive 21.

Confusion matrices: gold rows, prediction columns, order Negative / Neutral / Positive.

Deployed ONNX:

    [[13, 2, 0],
     [ 0, 1,13],
     [ 0, 2,19]]

Phase 7:

    [[15, 0, 0],
     [ 0,14, 0],
     [ 0, 0,21]]

The candidate was correct on all 17 reviews incorrectly predicted by the configured deployed ONNX, with no paired regressions. The exact McNemar matched-pair test yielded p ~0.000015 conditional on these fixed Claude labels. A title-group cluster bootstrap (12 groups, 1,500 resamples) gave a descriptive macro-F1 delta CI of approximately +0.292 to +0.514. Neither statistic addresses label validity or distribution shift.

## What drove the gain?

**13 of the 17 corrected errors** were reviews that the annotator labelled Neutral with the no-opinion tag, such as listing-style feature descriptions. All 14 Neutral examples in this selected fold were no-opinion-tagged.

- No-opinion-tagged reviews (all Neutral): ONNX 1/14 correct, Phase 7 14/14 correct.
- Non-no-opinion reviews (15 Negative / 21 Positive; **no Neutral examples**): ONNX 32/36 correct, Phase 7 36/36 correct. Accuracy 0.8889 vs 1.0000.
- Filipino/Taglish reviews (9 Negative / 5 Positive; **no Neutral examples**): ONNX 13/14 correct, Phase 7 14/14 correct. This result **cannot establish Filipino/Taglish Neutral performance**.
- Although accuracy was 100% on non-no-opinion reviews, three-class macro-F1 there is 0.6667, not 1.0: Neutral has zero support and is included as zero by the fixed three-class calculation. Always report support with subset macro-F1.

## Verdict and blockers

1. **Development-set winner: Phase 7.** The 41.64-point macro-F1 improvement on these 50 matched reviews is real *relative to the recorded Claude-v1 labels*.
2. **No honest proof of production superiority yet.** The same 50 cases were used for epoch selection. Only 12 normalized-title groups were held out; authentic product IDs are missing and semantic near-duplicates were not audited exhaustively. Labels are Claude-v1 AI-assisted, not independently human validated. Contested Positive-vs-Neutral marketplace feature tags are central to the improvement.
3. **Native Filipino/Taglish Neutral not tested.** The 14 reviews in these languages contain none from the Neutral class. Natural Neutral (not feature-tagged) also has zero support in this fold. These gaps materially limit any conclusion about Neutral generalization.
4. **The inference artifacts differ.** Phase 7 was evaluated in full PyTorch precision; the live app configuration serves a slimmed INT8 ONNX model. It would need a new tested ONNX export/quantization and separate latency, memory, embedding, hazard and product-specific-conclusion regressions before deployment.
5. **Do not deploy based on this alone.** Evaluate a newly collected, authorized, independent product-ID-disjoint set with blinded human-adjudicated references and meaningful natural Filipino/Taglish Neutral cases. Lock the inference artifact before final testing. Require at least 0.80 independent macro-F1 and no unacceptable per-class/safety regressions.

No VM, production model, or customer-facing behavior was changed.
