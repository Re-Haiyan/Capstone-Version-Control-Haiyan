# Evidence completeness

> **Label provenance caveat.** Precision figures below are agreement with *team-supplied labels of unverified provenance* (`annotation_provenance.md`), not with independent human gold.

## 1. The question

For every flag the checker raises, can a real phrase of the review be quoted as evidence? The previous round counted 155 flags without highlighted words (111 defect, 22 not-as-advertised, 21 quality, 1 safety).

## 2. The counts, confirmed (final release code, all 4,792 labelled reviews)

| Flag | Raised | With highlighted words | Listing comparison | No supporting words (model-only) |
|---|---:|---:|---:|---:|
| defect | 556 | 468 | 0 | 88 |
| quality | 413 | 395 | 0 | 18 |
| not as advertised | 459 | 437 | 19 | 3 |
| safety | 139 | 138 | 0 | 1 |
| counterfeit | 182 | 182 | 0 | 0 |

The 155 flags without words of the first audit are confirmed and were split by cause: 111 defect and 1 safety from the learned classifier, 21 quality from the extra-label classifier, and 22 not-as-advertised, of which 19 are listing comparisons (the sentence compared with the listing is itself the evidence) and 3 are classifier-only. The reusable patterns of this and the following audit round (spelling and spacing variants of "does not work", a leak, a torn part; see `evidence_policy_decision.md`) cut the model-only defect flags from 111 to 88 and the quality flags from 21 to 18.

## 3. What was implemented

* **`defaketive_sentiment/evidence.py`**, an additive `review_evidence` field in every analysis (no existing key changes). For each raised flag: `state` is `keyword_span` (matched words, quoted), `listing_context` (a listing comparison rule: the sentence is the evidence) or `model_only` (a learned classifier flagged it and no supporting words exist). A `keyword_span` carries each span's offsets **inside the sentence and inside the original review**, plus the quoted text, which is a slice of the review as written. A sentence that cannot be located exactly gets no review offset and keeps its sentence offset. A `model_only` flag carries the sentence, the model's score and an explicit note; it is **never given an invented phrase and never suppressed by default**.
* **Reusable patterns** for statements the keyword layer missed but a reader would highlight: not working ("hindi sya gumagana", "doesn't work", "ayaw umandar"), an intermittent or partial failure ("on and off", "isa lang ang gumagana"), thin or not durable. They changed 2 of 3,946 training rows' flags (the flags were already raised by the learned layer); 13 flags gained real evidence. No F1 moved by more than 0.001.
* **Tests** (`tests/test_evidence.py`, 14 tests): English, Filipino and Taglish; negation; a flag in the second clause; multiple simultaneous flags; sentence boundaries and absolute offsets; unsupported model-only cases; the field is additive; the opt-in policy.

## 4. The finding that matters: evidence predicts correctness

Agreement with the team-supplied labels, by evidence state, **training rows (development) and historical-test rows kept apart** (`research/results/evidence_precision_by_state_split.json`, final code):

| Flag | State | Train: raised, agree, precision | Historical test: raised, agree, precision |
|---|---|---|---|
| defect | keyword span | 401, 317, **0.79** | 67, 53, **0.79** |
| defect | **model only** | 70, 5, **0.07** | 18, 0, **0.00** |
| quality | keyword span | 309, 195, 0.63 | 86, 53, 0.62 |
| quality | **model only** | 15, 3, **0.20** | 3, 0, 0.00 |
| not as advertised | keyword span | 379, 305, 0.80 | 58, 42, 0.72 |
| not as advertised | listing comparison | 18, 8, 0.44 | 1, 1, 1.00 |
| not as advertised | model only | 2, 0, 0.00 | 1, 0, 0.00 |
| safety | keyword span | 110, 60, 0.55 | 28, 11, 0.39 |
| safety | model only | 0 | 1, 1, 1.00 |
| counterfeit | keyword span | 129, 114, 0.88 | 53, 50, 0.94 |

The direction is the same in both: a defect flag with no supporting words agrees with the label 5 times in 70 on training rows and 0 times in 18 on the historical test. (An earlier version of this table pooled training and test rows and, before the keyword gaps were closed, showed 17 of 101; the training-only figure then was 17 of 83. The gaps closed since were found from training rows only.) The small counts for safety, listing comparison and model-only not-as-advertised cannot be interpreted.

Reading 42 of the model-only defect cases (before the gaps were closed) showed three kinds: about a third had a defensible phrase the keyword layer missed (not working, intermittent failure, charging failure), about a tenth were wrong (a denial, praise or an unrelated text), and the rest were real complaints about something else that the model filed under defect. One reader judged these, not two independent annotators.

## 5. An opt-in policy, measured, off by default

`DEFAKETIVE_EVIDENCE_POLICY=require`: model-only **defect, quality and not-as-advertised** flags are not counted; every drop is listed in `review_evidence_dropped` with its reason and model score, so nothing disappears silently. **Safety is never dropped** (a missed hazard costs more than an unverified one) and counterfeit has no model-only cases. Default: `keep` (nothing changes).

Measured through the real pipeline (`research/results/evidence_policy_effect_v2.json`, final code):

| | Training rows (3,946): F1, precision, recall | Historical test (846): F1, precision, recall |
|---|---|---|
| defect, keep | 0.738, 0.68, 0.80 | 0.680, 0.62, 0.75 |
| defect, **require** | **0.791**, 0.79, 0.79 | **0.773**, 0.80, 0.75 |
| quality | 0.691 to 0.699 | 0.726 to 0.741 |
| not as advertised | 0.764 to 0.766 | 0.717 to 0.723 |
| safety, counterfeit | unchanged | unchanged |

On the historical test the defect gain is +0.093 F1 with the paired product-bootstrap interval **+0.046 to +0.162** (historical benchmark: the set was inspected during development, so this is not an independent test) (precision 0.62 to 0.80, recall unchanged); quality and not-as-advertised gains are within noise. **How the decision was reached, stated plainly:** the first precision-by-state table pooled training and test rows; the direction was then confirmed on training rows alone (defect precision 0.68 to 0.79, F1 0.738 to 0.791), so the training result is the basis and the test result is historical confirmation, not selection. The 0.80 aspiration is still just unmet for defect (0.79 training, 0.77 historical).

**Recommendation (superseded by `evidence_policy_decision.md`): do not enable `require`.** The labelled gain is real but the product-level audit shows it would also remove genuine failure reports that lack keyword evidence and flips 4 of 60 gadget verdicts. Run `shadow` first and close the vocabulary gaps listed there.

## 6. Known remaining gaps

* The core lexicon's original rule ("damage with a packing word nearby is a shipping matter") also hides item damage in the same sentence ("yupi ang box at basag ang takip"). It predates this work; it is documented in `annotation_policy_v2.md` (decision A) and not changed.
* Listing-comparison flags are right only 47% of the time; their "evidence" is the sentence plus the listing part, which a person must read side by side.
* Offsets are relative to the sentence and to the original review; they do not survive a re-segmentation of the same text by a different splitter.
