# Phase 7 — controlled XLM-RoBERTa research fine-tuning

**Status:** experimental model training only; **no deployment, release, VM changes, or independent 0.80 claim**.

The existing 3,400 policy-v1 marketplace development annotations are enough to run a research experiment, not to certify a production sentiment model. Source annotations are Claude AI-assisted and have not been independently human adjudicated. Two AI annotation passes disagreed on many Neutral/Positive template/tag cases; user-facing conclusions are especially sensitive to that boundary.

## Scope and safeguards

- Source: only the frozen dev-pool (400 rows) and Neutral-candidate (3,000 rows) Claude-labelled development sheets, verified field-by-field against their original review sheets. Only three sentiment classes, high-confidence labels and nonempty titles/text are eligible. Mixed, unclear, low-confidence and missing-title rows are excluded without changing any label.
- Model: Cardiff sentiment XLM-RoBERTa checkpoint, freeze the embedding and encoder except the final two layers; train classifier and final two layers for 2 epochs. Use review text only. Do not turn star ratings, listing titles, or product recommendations into training labels.
- Grouping: deterministic 5-fold stratified grouped split on the natural dev-pool subset; first fold is validation. Entire title groups held out from training, including candidate-pool rows with matching titles. Deduplicate exact normalized text; exclude conflicting duplicate labels. Actual marketplace product IDs are missing, so normalized product title is a proxy, not a verified independent product ID.
- Selection: best epoch by natural dev-pool macro-F1; report negative recall, Neutral F1, Filipino/Taglish and non-no-opinion subtotals. Report Cardiff base on the same validation rows. This selection split is development evidence only.
- No training, threshold tuning, or scoring on frozen final test, Phase 3 confirmation, or held-out v2. No private data or production DB contacted. No customer review texts or predictions uploaded as Actions artifacts or written to logs.
- Exported adapter_delta.safetensors contains only changed encoder and classifier tensors (not a standalone/deployable model); metrics.json records source hashes, group limits, subgroup metrics and release blocks. Rebuild needs the matching base checkpoint.
- CI training artifacts have short retention, are not committed to Git. Deployment gates remain blocked until an agreed S4 policy, authorized independent product-disjoint evaluation, human review of disputed labels, and independently labelled product conclusions.

## Execution

Audit data without downloading a model:

    python research/xlmr_optimization/phase7/train_xlmr_research.py --audit-only --output /tmp/phase7-audit

Train in a supported environment with access to the Cardiff checkpoint:

    python research/xlmr_optimization/phase7/train_xlmr_research.py --epochs 2 --seed 20261116 --batch 8 --grad-accum 2 --output /tmp/phase7-run

The GitHub Actions workflow phase7-xlmr-research.yml runs only on the dedicated research branch or manual dispatch. It never deploys to a VM or changes production code. A run failure is not a model result.

## Minimum decision criteria

A development improvement alone does not make the adapter production-eligible. Next evidence must include authentic product IDs, an agreed label policy, independently human-verified evaluation of Filipino and Taglish neutrals, stable safety/negative behavior, at least 0.80 macro-F1 on a fresh independent test, and independently labelled product conclusions. Report per-class precision, recall and F1, not just average accuracy.

Provenance: phase4/phase4_report.md, phase5/PHASE5B_RESULTS.md, phase6_annotation/PHASE6D_RESULTS.md, annotation_policy.md.
