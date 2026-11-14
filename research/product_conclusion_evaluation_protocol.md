# Protocol: independently evaluating product conclusions

**Status: a protocol and blank sheets. No product-level accuracy exists and none is claimed.** The aggregation (inverse-probability star weights, Wilson lower bounds, the 30-review floor, the count-based safety alert) is unchanged.

## 1. Four different questions (do not mix them)

| Level | Question | How it is answered | Status |
|---|---|---|---|
| 1. Review-level flags | Does each flag match the reviewer's report? | Labelled reviews, per-flag precision, recall and F1 | Done, with the provenance caveat (`evaluation_report.md`) |
| 2. Rule correctness | Given the flagged counts, does the verdict function return what its rules say? | Deterministic: unit tests on the verdict and conclusion functions (`tests/test_conclusion.py`, `tests/test_regression_matrix.py`, the end-to-end scenarios in `evaluation_report.md`) | Done; this is *automatic* correctness and says nothing about whether a shopper would agree |
| 3. **Conclusion accuracy** | Does the card shown for a product match an independent judgement of what its reviews add up to? | **Two annotators judge products blind** (below) | **Not done: needs the annotation** |
| 4. Usefulness | Do shoppers decide better with the card? | A user study | Out of scope |

Only level 3 can say the conclusion is accurate. A card can be a perfect function of wrong counts, or of right counts with thresholds a human would not choose.

## 2. What the annotators judge

For each product the annotator reads what a shopper could read, **without any system output**: the product name, the listed rating, the listed star percentages, and about 40 reviews (a random sample of 30, plus up to 10 that a plain word list says may describe a problem, so that rare concerns can be found). They then choose one card and answer two yes/no questions.

| Card | Meaning for the annotator (independent of the system's thresholds) |
|---|---|
| **Well reviewed** | Reviews are overwhelmingly positive about the product; any problems are isolated and minor; nothing a buyer would want warned about |
| **Mixed reviews** | A real share of positive and of negative reviews, and no single serious recurring problem dominates |
| **Some concerns** | Mostly positive or mixed, but a specific problem recurs across several reviews (a defect, doubts that it is genuine, one credible hazard report) that a buyer should weigh |
| **Not recommended** | Mostly negative, or credible repeated reports of a hazard or of fake goods |
| **Too few reviews** | The reviews given are too few, too repetitive or too unclear to form a view |

* `serious_safety_concern` (yes / no / unsure): is there a credible report of fire, smoke, burns, shock, injury, choking, a skin reaction or spoiled goods caused by the product?
* `counterfeit_concern` (yes / no / unsure): do several reviews credibly say it is fake?
* `main_reason` (a few words), `confidence` (high / low).

The two yes/no questions are separate from the card on purpose: they let the evaluation tell "the system mis-weighed a real problem" from "the annotators disagreed about the product".

## 3. Procedure

1. `python research/conclusion_eval.py make 100` samples 100 saved products, **stratified by the card the system currently shows** (so the rare cards are covered, not only the common one), and writes `research/conclusion_eval/`: `product_sheet_A.csv`, `product_sheet_B.csv` (the same products under anonymous ids P001 to P100, different order), `product_reviews.csv` (the reviews, keyed by product id) and `manifest_private.csv` (the system's card per product; **keep away from the annotators**).
2. Two annotators judge independently (no talking, no AI, no looking at the app), each filling their own sheet. A product left blank is missing, not judged.
3. `python research/conclusion_eval.py score sheet_A_done.csv sheet_B_done.csv` (needs 30 or more products judged by both) reports annotator-vs-annotator exact agreement and quadratic-weighted kappa on the four-step scale (Well reviewed, Mixed, Some concerns, Not recommended); each annotator against the system (exact match, how many steps apart); how often the system matches when the two annotators agree; and the **dangerous error**: products both annotators found seriously unsafe that the system showed as Well reviewed or Mixed reviews.
4. Disagreements between the annotators are adjudicated by a third person who sees both answers; only then is a reference card fixed for each product. Report accuracy against that reference, never against a single annotator.

## 4. Metrics and how to read them

* **Accuracy** (exact match with the adjudicated card) and the **confusion matrix**. With stratified sampling, report per-card recall (of the products annotators call "Some concerns", how many the system shows as such) and weight by the true card frequencies if an overall figure is quoted.
* **Weighted kappa**, because the cards are ordered: one step apart (Mixed against Some concerns) is a smaller error than three steps (Well reviewed against Not recommended).
* **Asymmetric cost.** The dangerous error above is the one that matters most; report it separately with its count and a Wilson interval.
* **Sample size.** For an overall accuracy known to about plus or minus 10 points (95%), about 100 products; for weighted kappa around 0.6 with an interval of about plus or minus 0.15, 60 to 80. Wilson intervals on accuracy and a product-level bootstrap on kappa, never review-level resampling.
* Annotator agreement is the ceiling: if the two annotators agree on 70% of products, a system cannot be shown to be better than about 70% against either.

## 5. Biases to keep in mind

* The saved products are the ones the team scanned: not a random sample of the marketplace.
* The review sample the annotators read is a sample (about 40 of up to 1,000): a product's real star mix is shown as percentages, so annotators can see when the sample under-represents the 5-star majority.
* The word list that adds possible-problem reviews is plain keywords, not the system; it only helps annotators find rare concerns.

## 6. What is ready

`research/conclusion_eval.py` (sheets and scoring), `research/conclusion_eval/` (100 blank product sheets for two annotators, the reviews file, the private manifest), the scenario tests, and this protocol. The scoring refuses to run on fewer than 30 products judged by both annotators.
