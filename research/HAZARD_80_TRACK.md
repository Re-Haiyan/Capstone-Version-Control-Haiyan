# DeFaketive Hazard Checker — 80% improvement track

**Research-only. Not deployed. Target not yet demonstrated.** The production VM, frozen data and labels, model thresholds and verdict logic are unchanged.

## Target
Use review-level predictions for the five flags: defect, counterfeit, safety, not_as_described and quality. Require **macro F1 >= 0.80 and EACH category F1 >= 0.80**, safety recall >= 0.80, at least 20 real positive reference labels per category, and product-disjoint, rights-cleared independent evaluation. Do not call sentiment accuracy a Hazard Checker score.

## Existing historical reference (NOT the new score)

| Flag | Historical support | F1 |
| --- | ---: | ---: |
| Defect | 68 | 0.685 |
| Counterfeit | 53 | 0.943 |
| Safety | 16 | 0.533 |
| Not as described | 60 | 0.717 |
| Quality | 57 | 0.731 |

**Macro F1 0.722; micro F1 0.740**, 846 historical reviews across 82 products. Source: research/evaluation_report.md and research/results/evaluation_all.json. These are team-supplied silver labels of unverified provenance and the test was previously inspected. Never optimize against this test or call these numbers independent verification.

## Research changes

1. Scan every heat/spelling mention, not only the first. A negated first reference can no longer hide a subsequent real one.
2. Distinguish the reviewer's hot phone from the purchased charger, including an explicitly denied heat report on that charger.
3. Bump the safety rule revision so cached summaries can be invalidated on future approval.
4. Add synthetic regression cases and research-only Python 3.11/3.12 CI.
5. Add a fail-closed scoring tool to report metrics, support, rights, duplicate/old-product exact overlap, and declared label provenance. This tool does not train a model or edit labels.

These narrow engineering fixes are **not** evidence of 80% F1 until an actually separate evaluation is conducted.

## Run locally on new data

Create a NEW rights-cleared, product-disjoint reference CSV with header:
review_id,product_id,product_name,stars,review_text,true_flags,annotation_method,adjudicated,rights_confirmed

Use pipe-separated flags. annotation_method must state ai_assisted, team_silver, or human_adjudicated. Preserve source rights, annotator identity records, and adjudication separately, if available. Only accurately declare human work that occurred.

1. Generate ID-only predictions without uploading raw reviews: python research/hazard_predict.py --reference fresh_reference.csv --out fresh_predictions.csv --model learned
2. Score: python research/hazard_80_gate.py --reference fresh_reference.csv --predictions fresh_predictions.csv --exclude evaluation/annotated/train_v3.csv --exclude evaluation/annotated/test_v3.csv --out local_hazard_result.json

**Important:** The two exclusion files above are only an example minimum. Include every historical, training, and development data file in the exclusion union. Verify near-duplicate review similarity, ID aliases and product-family leakage separately. No CSV source field alone proves human annotation. An AI-only score is descriptive agreement, not independently verified human accuracy. Never upload customer review text to public CI artifacts.

Select rules/thresholds on train and V3; test the final frozen candidate only once on independent F2. Do not adjust labels, thresholds or split after inspecting the final result. Report per-label precision, recall, F1, support and product grouping.

## Priority for future evidence-driven work

Safety: reduce false alarms from heat/feature names and other devices while protecting fire, shock and injury recall. Defect: separate packaging from broken products and improve leakage/arrival damage. Not-as-described: require an actual claim mismatch. Quality: reduce false positives without sacrificing recall. Counterfeit: preserve already-strong precision and use allegation language, not authenticated-fake claims.

No production update until metric evidence, all regression tests, staging checks, rollback/off switch and explicit release approval.
