# Human evaluation: the final pack, instructions and status

## **STATUS: PENDING HUMAN EVALUATION.**

No human rating exists anywhere in this repository. Nothing was filled in by the system, by the developer, or by an AI; no annotator's answer was
guessed; no developer judgement is presented as ground truth. The pack contains **empty sheets**. The scoring command refuses to produce any number unless two
annotators have completed enough rows, and it computes only from what they wrote. Every figure labelled "developer-judged" elsewhere in this folder is
**not** a result of this evaluation.

## 1. The primary instrument: `human_eval_pack/` (built by `final_eval_pack.py make`)

| File | For | Contents |
|---|---|---|
| `INSTRUCTIONS.md` | annotators | task, order of the three sheets, rubric with examples of supported, partly supported and unsupported statements |
| `reviews.csv` | annotators | every review of every sampled product: stars and text only (no reviewer, no system output); 35 products |
| `card_sheet_A.csv`, `card_sheet_B.csv` | one annotator each | the annotator's OWN overall assessment, safety concern, authenticity concern. **No system output on it.** |
| `claims_sheet_A.csv`, `claims_sheet_B.csv` | one annotator each | 80 claims (aspect, direction, quotation, review number) to label correct / wrong aspect / wrong direction / not about the product / unclear |
| `words_sheet_A.csv`, `words_sheet_B.csv` | one annotator each | two anonymous texts per product (old and new wording, random order), rated 1 to 5 on the seven dimensions, plus unsupported-claim and safety-error flags |
| `key_private.csv` | **not for annotators** | which text was old, the system's card, the sampling stratum, language share, hazard counts |

**Order matters, and the instructions say so:** card sheet first (independent judgement), claims second, words last (it shows the system's assessment label, which is
identical under both texts and so does not reveal which text is new). Annotators work alone and must not open the key.

## 2. The sample (real products only; composition checked by `tests/test_final_eval_pack.py`)

| | |
|---|---|
| Products | **35** |
| Real non-electronics that were **not read** while the aspect rules were written | 16 (3 hair, 5 skin, 2 apparel, 4 appliance, 2 food/supplement) from the held-out half of the project's own scans, analysed by the app's own pipeline |
| Saved electronics | 19, stratified by the decision the system shows. These were used while the first rules were developed, so they are **not** untouched (reported separately via the key) |
| System assessments | Well reviewed 9, Some concerns 8, Mixed reviews 6, Not recommended 8, Too few reviews 4 (all five present) |
| Products with safety reports / authenticity reports | 24 / 23 (hard cases are in, not only easy ones) |
| Products with at least 25% Filipino or Taglish reviews | 28 |
| Claims | 80 (40 from the unread real products, 40 from electronics), one per product line, in random order |

Limits of this sample: footwear and motorcycle parts are absent because **no real review of them exists in the project** (`dataset_specification.md`); the 16
unread real products are all from the held-out half but a few of their *claims* were seen in earlier sampling rounds (`aspect_validation.md` §3); 35 products
is just above the minimum of 30 the scorer requires, enough for a first estimate and not for fine comparisons between categories.

## 3. What the scorer computes (only from real annotations)

`python research/product_specific_conclusions/final_eval_pack.py score <folder with the six filled sheets>`; it refuses with fewer than 30 products rated by both
annotators (card and words) or fewer than 50 claims.

| Output | Definition |
|---|---|
| Exact agreement, Cohen's kappa (card) | between the two annotators on the five assessments; with Wilson 95% intervals for the proportions |
| System versus each annotator, and where both annotators agree | exact agreement of the system's card with each annotator, and with the pair when they agree |
| Dangerous error | the system says "Well reviewed" while **both** annotators flag a serious safety concern |
| Factual claim precision | share of claims an annotator labels `correct`, for A, for B, and strict (both), each with a Wilson 95% interval; kappa on the five labels |
| Per-dimension scores (words) | mean for the old and new text on each of the seven dimensions (each product's value is the mean of the two annotators), paired difference with a 2,000-resample bootstrap 95% interval, exact agreement and quadratic-weighted kappa |
| Unsupported-claim rate | share of texts flagged by an annotator, old and new, with Wilson intervals |
| Safety-related error counts | share of texts flagged `safety_error`, old and new |
| Recommendation agreement | the `recommendation` dimension, plus the card comparison above |
| Preference | how often each version is preferred |

The arithmetic is tested on synthetic sheets inside a temporary folder (`tests/test_final_eval_pack.py`); those numbers are not evidence and are never written anywhere.

## 4. How to read results when they exist

- A gain in `faithful` and `relevant` without a loss in `safety`, `sentiment` or `factual`, and a claim precision whose **lower interval end** meets the bar written in advance
  (`dataset_specification.md` suggests 85%), is the result the feature is built for.
- A gain in `relevant` with a fall in `faithful`, a higher unsupported rate, or any dangerous error means the extraction is inventing structure or hiding a hazard: report it and fix the tables.
- Report electronics and non-electronics separately; do not pool across categories whose rules differ in maturity.
- The card comparison says nothing about whether the **candidate** decision policy is better: that needs the changed products judged (one saved product differs, so a fresh
  sample with neutral-heavy products would be needed; `recommendation_policy_comparison.md`).

## 5. Earlier instruments (kept)

`research/conclusion_eval/` (the card, 100 electronics, existing protocol) and `rating/` (words, the same 100 products, seven criteria, built earlier) remain valid and blind;
the final pack above supersedes them as the main evaluation because it adds real non-electronics products, the claim sheet and stratified hard cases. They can be run too.
`aspect_validation_sample.csv` is a further claim sample from the held-out real products (partly seen by the developer; prefer the pack's claim sheets).

## 6. Outstanding

Two independent annotators, each a few hours (35 products, 80 claims). Until then this requirement is **PENDING HUMAN EVALUATION** and no figure from it may be quoted.

## AI-assisted evaluation (approved by the panel and adviser; stated by the owner)

The research panel and adviser approved AI-assisted annotation, with ChatGPT as the primary AI-assisted annotator and the identifiers **Team Label 1** (sheet A) and **Team Label 2** (sheet B).
This repository's earlier study handled the same situation for sentiment labels (`research/xlmr_optimization/ai_assisted_annotation_methodology.md` on the `deployment` branch); the rules below follow it.

**Status: PENDING.** No sheet has been filled, by anyone or anything. Nothing in this folder is an annotation. Claude Code, which built the pack, did not label it, and no number below is a result.

### Rules
1. **AI-assisted labels are never called human annotation.** `final_eval_pack.py score` refuses to run without `provenance.json` next to the filled sheets (template: `human_eval_pack/provenance_template.json`). Each label set states its type (`ai_assisted` or `human`), annotator, exact model version, interface, dates, the file holding the complete prompts, and how much a person reviewed. Unknown values must be written as `not recorded`.
2. If either set is `ai_assisted`, the scorer's output says "AI-assisted reference standard (not independent human annotation)", sets `independent_human_evaluation_completed` to false, and carries the wording rule: report agreement with the AI-assisted reference, not human inter-annotator reliability or ground truth.
3. **The requirement for an independent human evaluation stays open** until two humans complete the sheets, or the panel formally amends the protocol in writing (attach the approval to a protocol amendment before the thesis calls the AI-assisted result sufficient).
4. Team Label 1 and Team Label 2 are likely to share one source and its biases, so their agreement is descriptive of consistency, not reliability. Separate sessions or separate people reviewing a sample of rows reduces but does not remove this.
5. Run the AI annotation honestly: give the annotator only `human_eval_pack/` (never `key_private.csv` or `features_key_private.csv`), the instructions, the sheet letter and the order (features, card, claims, words). Save the complete prompts and raw outputs. Do not edit labels afterwards to improve a score; a person's corrections go in new columns with the reviewer and date.

### What is measured, and where
| Question | Sheet | Output | Valid when |
|---|---|---|---|
| Is the feature identified correctly, and in the right direction? | claims | claim precision with a Wilson interval (`correct`, `wrong_aspect`, `wrong_direction`) | both sets have at least 50 labelled claims |
| Does the quotation support the conclusion? | claims | the same labels (`correct` means the quotation says it); the quotation is mechanically verified to be verbatim | same |
| Are features missed? Recall and F1 | features | micro precision, recall and F1 of (review, feature, direction) pairs against each set, against the pairs both list, and against either | both sets have at least 40 reviews listed |
| Are review counts accurate? | not annotated | counts are distinct review ids, reproduced mechanically (`evidence_verification.md`); annotators are not asked to count | always (mechanical) |
| Are unsupported claims avoided? | words | `unsupported` rate for the new and old text | at least 30 products complete in both |
| Are safety and authenticity reports qualified? | words, card | `safety` rating, `safety_error` rate, "well reviewed while both flag a serious safety concern" | same |
| Is the overall assessment right? | card | exact agreement and kappa, system versus each set | at least 30 products |

**F1.** F1 exists only for the features sheet, because only there can a miss be recorded. The 0.80 target is printed next to the result as a figure to report against. It is never a reason to change labels, the 150-review sample, or the extractor's cue tables, and the extractor must not be tuned on the reviews of this pack. Where the result is below 0.80, that is reported as it is. Claim precision, hazard F1 and sentiment F1 are separate figures and are never combined (`research_integrity.md`).

### Procedure
```
python research/product_specific_conclusions/final_eval_pack.py make      # already done; deterministic
# fill sheets A and B (copy to a working folder; never write into human_eval_pack/), add provenance.json
python research/product_specific_conclusions/final_eval_pack.py score <working folder>
```
The scoring arithmetic is tested on synthetic sheets in a temporary folder only (`tests/test_final_eval_pack.py`); those numbers are not evidence about the system.
