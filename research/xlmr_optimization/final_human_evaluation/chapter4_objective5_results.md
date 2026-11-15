# Chapter 4, Objective 5: sentiment evaluation of the XLM-RoBERTa classifier (draft status)

**This section is a status draft. Tables A and B, and the final-test row of Table C, are NOT YET VERIFIED, because no independently human-annotated, adjudicated reference exists.** Only results that were actually measured appear, each with its label status.

## Table A. Human annotator agreement

NOT YET VERIFIED. Two annotation sheets were returned, but their human origin could not be substantiated (`annotation_provenance.md`), so no agreement statistic is reported. Total eligible reviews, raw agreement, Cohen's kappa, interval and class findings: pending genuine independent sheets.

## Table B. Sentiment classification performance on the frozen final test (400 reviews)

NOT YET VERIFIED (not scored). Precision, recall, F1 and support for positive, neutral and negative, accuracy and macro F1: pending.

## Table C. Comparison with previous evaluations (all measured; the shipped model, ONNX int8)

| Evaluation | Rows scored | Labels | Accuracy | Macro F1 | Neutral F1 | Independence |
|---|---:|---|---:|---:|---:|---|
| FiReCS test | 3,147 | published, authors' labels | 0.833 | 0.833 | 0.756 | the shipped model was gated on this file |
| Older team-labelled marketplace rows | 150 | team-supplied, unverified | 0.847 | 0.836 | 0.737 | no provenance; older file |
| Historical marketplace benchmark | 846 | team-supplied, unverified | 0.655 | 0.570 | 0.186 | inspected during development |
| New frozen final test | 400 | not yet verified | NOT YET VERIFIED | NOT YET VERIFIED | NOT YET VERIFIED | prepared and frozen; about 100 reviews have earlier AI or team labels |

The rows are **not directly comparable**. FiReCS is balanced across three classes and labelled by its authors. The marketplace files are neutral-poor, differ in label policy (what counts as neutral), size and composition, and their labels have no verified provenance; the older 150 rows and the 846 rows give opposite impressions of the same model. The frozen final test uses policy v1 (mixed as a tag, delivery-only reporting) and has no verified labels yet.

## Table D. Error analysis

Measured on the historical benchmark only (`error_analysis.md`): of 292 disagreements with the labels in 846 reviews, 129 are neutral predicted as positive, 61 negative predicted as neutral, 50 positive as neutral, 31 neutral as negative, 19 negative as positive and 2 positive as negative. Mixed-opinion, short and Filipino reviews are the hardest. These are disagreements with unverified labels. Delivery-only and mixed-review limitations on the final test: not yet measured.

## Table E. Evaluation limitations

| Item | Status |
|---|---|
| Annotation provenance | not substantiated for the returned sheets |
| Inter-annotator agreement | not reported |
| Adjudication | not performed (A03 pending) |
| Dataset imbalance | FiReCS balanced; marketplace neutral 6% to 23%; the frozen test is stratified by star group |
| Product-category coverage | 375 of 400 frozen reviews are electronics (25 home or fashion); none from beauty, food or automotive |
| Potential leakage | none with candidate training or selection data; about 100 frozen reviews appear in earlier AI- or team-labelled files; the shipped model's own training data are undocumented |
| Confidence intervals | product-grouped bootstrap on marketplace sets; row bootstrap on FiReCS (optimistic) |
| Remaining generalisation limits | one electronics-heavy marketplace mix; a single shipped model; unverified labels in the historical sets |

## Interpretation (restricted to what is verified)

The shipped model reproduces its published FiReCS score (0.833). Against team-supplied marketplace labels its macro F1 is 0.84 on 150 older rows and 0.57 on 846 rows, with the neutral class weakest on the larger set; whether that reflects the model or the labels cannot be decided until verified labels exist. The objective of reporting an independent sentiment score on a frozen marketplace test is therefore not yet met.
