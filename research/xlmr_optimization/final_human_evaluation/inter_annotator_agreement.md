# Agreement between Team Label 1 and Team Label 2 (descriptive; NOT independent human reliability)

**Read this first.** Both sets are **AI-assisted annotation sets** (ChatGPT is the approved primary annotator; `../ai_assisted_annotation_methodology.md`). They are not independent of each other: identical aspect text on all 50 mixed rows, templated rationales, files written one second apart. The figures below describe **how consistently the AI-assisted rubric application agrees with itself**. They are **not** inter-annotator reliability, do not show the labels are correct, and must not be cited as Cohen's kappa of human annotators. Computed with `sentiment_agreement.py score` on the untouched sheets, matched by review ID.

## Three-class agreement (positive, neutral, negative)

| Subset | Eligible reviews | Raw agreement | Cohen's kappa (95% interval) |
|---|---:|---:|---|
| All reviews | 383 | 0.916 | 0.842 (0.787 to 0.894) |
| Excluding delivery-only (either set tag; 33 eligible reviews removed) | 350 | 0.914 | 0.838 (0.787 to 0.889) |

Eligible = both sets give positive, neutral or negative; the 17 other reviews (mixed or unclear in either set) are excluded and reported below, **never counted as neutral**. Delivery-only rule when the sets differ: a review is excluded if either set tags it.

Per class (share of Team Label 1's answers that Team Label 2 repeats): negative 0.987 (77 of 78), neutral 0.918 (45 of 49), positive 0.895 (229 of 256). Confusion (rows Team Label 1, columns Team Label 2; `agreement_confusion_matrix.csv`): negative [77, 1, 0], neutral [0, 45, 4], positive [0, 27, 229]. **All the disagreement is one direction: 27 reviews Team Label 1 calls positive and Team Label 2 calls neutral** (plus 4 neutral to positive).

## Mixed, unclear and tags

* Mixed in `sentiment` (no dominant polarity): 7 in Team Label 1, 6 in Team Label 2; 6 jointly. The `mixed` tag appears on 50 reviews in both sets, identical on all 50 (kappa 1.000, which is itself a dependence signal); the dominant three-class label differs on 1 mixed review.
* Unclear: 6 and 10 (every review Team Label 1 marked unclear, Team Label 2 did too; Team Label 2 marked 4 more).
* Other tags: delivery-only 32 vs 33, raw agreement 0.998 (kappa 0.983); no-opinion 43 vs 59, raw agreement 0.935 (kappa 0.709).
* Low-confidence rows: 27 and 25. Disagreements: 37 of 400 reviews, 11 of them involving a low-confidence row in at least one set (`disagreement_cases.csv`). They stay visible; none was discarded.

## Where they disagree (37 reviews; `disagreement_cases.csv`)

positive versus neutral 31 (the dominant pattern: feature descriptions 13, generic praise 12, "sulit" value statements 6, delivery or seller 3, among them), unclear versus classified 4, negative versus neutral 1, mixed versus single polarity 1. The recurring cause is the policy rule for feature lists and generic praise (S4: a feature list without an opinion is neutral; generic praise is positive): one set applies S4 more strictly. No row was resolved in favour of either set; the human adjudication sheet is `adjudication_sheet.csv`.

## What may and may not be concluded

May: the AI-assisted rubric application is highly self-consistent (kappa 0.84) except for the neutral/positive boundary. May not: that the labels are valid, that two human annotators would agree this much, or that agreement establishes a reference standard. Independent human reliability would need two humans who did not see AI output (an optional extension, `../protocol_amendment_ai_assisted_annotation.md`).
