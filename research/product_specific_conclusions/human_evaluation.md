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
