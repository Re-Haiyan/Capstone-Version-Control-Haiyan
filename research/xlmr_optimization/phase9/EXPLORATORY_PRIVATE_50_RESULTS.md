# Phase 9 — exploratory offline model comparison on 50 user-exported reviews

**Research-only. No VM changes, no production model replacement, no private review text committed.**

## Method

- Source: user-provided 2026-11-15 DeFaketive export with 72,647 reviews from 399 listings with reviews.
- Sample: 50 review texts from nine listings whose normalized titles had no match in six checked historical repository files; at most six reviews/listing. All nine product IDs and exact reuse against unavailable private datasets remain unverified.
- Blind labels: one GPT-6 assistant label pass under the locked project policy v1 **without viewing star ratings**; this is AI-assisted, **NOT independently human-validated gold**. Distribution: 28 positive, 14 negative, 5 neutral, 2 mixed, 1 unclear. Mixed/unclear excluded from the 47 three-class scores. 16/50 low-confidence.
- Offline deployed artifact: exact repository-checked `xlmr_firecs_v1` INT8 ONNX model, hash e04da4c268bc8ab94e27da2e0fb4206f38dadc43e9cfb52050818a5bb40c3478; tokenizer hash verified against the deployment manifest. **The live VM's running version was not queried.**
- Offline Phase 7: base checkpoint `cardiffnlp/twitter-xlm-roberta-base-sentiment` pinned revision `f2f1202b1bdeb07342385c3f807f9c07cd8f5cf8` plus saved Phase 7 encoder-last-two-layers-and-classifier delta. Exactly the same 50 review texts scored by both artifacts.
- Historical text screen: 0 normalized exact-text hash matches in eight checked repository sheets (5,566 rows); no proof of excluding unseen local corpora or semantic near-duplicates.
- Raw review texts, review IDs, labels and row-level model outputs exist in the private downloadable user package only, **not in GitHub**. Only this aggregate report has been committed.

## Paired metrics on 47 three-class cases

| Metric | Configured deployed ONNX | Phase 7 FP32 |
|---|---:|---:|
| Accuracy | 0.8085 | **0.9149** |
| Macro-F1 | 0.6469 | **0.9029** |
| Macro precision | 0.6894 | 0.9410 |
| Macro recall | 0.6262 | 0.8738 |
| Negative F1 | 0.8333 | 0.8889 |
| Neutral F1 | 0.2222 | 0.8889 |
| Positive F1 | 0.8852 | 0.9310 |
| Negative recall | 0.7143 | 0.8571 |
| Correct | 38 / 47 | **43 / 47** |

Reference supports: Negative 14, Neutral 5, Positive 28. Candidate fixes 6 configured-deployed errors and introduces 1 new error, with 3 errors shared; 37 correct for both. Two-sided exact McNemar matched-pair p=0.125. Group-bootstrap 95% macro-F1 delta CI [-0.1001,+0.3969] (nine listing-title groups, 1,000 resamples) includes zero. These are descriptive, statistically fragile, and dependent on disputed AI labels.

## Mandatory caveat on neutral

Four of the five Neutral examples are English template-style feature lists tagged no-opinion; Phase 7 recognized all four as Neutral while deployed ONNX predicted Positive. The **only natural/lukewarm Filipino Neutral** was correctly Neutral for deployed ONNX and incorrectly Positive for Phase 7. Thus Phase 7's Neutral gain is mostly **template recognition**, not evidence that its natural Filipino/Taglish Neutral sentiment is accurate.

The 'non_no_opinion' subgroup has only one Neutral reference (not reliable for ranking): deployed macro-F1 0.7269, Phase 7 macro-F1 0.6066. After removing delivery-only comments, n=43: deployed 0.6331, Phase 7 0.8948. On 34 high-confidence three-class examples, deployed 0.6046, Phase 7 0.9781, but only two Neutral references.

## Decision

Phase 7 performs better on this small diagnostic cohort, but **neither an independent ≥0.80 macro-F1 gate nor production safety is certified**. This AI-labelled sample must not replace a fresh product-ID-disjoint set with genuine human-blinded annotations. Check natural Filipino/Taglish Neutral cases, negative recall, ONNX export/runtime and hazard/product-specific-conclusion regressions before deploying.

Relevant original runs: [Phase 7 training](https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan/actions/runs/43734828440), [earlier 50-review development comparison](https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan/actions/runs/43738717812), [Phase 9 model-assets-only recovery](https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan/actions/runs/43744627842).
