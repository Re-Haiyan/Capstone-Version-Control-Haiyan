# Evidence-required flag policy: audit and decision

**Decision: do not enable `DEFAKETIVE_EVIDENCE_POLICY=require`. Enable `shadow` first (needs the owner's approval), close the vocabulary gaps below, and decide on real-world evidence.** The policy stays off by default; nothing here changes production.

> **Label provenance caveat.** F1 and "true defects lost" are agreement with *team-supplied labels of unverified provenance*; the 846-row test is a **historical benchmark** (inspected during development, reused adaptively). A gain on it is not proof of real-world performance, and no confidence interval below is a claim of statistical significance for new data.

## 1. What the policy does

`require` stops counting a **model-only** flag (the learned classifier raised it, no supporting words exist in the review) for defect, quality and not-as-advertised. Safety is never dropped. Every drop is listed in `review_evidence_dropped`. `shadow` records what `require` would drop and the verdict it would give, and changes nothing.

## 2. Audit of the flags that would be dropped (final code, `results/evidence_policy_audit.json`, `evidence_policy_audit.csv`)

| Flag | Rows | Would drop | Labelled true among them |
|---|---|---:|---:|
| defect | training | 68 | 4 |
| defect | historical test | 18 | 0 |
| quality | training | 15 | 3 |
| quality | historical test | 3 | 0 |
| not as advertised | training / test | 2 / 1 | 0 / 0 |

Defect drops split by reading each (one reader, not two annotators; the reading categories are my triage, not annotations):

| Triage | Training (dropped, labelled true) | Test |
|---|---|---|
| Possible missed evidence: a phrase a reader would highlight that the keyword layer lacks | 18, 3 | 3, 0 |
| Denial or praise | 4, 1 | 2, 0 |
| No specific problem stated | 28, 0 | 7, 0 |
| Complaint about something else | 18, 0 | 6, 0 |

**Genuine missed evidence versus unsupported predictions.** About a quarter of the dropped defect flags are genuine misses of the keyword layer (18+3 of 86); the rest (about three quarters) are predictions with no stated failure. Only the first group, 3 of 18 on training rows, includes defects the supplied labels call true. **True defects lost:** 4 on training rows (defect) and 3 (quality), 0 on the historical test. These are fixable with vocabulary, not by keeping the model-only flags: see section 5.

## 3. Effect on labelled agreement (historical benchmark, not independent)

Defect F1, keep to require: training 0.738 to 0.791 (precision 0.68 to 0.79, recall 0.80 to 0.79); historical test 0.680 to 0.773 (precision 0.62 to 0.80, recall unchanged 0.75; paired product-bootstrap interval of the gain +0.046 to +0.162). Quality: +0.008 (train), +0.015 (test, interval 0.000 to 0.042). Not-as-advertised: +0.002 and +0.006. Safety and counterfeit unchanged. The interval is a bootstrap over products of the *same* inspected rows; it quantifies resampling noise, not whether the gain will appear on new reviews. The training result is the basis; the test result is a historical confirmation of direction.

## 4. Category-specific effects (defect flag, `results/evidence_policy_effect_v2.json`)

| Group | Train rows | Defect flags dropped | True defects lost | Train F1 keep to require | Test rows | Test dropped | Test F1 keep to require |
|---|---:|---:|---:|---|---:|---:|---|
| automotive_tools | 305 | 3 | 0 | 0.779 to 0.804 | 20 | 0 | 1.00 to 1.00 |
| baby_kids_toys | 253 | 0 | 0 | 0.615 to 0.615 | 76 | 0 | 0.50 to 0.50 |
| beauty_health | 742 | 18 | 0 | 0.704 to 0.794 | 227 | 7 | 0.467 to 0.609 |
| **electronics** | 378 | 21 | **4** | 0.633 to 0.687 | 77 | 5 | 0.706 to 0.828 |
| fashion | 524 | 1 | 0 | 0.789 to 0.800 | 61 | 0 | 0.75 to 0.75 |
| food_grocery | 53 | 0 | 0 | 1.00 to 1.00 | 158 | 2 | 0.40 to 0.667 |
| home_living | 1002 | 18 | 0 | 0.791 to 0.838 | 200 | 4 | 0.769 to 0.82 |

Most drops are in beauty, home and **electronics**. Every true defect lost on training rows is in electronics, the category where "does it work" is the product's whole point. Several groups have so few labelled defects (baby, food, automotive) that no per-group figure is interpretable.

## 5. Product-level effect (conclusion cards): the reason not to enable

Shadow evaluation on 60 saved Lazada products (**all gadgets**: the local database holds nothing else), with the switch set to `shadow` and compared with `require` run separately (`results/shadow_evidence_policy_local.json`; the shadow block equals the `require` result for 54 of 54 products with something to drop):

* 54 of 60 products have at least one flag that would be dropped; 4 change verdict and card; 0 change a safety count.
* All 4 changes are **warning removed**: *possible counterfeit or defect* to *no warning signs*; caution to recommended (1) or mixed (3). They are a Qualcomm 35W charger accessory (5 defect flags dropped), a K12 mini audio player (11), a BLUESKY 10000 mAh power bank (25) and a KC58 20000 mAh power bank (58).
* The KC58 and BLUESKY cases are the issue: a power bank with dozens of model-only defect flags loses its warning. The earlier reading of gadget cases (one reader) found that many such flags are failure reports the keyword layer cannot quote (partial failure, connection or capacity complaints; see section 7 for the phrase list); I did not re-read the 58 KC58 flags individually for this document, so the share that is genuine is not quantified. Removing them makes the product look safer on the cards, the costly direction for this app. The benchmark F1 gain does not capture this because labelled rows rarely have that many defects on one product.
* **VM check (production database, 10 Lazada + 10 Shopee products, `results/vm_shadow_policy.json`):** 18 of 20 have something to drop (441 defect-flagged reviews would fall to 309); **0 verdicts and 0 cards change, 0 safety counts change**, and the shadow block equals the `require` result for 18 of 18. So the product-level harm seen locally (4 of 60) did not appear in this VM sample of 20. The samples are small and differently chosen, so this does not show the policy is safe; it shows the effect is concentrated in a few high-flag gadget products (the local power banks), which is what the shadow rollout should look for.

## 6. Safety handling

Safety is never dropped, and the drop list never contains a safety flag: 0 safety counts changed in the local shadow and in the labelled sets (safety F1 unchanged 0.638 train, 0.533 test). A heat or smoke review that the learned layer flagged as a defect remains a safety flag through the existing heat rule, which is exempt from the policy.

## 7. Regression cases and the vocabulary gaps to close first

Defects the supplied labels call true that `require` would lose (all unquotable by the keyword layer) point to missing vocabulary: "isn't / aren't working", "ayaw kumonek / connect / pair / play", "gumagan\w*" and similar spellings, "isang X lang ang nagana", abrupt drain ("wala pang N minutes lowbat", "won't even reach N%"), capacity-mismatch statements ("hindi umabot sa 20000"). **None of these was added to the release candidate**: they were found late, and adding rules after the validation runs would invalidate the measurements of `release_validation.md`. They are the first work of the next round; each must be added as a reusable pattern with a test, then the policy re-measured (training rows first) and the shadow data on real products reviewed.

## 8. Shadow-mode rollout proposal (needs approval)

1. Deploy the release candidate as in `release_manifest.md`. Switch stays unset.
2. After the re-check, set `DEFAKETIVE_EVIDENCE_POLICY=shadow` in the service environment. Production output is identical (verified: `shadow` equals `keep` in analysis, only an extra field appears; benchmark 14.1 reviews/s, memory +5 MB).
3. Each scan then stores `shadow_evidence_policy` (verdict_state, flagged reviews, dropped flags). For two weeks, once a week, list products whose verdict would change; the owner or an annotator reads the dropped flags of each.
4. **Activation criteria (all):** (a) the vocabulary gaps are closed and re-measured; (b) no product whose reviews hold three or more dropped flags that a reader accepts as real changes verdict state; (c) a fresh, independently human-labelled sample (`annotation_execution_guide.md`) shows the dropped flags are wrong at least as often as 80% of the time; (d) the owner approves in writing. Until then the app keeps `keep`.
5. Rollback: unset the variable and restart; no data changes.

## 9. What is established and what is not

Established (on the supplied labels): model-only defect flags agree with the label 5 of 70 times on training rows and 0 of 18 on the historical test, against 0.79 with words; the policy raises labelled defect F1 and loses 4 labelled defects on training rows. Not established: that this holds on real reviews, that the labels are correct, or that the product-level effect is acceptable (it is not, on the local power banks). No claim of significance on new data is made.
