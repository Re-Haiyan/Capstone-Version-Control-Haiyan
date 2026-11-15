# Candidate comparison: neutral-focused strategies (development data only)

Source: `results/neutral_strategies.json` (`neutral_strategies.py`); per-class tables `strategy_per_class_report.csv`, confusion matrices `strategy_confusion_matrices.csv`. Features: the shipped encoder's 768-d embedding with a logistic head. Training rows 16,575 (FiReCS 7,340, marketplace team labels 3,134, AI-pool 6,101); **development validation** (separate, never trained on in that comparison): 495 marketplace-team rows of 36 held-out products and 677 AI-pool rows of 10% of the annotation groups (FiReCS is training-only because its texts are inside the shipped encoder's own training). Grouped 5-fold cross-validation is reported for stability. **Not final-test results; the frozen test and its earlier scores were not touched; the shipped model is unchanged.**

**Labels are not yet policy-v1 consistent**, so every figure below measures agreement with mixed rubrics (see `neutral_error_analysis.md`); the selection here is provisional.

## Development validation, marketplace slice (495 rows; neutral 83)

| Strategy | Acc | Macro F1 | Neutral P | Neutral R | Neutral F1 | Neg F1 | Pos F1 | CV market macro F1 (neutral F1) |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| S0 baseline head (C 0.003; the locked `sentiment_head_v1`) | 0.756 | 0.647 | 0.44 | 0.23 | 0.30 | 0.81 | 0.83 | 0.609 (0.21) |
| S1 class-weighted | 0.743 | 0.662 | 0.39 | 0.34 | 0.36 | 0.80 | 0.82 | 0.629 (0.30) |
| **S2 balanced resampling** | 0.745 | **0.665** | 0.39 | 0.34 | 0.36 | 0.81 | 0.82 | 0.626 (0.30) |
| S3 neutral hard-example mining | 0.741 | 0.663 | 0.39 | 0.35 | 0.37 | 0.80 | 0.82 | **0.635 (0.33)** |
| S4 bias calibration (inner split) | 0.754 | 0.662 | 0.44 | 0.29 | 0.35 | 0.81 | 0.82 | 0.615 (0.23) |
| S5 weighted + mining + calibration | 0.741 | 0.650 | 0.39 | 0.29 | 0.33 | 0.80 | 0.82 | 0.627 (0.28) |

C 0.03 variants were no better (best 0.656, neutral F1 0.35). AI-pool slice (677 rows; only 15 neutral, so neutral numbers are not interpretable): macro F1 0.69 to 0.74, neutral recall up to 0.53 with precision 0.20.

Pooled cross-validation macro F1 (all 17,747 rows) is 0.84 to 0.86 for every strategy; it is dominated by FiReCS rows the encoder has already seen and must not be quoted as performance.

## Reading

* **No strategy comes near 0.80 for neutral.** The best neutral F1 on the marketplace validation slice is 0.37, with precision near 0.4 and recall near 0.35 (baseline 0.30 with recall 0.23). Class weighting, balanced resampling and hard-example mining each lift neutral recall by about 0.1 and macro F1 by about 0.015 to 0.02 at a small cost in neutral precision; bias calibration helps accuracy, not neutral. The differences among S1 to S4 are within noise of one split of 83 neutral rows.
* Positive and negative F1 (about 0.82 and 0.81 on marketplace) are not harmed by any strategy, but they are also below 0.85 here; the frozen-test positive and negative figures (0.89, 0.87) came from a different rubric and reference.
* **Logistic head versus full or parameter-efficient fine-tuning: not run.** A full fine-tune of this corpus is about 2 hours of CPU, and the neutral labels do not yet follow one definition; training on contradictory neutral definitions would measure the contradiction, not the model. The earlier seven full fine-tuning runs (`experiment_log.md`) reached marketplace-validation macro F1 0.66 to 0.69 with neutral F1 0.35 to 0.41 on team labels: the same ceiling as the head here.
* **Separate no-opinion handling: a rule is not supported by the data.** Among the training reviews that look like a feature list (regular expression), only 21% of the marketplace team labels are neutral (685 of 1,064 are positive) and 1% of the AI-pool labels (18 of 1,517). A "feature list means neutral" rule would be wrong against the existing training labels 79% to 99% of the time. A no-opinion detector can only be trained on rows labelled under policy v1.
* Mixed reviews are handled by excluding them from three-class training (policy v1) and are not a model output.

## Provisional selection

On the pre-declared metric (marketplace validation macro F1): **S2 balanced resampling (0.665)**, with S3 and S1 indistinguishable. This is **not** adopted: the gain over the locked head (0.647) is 0.018 on one split, the labels are inconsistent, and the neutral target is far away. The locked `sentiment_head_v1` and the shipped model are unchanged.
