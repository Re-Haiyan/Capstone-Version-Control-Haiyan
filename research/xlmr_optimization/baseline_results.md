# Baseline results (verified by re-running the deployed artifact)

Model: the shipped ONNX int8 file (SHA-256 `e04da4c2...`), scored one review at a time, raw text, maximum length 128, exactly as the app runs it (`inference.py onnx_int8`). Predictions are kept in `predictions/onnx_int8__*.csv` so every experiment compares on identical rows. Metrics: `results/metrics__onnx_int8__*.json`; confusion matrices: `confusion_matrices/`. Marketplace sets are scored on their high-confidence rows. **Marketplace labels are team-supplied and of unverified provenance; none of these is independent gold.** Intervals are product-grouped bootstrap (marketplace) or row bootstrap (FiReCS, which has no product field and is therefore optimistic).

## Dataset A: FiReCS test (3,147 reviews, published authors' labels)

| Metric | Deployed int8 | Public base checkpoint, zero-shot (FP32) |
|---|---:|---:|
| Accuracy | **0.833** | 0.682 |
| Macro F1 | **0.833** (0.820 to 0.847) | 0.639 |
| Weighted F1 / micro F1 | 0.832 / 0.833 | 0.634 / 0.682 |
| Negative: precision, recall, F1 | 0.87, 0.85, 0.86 | 0.65, 0.90, 0.76 |
| Neutral: precision, recall, F1 | 0.79, 0.73, 0.76 | 0.71, 0.24, 0.36 |
| Positive: precision, recall, F1 | 0.84, 0.93, 0.89 | 0.71, 0.93, 0.80 |
| Support (neg / neu / pos) | 1,027 / 1,087 / 1,033 | same |

Confusion matrix of the deployed model (rows true, columns predicted: negative, neutral, positive): negative 872, 142, 13; neutral 134, 789, 164; positive 1, 70, 962.
**The historical 0.833 is reproduced exactly.**

## Dataset B: historical marketplace evaluation, 846 reviews (`test_v3`; 82 products; **inspected during earlier development**)

| Metric | Deployed int8 | Public base, zero-shot |
|---|---:|---:|
| Accuracy | 0.655 | 0.713 |
| Macro F1 | **0.570** (0.527 to 0.618) | 0.637 (0.591 to 0.676) |
| Negative: precision, recall, F1 | 0.83, 0.67, 0.74 | 0.76, 0.79, 0.77 |
| Neutral: precision, recall, F1 | 0.22, 0.16, **0.19** | 0.48, 0.26, 0.33 |
| Positive: precision, recall, F1 | 0.71, 0.87, 0.78 | 0.74, 0.88, 0.80 |
| Support | 240 / 191 / 415 | same |

Deployed confusion: negative 160, 61, 19; neutral 31, 31, 129; positive 2, 50, 363. Subgroups (deployed, heuristic language and the file's product groups; `results/metrics__onnx_int8__market_test_v3.json`): macro F1 English 0.586, Taglish 0.554, Filipino 0.477; by group: electronics 0.686 (77), beauty 0.647 (227), food 0.538 (158), home 0.500 (200), baby 0.586 (76), fashion 0.402 (61). Per marketplace: not separable (the file has no marketplace field).

## Dataset C: other team-supplied sets (unverified labels; not independent)

| Set (high-confidence rows) | Deployed macro F1 | Neutral F1 | Negative recall | Note |
|---|---:|---:|---:|---|
| `train_v3` (3,946) | 0.605 | 0.244 | 0.670 | development data of the rules, **not** of the sentiment model's fine-tuning (unknown) |
| `gold_labels_200` (150) | 0.836 | 0.737 | 0.810 | older file, labelled "gold" without provenance |
| `heldout_labels_100` (76) | 0.785 | 0.593 | 0.778 | older file |
| `fresh` (293) / `fresh2` (253) | 0.718 / 0.737 | 0.340 / 0.390 | 0.795 / 0.790 | **mostly present in `train_v3`**: not independent |
| the two older files together (226) | 0.822 | | | the same rows are 0.758 with the low-confidence ones (300) |

## Reconciliation with the historical table

| Historical row | This study | Reason for any difference |
|---|---|---|
| Shipped int8: FiReCS 0.833 | 0.833 | identical |
| Shipped int8: marketplace 0.706 | not located (0.822 on 226 older rows, 0.758 on all 300, 0.570 on the 846) | the file behind 0.706 is not identifiable; marketplace files differ in size, label policy and neutral share |
| About 0.586 on 846 reviews | 0.570 raw model (0.586 in `research/evaluation_report.md`) | different row filter (that table kept rows that also carry a flag label) and the pipeline's output |
| Original 0.846 / 0.719, pruned 0.847 / 0.722, ONNX FP32 0.847 / 0.722 | **not reproducible: the fine-tuned FP32 checkpoint is missing** | `model_audit.md`; a re-fine-tune of the public base on FiReCS (`b_firecs_s1`) gives FiReCS test 0.844 |

## What the baseline shows

The deployed model is strong on FiReCS (balanced classes) and weak on the neutral class of the 846-row marketplace file (F1 0.19), where it also misses a third of negative reviews. Three things are true at once and must not be merged: a published benchmark, a historical team-labelled benchmark that is far harder, and older team-labelled files on which it looks good again. They cannot be ranked against each other without verified labels.
