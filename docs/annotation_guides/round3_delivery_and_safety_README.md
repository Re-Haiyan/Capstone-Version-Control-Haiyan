# Round 3 annotation: a new "delivery" label, and more safety rows

Two jobs. Do job A first (it is quick), then job B.

## Job A: the delivery label (1,184 rows, yes or no)

Files: `delivery_check_train.csv` (1,024 rows) and `delivery_check_test.csv` (160 rows).
These are reviews you have ALREADY labelled for defect, quality and the rest. Do not redo those. Only fill the new column:

- `delivery` = `yes` if the reviewer complains about **delivery, packaging or the seller**: it arrived late, the courier or rider, the box or seal was opened, wet, crushed or tampered with, bad or missing packing, the seller did not reply or refused a refund, freebies or the receipt were not given.
- `delivery` = `no` if the review is praise about delivery ("fast delivery, well packed") or is only about the product.
- A review can be BOTH `yes` here and have `defect` or `not_as_described` from before. If the product is broken and the reviewer blames shipping or packing, answer `yes`. That is fine.
- `confidence`: `high`, or `low` when you cannot tell.
- The test file (160 rows) should be done by two people independently if you can. The training file needs one person.

Reviews that did not mention delivery, packing or the seller (about 3,000 rows) are treated as `no`. You do not need to look at them.

## Job B: more safety reports (397 rows)

Files: `label_safety_train.csv` (304 rows) and `label_safety_test.csv` (93 rows). New reviews, picked because they contain a hazard word (heat, smoke, rash, expired, choking and so on), so most are not real reports. Label them exactly as before: `sentiment`, `flags` (one or more of defect, counterfeit, safety, not_as_described, quality, joined with `;`, or `none`) and `confidence`. The aim is a real set of safety reports to learn from and to measure on. The test file again by two people if you can.

The safety rule, from the earlier guide: label what the reviewer reports about the product itself; heat that is the weather or the job of the product is not safety; praise and denials ("no rash") are not reports; mild "umiinit lang" with no worry is not safety, "umiinit habang nagchacharge, nakakatakot" is.

Do not open `keep-separate-key`. Save each file under a new name (for example `annotated_delivery_train.csv`).
