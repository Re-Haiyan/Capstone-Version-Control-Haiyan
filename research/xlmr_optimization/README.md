# XLM-R sentiment optimisation and validation

**Outcome: INSUFFICIENT EVIDENCE (`final_recommendation.md`). Nothing was deployed, pushed or merged; production (`2c6e056`) is untouched. No human annotation exists: the independent final test is prepared, frozen and unlabelled, so the 0.80 targets are NOT ACHIEVED and NOT YET VERIFIED.**

| Document | Content |
|---|---|
| `model_audit.md` | which model runs (verified on the VM), checkpoint provenance (the fine-tuned FP32 is missing), what could be reproduced |
| `dataset_audit.md` | inventory with hashes, class imbalance, duplicates, leakage, the "fresh" sets that are not fresh, the frozen sampling plan |
| `annotation_policy.md`, `annotation_execution_guide.md` | sentiment labelling policy **v1 (approved and frozen)** and instructions for two independent annotators |
| `baseline_results.md` | the deployed model re-scored (FiReCS 0.833 reproduced exactly) |
| `error_analysis.md` | error taxonomy with counts and likely causes |
| `experiment_log.md` | every run, settings, seeds; which experiments were skipped and why |
| `model_comparison.md` | existing against candidates, three evidence levels, seed variation |
| `onnx_benchmark.md` | pruning and int8 variants, latency, memory (this PC and the VM) |
| `conclusion_impact.md` | effect on product conclusions |
| `ai_assisted_annotation_methodology.md`, `protocol_amendment_ai_assisted_annotation.md` | the labels are AI-assisted (ChatGPT, panel-approved): methodology, limits, protocol amendment |
| `optimization_report.md`, `final_human_evaluation/` | head optimisation with cross-validation, frozen-test scoring against the AI-assisted reference, provenance, agreement, adjudication sheet, leakage audit, Chapter 4/5 drafts |
| `phase2/phase2_report.md` | Phase 2 (neutral recovery): denominators, S4 recommendation, neutral error analysis, strategy comparison, annotation batches for ChatGPT, held-out v2 protocol, blockers |
| `limitations.md`, `final_recommendation.md` | validity threats; ADOPT / DO NOT ADOPT / INSUFFICIENT EVIDENCE |
| `results/`, `predictions/`, `confusion_matrices/`, `runs/` | every metric, prediction, confusion matrix and training log behind the reports |

## Reproduce (training environment `D:/defaketive-train`, CPU; the app's own Python for steps marked *)

```
python research/xlmr_optimization/inventory.py                          # hashes, distributions, duplicates (restores FiReCS from git 5ea027e, checks its hashes)
python research/xlmr_optimization/inference.py onnx_int8 firecs_test market_test_v3 ...   # baselines (also cardiff_fp32, hf:<dir>)
python research/xlmr_optimization/metrics_x.py predictions/<tag>__<set>.csv ...  # metrics, confusion matrices
python research/xlmr_optimization/error_analysis.py predictions/onnx_int8__market_test_v3.csv
python research/xlmr_optimization/splits.py                             # fixed validation splits
python research/xlmr_optimization/finetune.py --name c1_mix_ce_s1 --mix firecs+market --loss ce --epochs 2 --seed 1   (c2: --loss weighted; d1: --market-repeat 2)
python research/xlmr_optimization/calibrate.py <tag>                    # temperature and decision rule fitted on validation only
python research/xlmr_optimization/paired_diff.py <candidate> onnx_int8 market_test_v3 firecs_test
python research/xlmr_optimization/prune_vocab.py <checkpoint> <out>; export_onnx.py <checkpoint> <out>; onnx_benchmark.py <tag>=<onnx>|<tokenizer>
python research/xlmr_optimization/conclusion_impact.py labels hf:<dir> <name>;  *conclusion_impact.py impact <name>
*python research/xlmr_optimization/build_annotation_sheets.py <copy of the production database>    # the frozen sheets (already built)
```

Checkpoints and ONNX artifacts are in `D:/defaketive-train/xlmr/` (outside the repository). Tests: `tests/test_sentiment_agreement.py` (the annotation tooling, on synthetic fixtures that are not annotations).
