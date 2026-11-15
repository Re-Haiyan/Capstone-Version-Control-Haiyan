# Chapter 4, Objective 5: sentiment evaluation of the XLM-RoBERTa classifier

**Reference standard.** The 400-review frozen test is labelled by two AI-assisted annotation sets (ChatGPT, approved by the research panel and adviser). All scores below measure agreement with an AI-assisted reference under policy v1; they are not accuracy against independently verified ground truth. Human adjudication of the 37 disagreements is pending.

## Table A. Agreement between the two AI-assisted annotation sets (descriptive; not independent human reliability)

| Subset | Eligible reviews | Raw agreement | Cohen's kappa (95% CI) |
|---|---:|---:|---|
| Three-class, all | 383 | 0.916 | 0.842 (0.787 to 0.894) |
| Three-class, excluding delivery-only | 350 | 0.914 | 0.838 (0.787 to 0.889) |

Per class (Team Label 1's answers repeated by Team Label 2): negative 0.987, neutral 0.918, positive 0.895. All disagreement concentrates on positive versus neutral (31 of 37). Mixed: 7 and 6 reviews (6 joint); tags: delivery-only kappa 0.98, mixed 1.00 (identical text, a dependence signal), no-opinion 0.71; low-confidence rows 27 and 25. The two sets share a source and are not independent, so these figures describe the AI rubric's self-consistency only.

## Table B. Sentiment classification performance on the frozen test (reference: the 351 reviews where both sets agree)

| Model | Accuracy | Macro P | Macro R | Macro F1 (95% CI) | Weighted F1 | F1 neg | F1 neu | F1 pos |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| Shipped XLM-RoBERTa (ONNX int8), primary | 0.741 | 0.640 | 0.552 | 0.581 (0.535 to 0.625) | 0.747 | 0.736 | 0.139 | 0.870 |
| Sentiment head on the shipped encoder (`sentiment_head_v1`) | 0.826 | 0.694 | 0.647 | 0.653 (0.605 to 0.702) | 0.798 | 0.874 | 0.194 | 0.892 |

Support: negative 77, neutral 45, positive 229. Against either set alone the head scores accuracy 0.819 and 0.771, macro F1 0.641 and 0.623. Precision, recall and F1 per class for every reference and subset: `final_test_classification_report.csv`. Each model was scored once; the test chose nothing. **The 0.80 target is not met** for macro precision, recall, F1, weighted F1 or neutral F1; accuracy, negative F1 and positive F1 of the head exceed 0.80.

## Table C. Comparison with previous evaluations (shipped model)

| Evaluation | Rows | Labels | Accuracy | Macro F1 | Neutral F1 |
|---|---:|---|---:|---:|---:|
| FiReCS test | 3,147 | published, authors' labels | 0.833 | 0.833 | 0.756 |
| Older marketplace rows | 150 | team-supplied, no provenance | 0.847 | 0.836 | 0.737 |
| Historical benchmark | 846 | team-supplied, unverified | 0.655 | 0.570 | 0.186 |
| Frozen final test (agreed reference) | 351 | AI-assisted (ChatGPT) | 0.741 | 0.581 | 0.139 |

Not directly comparable: FiReCS is balanced and author-labelled; the marketplace sets are neutral-poor and differ in label policy, size and composition; the final test uses policy v1 and an AI-assisted reference, and about 100 of its reviews appeared in earlier AI or team labelled files. The final-test result is close to the historical 846-review benchmark (0.581 against 0.570), which supports a real neutral-class weakness rather than an artefact of one label file.

## Table D. Error analysis (final test; descriptive, nothing was changed in response)

Head, agreed reference (rows true, columns predicted negative, neutral, positive): negative [66, 5, 6]; neutral [3, 6, 36]; positive [5, 6, 218]. The dominant error is neutral reviews predicted positive (36 of 45): feature lists, no-opinion text and lukewarm remarks, which policy v1 labels neutral and the training sources mostly label positive. Negative recall rose from 0.60 (shipped) to 0.86 (head). Mixed reviews (6 to 7) are outside the three-class scores; delivery-only exclusion changes macro F1 by under 0.02.

## Table E. Evaluation limitations

| Item | Status |
|---|---|
| Annotation provenance | AI-assisted (ChatGPT); process record (model version, prompts, human review) still to be completed |
| Inter-annotator agreement | descriptive only; the two sets are not independent |
| Adjudication | 37 disagreements prepared; human decisions pending; original labels preserved |
| Reference standard | AI-assisted; verified only after human adjudication and a documented human check of agreed rows |
| Dataset imbalance | neutral 45 of 351 (13%); the test is stratified by star group |
| Product-category coverage | 375 of 400 reviews are electronics; none from beauty, food or automotive |
| Potential leakage | none with candidate training or selection data; about 100 reviews appeared in earlier AI- or team-labelled files; the shipped model's own training data are undocumented |
| Training corpus | AI-silver pool labels follow an older rubric (neutral 2%); FiReCS rows are texts the encoder has seen; pooled cross-validation 0.861 is inflated (marketplace team labels: 0.609) |
| Confidence intervals | product-grouped bootstrap |

## Interpretation (restricted to measured results)

Against an AI-assisted reference the shipped classifier reaches macro F1 0.58 and the optimised head 0.65; both are strong on positive and negative and weak on neutral (F1 0.14 and 0.19). The 0.80 target is not reached; the shortfall is concentrated in the neutral class and traces to a mismatch between the neutral definition of the final-test rubric and that of the training sources, which a rubric-consistent AI-labelled development set and human adjudication are expected to address.
