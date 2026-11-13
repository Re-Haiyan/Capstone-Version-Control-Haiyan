# Non-gadget batch: results

Labels: `label_batch_nongadget.csv` and `label_batch_nongadget_part2.csv` in this folder, labelled by the team (570 reviews, 522 marked high confidence). Scored with `evaluation/score_nongadget.py`, product title included, high-confidence rows only.

## How the rules were tuned

- The rules in `lexicons/categories/` were tuned on the **dev** half (270 high-confidence rows) in two rounds.
- The **test** half (252 rows) was kept back. It was scored once after the second round of tuning. It was scored again after one last code fix (F11 now respects a category exception); that fix came from a unit test and dev rows, and it changed no test result. Treat the test numbers as read twice, not as a fresh sample.
- The test half is the number to quote. The dev numbers are optimistic by construction.

## Test half (252 rows): tuned rules against the old checker with no product category

| Label | Positives | Old: P / R / F1 | Tuned: P / R / F1 |
|---|---|---|---|
| Defect | 41 | 0.78 / 0.78 / 0.78 | 0.74 / 0.78 / 0.76 |
| Counterfeit | 16 | 0.89 / 1.00 / 0.94 | 1.00 / 1.00 / 1.00 |
| Not as advertised | 28 | 1.00 / 0.25 / 0.40 | 0.92 / 0.43 / 0.59 |
| Quality | 25 | 0.69 / 0.44 / 0.54 | 0.75 / 0.60 / 0.67 |
| Safety | 6 | 0.00 / 0.00 / n/a | 1.00 / 0.50 / 0.67 |

Sentiment accuracy is unchanged at 0.881 (222 of 252).

## Round 3 (after the table above was first written)

Three general size and fit rules were added for fashion (a size labelled bigger that fits smaller, "kala ko maxi" with a short dress, a typo of "mali mali ... size"). They came from dev rows and general wording, not from the test misses, but the test half had already been read, so the move from 0.55 to 0.59 is not a clean measure. Recall is now 0.43 (12 of 28). Nothing else changed; the 179 tests pass.

## Dev half (270 rows), tuned: for reference only

Defect 0.84, counterfeit 1.00, not as advertised 0.83, quality 0.76. The drop from dev to test (for example not as advertised 0.83 to 0.55) is the cost of tuning on 270 rows.

## Gadget sets: unchanged

`score.py` on the gold and held-out sets gives the same result as before the category work, because it reads reviews without a product title. A change to the shared code (the `wlng` spelling variant, and category exceptions now binding the label model and the f11 and s3 rules) did not move any gadget score.

## What these numbers do and do not say

- **Defect did not improve.** It is 0.76 against 0.78, two more false positives on the test half. The gains are in not-as-advertised, quality, counterfeit and safety.
- **Safety has 6 positives.** 3 of 6 found, no false alarms. Do not quote it as an F1; quote it as "3 of 6 reports found, none wrong".
- **Counterfeit is concentrated.** Most of its positives are reviews of two products (a skincare soap and a food item), so 1.00 is not a general result.
- **Not as advertised still misses 16 of 28.** Recall 0.43 is the weakest result.
- **48 products.** Reviews of one product resemble each other. These scores describe these products, not every product in a category.
- **Two policies come from the team's labels.** Damage that arrived (dented, crushed) counts as a defect on non-gadget groups even when the review also mentions packaging. A battery that drains fast is a quality complaint, not a defect, on home, beauty and sports products. Gadgets keep the old policy.

## Next step if more tuning is wanted

The test half is now used. A fresh batch of reviews, from products not scanned yet, is the only clean test of further changes.
