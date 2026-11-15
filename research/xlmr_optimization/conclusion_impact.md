# Effect on downstream product conclusions

Method (`conclusion_impact.py`): the same 60 saved Lazada products used in the earlier shadow-sentiment study (at least 60 written reviews each; all gadgets, because the local database holds only gadgets), 8,054 unique review texts. Each candidate labels every review once; the real analysis then runs with the calibrator hook replaced, in that process only, by those labels, the summary's shadow block is built with the same star-level weights, and the real conclusion card is built from it and from the deployed fields. Issue warnings (the verdict states) are untouched. Nothing is saved and no setting changes. **This measures behaviour change, not accuracy**: no independently labelled product-level judgments exist, so a changed conclusion cannot be called right or wrong. The existing customer-facing sentiment calibrator stays disabled.

| | Deployed | `c2_mix_weighted_s1` | `d1_mix_ce_rep2_s1` (best by the selection rule) |
|---|---:|---:|---:|
| Mean positive share | 0.802 | 0.682 | 0.720 |
| Mean neutral ("uncertain") share | 0.117 | 0.225 | 0.185 |
| Mean negative share | 0.081 | 0.094 | 0.094 |
| Conclusions: recommended / mixed / caution / not recommended | 25 / 4 / 22 / 9 | 4 / 24 / 21 / 11 | 14 / 14 / 23 / 9 |
| Products whose conclusion changes | n/a | **24 of 60** (23 less favourable, 1 more) | **12 of 60** (11 less favourable, 1 more) |
| Main transition | n/a | recommended to mixed: 20 | recommended to mixed: 10 |
| Ranking agreement with the deployed order (Spearman, positive share / lower bound) | 1 | 0.60 / 0.58 | 0.71 / 0.70 |
| "Recommended" despite an issue warning | 0 | 0 | 0 |

Findings:

* Both candidates lift the neutral share and lower the positive share, so a product that is "Well Reviewed" under the shipped model often becomes "Mixed Reviews". This is the pattern the question asked about (neutral rises while negative barely moves, 0.081 to 0.094): the conclusion thresholds (`RECOMMEND_SHARE 0.75`, `RECOMMEND_BOUND 0.65`, neutral counted in the denominator) were set around the shipped model's neutral behaviour and are not neutral-invariant; a model with a better neutral class mechanically produces more "Mixed" cards. Whether that is more accurate is **unknown**.
* Rankings change materially (Spearman 0.60 to 0.71), so recommendation order would move even where the card does not.
* No contradiction between an issue warning and a "recommended" conclusion appears for either.
* The result is the same direction as the earlier calibrator study (15 of 60 cards changed), so it is a property of correcting neutral, not of one method.
* A sentiment candidate must therefore **not be switched on for customer-facing conclusions** until the conclusion policy (`research/conclusion_policy_review.md`) and independently labelled conclusions exist.
