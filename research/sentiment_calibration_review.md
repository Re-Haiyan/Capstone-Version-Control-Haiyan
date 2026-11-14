# Sentiment calibration review (opt-in, off by default)

> **Label provenance caveat.** "Gold" sentiment below means the *team-supplied* sentiment labels of unverified provenance (`annotation_provenance.md`). The calibrator learns those labels' definition of neutral.

**Decision for the owner: do not activate in production yet.** It is a better *classifier of the team's labels*, but on real saved products it moves the buying conclusion for one product in four, mostly by turning "Well reviewed" into "Mixed reviews" without any rise in negative reviews. Kept disabled by default; a shadow mode now exists to watch it on live data.

## What it is

A logistic regression over the deployed model's three probabilities, the star rating and word + character TF-IDF of the text (`research/train_sentiment_calibrator.py`; 1.5 MB, 2.4 ms per review, scikit-learn 1.9.0 like the VM). Not wired into the pipeline unless `DEFAKETIVE_SENTIMENT_CALIBRATOR` names the artifact.

## 1. Is it shortcut learning on the stars? No (`research/sentiment_calibration_audit.py`)

Feature ablation, macro F1 (out-of-fold, product-grouped CV on 3,946 rows / historical test of 846 rows):

| Features | CV | Historical test | CV neutral F1 |
|---|---:|---:|---:|
| deployed model, as is | 0.605 | 0.570 | 0.244 |
| model probabilities only (re-fitted) | 0.605 | 0.569 | 0.219 |
| stars only | 0.564 | 0.539 | 0.169 |
| probabilities + stars | 0.622 | 0.593 | 0.254 |
| **text only** | 0.707 | 0.734 | 0.488 |
| probabilities + text | 0.707 | 0.720 | 0.459 |
| probabilities + stars + text (the calibrator) | 0.718 | 0.717 | 0.477 |

Text alone matches the full model; stars add about 0.01. The calibrator is in effect a text classifier trained on the team's labels, with the deployed model adding almost nothing. On the 425 training reviews whose stars contradict their sentiment (4 to 5 stars but negative, or 1 to 2 stars but positive) accuracy rises from 0.398 to 0.576, which a stars shortcut could not do.

## 2. Stability across product groups (out-of-fold macro F1, deployed to calibrated)

automotive/tools 0.586 to 0.711, baby/toys 0.651 to 0.687, beauty/health 0.630 to 0.730, electronics 0.605 to 0.690, fashion 0.597 to 0.679, home/living 0.607 to 0.703, pets 0.565 to 0.764, other 0.594 to 0.718, food 0.611 to 0.827 (53 rows), sports 0.478 to 0.671 (66 rows), office/media 0.457 to 0.499 (61 rows). The calibrator is better in every group; the groups with fewer than about 70 rows are not interpretable.

## 3. Delivery-only reviews

101 training reviews carry only a delivery complaint: deployed accuracy 0.554, calibrated 0.644; the team calls 20% of them positive and the calibrator 15% (the deployed model's share on these rows was not measured). Delivery-only reviews are better handled, not mishandled; neither model reads "positive about the product, negative about the courier" as two sentiments.

## 4. Effect on the positive and neutral shares

Labelled training rows, share negative / neutral / positive: team-supplied 0.305 / 0.183 / 0.511; deployed 0.246 / 0.156 / 0.599; calibrated 0.304 / 0.146 / 0.550. The deployed model over-states positive by 9 points and under-states negative by 6; the calibrator closes most of that.

## 5. Effect on product conclusions: shadow mode on 60 saved products (`research/shadow_sentiment.py`)

The real pipeline ran on 60 randomly chosen saved products (those with at least 60 written reviews; all 60 are gadgets, because the local database holds only gadgets, all weighted by the listing's star mix). The calibrated sentiment was computed beside the deployed one and the conclusion card was built twice. Verdict states (safety, counterfeit, defect) are untouched by sentiment, by construction.

| | Deployed | Calibrated |
|---|---:|---:|
| Mean positive share | 80.2% | 70.9% |
| Mean neutral ("uncertain") share | 11.7% | 20.4% |
| Mean negative share | 8.1% | 8.7% |
| Mean Wilson lower bound on positive | 0.697 | 0.596 |
| Cards: Well reviewed / Mixed / Some concerns / Not recommended | 25 / 4 / 22 / 9 | 14 / 15 / 22 / 9 |

**15 of 60 conclusions change: 13 become less favourable, 2 more.** The biggest move is 12 products from *Well reviewed* to *Mixed reviews*. Among the 15 that change, the negative share is 7.2% before and 9.4% after, while the neutral share doubles (11.9% to 23.1%). In other words these products do not gain negative reviews; they gain reviews the calibrator reads as *no stated opinion* (feature lists, "ok lang", generic 5-star text), exactly as the team's labels define neutral.

## 6. What this means

* The calibrator is more faithful to the team's labels, and it also exposes a design question the labels hide: **"Mixed reviews" now means "many reviews state no opinion", not "opinions disagree".** A shopper reading "Mixed reviews" would assume conflict.
* **Options for the owner, none of them taken:** (a) leave it off; (b) turn it on and also change the conclusion rule so that neutral reviews are left out of the positive-share denominator (positive among reviews that take a side); (c) rename or retire the neutral bucket in the conclusion. (b) and (c) are product decisions that need the conclusion protocol (`product_conclusion_evaluation_protocol.md`) to be judged.
* The local saved products are gadgets only; groups with many neutral feature-list reviews (beauty, home) are likely to move more and have not been shadow-tested on saved products.

## 7. The shadow mechanism

`DEFAKETIVE_SENTIMENT_CALIBRATOR` (path) with `DEFAKETIVE_SENTIMENT_CALIBRATOR_MODE` = `shadow` (default when a path is set) or `on`. In shadow mode every analysis gains `sentiment.calibrated` and every summary gains a `shadow_sentiment` block (counts, weighted shares, lower bound) beside the real fields; nothing a user sees changes. In `on` mode the calibrated label replaces the deployed one and the deployed label is kept as `sentiment.deployed_label`. A missing or broken artifact leaves everything as it was. Tests: `tests/test_sentiment_shadow.py`.
