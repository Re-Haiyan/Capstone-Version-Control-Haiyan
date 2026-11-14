# Conclusion policy review: opinion, no opinion and "Mixed reviews"

> **Evidence class.** Sentiment labels are *team-supplied labels of unverified provenance*. The product-level figures come from 60 saved products, all gadgets (the local database holds only gadgets), in shadow mode: **development evidence, not an independent evaluation**. No independently labelled product conclusion exists, so no policy here is validated and none is activated.

## 1. What the card does today (read from `dashboard_utils._conclusion`)

For a product whose verdict is "no warning signs":

| Positive share (neutral counted in the denominator) | Card |
|---|---|
| at least 75% **and** the Wilson lower bound at least 0.65 | Well reviewed |
| 50% up to the above | **Mixed reviews** |
| below 50% | Not recommended |

* A review that states **no opinion** counts against "Well reviewed" exactly like a **negative** review.
* The card text names only the positive and the negative percentage ("opinions are mixed: 67% of reviewers were positive and 9% negative"); the neutral share, which is what pulled the card down, is not shown.
* **This is true today, before any calibrator.** On the 60 saved products, all 4 current "Mixed reviews" cards have at most 13% negative reviews (one has 3% negative and 76% positive, mixed because of the lower-bound test). With the sentiment calibrator, 14 of 15 "Mixed reviews" cards would have under 15% negative.

## 2. Five kinds of review, and where each should go

| Kind | Example | Today's treatment |
|---|---|---|
| Positive | "Ang ganda, sulit na sulit" | positive |
| Negative | "Sira agad, nakakadismaya" | negative |
| **Neutral: no opinion** | A feature list ("Moisturizes hair, easy to use"), "ok lang", a delivery note | uncertain (counts against the product) |
| **Mixed: both opinions** | "Maganda ang tela pero madaling masira" | one sentiment label for the whole review; the issue flags (defect, quality) carry the complaint |
| **Insufficient informative reviews** | A product whose reviews are almost all "ok" or generic | counted as usable; only the total count (30) gates "too few reviews" |

The team's labels use *neutral* mainly for the third kind (507 of 724 neutral training reviews are 5-star), which is why a calibrated model, which learns that definition, produces more neutral reviews.

## 3. Is "Mixed reviews" appropriate when neutral rises and negative does not?

**It does not describe the evidence.** "Mixed" tells a shopper that opinions conflict. When positive is 60% to 75%, neutral 20% to 30% and negative under 13%, the reviews do not conflict; many of them simply say nothing about quality. The reader sees "Mixed reviews" and "9% negative" together. This is a *card-design* question, not a sentiment-accuracy question, and it exists today. It cannot be settled by this audit: only independently judged product conclusions (`product_conclusion_evaluation_protocol.md`) can say whether shoppers or annotators would call such a product "Well reviewed" or "Mixed".

## 4. Alternatives (research code: `research/conclusion_policies.py`; not in the app)

* **P0 today.**
* **P1 opinionated only.** Shares among reviews that take a side (positive over positive plus negative); fewer than 20 such reviews gives "not enough" (insufficient *informative* reviews).
* **P2 negative-led.** "Well reviewed" needs a negative share of at most 15% and 75% positive among opinionated reviews; "Not recommended" at 40% negative or under 50% positive among opinionated; otherwise "Mixed"; fewer than 20 opinionated gives "not enough".
* **P3 wording only.** The same decisions as today; when the card is "Mixed" but negatives are under 15% and neutrals at least 25%, the text says that many reviews state no opinion, instead of "opinions are mixed".

### Existing scenario tests (`tests/test_conclusion.py`, no warning signs)

| Scenario pinned by the tests | Today | P1 | P2 | P3 |
|---|---|---|---|---|
| 85 positive, 5 uncertain, 10 negative (bound 0.78) | recommended | same | same | same |
| 9 of 10 positive, small sample (bound 0.6) | mixed | **not enough** | **not enough** | same |
| 60 / 10 / 30 | mixed | same | same | same |
| 30 / 10 / 60 | not recommended | same | same | same |
| Weighted 90 / 5 / 5 (bound 0.8) | recommended | same | same | same |

P1 and P2 break exactly one pinned expectation: a 10-review sample would read "not enough" instead of "mixed" (arguably better, but it changes a pinned behaviour). P3 breaks none.

### Neutral-heavy scenarios (positive / uncertain / negative, 100 reviews)

| Scenario | Today | P1 | P2 | P3 |
|---|---|---|---|---|
| 75 / 15 / 10 | recommended | recommended | recommended | recommended |
| 70 / 20 / 10 | mixed | recommended | recommended | mixed (new wording) |
| 60 / 35 / 5 | mixed | recommended | recommended | mixed (new wording) |
| 50 / 40 / 10 | mixed | recommended | recommended | mixed (new wording) |
| 40 / 40 / 20 | not recommended | mixed | mixed | not recommended |
| 30 / 60 / 10 | not recommended | mixed | mixed | not recommended |
| 10 / 85 / 5 | not recommended | not enough | not enough | not recommended |

Today a product with 10% positive, 85% neutral and 5% negative is "Not recommended", and a product with 30% positive, 60% neutral and 10% negative is also "Not recommended": the card calls a product mostly unopinionated "advised against". P1 and P2 are the only policies that do not.

### The 60 saved products, sentiment-only decisions (warning states ignored, so not the same counts as the real cards)

| Policy and sentiment | Well reviewed | Mixed | Not recommended | Not enough | Changed against today |
|---|---:|---:|---:|---:|---:|
| P0, deployed sentiment | 46 | 11 | 3 | 0 | 0 |
| P1, deployed | 56 | 3 | 1 | 0 | 12 |
| P2, deployed | 54 | 5 | 1 | 0 | 10 |
| P0, calibrated sentiment | 20 | 37 | 3 | 0 | 30 |
| P1, calibrated | 55 | 4 | 1 | 0 | 11 |
| P2, calibrated | 53 | 6 | 1 | 0 | 11 |

With P1 or P2 the calibrated sentiment and the deployed sentiment give nearly the same cards (55 and 56 "Well reviewed"): the **conclusion becomes insensitive to how neutral is defined**, which is the property the calibrator problem showed was missing. With P0 they differ for 30 of 60 products.

## 5. What each choice risks

* **P1 and P2 are more lenient.** They would raise "Well reviewed" from 46 to about 55 of 60 gadget products. If neutral reviews are partly *lukewarm complaints* ("ok lang" meaning "not great"), these policies hide that. The team's neutral class is mostly no-opinion text, but nobody has measured the lukewarm share.
* **P3 is the safest but only repairs the wording**, not the decision: a well-liked product with many unopinionated reviews would still read "Mixed reviews" in the badge.
* Any policy interacts with the weighting: the shares are inverse-probability weighted, so a heavy 5-star mix with generic text makes neutral large.

## 6. Recommendation (not an activation)

1. **Do not change the decision rule now.** Independent product-level judgements do not exist. P1 and P2 are plausible, but they would make today's most common card more lenient on an unmeasured assumption.
2. **Do fix the wording first (P3), as a low-risk interim step, if the owner wants one:** when the card is "Mixed" and negatives are under 15% and neutrals at least 25%, say that "many reviews state no opinion" and show the neutral share beside the positive and negative shares. It changes no decision and breaks no existing test. (Not implemented in the app in this round; it would be a front-end and wording change that needs the owner's agreement.)
3. **Judge P0, P1, P2 on independent conclusions** (100 products, two annotators, `research/conclusion_eval/`), then pick on measured agreement and on the dangerous-error rate (safety concerns reassured), and only then change the rule.
4. **Keep the sentiment calibrator disabled** until a conclusion rule that is robust to the neutral definition (P1, P2, or an owner-chosen alternative) is in place, because with today's rule the calibrator changes 15 of 60 cards (12 of them from "Well reviewed" to "Mixed reviews").
