# Finalization round: summary

> **Label provenance caveat.** Every score is against *team-supplied labels of unverified provenance*: the labels came back minutes after the blank files were created (0.3 to 1.5 seconds per review), so they are silver, not independent human gold (`annotation_provenance.md`).

Branch `deployment` (local commits, pushed to the owner's repository; nothing deployed, the VM is still at `d74589a`). Start: commit `e3d629c`, 206 tests. End: 257 tests, all pass. Sections 1 to 10 of the brief were carried out; the brief was cut off at "## 11." (nothing after that heading was received), so that section was not worked on.

## What was actually implemented

**Production code (all additive or default-off; no API key removed; every default behaviour unchanged unless stated)**

| Change | Default | Where |
|---|---|---|
| `review_evidence`: per flag, a state (`keyword_span`, `listing_context`, `model_only`), quoted spans with sentence and absolute review offsets; never an invented phrase | on (an extra key) | `evidence.py`, `hazard_model.analyze` |
| Evidence policy `require`: model-only defect, quality and not-as-advertised flags are not counted; every drop is listed in `review_evidence_dropped`; safety never dropped | **off** (`DEFAKETIVE_EVIDENCE_POLICY`) | `evidence.py` |
| Reusable "not working", intermittent-failure and thin patterns | on | `all.add.tsv` |
| Clause-level context: feared fake resolved as genuine | on | `hazard_model._feared_not_fake` |
| Clause-level context: soft statement resolved by a benign clause | **off** (`DEFAKETIVE_CLAUSE_RESOLVE=safety,quality`) | `hazard_model._resolved_by_contrast` |
| Order clause plus a different arrival clause across "pero"; a concrete size or colour before "ang pinadala / dumating" | on | `hazard_model._joined_mismatch`, `all.add.tsv` |
| Packing-damage guard made span-level; a conjunction no longer attaches a damage word to the box | on | `product_category.py` |
| Sentiment calibrator shadow mode (`sentiment.calibrated`, `shadow_sentiment` summary block); `on` mode keeps the deployed label | **off** (`DEFAKETIVE_SENTIMENT_CALIBRATOR`) | `sentiment_calibration.py`, `product_badges.py` |

**Research tooling and documents** (all in `research/`): `annotation_provenance.md`, `annotation_policy_v2.md`, `evidence_completeness.md`, `clause_context.md`, `sentiment_calibration_review.md`, `product_conclusion_evaluation_protocol.md`, `fresh_eval/README.md`, `agreement/GUIDE.md`, the corrected `annotation_audit.md`; scripts `fresh_eval.py`, `conclusion_eval.py`, `policy_impact.py`, `shadow_sentiment.py`, `sentiment_calibration_audit.py`, `evidence_cases.py`, and a rewritten `agreement.py` (anonymous ids, missing-annotation handling, `compare`).

**Tests: 257 pass (51 new this round):** evidence (14), clause context (13), shadow sentiment (4), agreement sheets and scoring (9), conclusion sheets (6), fresh evaluation set (5), plus the earlier ones.

## What was actually executed, and what it showed

1. **Annotation audit counts reconciled.** 534 and 502 were both real but measured different things (entries against unique reviews); worse, **219 of the 264 hazard entries came from a bug of mine** (the stem "amag", mold, matched inside "damage" and "magnetic"). Fixed with word-start matching and benign contexts: now **285 entries over 280 unique reviews, 16 high priority, 117 needing the listing, all needing manual adjudication**. All 219 removed rows were checked.
2. **Provenance audit: the labels cannot be called human gold.** Returned files appeared 7 to 22 minutes after the blank files were created, for 270 to 3,863 reviews each. No annotator ids, timestamps or tool records exist. Verified provenance of every labelled set: unknown.
3. **Evidence completeness.** The 155 flags without words are confirmed and split by cause. **A flag without supporting words agrees with the label 17% of the time (defect), against 79% with words.** With the opt-in policy, defect F1 0.733 to 0.767 on training rows and 0.680 to 0.773 on the historical test (paired interval for the gain +0.044 to +0.162), precision 0.62 to 0.80.
4. **Clause context.** A reusable mechanism was built; resolving "pero okay" for quality or heat was measured to cost F1 (quality 0.691 to 0.660), so it is a switch, off. The order/arrival mismatch raised not-as-advertised F1 0.764 to 0.772 on training rows.
5. **Agreement workflow.** Found and fixed a leak (original id prefixes revealed the sampling stratum); sheets are now anonymous; missing annotations are handled; `compare` adds annotator-versus-supplied-label agreement.
6. **Fresh evaluation set.** **All 89 products not already used are gadgets**; no non-gadget product is unseen, so an independent non-gadget test cannot be built from the current pool. A gadget set (712 representative reviews with sampling weights, 69 enrichment, 199 training candidates) and a sufficiency analysis were produced; a test caught and fixed a zero sampling weight.
7. **Sentiment calibrator.** Not a stars shortcut (text alone: macro F1 0.707 CV, 0.734 historical test). Better in every product group. **Shadow mode on 60 saved products: 15 conclusions change, 12 of them from Well reviewed to Mixed reviews, with no rise in negative reviews** (positive 80.2% to 70.9%, neutral 11.7% to 20.4%, negative 8.1% to 8.7%). Not activated.
8. **Conclusion accuracy protocol.** Sheets for 100 products and a scoring tool that refuses to run without two judged sheets; no accuracy is claimed.
9. **Policy v2 compared with v1 and with the current rules**, decision by decision: B, C, H, I already met; real gaps for A (item damage beside packing, a `delivery` rule flag), E, F (a hypothetical fear is flagged as a defect), J (an effect complaint is flagged as a defect); D and G need an owner decision. The data **do not justify an `effectiveness` flag** (11 rows, 8 labelled counterfeit).

## What improved (measured)

* Defect (opt-in policy): +0.034 F1 on training rows, +0.093 on the historical test (interval above zero).
* Not as advertised: 0.764 to 0.772 on training rows (order/arrival).
* Defect: 0.733 to 0.736 (span-level packing guard).
* Evidence: 13 more flags with real quoted evidence; every flag now has an explicit evidence state.
* Sentiment (opt-in): macro F1 0.57 to 0.72 on the historical test, not activated.

## What remains uncertain

Whether any label is human-quality (provenance); whether the evidence policy's gain holds on a fresh test (the historical test is not untouched); whether the calibrator's conclusion shifts are desirable (a product decision); how the five-flag rules behave on non-gadget products that were never labelled; policy decisions D, E, F, G.

## What requires human annotation or decisions

1. **Two annotators on the 300 agreement sheets** (`research/agreement/GUIDE.md`), then `agreement.py score` and `compare`. This settles the provenance question.
2. **Two annotators on 100 products** (`research/conclusion_eval/`), then `conclusion_eval.py score`.
3. **Annotation of the fresh set** (`research/fresh_eval/`); and collection of new non-gadget scans for a non-gadget final test.
4. **Owner approval** of policy v2 (A to J), of the evidence policy, and a decision on the calibrator's treatment of neutral.

## What is ready for deployment (needs explicit approval; nothing was deployed)

* The rule changes of `831f22f` and this round's default-on changes (evidence field, reusable patterns, feared-fake and order/arrival handling, span-level packing guard): 257 tests, no regression on any labelled file, documented effects.
* **Opt-in switches, all off:** evidence policy, clause resolution, sentiment calibrator. The evidence policy is the one recommended for approval (defect precision 0.62 to 0.80).

## What to investigate next

1. The core lexicon's "damage near a packing word is shipping" rule (decision A gap 1).
2. A rule-layer `delivery` flag (policy A needs it).
3. A hypothetical fear and an effect complaint are flagged as defects (F, J).
4. Shadow-test the calibrator on non-gadget saved products and decide the neutral treatment.
5. Verify the provenance of the two shipped classifiers.
