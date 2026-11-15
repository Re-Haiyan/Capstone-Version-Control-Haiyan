# Final evaluation report (AI-assisted reference standard)

**Status: SCORED against an AI-assisted reference; NOT a verified-ground-truth result.** The 400-review test is labelled by two AI-assisted sets (ChatGPT, approved by the panel and adviser). Scores below measure agreement with that annotator under policy v1. They are not accuracy against independently verified labels, and human adjudication of the 37 disagreements is still pending.

## Protocol followed

| Step | Status | Evidence |
|---|---|---|
| Provenance classified (AI-assisted, not independent human) | done | `annotation_provenance.md`, `../ai_assisted_annotation_methodology.md`, `../protocol_amendment_ai_assisted_annotation.md` |
| Sheets validated against the frozen blanks by review ID | done, 0 invalid rows | `validation_report.md` |
| Agreement computed descriptively, labelled not-independent | done | `inter_annotator_agreement.md` |
| Disagreements prepared for human adjudication | done, **decisions pending** | `adjudication_sheet.csv` (37 rows, final fields empty; originals untouched) |
| Leakage audit | done: no overlap with candidate training or selection data; about 100 frozen reviews had earlier AI or team labels; matching rows were removed from the optimisation corpus | `leakage_audit.md`, `../results/optimized_head_corpus.json` |
| Models locked before scoring | done | `model_selection_lock.json` (shipped model primary; `sentiment_head_v1` added before it was scored) |
| Each locked model scored once; frozen test chose nothing | done | `final_test_*.json/csv` |

## Results (reference = the 351 reviews on which both AI-assisted sets agree; sheet A and sheet B alone are in `final_test_metrics.json`)

| | Shipped model | `sentiment_head_v1` |
|---|---:|---:|
| Accuracy | 0.741 | 0.826 |
| Macro precision / recall | 0.640 / 0.552 | 0.694 / 0.647 |
| Macro F1 (95% product bootstrap) | 0.581 (0.535 to 0.625) | 0.653 (0.605 to 0.702) |
| Weighted F1 | 0.747 | 0.798 |
| F1 negative / neutral / positive | 0.736 / 0.139 / 0.870 | 0.874 / 0.194 / 0.892 |
| Support (negative / neutral / positive) | 77 / 45 / 229 | same |

Mixed (no dominant polarity: 6 to 7 reviews) and unclear (6 to 10) reviews are excluded from the three-class scores and reported separately, never counted as neutral. Delivery-only exclusion and prior-label exclusion are in `final_test_classification_report.csv`. Confusion matrices: `final_test_confusion_matrix.csv`.

**The 0.80 targets are not achieved**: macro precision, recall and F1, weighted F1 (0.798) and especially neutral F1 (0.19) stay below 0.80. Accuracy, negative F1 and positive F1 of the head exceed 0.80. Causes and legitimate next steps: `../optimization_report.md`.

## What must still happen before the result is called verified

1. Fill the annotation process record for each set (`../annotation/annotation_process_record_template.md`).
2. A named human reviews the 37 disagreements and a random sample of agreed rows (size to be confirmed by the adviser); report agreement between the human review and the AI-assisted labels.
3. Attach the written panel and adviser approval to the protocol amendment.

Production is unchanged (`2c6e056`); neither the head nor any candidate was deployed.
