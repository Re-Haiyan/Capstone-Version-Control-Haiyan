# Optimisation under the AI-assisted methodology: what was done, what was measured, why 0.80 was not reached

**Reference standard.** The frozen 400-review test is labelled by two **AI-assisted sets** (ChatGPT; `ai_assisted_annotation_methodology.md`). A score against it is agreement with the AI annotator under policy v1, **not** accuracy against independently verified ground truth, and it is described that way everywhere. The frozen test never entered training, validation, tuning, rubric revision or model selection; each locked model was scored once.

## 1. Rubric consistency (what was examined)

* Policy v1 (`annotation_policy.md`, frozen) is the rubric of the final-test labels. The 10,000-review pool was labelled earlier under an older guide in which `mixed` was a class and neutral was almost unused: **146 of 6,778 usable pool rows are neutral (2%)** against about 13 to 18% neutral in the final test. FiReCS neutral is a third of its data (and, per a dataset manifest not yet verified, may include mixed opinions); marketplace team labels have 18% neutral.
* The sources therefore apply **different definitions of neutral**. Policy v1 makes feature lists and "no opinion" reviews neutral; the training sources mostly call such text positive. This is the main inconsistency (positive versus neutral), and it is also where the two AI-assisted test sets disagree (31 of 37 disagreements).
* Mixed reviews: not three-class training rows (policy v1). Mixed and unclear pool rows (2,153) were excluded by that rule, and nothing else was dropped for difficulty.

## 2. What was optimised (training data only)

* Corpus (`results/optimized_head_corpus.json`): 17,747 rows = FiReCS train 7,340 + marketplace train_v3 deduplicated 3,629 + AI-pool rows 6,778 (positive, neutral, negative; high or medium confidence; the pool's own `test_candidate` split removed). 48 rows matching a frozen-test text exactly and 11 near duplicates were removed **before** any model saw them.
* Method: a logistic head on the shipped encoder's 768-d mean embedding (the production model, so deployment adds only a small head); standardised features; grid over features (embedding, embedding plus log-probabilities), C (0.003 to 0.3) and class weighting (none, balanced): 20 configurations, **stratified grouped 5-fold cross-validation** (groups: product, review, annotation group), selection by pooled out-of-fold macro F1 (`results/optimized_head_cv.json`).
* Chosen: embedding only, C 0.003, no class weighting (balanced weighting did not help). Artifact: `research/artifacts/sentiment_head_v1.joblib`, hash in the lock.
* Not done (and why): fine-tuning the encoder on the AI-labelled pool and grouped cross-validation of full XLM-R runs (about 1 hour of CPU per run; the earlier seven runs are in `experiment_log.md`); preprocessing changes (the encoder is trained on raw text; no experiment found a gain); hyper-parameters of the encoder; further class-balancing variants.

## 3. Cross-validation results (training data; do not read as test performance)

| Rows (out-of-fold) | Accuracy | Macro F1 | F1 neg / neu / pos |
|---|---:|---:|---|
| All 17,747 (head) | 0.889 | **0.861** | 0.923 / 0.737 / 0.922 |
| All, shipped model on the same rows | 0.842 | 0.811 | 0.869 / 0.652 / 0.912 |
| FiReCS (7,340), head / shipped | 0.918 / 0.918 | 0.918 / 0.918 | neutral 0.880 / 0.880 |
| Marketplace team labels (3,629), head / shipped | 0.734 / 0.708 | **0.609 / 0.607** | neutral 0.212 / 0.250 |
| AI pool (6,778), head / shipped | 0.942 / 0.832 | 0.711 / 0.646 | neutral 0.209 / 0.137 (146 neutral rows) |

**The pooled 0.861 is inflated and must not be quoted as performance.** The encoder was fine-tuned on FiReCS train, so the FiReCS rows (41% of the corpus) are texts it has seen (0.918 for both head and shipped model); the pool contributes almost no neutral rows. On the marketplace team labels, the only source resembling the test domain with neutral present, the head adds nothing (0.609 against 0.607).

## 4. Final-test results (one scoring per locked model; AI-assisted reference; full tables in `final_human_evaluation/final_test_*.csv`)

Reference = reviews on which both AI-assisted sets give the same three-class label (351 reviews: 77 negative, 45 neutral, 229 positive); sheet A (387) and sheet B (384) give the same picture (`final_test_metrics.json`).

| Metric | Target | Shipped model | Head `sentiment_head_v1` |
|---|---:|---:|---:|
| Accuracy | 0.80 | 0.741 | **0.826** (met on this reference) |
| Macro precision | 0.80 | 0.640 | 0.694 |
| Macro recall | 0.80 | 0.552 | 0.647 |
| Macro F1 | 0.80 | 0.581 (0.535 to 0.625) | **0.653** (0.605 to 0.702) |
| Weighted F1 | 0.80 | 0.747 | 0.798 |
| F1 negative | 0.80 | 0.736 | **0.874** (met) |
| F1 neutral | 0.80 | 0.139 | **0.194** |
| F1 positive | 0.80 | 0.870 | **0.892** (met) |
| Neutral precision / recall | | 0.12 / 0.16 | 0.35 / 0.13 |

On sheet A alone the head scores accuracy 0.819, macro F1 0.641; on sheet B alone 0.771 and 0.623. Excluding delivery-only reviews, or reviews present in earlier AI- or team-labelled files, changes macro F1 by at most 0.03 in either direction (`final_test_classification_report.csv`). Confusion matrices: head (agreed reference, rows true negative, neutral, positive): [66, 5, 6], [3, 6, 36], [5, 6, 218]; shipped: [46, 28, 3], [1, 7, 37], [1, 21, 207].

## 5. Targets: what is met and what is not

**Not met:** macro precision, macro recall, macro F1, weighted F1 (0.798 is just below), and above all **neutral F1 (0.19)**. Met by the head: accuracy, negative F1, positive F1. The 0.80 target for every metric is **not achieved**, and no number was manipulated to approach it.

## 6. Causes, from evidence

1. **Neutral recall collapses to 0.10 to 0.13**: 36 of 45 neutral reviews are predicted positive. The test's neutral reviews are mostly feature lists, "no opinion" text and lukewarm remarks (policy S3/S4); the training sources label that kind of text positive or have almost no neutral rows (pool 2%). It is a **rubric mismatch between training labels and the final-test rubric**, not a model-capacity limit that was demonstrated.
2. The head improves negative recall (0.60 to 0.86) because the added marketplace and pool data contain many marketplace complaints; the neutral class gains precision (0.12 to 0.35) but not recall.
3. The final reference is AI-assisted: part of the remaining gap may be AI-annotator choices (the two sets differ by 31 positive-versus-neutral calls), which only human adjudication can settle.
4. Small test: 45 neutral reviews; the neutral F1 interval is wide.

## 7. Legitimate next improvements (none fabricated or performed here)

1. Label the dev pool (400 reviews, different products) and a much larger development sample **with policy v1 by the same AI annotator, with the process recorded**, so that neutral (feature lists, no-opinion, lukewarm) is represented under the final-test rubric (target at least 1,500 neutral rows); never relabel the frozen test.
2. Re-run the grouped cross-validation on that corpus, then fine-tune the whole encoder (two to three seeds) and compare by out-of-fold macro F1 and neutral recall.
3. Handle FiReCS honestly in cross-validation (its texts are inside the shipped encoder's training); validate on held-out products only.
4. Human adjudication of the 37 disagreements and a random human check of agreed rows, so the reference can be called verified; the neutral boundary decision (S4) may need adviser attention because it is the least stable part of the rubric.
5. Re-score the frozen test only if the new model is locked in advance and the protocol allows another scoring (this one is already used for the two locked models).
