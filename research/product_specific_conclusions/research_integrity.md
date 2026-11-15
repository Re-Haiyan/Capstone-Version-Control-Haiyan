# Research integrity: what each result is, and what it is not

This feature supports a capstone. The rule for every number is: **say what was measured, on what, by whom, how, when, and what it cannot show.**
Three different things are evaluated in this project. They use different measures and must never be combined into one figure.

## 1. The three evaluations

| | XLM-RoBERTa sentiment | Hazard checker | Product-specific conclusion |
|---|---|---|---|
| Question | Is each review's sentiment (positive, neutral, negative) labelled correctly? | Is each hazard flag (safety, defect, counterfeit, quality, not as described) right for each review or sentence? | Is what the card SAYS about a product true of its reviews, relevant, clear, safe in its handling of hazards, and is the recommendation appropriate? |
| Unit | a review | a review or sentence and a flag | a product's conclusion, and each claim in it |
| Measures | accuracy, per-class precision, recall, F1, macro F1 | per-category precision, recall, F1, macro F1 | factual correctness, evidence faithfulness, category relevance, sentiment consistency, safety handling, clarity, recommendation agreement; claim precision with a confidence interval; agreement between annotators |
| Status here | **not re-measured or changed** by this work | **not re-measured or changed**; thresholds and models untouched | automatic checks done; **independent human evaluation pending** |

**There is no combined F1 for the conclusion feature, and none may be made.** An F1 describes a classifier's labels; a conclusion is generated text.
The F1 scores of the other two components say nothing about whether the conclusion is faithful, and the conclusion's claim precision says nothing about the
models' F1.

## 2. What the software tests prove, and what they do not

| Evidence | What it proves | What it does not prove |
|---|---|---|
| 400 passing tests | the code does what the tests say, and the old behaviour (decisions, verdicts, saved reports) did not regress | that a conclusion is *true* of real reviews |
| 182 of 182 verdicts and decisions unchanged | the feature changes no verdict | that the verdicts are right (that is the hazard checker's and the policy's question) |
| 5,356 of 5,356 quotations verbatim, ids valid, counts reproducible | every claim is *traceable* to a review | that the aspect and direction are the right reading of the sentence |
| `quality_audit.py` clean | the text obeys rules about what it may say | that what it says is true |
| developer-judged claim correctness (80% first look, 89% after fixes, real non-electronics; 88/86/94% on electronics, earlier extractor) | the developer, who wrote the rules, found these shares correct | independent accuracy: one judge, the author, on data used to fix errors |

**A passing software test is not evidence of factual accuracy, and developer-judged precision is not human-validated precision.** Only the two-annotator
evaluation (`human_eval_pack/`) can supply the latter.

## 3. Register of every reported result

| Result | Source | Sample | Method | Date | Limitations |
|---|---|---|---|---|---|
| Verdict and decision unchanged | `tests/test_product_conclusion.py` vs `tests/fixtures/verdict_baseline_before_aspects.json` | 182 saved products (electronics) | exact comparison with a baseline taken before the change | re-run 2026-11-15 | electronics only |
| Quotations / ids verified | `evidence_verification.py` | 182 saved + 21 real non-electronics | mechanical | 2026-11-15 | does not judge correctness of the reading |
| Claim correctness, electronics (88, 86, 94 of 100) | `precision_check.md` | 3 random draws of 100 claims | one developer, by hand | 2026-11-13/14 | earlier extractor; superseded; same person who tuned the rules |
| Claim correctness, real non-electronics (56 of 70; 62 of 70) | `aspect_validation.md` | 70 + 70 random claims from the held-out half | one developer, by hand | 2026-11-14/15 | the second draw is after fixing the first; neither is independent; the held-out half was later read in part |
| Coverage per category | `aspect_validation.py` | the project's real scans | automatic | 2026-11-15 | coverage is not accuracy |
| Latency, memory | `benchmark.py` | saved + real products | measured | 2026-11-15 | this PC, not the VM or a staging copy |
| Policy comparison (1 of 182 would change) | `recommendation_policy_compare.py` | 182 saved products | automatic | 2026-11-15 | no independent labels, so it cannot say which policy is right |
| AI-assisted features and claims evaluation | `final_eval_pack.py score ai_annotation/claude_session_1` | 150 reviews, 80 claims | one pass by Claude Sonnet 5.5 (Claude-assisted, not ChatGPT, not human, no person reviewed) | 2026-11-15 | one set, annotator is the system's author, interpretation rules disclosed; features P 0.718, R 0.285, F1 0.408 (target 0.80 not met); claims 63 of 80 correct |
| Card, words, agreement, independent human evaluation | | **none yet** | | | **PENDING** (no written amendment replacing the independent-human requirement) |

## 4. Rules this project follows

1. No human rating is generated, guessed, filled in, or replaced with a model's. Empty sheets stay empty; the scorer refuses to run on fewer than 30 products (or 50 claims) rated by both annotators.
2. Developer judgements are labelled "developer-judged" wherever they appear and are never called ground truth.
3. Data used to write or fix rules is never used as the final test. The record of which data was read when is in `aspect_validation.md` §3 and `dataset_specification.md`.
4. No review text is invented or edited for an evaluation. Constructed sentences appear only in unit tests and are labelled.
5. A negative or uncomfortable result is reported (for example: the first extractor's 80% first-look precision on real reviews, two silent bugs, a candidate policy that weakened a hazard label).
6. The live recommendation policy and the hazard thresholds are unchanged and were not tuned to improve any figure here.
7. **AI-assisted labels are labelled as such, with the AI that actually did the work.** (ChatGPT is the approved primary annotator, but where Claude annotated, the record says Claude; no work is attributed to a tool that did not perform it.) The panel and adviser approved AI-assisted annotation (primary annotator ChatGPT; identifiers Team Label 1 and Team Label 2). Such labels are never described as human or independent; the scorer requires a provenance record and prints "AI-assisted reference standard (not independent human annotation)"; the independent-human requirement stays open until completed or formally amended. Labels, the evaluation sample and the extractor's thresholds are never changed to reach an F1 target (0.80 is reported against, not tuned toward). Agreement between two AI label sets measures consistency, not reliability.

## 5. Methods description for the thesis (no findings)

> **Product-specific conclusion generation.** For each analysed product, the system produces a short conclusion that states which product features reviewers praised or criticised,
> with the number of distinct reviews supporting each statement and the reviewers' own words. The overall assessment (one of five categories) is determined by the
> project's existing hazard verdict and sentiment shares and is not altered by this component. A rule-based extractor segments each review into clauses with the project's
> Taglish-aware segmenter and matches each clause against a table of cue phrases, written in English, Filipino and Taglish, for the features of the product's category (39
> categories grouped into ten profiles, plus general features common to all products). A cue under a negation is read as its opposite; clauses that express a hypothesis, a
> comparison, a habit, sarcasm, or the absence of use are excluded, as are lists of phrases the marketplace suggests to the buyer. A review counts once per feature and
> side. Features are described with wording that follows the number of supporting reviews (one, some, several, many), and the words "most" or "majority" are used only when a
> majority of the analysed sample supports the statement. Reports of safety hazards and of doubts about authenticity are produced by the existing hazard checker and are
> presented as unverified customer reports. Every statement can be traced to review identifiers and text positions; a mechanical check confirms that each quotation occurs
> verbatim in its review.
>
> **Evaluation design.** Three questions are evaluated separately: the correctness of review-level sentiment (accuracy and F1), the correctness of hazard flags (per-category
> precision, recall and F1), and the quality of the generated conclusion. The conclusion is evaluated by two independent annotators who read the reviews of each product before
> judging, blind to the system's output where it could bias them: (1) they assign an overall assessment of their own; (2) they label each extracted claim as correct, about a different
> feature, in the wrong direction, not about the product, or unclear; (3) they rate two anonymous versions of the conclusion text (the previous and the new wording, in random
> order) from 1 to 5 on factual correctness, faithfulness to the reviews, relevance, sentiment consistency, handling of safety and authenticity, clarity and appropriateness of the
> recommendation, and mark unsupported claims and safety errors. Agreement is reported as exact agreement and Cohen's kappa (quadratic-weighted for the ordinal ratings); claim precision
> with a Wilson 95% interval; rating differences with a paired bootstrap interval. Products were drawn from real marketplace reviews, stratified by assessment category and including
> hazard reports, authenticity complaints and Filipino and Taglish reviews; products used to develop the extraction rules are identified and reported separately.
>
> **Limitations to state.** The extractor's cue tables are hand-written and cover the product categories for which real reviews were available; two categories (footwear and motorcycle parts) had
> no real reviews and are experimental. Menu-tag and terse-list exclusion trades recall for precision. Reviews analysed are a star-stratified sample of at most 300 per product. The results of the
> annotation, when completed, apply to the sampled products and categories only.

(The evaluation paragraphs describe the design. They contain no results and none may be added until annotations exist.)
