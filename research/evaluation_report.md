# Evaluation report

## 0. Which numbers mean what

| Kind | Meaning | Used to choose things? |
|---|---|---|
| Training / fit | Rules tuned on these rows (their errors were read) | Yes, by construction. **Optimistic.** |
| Cross-validation (CV) | Product-grouped 5-fold on the training file, models only | Hyper-parameters and thresholds, on out-of-fold predictions. Slightly optimistic. |
| Development (validation slice) | 12% of training products (413 rows) never read for rule tuning | Fusion strategy selection (few positives per flag: noisy) |
| **Historical test** | 846 rows, 82 products, inspected during earlier development | **No.** Reported only. It is a historical benchmark, not an untouched test. |
| Fresh final test | A new product-disjoint set | **Does not exist yet.** Needed (section 6). |

## 1. Deployed rules, historical test (846 rows)

| Flag | Positives | TP | FP | FN | Precision | Recall (Wilson 95%) | F1 (product-bootstrap 95%) |
|---|---:|---:|---:|---:|---:|---|---|
| defect | 68 | 51 | 30 | 17 | 0.63 | 0.75 (0.64, 0.84) | 0.69 (0.60, 0.76) |
| counterfeit | 53 | 50 | 3 | 3 | 0.94 | 0.94 (0.85, 0.98) | 0.94 (0.86, 0.99) |
| safety | 16 | 12 | 17 | 4 | 0.41 | 0.75 (0.51, 0.90) | 0.53 (0.31, 0.67) |
| not as advertised | 60 | 43 | 17 | 17 | 0.72 | 0.72 (0.59, 0.82) | 0.72 (0.62, 0.81) |
| quality | 57 | 53 | 35 | 4 | 0.60 | 0.93 (0.83, 0.97) | 0.73 (0.42, 0.83) |

Macro F1 0.722, micro F1 0.740. Product counts behind the positives (test file): defect 34, counterfeit 19, safety 11, not-as-advertised 31, quality 13. The very wide quality interval comes from its 13 products; the safety interval from 16 positives.

**The tuned rules improved the earlier benchmark** (not-as-advertised 0.59 to 0.72, defect 0.67 to 0.68 to 0.69) but the 0.80 aspiration is reached only for counterfeit. Sentence-level tuning on training errors lifted defect from 0.67 to 0.74 on the rows it was tuned on, and only to 0.68 to 0.69 on the test: the difference is overfitting to what was read.

## 2. Where the rules do well and badly (historical test, F1 by product group)

| Group (rows) | defect | counterfeit | safety | not as advertised | quality |
|---|---|---|---|---|---|
| beauty/health (227) | 0.47 (13) | 0.96 (24) | 0.60 (4) | 0.56 (11) | n/a (0) |
| home/living (200) | 0.77 (32) | 0.87 (11) | 0.22 (2) | 0.72 (19) | 0.76 (26) |
| food/grocery (158) | 0.40 (2) | 1.00 (9) | 0.50 (2) | 0.80 (11) | 1.00 (3) |
| electronics (77) | 0.73 (13) | 0.93 (8) | 0.64 (8) | 0.80 (6) | 0.29 (2) |
| baby/kids/toys (76) | 0.50 (3) | 1.00 (1) | n/a (0) | 0.71 (7) | 0.00 (1) |
| fashion (61) | 0.75 (3) | n/a (0) | n/a (0) | 0.67 (4) | 0.89 (25) |
| pets (27), automotive (20) | support 0 to 2 per flag; not interpretable | | | | |

(support in brackets.) Cells with fewer than about 10 positives are not interpretable. The one group-level weakness with enough support is **defect on beauty/health** (0.47 on 13 positives): in these products defect labels are mostly leaks and damaged packs, which overlap with the delivery policy question.

## 3. Sentiment (all 4,792 labelled rows; the model was not trained on these labels)

| | Accuracy | Macro F1 (95%) | negative F1 | neutral F1 | positive F1 |
|---|---:|---|---:|---:|---:|
| Training rows (3,946) | 0.722 | 0.620 (0.605, 0.638) | 0.783 | **0.248** | 0.829 |
| Historical test (846) | 0.673 | 0.586 (0.548, 0.627) | 0.776 | **0.194** | 0.787 |

The figures of about 0.90 quoted for earlier sets were accuracy on mostly-positive data; on this complaint-heavy, balanced-by-flag data accuracy is 0.67 to 0.72 and **neutral is the failure**: 410 of 724 training reviews the team calls neutral are predicted positive. Reviews labelled neutral are mostly 5-star (507 of 724): they are reviews without a stated opinion, feature lists, and "ok lang". Accuracy by stars: 1-star 0.92, 2-star 0.83 to 0.87, 3-star 0.43 to 0.48, 4-star 0.29 to 0.54, 5-star 0.67 to 0.71. Delivery-only reviews: accuracy 0.55 on 101 training rows.

**Recalibration (`exp_sentiment.py`, opt-in module `sentiment_calibration.py`):** a logistic regression over the model's three probabilities, the stars and word+character TF-IDF of the text.

| | CV macro F1 | Historical test macro F1 | Neutral F1 (test) |
|---|---:|---:|---:|
| Deployed model | 0.605 | 0.570 | 0.19 |
| Probabilities + stars | 0.622 | 0.593 | 0.22 |
| **Probabilities + stars + text** | **0.718** | **0.717** | **0.49** |

The gain (+0.11 to +0.15 macro F1) is consistent between CV and the historical test, which was not used to select the method. It is **not wired into the app by default** because it changes the positive share that feeds the buying conclusion; the artifact (1.5 MB, 2.4 ms per review) is in `research/artifacts/` and is activated by an environment variable. It learns this team's definition of neutral and this complaint-heavy sample; before use it should be checked on a fresh sample.

## 4. Product-level conclusion reliability (Part 13)

Code review and end-to-end scenarios (the scenarios are in `tests/test_regression_matrix.py` and `tests/test_conclusion.py`):

* **Sampling.** The system already weights each star level back to the listing's star distribution (`analyze_reviews._stratum_weights`, inverse-probability weights); when the distribution is unavailable rates are unweighted and the coverage block says so. Rates use Wilson lower bounds, a 30-review minimum, absolute floors per flag and a count-based safety alert. The per-star sampling bias the brief worries about is therefore handled in the design; this round did not find a defect in it.
* **Scenarios run through the real pipeline:** 8 positive reviews -> insufficient evidence; 59 positive + 1 fire report -> "possible safety issue" (one severity-4 report: the alert needs two); 59 positive + 1 mild-warmth remark -> no warning signs; 40 positive + 6 fake reports -> possible counterfeit or defect; 40 positive + 3 defect reports -> no warning signs (below the floor); 30 negative quality-only reviews -> no warning signs from the verdict (the buying conclusion carries the negative sentiment).
* **Limits.** The verdict covers safety, counterfeit and defect only; quality complaints reach the user only through the sentiment-based conclusion, which inherits the neutral-class weakness above. The thresholds are fixed constants; no independently labelled product conclusions exist to validate them, so **product-conclusion accuracy cannot be reported** (blocker: needs human-labelled conclusions for a sample of products). Thresholds were not changed.

## 5. Calibration and thresholds

One threshold per flag from a 17-point grid (0.10 to 0.90 by 0.05), chosen on out-of-fold predictions. Stability (300 product-bootstrap resamples, `threshold_stability.py`): defect 0.40/0.45/0.45 (10th/median/90th percentile), counterfeit 0.20/0.20/0.25, safety 0.20/0.20/0.30, not-as-advertised 0.40/0.40/0.50, quality 0.40/0.50/0.50. The thresholds are stable for the sparse model. They are not used by the deployed rule layer, which has its own gates.

## 6. What is still needed for a valid final claim

1. **A fresh product-disjoint final test set** (new scan, labelled by two annotators, never used for tuning). `research/active_learning_candidates.csv` and the agreement sheets prepare this.
2. **Inter-annotator agreement** from two independent annotations (`research/agreement.py`); until then no label ceiling can be quoted.
3. **Independently labelled product conclusions** for conclusion accuracy.
4. Adjudication of the queue (`annotation_audit.md`, `suspected_label_errors.csv`) under an approved policy (`annotation_policy_proposal.md`).
