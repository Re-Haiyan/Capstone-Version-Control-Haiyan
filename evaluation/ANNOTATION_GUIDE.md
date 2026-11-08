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
