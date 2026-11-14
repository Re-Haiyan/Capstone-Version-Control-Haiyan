# Proposed fresh evaluation set

**Status: a proposal with a blank annotation sheet. No labels exist for it and none were invented.** Built by `research/fresh_eval.py`; counts in `research/results/fresh_eval_summary.json`.

## What is here

| File | Content |
|---|---|
| `fresh_eval_sheet.csv` | 980 reviews under anonymous ids (F0001 to F0980), columns `id, stars, product, review_text, sentiment, flags, confidence`, label columns empty. Roles are mixed and not shown. |
| `split_manifest.csv` | For each sheet id: role, product, group, stars, sampling weight, a short hash of the text. **Keep it away from the annotators.** |
| `active_learning_candidates_disjoint.csv` | The 200 active-learning candidates minus the ones that share a product with the test products (1 dropped). |

## The three roles (never merge them in a report)

| Role | Rows | What it is | What it may be used for |
|---|---:|---|---|
| `representative` | 712 | Up to 8 reviews drawn uniformly at random from each of 89 eligible products, with a sampling weight (the listing's star mix over the pool's star mix, times pool size over sample size) because the scanner reads a fixed number of reviews per star level | The only role that may support a headline figure, and only for **gadget** reviews of products the team scans |
| `enrichment` | 69 | Reviews with a hazard, fake or mismatch word from the same products | Estimating rare-flag behaviour and finding failure modes. **Not representative**; never quote its scores as marketplace performance |
| `al_candidate` | 199 | Informative unlabelled reviews picked by rule/model disagreement, rarity, uncertainty and chance (`research/active_learning.py`) | Training data for the next round. **Not a test.** Their products are disjoint from the test products |

## Disjointness and eligibility

* 387 products appear in at least one labelled, pooled or previously inspected file (training, the historical test, the labelling pools and the earlier fresh batches). Eligible products appear in none of them, have at least 30 usable reviews, and have a listing star distribution recorded.
* **All 89 eligible products are gadgets (electronics).** Every non-gadget product scanned so far has already been labelled or inspected, so **no independent non-gadget test can be built from the current pool.** The representative set therefore tests the system on unseen *gadgets* only.
* The star mix is heavily 5-star once weighted (94% of the weighted representative sample), as the marketplace is; unweighted, the sheet shows 579 of 712 as 5-star reviews because eight random reviews per product come mostly from the large 5-star level, while 1-star reviews are relatively common in the pool.

## Is it enough? (research/results/fresh_eval_sufficiency.json)

For a stable F1 on a flag, about 50 positives are wanted. Expected positives among the 712 representative reviews depend on how common each flag is among random reviews, which is **not known for gadgets**: the only gadget rows in the training file came from hazard-word slices (inflated), and the only random rows are non-gadget (lower).

| Flag | Lower bound: non-gadget random rows (prevalence, expected positives in 712) | Upper bound: enriched gadget rows (prevalence, expected positives in 712) |
|---|---|---|
| defect | 3.5%, about 25 | 12.2%, about 87 |
| counterfeit | 1.5%, about 11 | 5.8%, about 41 |
| safety | 0.5%, about 4 | 8.7%, about 62 |
| not as advertised | 5.5%, about 39 | 5.3%, about 38 |
| quality | 2.3%, about 16 | 3.7%, about 26 |
| delivery | 2.5%, about 18 | 4.5%, about 32 |

So the 712 reviews may give 50 or more positives for defect and not-as-advertised, but probably **not** for counterfeit, safety or quality. **Recommended first step:** have two annotators label a random pilot of 200 of the representative reviews, which gives a real prevalence estimate for gadgets, then decide how many more to label.

## What must be collected for a non-gadget final test

Reviews needed for 50 positives from a purely random sample (non-gadget prevalence from the training file): defect 1,445; not-as-advertised 910; quality 2,145; delivery 2,015; counterfeit 3,325; safety 9,500. A random test cannot power counterfeit and safety. Recommended design:

1. Scan new non-gadget products (about 60 to 80 across beauty, home, fashion, food, pets, baby, car, sports), none already in `evaluation/`.
2. Take a random sample of about 3,000 reviews with sampling weights as above (**phase 1**: no labels).
3. **Phase 2**: label every review the deployed rules flag (about a third) plus a random 10% of the unflagged ones (weight 10). Weighted recall and precision, with product-bootstrap intervals, then estimate performance without labelling all 3,000. About 1,250 labels instead of 3,000.
4. Two annotators on the labelled rows (use `research/agreement.py`, copying the sheet to A and B), adjudicate disagreements, and record who labelled what.
5. Freeze rules, thresholds and policy before opening the labels; score once.

## How to annotate

Use `research/agreement/GUIDE.md` (same rules: independent, no AI, policy v1 unless v2 is approved). For this set, give each annotator a copy of `fresh_eval_sheet.csv` and keep `split_manifest.csv` private.
