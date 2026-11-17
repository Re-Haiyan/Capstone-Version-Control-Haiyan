# Defect gaps: charging failure + drain remark, abrupt drain wording, combined failure phrases

Branch `feature/defect-recall-charging-abrupt-combined-20261118` (from deployment `fc56fa9`). Model version NOT bumped. Nothing deployed.

## Root causes (all in the category-exemption layer, not the model)
1. `all.tsv` drain row exempts the learned model's defect flag for any sentence with drain wording; a charging failure in the same sentence ("bilis ma lowbat ayaw pa ma charge") was explained away. Fix: keyword rules for charging failures (`all.add.tsv`).
2. The row's abrupt/measurable cues (`agad`, `minuto`, `wala pang`...) were only read OUTSIDE the term's own +-2-word window, which is where they sit. Also `\d` matched only single-digit tokens ("30kins", "10mins" never matched). Fix: `*` marker on the `unless` cell reads the whole window (`_Unless`, opt-in, only this row); `isang gamit` and "number + minutes" added.
3. `_DENIED_DAMAGE` ("nothing was damaged") let 2 filler words sit between a negator and a damage word, so "not WORKING sira agad" read as "not broken" and cancelled both failure phrases. Fix: a failure verb can no longer be a filler word.
Needed consequence of 2: a negated drain ("hindi agad malowbat") lost its accidental protection; an explicit negated-drain exemption row restores it (unambiguous negators only: "wala na lowbat" means the battery is dead).

## Evidence
Labelled (4,817 distinct high-confidence reviews, 529 defect positives; no rule written from them):
| set | baseline P / R / F1 | candidate P / R / F1 |
|---|---|---|
| all | 0.711 / 0.820 / 0.762 | 0.711 / 0.822 / 0.762 |
| held-out test_v3 (792) | 0.634 / 0.776 / 0.698 | identical |
| other labelled batches (1,171) | 0.865 / 0.865 / 0.865 | identical |
Paired product-bootstrap F1 difference +0.0004, 95% CI [-0.0018, +0.0033]: no measurable change. Only 2 labelled reviews change (1 true defect gained, 1 false positive gained); no other flag changes. Only 93 labelled reviews have drain wording, so the labels cannot show an improvement for this slice.

Production reviews (412 saved products, 75,747 reviews; baseline = saved production analyses, candidate = incremental re-analysis of 21,928 possibly-affected reviews, aggregation unchanged):
- defect tags gained 127, lost 1; safety tags changed 0; sentiment labels changed 0; other flags changed 0
- 47 products have a different defect flag count; 1 verdict changes (AMZ ZQS-1202 speaker: no warning signs -> possible counterfeit or defect, 61 -> 66 flags); 1 recommendation changes (consider -> caution)
- 22 gained reviews read by hand (not the team's labels): about 20 genuine abrupt failures, 2 borderline ("2 hours lang", "1 hour low batt"), 0 clear false positives; the 1 lost flag was praise ("hindi agad nalolowbat")

Method validation: aggregation rebuilt from saved analyses equals the stored production summary for 408 of 412 products; the other 4 differ by one emoji-only review (U+1FA77, unknown to Python 3.11's Unicode 14 here, known on the VM's 3.12), identically for baseline and candidate. Full re-analysis equals incremental at decision level (verdict, flag counts, tags, rates) on 4 products including a 1,639-review one; the only difference found is a last-digit float in one intermediate score. Duplicate (text, rating) pairs within a product: 2,481, none with different stored analyses.
