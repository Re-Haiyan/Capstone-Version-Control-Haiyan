# Evidence completeness

> **Label provenance caveat.** Precision figures below are agreement with *team-supplied labels of unverified provenance* (`annotation_provenance.md`), not with independent human gold.

## 1. The question

For every flag the checker raises, can a real phrase of the review be quoted as evidence? The previous round counted 155 flags without highlighted words (111 defect, 22 not-as-advertised, 21 quality, 1 safety).

## 2. The counts, confirmed

Re-run over all 4,792 labelled reviews with the new `review_evidence` field (`research/evidence_cases.py`):

| Flag | Raised | With highlighted words | Listing comparison | No supporting words (model-only) |
|---|---:|---:|---:|---:|
| defect | 540 | 439 | 0 | 101 |
| quality | 413 | 395 | 0 | 18 |
| not as advertised | 449 | 427 | 19 | 3 |
| safety | 139 | 138 | 0 | 1 |
| counterfeit | 182 | 182 | 0 | 0 |

The 155 of the previous round are confirmed and now split by cause: **111 defect and 1 safety** from the learned classifier, **21 quality** from the extra-label classifier, **22 not-as-advertised**, of which **19 are listing comparisons** (the sentence compared with the listing is itself the evidence) and 3 are classifier-only. Before the patterns below, the model-only totals were 111 + 21 + 3 + 1 = 136; they are now 101 + 18 + 3 + 1 = 123.

## 3. What was implemented

* **`defaketive_sentiment/evidence.py`**, an additive `review_evidence` field in every analysis (no existing key changes). For each raised flag: `state` is `keyword_span` (matched words, quoted), `listing_context` (a listing comparison rule: the sentence is the evidence) or `model_only` (a learned classifier flagged it and no supporting words exist). A `keyword_span` carries each span's offsets **inside the sentence and inside the original review**, plus the quoted text, which is a slice of the review as written. A sentence that cannot be located exactly gets no review offset and keeps its sentence offset. A `model_only` flag carries the sentence, the model's score and an explicit note; it is **never given an invented phrase and never suppressed by default**.
* **Reusable patterns** for statements the keyword layer missed but a reader would highlight: not working ("hindi sya gumagana", "doesn't work", "ayaw umandar"), an intermittent or partial failure ("on and off", "isa lang ang gumagana"), thin or not durable. They changed 2 of 3,946 training rows' flags (the flags were already raised by the learned layer); 13 flags gained real evidence. No F1 moved by more than 0.001.
* **Tests** (`tests/test_evidence.py`, 14 tests): English, Filipino and Taglish; negation; a flag in the second clause; multiple simultaneous flags; sentence boundaries and absolute offsets; unsupported model-only cases; the field is additive; the opt-in policy.

## 4. The finding that matters: evidence predicts correctness

Agreement with the team-supplied labels, by evidence state (`research/results/evidence_precision_by_state.json`, all labelled rows):

| Flag | State | Raised | Agree with label | Precision |
|---|---|---:|---:|---:|
| defect | keyword span | 439 | 348 | 0.79 |
| defect | **model only** | 101 | 17 | **0.17** |
| quality | keyword span | 395 | 248 | 0.63 |
| quality | **model only** | 18 | 3 | **0.17** |
| not as advertised | keyword span | 427 | 340 | 0.80 |
| not as advertised | listing comparison | 19 | 9 | 0.47 |
| not as advertised | model only | 3 | 0 | 0.00 |
| safety | keyword span | 138 | 71 | 0.51 |
| safety | model only | 1 | 1 | 1.00 |
| counterfeit | keyword span | 182 | 164 | 0.90 |

A flag with no supporting words is right about 1 time in 6. Reading 42 of the model-only defect cases showed three kinds: about a third have a defensible phrase the keyword layer missed (not working, intermittent failure, charging failure; some now covered by the new patterns); about a tenth are wrong (a denial such as "Wala leak and damage", praise such as "Gumagana xa..", or an unrelated text); the rest are real complaints about *something else* (a missing item, a skin reaction, a pet that will not eat) that the model filed under defect. One reader judged these, not two independent annotators.

## 5. An opt-in policy, measured, off by default

`DEFAKETIVE_EVIDENCE_POLICY=require`: model-only **defect, quality and not-as-advertised** flags are not counted; every drop is listed in `review_evidence_dropped` with its reason and model score, so nothing disappears silently. **Safety is never dropped** (a missed hazard costs more than an unverified one) and counterfeit has no model-only cases. Default: `keep` (nothing changes).

Measured through the real pipeline (`research/results/evidence_policy_effect.json`):

| | Training rows (3,946): F1, precision, recall | Historical test (846): F1, precision, recall |
|---|---|---|
| defect, keep | 0.733, 0.69, 0.79 | 0.680, 0.62, 0.75 |
| defect, **require** | **0.767**, 0.79, 0.74 | **0.773**, 0.80, 0.75 |
| quality | 0.691 to 0.699 | 0.726 to 0.741 |
| not as advertised | 0.764 to 0.766 | 0.717 to 0.723 |
| safety, counterfeit | unchanged | unchanged |

On the historical test the defect gain is +0.093 F1 with the paired product-bootstrap interval **+0.044 to +0.162** (precision 0.62 to 0.80, recall unchanged); quality and not-as-advertised gains are within noise. **How the decision was reached, stated plainly:** the first precision-by-state table pooled training and test rows; the direction was then confirmed on training rows alone (defect precision 0.69 to 0.79, F1 0.733 to 0.767), so the training result is the basis and the test result is historical confirmation, not selection. This does not change the 0.80 aspiration being unmet for defect (0.77).

**Recommendation (needs the owner's approval; not enabled):** adopt `require` for defect, quality and not-as-advertised, and show flags without evidence as "unverified" in the interface if they are shown at all.

## 6. Known remaining gaps

* The core lexicon's original rule ("damage with a packing word nearby is a shipping matter") also hides item damage in the same sentence ("yupi ang box at basag ang takip"). It predates this work; it is documented in `annotation_policy_v2.md` (decision A) and not changed.
* Listing-comparison flags are right only 47% of the time; their "evidence" is the sentence plus the listing part, which a person must read side by side.
* Offsets are relative to the sentence and to the original review; they do not survive a re-segmentation of the same text by a different splitter.
