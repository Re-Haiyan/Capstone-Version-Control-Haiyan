# Phase 5B: predeclared training-quality sensitivity

This research experiment tests whether Phase 5 annotation uncertainty affects a reproducible TEXT-ONLY classifier; it does not retrain XLM-RoBERTa or select a production model.

## Why
The original Phase 4 embedding files in research/xlmr_optimization/data/head and the private URL-to-product group mapping used by Phase 4 are not committed. The saved logistic head artifacts alone cannot reproduce the full Phase 4 optimization in GitHub Actions.

## Three comparisons
A: all original Claude-v1-labelled eligible development rows.
B: exclude the 71 reviews with Claude/GPT-6 disagreement, using the exact same unchanged Claude label on all remaining rows.
C: B plus training weight 0.25 for S4-uncertain tag-list reviews. Labels are never relabelled.

## Protocol
Word/character TF-IDF + balanced LinearSVC. Fit vocabulary separately inside each training fold. Five folds per seed, seeds 11, 12, 13. StratifiedGroupKFold uses NORMALIZED PRODUCT TITLE as a PROXY group; it is not verified product-ID disjoint. Rows with missing product titles and mixed/unclear labels are excluded and counted. All rows with any title group appearing in the 140 GPT-6 manually reviewed examples are excluded from all evaluations (but may appear in training). All three variants are tested against the exact same remaining out-of-fold Claude labels.

Metrics report macro F1, Neutral F1, precision/recall, confusion and supports on naturally sampled dev-pool reviews, non-tag-list rows, English, Taglish and Filipino separately. Their reliability depends on the existing one-annotator labels, and small subgroups are unstable.

## Limitations and decision
Do not claim independent performance or 0.80 target attainment from these measurements. These are development sensitivity scores for a separate lexical model, NOT new XLM-RoBERTa scores. The 71 disagreements are *unresolved*. Better results in this experiment would only justify a future XLM-R fine-tuning run with the missing authenticated group IDs/embeddings and a versioned S4 policy. If scores worsen or safety-relevant Negative recall falls, retain baseline.

Workflow: .github/workflows/phase5b-sensitivity.yml. Only aggregate JSON is uploaded; no raw reviews, deployed models, inference API, locked test, Phase 3 confirmation or held-out v2 is used.
