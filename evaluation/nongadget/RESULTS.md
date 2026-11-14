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

## Fresh batch (clean test): 310 reviews from 69 products scanned after the tuning

Labelled by the team (`evaluation/fresh/label_batch_fresh.csv`, 293 high-confidence rows). Scored once, with no tuning on it, using `score_nongadget.py`. Products and reviews were not in any earlier batch. Positives are few: defect 11, counterfeit 7, safety 3, not as advertised 22, quality 5.

| Label | Positives | No category: P / R / F1 | Tuned: P / R / F1 |
|---|---|---|---|
| Defect | 11 | 0.86 / 0.55 / 0.67 | 0.55 / 0.55 / 0.55 |
| Counterfeit | 7 | 0.88 / 1.00 / 0.93 | 0.88 / 1.00 / 0.93 |
| Not as advertised | 22 | 1.00 / 0.32 / 0.48 | 0.81 / 0.59 / 0.68 |
| Quality | 5 | 0.29 / 0.40 / 0.33 | 0.20 / 0.40 / 0.27 |
| Safety | 3 | 0.00 / 0.00 / n/a | 0.33 / 0.67 / n/a |

Sentiment accuracy 0.901 (264 of 293).

What it says:
- **Not as advertised improved on unseen products** (recall 0.32 to 0.59, F1 0.48 to 0.68). This is the clearest gain.
- **Counterfeit holds** (7 of 7 found).
- **Defect precision got worse with the category** (0.86 to 0.55): 5 false alarms against 1. Several are reviews that deny a problem ("received without any damage", with a typo; "the box had dents but the contents weren't damaged"). The arrived-damaged rules for non-gadget groups are too eager on these.
- **Safety has 3 positives**, so no score is quoted. It found 2 of 3 but raised 4 false alarms, including praise ("Safe and non-toxic for babies") and "nagbalat" (skin peeling after sunburn).
- **Quality has 5 positives**; do not read the score.
- These false-alarm types were not seen in the earlier tuning. Fixing them is legitimate, but any later score on this batch is no longer clean.

### After the fix for denials and praise (fresh batch is no longer a clean test)

A guard was added in `product_category.denied()`: a review that says nothing was damaged ("received without any damage", typos included), praise ("safe and non-toxic"), a far expiry date, peeling after sunburn, and "did not work" as an effect on a skin or health product are no longer read as defect or safety reports. It was written after reading the fresh batch's false alarms, so **the numbers below are not a clean test**; quote the table above for the unseen-product result and this one as the effect of the fix.

| Fresh batch | Before fix P / R | After fix P / R |
|---|---|---|
| Defect | 0.55 / 0.55 (5 false alarms) | 0.86 / 0.55 (1 false alarm) |
| Safety | 0.33 / 0.67 (4 false alarms) | 0.67 / 0.67 (1 false alarm) |

Dev and test halves of the first batches are unchanged by the fix (defect 33 of 36 and 32 of 41 found), so the guard did not cost recall there. A first version of the guard was too broad (it hid real defects when a denial appeared elsewhere in the sentence, and "no" matched inside "ano"); it was narrowed after those two halves showed the loss. 185 tests pass, 6 of them new.

### Second fix: denied category terms and packing quality

Category terms for quality and not as advertised were never checked for negation ("hindi malagkit", "wala xiang amoy" counted as complaints). They now are. The guard also sets aside "packing quality is awful" (the packing, not the product) and "manipis ... hindi pala" (feared, not so). Written after reading the fresh batch's quality false alarms, so the fresh batch stays a non-clean test.

Fresh batch quality false alarms went from 8 to 4 (precision 0.20 to 0.33, recall unchanged at 0.40; 5 positives, so do not read the score). Dev and test halves of the first batches are unchanged, except dev not as advertised 0.86 to 0.88. 189 tests pass.

A second fresh scan (pets, appliances, bedding, bags, lipstick, shampoo) was started and stopped: Lazada returned no listings for any search after the earlier day's scan. The scanner never answers a verification, so it was left alone. Try again later, with fewer searches per run.

## Second fresh batch (clean test of the rules as deployed at d74589a)

270 reviews from 75 products scanned after the second round of fixes (pets, small appliances, bedding, hair care, bags, kitchen, toys). Labelled by the team (253 high-confidence rows), scored once before any change. Products overlap with no earlier batch.

| Label | Positives | No category: P / R / F1 | Tuned: P / R / F1 |
|---|---|---|---|
| Defect | 29 | 0.73 / 0.66 / 0.69 | 0.73 / 0.66 / 0.69 |
| Not as advertised | 36 | 0.86 / 0.17 / 0.28 | 0.86 / 0.33 / 0.48 |
| Quality | 16 | 0.62 / 0.62 / 0.62 | 0.73 / 0.50 / 0.59 |
| Counterfeit | 2 | n/a | n/a |
| Safety | 1 | n/a | n/a |

Sentiment accuracy 0.905 (229 of 253). Counterfeit (2) and safety (1) have too few positives to score.

- **Not as advertised is still the weak spot:** it finds 12 of 36. Most misses are the wrong item delivered ("dogfood imbis na catfood", "lipbalm not lipstick"), missing items ("8 bedsheets ang order pero puro pillow case", "pack of 2, isa lang"), and a size or material that differs ("hindi cotton"). The first fresh batch had the same weakness in fashion; the size and wrong-item rules there were never written for home, pet, toy and appliance groups.
- **Defect is flat against no category** (the category adds nothing here). Many misses are "arrived dented or scratched" on small appliances, a policy the team labels as a defect.
- **Quality dropped in recall** against no category (0.62 to 0.50) while precision rose.
- The category work helps most where the general rules have no words for a kind of complaint, and little where they already do.
