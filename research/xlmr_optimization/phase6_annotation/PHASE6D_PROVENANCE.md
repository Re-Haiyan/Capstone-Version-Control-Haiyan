# Phase 6D: 200 GPT-6 annotations — full-text review provenance

**Date:** November 15, 2026 (Asia/Manila). **Annotator:** GPT-6 in ChatGPT. **Role: AI, not human.** This is a new *second-AI* development review, not independent human ground truth, not a corrected reference or a trained model.

## Preselection and locking
- The original 3,400-row development pool includes 400 dev and 3,000 neutral candidates. The random 200 IDs were precommitted at `9f0a4ad0ac5e5f22481ee38d77d5073dd3f87e7f`, using Python `random.Random(20261115).sample(sorted(all_3400_development_ids), 200)`.
- **Source read before labeling:** Original unlabeled `annotation/dev_pool_sheet.csv` and `annotation/neutral_candidate_pool.csv` for those IDs. For each case GPT-6 read full `review_text`, product title and language hint. Original Claude labels, stars, model predictions and prior GPT-6 label files were not fetched during the new 200-case labeling pass.
- Batches of 40 were committed separately before any comparison: `a42e10e`, `91b21fd`, `8c99947`, `fda7f2a`, `526f974`. The consolidated 200-row CSV is an exact concatenation of those locked batches.
- Existing conversation context may have exposed prior GPT-6/Claude opinions on individual cases even though those files were not opened during labeling. **13 of these 200 reviews were also in previously GPT-6-reviewed samples.** Therefore this is **NOT a strictly independent or blinded annotation evaluation**. Preserve this overlap as a stratification variable and show excluding it for sensitivity checks.

## Applied policy
Approved `annotation_policy.md` v1 S1–S4. Negative for actual defects or explicit dissatisfaction (including Filipino/Taglish); Neutral for pure specifications/no opinion or lukewarm `okay lang`; Positive for explicit praise and evaluative adjectives, including affirmative template-like phrases with **low confidence** where buyer authorship cannot be verified. Delivery-only reviews tagged separately; Mixed kept separate when no polarity dominates or tagged on a dominant label with two aspects. Gibberish or off-topic text marked Unclear when no product opinion can be decided. Full review endings were read; buyer hopes about future battery life do not become present defects.

**Policy caveat:** S4 says feature descriptions lacking opinions are Neutral, but the exact standing of buyer-selected positive descriptors is unresolved. My Positive-low judgments on promotional tag lists should **NOT** be interpreted as verified buyer sentiment. No automatic replacement of Claude Neutral labels is justified by this pass.

## Research integrity and exclusions
- Existing 3,400 Claude labels, 140 previous GPT-6 labels, 54 previous GPT-6 labels, locked evaluations, confirmation data and all model weights remain unchanged.
- 200 selected reviews are **random within a deliberately assembled Neutral-candidate-enriched development pool**, not representative of ordinary Shopee/Lazada marketplace prevalence.
- This is a reviewer agreement and annotation consistency study, not a model performance estimate. No 0.80 claim, no retraining, no deployment, no human gold label claim.
- A separate source-locked comparison script computes descriptive agreement after the full second labels have been committed. Disagreements remain `proposed_not_adjudicated`.
