# Phase 5: cross-provider AI annotation audit (2026-11-15)

## Decision

**Do not replace the original Claude labels automatically and do not deploy/retrain from this disagreement-enriched sample as though it were truth.** Independent second-AI annotation now exists and identifies a major unresolved **policy S4** problem. Further model optimization should wait for a versioned clarification and adjudication of clear cases. It is better to abstain from ambiguous samples than to manufacture stronger metrics.

## Sources and sequencing

- Frozen annotation policy: `research/xlmr_optimization/annotation_policy.md`, v1, unchanged.
- Original dev/candidate CSVs: 3,400 reviews, full text checked against AI-labelled files.
- Claude annotation: `annotation/ai_labelled/*_ai_v1.csv`, Claude Sonnet 5.5, 2026-11-15.
- Second AI pass: `phase5/gpt6_second_ai_labels_v1.csv`, ChatGPT GPT-6, 140 complete reviews. **Locked separately at commit `80b2ac33e5f14e16318cf8b4ebf671e3d17fdc40` BEFORE any per-ID Claude labels were fetched.** The independent-reader instructions, review selection limitations and exact AI provenance are in `phase5/gpt6_annotation_provenance.md`. These are two different AI annotations; they are *not* independent human labels.
- Comparison: `phase5/compare_second_ai.py` and GitHub Actions artifact `phase5-ai-agreement`. No model predictions or final test labels accessed. No original label modified.

## Results (deliberately difficult sample, N=140)

| | Claude | GPT-6 |
|---|---:|---:|
| Negative | 7 | 10 |
| Neutral | 85 | 16 |
| Positive | 48 | 110 |
| Mixed | 0 | 3 |
| Unclear | 0 | 1 |

Five-class exact agreement: **69/140 (49.29%)**; Cohen's kappa **0.22886**. Of the 71 disagreements, **63 are Claude Neutral versus GPT-6 Positive**, three Neutral versus GPT-6 Negative, three Neutral versus GPT-6 Mixed, one Claude Positive versus GPT-6 Negative, and one Claude Negative versus GPT-6 Unclear.

Three-class conditional agreement, excluding four pairs in which GPT-6 marked mixed/unclear: 69/136 (50.74%), kappa 0.230665. This conditional subset is *not* a three-class classifier performance estimate.

| Selected reason for annotation | N | Exact agreement |
|---|---:|---:|
| Potential unread text beyond character 170 | 30 | 0/30 |
| Neutral-looking marketplace tag lists | 30 | 5/30 |
| Positive-looking marketplace tag lists | 30 | 29/30 |
| Filipino/Taglish neutral-focused cases | 25 | 11/25 |
| Ordinary positive/negative opinion controls | 25 | 24/25 |

The sample is intentionally enriched for difficult cases and **cannot estimate general population agreement, error rate or test accuracy**. Kappa for small single-label subgroups is not a meaningful measure of correctness. One AI provider is not inherently right.

## Examples of high-priority review, not automatic fixes

- `N2431`: "mabagal po sya Hindi fast charger" is explicit negative product experience, despite the preceding feature list. Claude: Neutral; GPT-6: Negative.
- `N2968`: "Nag automatic off kasi yung right" suggests a functional earbud defect. Claude: Neutral; GPT-6: Negative.
- `N1462`: "napakaganda ng sound di siya masakit" expresses personal praise after tags. Claude: Neutral; GPT-6: Positive.
- `N0797`: "LEGIT AT ANG MURA ... GANDA SOUNDS" expresses praise after tags. Claude: Neutral; GPT-6: Positive.
- `N1163`: reports both poor battery endurance and good room sound. Claude: Neutral; GPT-6: Mixed.

These examples are candidate adjudication priorities, not a certified reference standard. They demonstrate why all review text, including the suffix after a template list, must be read. The original annotations are preserved for auditability.

## Research-integrity limitations

- These two AI passes were independently produced at the per-review level, but both may have common priors or biases. They are not independent human experts.
- The second pass had access to the *general category of difficult cases* by design. It did not see previous per-ID Claude labels before recording decisions.
- The S4 boundary is disputed: whether buyer-selected positive tags constitute the buyer's endorsement, and whether positive adjectives in a template are sufficiently attributable to the buyer. This cannot be decided from positive adjectives alone.
- The second pass used some low-confidence Positive readings where a marketplace-generated tag list may not actually reflect personal experience.
- Earlier Claude annotations were sometimes produced after only ~170 visible characters. The source-fidelity audit confirms all stored texts match full originals, **not** that they were all read completely by the first annotator.
- No human adjudicator, new held-out evaluation, or independent classifier F1 is claimed.
- A change in label policy requires a separate version; do not rewrite the v1 training references silently.

## Best-practice actions

1. Obtain the research team/adviser's explicit policy choice for buyer-selected marketplace tag lists; write **v2**, leave v1 intact.
2. Use a **two-axis annotation**: (A) expressed review-text polarity, and (B) evidence provenance (`verified_personal_use` / `buyer_selected_platform_tags` / `listing_like_or_unknown` / `delivery_only`). Unknown should never become claimed verified use. This proposal is not yet an approved policy.
3. Independently review all 71 disagreements, prioritizing clear after-tag personal experience and defect reports. Record an adjudicator identity and evidence, preserving both AI sources.
4. Check more randomly sampled reviews for calibration, because the 140-case sample is intentionally enriched for hard cases.
5. For **experimental training only**, compare excluding or downweighting disputed template-only Neutral rows; analyze Filipino/Taglish with actual examples. Do not relabel these as Positive by default. Use product-grouped, nested validation and report all per-class metrics.
6. Obtain an **authorized fresh, product-disjoint** held-out test to claim any 0.80 threshold. Final-test labels must be locked before scoring.
7. Run a complete 182-product hazard, sentiment and decision impact review before any release. No model or recommendation policy is deployed here.

## Artifacts

- Source integrity: `phase5/label_quality_audit.py` and GitHub Actions output `phase5-label-audit`.
- Second GPT-6 annotations: `phase5/gpt6_second_ai_labels_v1.csv` and provenance.
- Unmodified original Claude annotations: `annotation/ai_labelled/`.
- Descriptive agreement: GitHub Actions output `phase5-ai-agreement` with `agreement.json` and `disagreement_queue.csv`.
- Future policy: `phase5/S4_V2_PROPOSAL.md`, **draft only**.

No weights changed. No frozen test accessed. No production deployment.

## Training data uncertainty ablation (not a retest)

The development-only `phase5/training_ablation_manifest.py` generates three sample-weight columns: unchanged v1, exclude only the 71 cross-provider disputed items, and tentatively downweight all S4-ambiguous tag-shape rows to 0.25 while excluding disputed items. These are **candidate training views, not corrected annotations or new truth**. The GitHub Actions artifact records the effective class supports. Do not compare their F1 without independent product-grouped selection, and do not claim either alternative is better without experiments. No model training is performed by this script.
