# Aspect sentiment and the 10,000-review annotation queue

The existing pool is input data, not 10,000 verified annotations. The local
`annotation_batch_10000/annotations.csv` contains machine proposals (where
allowed) and empty human fields. Nothing is approved automatically. No model
weights are retrained by these scripts.

Completed local batch: 10,000 rows / 10,000 unique normalized texts; 7,740
training candidates, 1,021 validation candidates, 939 blind test candidates,
and 300 previously exposed examples. There are 9,061 machine proposals and
zero human approvals. All proposed and human labels have separate fields.

## Labeling rules

- Positive: explicit approval or satisfaction.
- Negative: explicit dissatisfaction or a reported failure.
- Neutral: factual content with no clear positive/negative opinion.
- Mixed: both positive and negative opinions in the review. Do not collapse
  this into neutral during annotation.
- Unclear: insufficient context, unintelligible text, unresolved sarcasm or
  ambiguity. Do not guess from the star rating.

Annotate each explicitly discussed aspect: delivery, packaging, seller_service,
price, quality, functionality. Do not infer a product failure from poor delivery,
or a counterfeit allegation from negative sentiment. Preserve the existing
safety/defect/counterfeit labels as a separate task.

Record `human_aspects` as a JSON list, for example:

```json
[{"aspect":"delivery","label":"positive","text":"Fast delivery","span":[0,13]}]
```

Offsets count Unicode characters, not bytes or JavaScript UTF-16 units. Evidence
must be an exact substring. Use `[]` for no supported aspect. The proposed cue
layer deliberately abstains on ambiguous/multiple-topic clauses and is not a
faithful explanation of the transformer's internal reasoning.

## Human review

Read the whole review, correct rather than copy proposals, fill human_sentiment,
human_aspects, reviewer and reviewed_at (ISO date/time), then set annotation_status
to `approved`. Leave disputed cases pending with notes. Independently double-label
at least 10% and all ambiguous cases; adjudicate disagreements and report agreement.
Low model confidence prioritizes review; it is not a calibrated probability of truth.

## Splits and leakage

The stable normalized-text hash keeps exact/normalized duplicates in one split.
Previously exposed gold and held-out examples are marked `legacy_exposed` and
must not count as a fresh evaluation. Other buckets are roughly 80% train, 10%
validation and 10% blind test candidates. Blind rows receive no suggestions or
stars. Do not tune from them or open their labels until the candidate is frozen.

Historical model-training overlap is unknown, and product IDs are absent; these
are test *candidates*, not a certified independent benchmark. Acquire a fresh,
human-labeled product/time-disjoint set to establish independent performance.
Check near-duplicate review templates before training. Do not present a machine-
labeled sample as human gold, or tune thresholds on the test set.

## Commands (from repository root)

```powershell
backend/.venv/Scripts/python.exe scripts/annotate_reviews.py
backend/.venv/Scripts/python.exe scripts/export_approved_annotations.py evaluation/annotation_batch_10000/annotations.csv evaluation/annotation_batch_approved
```

Both commands refuse to overwrite an output directory. The exporter rejects
missing approvals, invalid evidence and duplicate groups crossing splits. Test
and legacy-exposed records are exported separately, never into train.jsonl.
Generated annotations remain local and Git-ignored.

## Adoption gate

The app's optional `aspect_sentiment` field is an experimental rule-cue layer,
shown as “Opinions by topic · Preview” on newly analyzed reviews. Older reports
continue to work without it. Model-version suffix changes mark old reports stale;
saved reports are not silently rewritten. Overall sentiment and hazard verdicts
remain unchanged. This is expanded explainability, not a proven accuracy gain.

After human approval, train a candidate separately; compare macro-F1, per-class
precision/recall, confusion matrices, aspect evidence accuracy and latency to the
existing model. Use validation only for tuning. Keep the current model until a
fresh independent test demonstrates a gain without hazard regressions.

## Direct AI annotation (separate from classifier proposals)

`annotation_batch_ai_direct/part_1.tsv` through `part_10.tsv` contain direct
AI text judgments. Annotators receive IDs and complete review text only, not
star ratings or existing model/gold labels. These are AI-reviewed silver labels,
not human approvals. Each row carries overall sentiment, judgment confidence,
and sentiments for explicitly discussed aspects. Evidence spans are not part
of this direct-label dataset; do not misattribute the app's rule highlights to
the direct annotators.

After all batches finish, validate and assemble them with:

```powershell
backend/.venv/Scripts/python.exe scripts/merge_direct_annotations.py
```

The assembler requires all 10,000 assigned IDs exactly once and preserves source
texts and original split assignments. Output has CSV, separate split JSONL files,
input/output provenance hashes, counts and a manifest. The source pool and original
blind queue remain unchanged. Former blind examples are labeled in this separate
copy, so this copy is **not** an untouched test set. Disagreements with prior
proposals and lower-confidence judgments are flagged for adjudication, not silently
called corrections. No training or deployment is performed by the assembler.

`complete_ai_annotations.py` is a different, optional automated-prediction workflow;
it uses the existing classifier and rules and must not be described as direct AI
review. Do not confuse its output with the direct annotation batches.

## Enhanced dataset, review heads and human-review tools (November 9, 2026)

**Combined dataset.** `scripts/build_enhanced_dataset.py` writes
`evaluation/enhanced_dataset_v1/` (refuses to overwrite): FiReCS train/test and
SentiTaglish from `origin/Version-1.2` plus the 10,000-review pool, 20,525 rows.
`label4` keeps mixed; `label3` maps mixed to neutral; unclear rows are not
trainable. Splits: `test_firecs` (official FiReCS test), `test_pool` (pool test
candidates), `legacy_exposed` (gold/held-out rows, never trained on),
`validation`, `train`; an assert checks no test text leaks into training.
`pool_enriched.csv` adds stars, star/text mismatch, the live model's label and
hazard tags, template and language flags. Pool labels are AI silver labels.

**Review heads.** `scripts/train_review_heads.py` trains logistic-regression heads
on the shipped XLM-R encoder (mean last hidden layer + log probabilities, one ONNX
run): sentiment, a mixed detector and six aspect mention/polarity heads, into
`backend/sentiment-analysis/models/review_heads_v1/`.

| Set (macro F1, text only) | Shipped model | Heads |
|---|---|---|
| FiReCS test, human labels (3,147) | 0.833 | 0.836 |
| Pool test, AI labels (930) | 0.784 | 0.835 |

`scripts/check_review_heads.py` runs both through the app with stars: hazard flags
identical on all 1,231 reviews, but on the small gold (150) and held-out (76)
high-confidence sets the heads scored lower (0.872 to 0.861 and 0.849 to 0.759).
Because the gain appears only against AI labels, the heads' sentiment label was
**not** adopted.

**What the app serves.** The default `xlmr` model keeps the shipped label exactly
(same logits; `model_version` unchanged, so saved reports stay current) and adds
the heads' extras to each review: `sentiment_extra.mixed`,
`aspect_sentiment_learned` and `review_signals` (template, star/text conflict),
versioned as `extras_version`. Missing head files fall back to the plain model
with a warning; `DEFAKETIVE_REVIEW_EXTRAS=0` turns the extras off.
`DEFAKETIVE_SENTIMENT_MODEL=xlmr_heads` serves the heads' label instead (not
recommended until it beats the shipped model on human labels). Hazard checks always
read the shipped model's labels, so their calibration is unchanged.

**Human review (`scripts/review_queue.py`).** `export` wrote
`evaluation/human_review_round1/`: `adjudication.csv` (3,715 flagged rows, most
likely wrong first) and a blind stratified `double_label.csv` (1,001 rows) for two
people. `agreement <folder>` reports agreement and Cohen's kappa against the AI
labels and between humans. `fresh-test` wrote the template for a new frozen,
two-annotator test set (`evaluation/fresh_test_v1/`). `next-round <csv>` ranks new
reviews by model uncertainty for the next labelling batch.

## Sentiment blend, now the default (November 9, 2026)

`scripts/sentiment_boost_experiments.py` compared 24 GPU-free candidates under a
rule written before any result: not lower than the shipped model on FiReCS test
and on the team-labelled 300 (with the app's star rule), and >= 0.01 higher on one.
Tuning used human validation rows only. Winner: Lazada form fields rewritten as
sentences ("Battery Life:matagal" -> "Battery Life: matagal.") and probabilities
blended 0.6 shipped / 0.4 a head trained on human labels only
(`scripts/build_sentiment_blend.py` -> `models/sentiment_blend_v1/`).

`scripts/check_sentiment_blend.py` (app path, stars, paired bootstrap 95% CI of
the macro-F1 difference):

| Set | Shipped | Blend | Difference 95% CI |
|---|---|---|---|
| FiReCS test, human (3,147) | 0.833 | 0.838 | +0.001 to +0.010 |
| Team-labelled 300, with stars | 0.818 | 0.844 | -0.002 to +0.054 |
| Pool test, AI labels (931) | 0.789 | 0.811 | +0.010 to +0.035 |

Hazard flags: identical on all 1,231 reviews. The team set was also used to pick
the winner among 12 qualifiers, so its gain is optimistic.

Serving: the default `xlmr` now returns the blend label with its own
`model_version` (saved reports are re-analysed) plus the mixed/aspect extras;
hazard checks still read the plain shipped model on raw text.
`DEFAKETIVE_SENTIMENT_BLEND=0` restores the shipped label (extras only), and
adding `DEFAKETIVE_REVIEW_EXTRAS=0` serves the plain shipped model.
