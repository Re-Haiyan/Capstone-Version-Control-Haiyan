# Decision record — automatic category-based sentiment correction

**Date:** 2026-11-18  
**Decision:** NO-GO for automatic sentiment label replacement. Keep the contextual
step implemented but **shadow-only**; do not deploy a sentiment override.

This is a completed decision on the *current candidate*, not a claim that
category context can never improve sentiment. It addresses the explicit request
to finalize the panel flow without fabricating improvements.

## What was actually tested

- Shipped XLM-RoBERTa three-class sentiment probabilities (preexisting
  research cache; NOT cryptographically bound to the current ONNX binary).
- The pc6 title-derived category-specific narrow cues: thin-device praise,
  thin-fabric complaint, battery/powerbank overheating complaint.
- The hypothetical outcome *if* the category rule replaced XLM-R's label,
  compared on every review against existing **team-supplied silver labels
  of unverified annotation provenance**. Changes are evaluated offline only.
- `research/category_sentiment/audit_category_rules.py` computes macro-F1,
  per-class F1, changed-label precision and product-cluster bootstrap.
  Results are reproducible through `category-sentiment-rule-audit.yml`.

### Paired rule results, historical (not independent)

| Set | Rows | Hypothetical changed labels | Matched reference after change | Worsened compared to reference | Macro-F1 delta |
|---|---:|---:|---:|---:|---:|
| Training dataset (descriptive, NOT out-of-fold) | 3,946 | 5 | 3 | 2 | 0.0000 |
| Previously inspected historical test | 846 | 1 | 1 | 0 | +0.0012 |

- Product-bootstrap macro-F1 delta 95% interval: training **[-0.0016, +0.0014]**;
  historical **[0.0000, +0.0037]**. The latter is not an independent
  significance or production claim; it arises from just **one** label change.
- Total rule coverage is very low, and one of five changes in training did
  not consistently help (2 worsened). Neither the 0.80 target nor a category
  improvement is established. There is no credible case to flip live labels.
- These rules are *not* a production-trained 49-category sentiment classifier.

### Separate learned-adapter comparison, also exploratory

The already studied 846 historical marketplace reviews scored:
- Generic XLM-R calibration: **0.7215** macro-F1.
- Category-aware XLM-R calibration: **0.7131** macro-F1.

The category-aware variant was worse than the generic on this inspected set;
the product-bootstrap comparison crosses zero. Training labels are silver and
historical evaluation is not independent. Neither candidate is qualified.

Reference: `research/category_sentiment/RO_BERTA_ADAPTER_EVALUATION_20261116.md`
on `research/category-aware-sentiment-shadow-20261116`.

## Finalized architecture and release behavior

**Product title → XLM-R (Positive / Neutral / Negative) → title-derived
category context → independent five-label Hazard Checker on ALL reviews →
evidence-backed product conclusion.**

The panel's logical Category-Aware Check is present. Currently it can record
non-authoritative research suggestions; it does **not** change the released
sentiment label or the hazard/verdict. This separation is intentional. Do not
describe it to the panel as a validated sentiment improvement.

The feature branch `feature/panel-flow-pc6-compatible-20261118` and draft
PR #47 combine the live Category UI, pc6 title disambiguation, narrowly
compatible pc4 saved-report handling and research-only category context. This
decision record **does not authorize merging or VM deployment**; the VM
must pass the separate live-data staging/release gates in
`deploy/PANEL_PC6_COMBINED_RELEASE.md`.

**Fail-closed activation:** `DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW=on` is NOT
an activation flag. The existing `category_sentiment.suggest()` only returns
audit metadata when its shadow mode is explicitly enabled; tests assert
`used_for_decision=False` and unchanged actual labels.

## What would qualify a future real correction

1. Freeze the candidate and its category model, code, encoder SHA, data policy
   and decision thresholds *before* evaluation. Verify the ONNX probability
   inputs against actual offline inference.
2. Obtain a **new, independently adjudicated, product-disjoint sample** of
   real marketplace reviews with EN, Filipino, Taglish, positive, neutral and
   negative language, plus diverse ambiguous products. Record two human
   independent ratings and adjudication; no training or prompt tuning on
   that holdout. Confirm data rights.
3. Compare **three systems on the same sample**: shipped XLM-R, stronger
   generic adapter, and category-aware candidate. Report macro-F1, per-class
   precision/recall/F1, confusion matrix, changes fixed/worsened,
   product-cluster CIs and performance per group/category.
4. Predefined acceptance: category-aware macro-F1 at least **0.80** (team
   target), statistically supported improvement over the stronger comparator,
   no deterioration of negative/safety-related recall, and no unreviewed lost
   genuine hazard flag or more favorable hazardous verdict.
5. Stage on the Azure VM with label-only off switch, report-version
   compatibility checks, load/latency/memory monitoring, DB backup and
   rollback rehearsal. Changing saved sentiment outputs requires a new
   model-version stamp and consent for any backfill; do not silently
   misrepresent old results as new.
6. Only after all gates, add a separately reviewed production activation path;
   do not enable one based on historical silver-score improvements.

**If the future independent benchmark fails, retain original sentiment
and category-aware explanations instead of forcing corrections.**
