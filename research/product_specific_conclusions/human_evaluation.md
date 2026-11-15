# Human evaluation: historical protocol and untouched blank pack

**2026-11-15 study-method note:** The owner has selected an **AI-only exploratory evaluation** and does not intend to recruit the two human annotators for this stage. The originally planned human study is **not being carried out**, not completed or replaced by fabricated human sheets. The separate GPT-6-assisted results and descriptive audit are in `ai_annotation/gpt6_qa_20261115/`; the human pack remains blank and the original human scorer remains available but must not be run on AI-labeled data as if people supplied it. All statements below describe the **historical human-only protocol**.

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
This repository's earlier study handled the same situation for sentiment labels (`research/xlmr_optimization/ai_assisted_annotation_methodology.md` on the `deployment` branch); the rules below follow it. ChatGPT remains the approved primary annotator, but **the labels that exist were produced by Claude, and are recorded as such**.

**Status: PARTLY DONE.** `human_eval_pack/` itself stays blank (the pack is never written to). One Claude-assisted annotation set, covering the features and claims sheets only, was made on 2026-11-15 and is reported in the last section, with its provenance in `ai_annotation/claude_session_1/`. The card and words sheets, a second annotation set, and the independent human evaluation are pending.

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

## AI-assisted evaluation results (Claude-assisted annotation, 2026-11-15; one annotation set)

**Source, stated exactly:** the labels were produced by **Claude (Claude Sonnet 5.5, via Claude Code)**, not by ChatGPT and not by a person. They are **Claude-assisted annotation**, one set ("Team Label 1"); no person reviewed them. Full record, interpretation rules and raw labels: `ai_annotation/claude_session_1/` (`annotation_process_record.md`, `provenance.json`, `raw/`, `scores.json`). The annotator is the assistant that built the system, so these results are **not independent**; they are reported as agreement with an AI-assisted reference and as nothing stronger. Independent human evaluation: **still pending**, because no written amendment replacing that requirement exists in the repository.

**Blindness:** the features sheet contains no system output and the answer keys were not opened before the labels were final. The claims sheet shows the system's claims by design.

### Feature extraction (150 random reviews of the 35 products; 96 have at least one reference feature)

| | Precision | Recall | F1 |
|---|---|---|---|
| All reviews (51 correct, 20 spurious, 128 missed) | **0.718** | **0.285** | **0.408** |
| Only the 93 reviews with no marketplace suggestion list (sensitivity to interpretation rule 1) | 0.783 | 0.297 | 0.431 |
| Positive statements | 0.739 | 0.337 | 0.463 |
| Negative statements | 0.680 | 0.218 | 0.330 |

**The 0.80 target is not met** for precision, recall or F1. Recall is the main shortfall: the extractor is deliberately conservative (it reads a clause only when a cue is present, and ignores lists, hypotheticals, comparisons and habit), so it reports a minority of what reviewers say. Of the 128 missed pairs, 95 were product features, 30 service (delivery, packaging, seller, freebies, arrival) and 3 authenticity. By profile (tiny samples, descriptive only): powerbank F1 0.44 (35 reviews), hair 0.45 (32), skin 0.24 (24), appliance 0.35 (15), earbuds 0.40 (14), apparel 0.54 (13), food 0.40 (13), general 0.67 (4). **Nothing was tuned, relabelled, removed or re-sampled in response**; the extractor version evaluated is `asp2` as committed. Reading these misses to improve the extractor would make this sample no longer unseen, so any improvement must be evaluated on fresh reviews.

What this means for the product: the conclusion text says "the reviews include reports of ..." with counts of distinct reviews and never claims to summarise everything, so low recall makes the explanation incomplete, not false; precision of the statements is the safety-relevant figure.

### Claims (80 claims: 40 real non-electronics, 40 electronics)

| Measure | Result | 95% Wilson interval |
|---|---|---|
| Claim correct (the quotation says this about the product, in this direction) | **63 of 80 (78.8%)** | 68.6 to 86.3% |
| Direction accuracy among claims about the right aspect | 63 of 67 (94.0%) | 85.6 to 97.7% |
| Quotation does not support the claim (wrong aspect 2, wrong direction 4, not about the product 1) | 7 of 80 (8.8%) | 4.3 to 17.0% |
| Unclear (wish, ambiguous wording, or a marketplace suggestion list) | 10 of 80 (12.5%) | 6.9 to 21.5% |

Claim correctness is a **precision-type** figure and is not an F1. Seven of the 80 quotations are marketplace suggestion lists; the rest of the unclear cases are wishes and ambiguous wording. Interval upper ends are above 0.80 and lower ends below it: this sample does not show the 0.80 target met or missed for claim correctness, only an estimate near it.

### Pending (not annotated by anyone)
| Question | Why pending |
|---|---|
| Overall assessment agreement (card sheet, 35 products) | needs all 5,946 reviews read; no sample substituted |
| Unsupported-statement rate, safety and authenticity wording errors, conclusion preference, overall usefulness (words sheet) | same; the rating of "factual" and "faithful" needs the full review set of each product |
| Agreement between annotation sets | only one set exists |
| Review evidence counts | not judged by annotators; verified mechanically (distinct review ids; `evidence_verification.md`) |
| Human-reviewed results | none exist; reported separately here when they do |


## Phase 3 evaluation sets and the card and words batches

**Phase 3 sets (separate from the locked pack above).** `phase3/data/` holds three new samples of real reviews, split by product: D1 (inspected development), D2 (development validation) and F (fresh final). The same Claude-assisted annotator labelled each set blind to the extractor (`phase3/annotated/provenance.json`; model Claude Sonnet 5.5, not ChatGPT, no human review). They are **AI-assisted reference labels, not independent human labels**. Results: `phase3/results.md`. Target 0.80: not met.

**Card and words sheets in product-level batches (prepared, not annotated).** These two sheets need every review of each product read (5,946 reviews for the 35 products). To make that manageable and honest:

```
python research/product_specific_conclusions/ai_annotation/batches.py make --size 5       # 7 batches: a reading packet and a blank return CSV each (generated, not committed)
# an annotator reads one card packet (no system output), fills batch_NN_card_return.csv; only afterwards the words packet for the same products
# put returned CSVs and a provenance.json (annotator, model version, interface, date, prompt file, human review) in a folder
python research/product_specific_conclusions/ai_annotation/batches.py merge <returned> --out <working folder>
python research/product_specific_conclusions/final_eval_pack.py score <working folder>   # single_annotation_set provenance
```
`merge` refuses without provenance, refuses a words row whose card row is missing, refuses any changed pre-filled column or out-of-range value, and leaves an untouched row blank. Whoever annotates (a person, ChatGPT, or Claude) is named in the provenance; AI-assisted and human-reviewed results are scored from separate folders and reported separately. **Status: no batch has been annotated; card, words, conclusion preference and agreement between sets remain pending.**
