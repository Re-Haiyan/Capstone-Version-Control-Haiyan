# Category-aware sentiment: shadow-only prototype (16 November 2026)

## What exists now

DeFaketive already derives a product category from the listing title and uses it in **hazard/defect rules**, but the shipped XLM-R sentiment model receives the original review text without a category token. The ONNX model was evaluated using that original text. Prepending a category to its inputs without retraining and testing would change the input distribution and might affect the learned hazard system that uses the same encoder.

This branch introduces a **small, opt-in, conservative shadow interpretation** for a few phrases whose meaning depends on product type. It is **not** a general category-conditioned sentiment model and **does not** change the deployed positive/neutral/negative label. The existing classifier, thresholding, calibration, learned hazard gating, report result, weighted sentiment split, and model version remain identical.

## Switch and output

Set `DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW=shadow` only in a **private, separate research run**. The default is off. There is **no on/production override mode**.

When the title matches a supported category and a narrow phrase fires, the review analysis gets:

```json
"sentiment": {
  "label": "neutral",
  "category_shadow": {
    "revision": "category-sentiment-shadow-v1",
    "mode": "shadow",
    "product_category": "apparel",
    "deployed_label": "neutral",
    "candidate_label": "negative",
    "disagrees": true,
    "rule": "fabric_too_thin",
    "matched_text": "sobrang nipis ng tela",
    "used_for_decision": false
  }
}
```

The candidate does **not** appear as an official prediction, is **not** in the product summary and does **not** change the risk checker.

## Current illustrative phrase families

- **Phone/laptop/tablet:** clearly praised thinness can be a favourable design comment.
- **Clothes/home textiles:** explicitly too-thin fabric can be a complaint.
- **Solar power/battery products:** explicitly reported overheating can be a negative signal. Such text must still be processed independently by the real safety checker; sentiment is not a safety classifier.
- All other categories, unknown products, negated phrases and unsupported wording **do not get a proposal**. This conservative, low-coverage behavior is deliberate.

**Known dependency:** Earlier an inverter with “Solar Controller” in its title was misclassified as `gaming`. Category accuracy must be measured before any category-aware sentiment system is promoted. The classifier repair is tracked independently in PR #29; it must be assessed and integrated safely rather than bypassing the category source.

## Requirements before deciding on production use

1. Validate product-category assignment against hand-checked titles in all marketplace groups; measure errors and false matches.
2. Collect rights-cleared, **human-labelled** English, Filipino and Taglish reviews across multiple product categories, with product-disjoint train/dev/test splits. Do not evaluate on reused or AI-labelled development text as though it were a gold holdout.
3. Compare **unchanged production XLM-R** vs. category-aware candidates on the exact same reviews. Report macro-F1 and per-class recall (particularly neutral), disagreements, category confusion, false positive/negative rates, and confidence intervals. Report candidate coverage; rule-only accuracy on fired examples is not overall accuracy.
4. Check complaint/safety interactions separately. Category-conditioned sentiment cannot dismiss hazard reports or silently change the hazard scorer's sentiment gating.
5. Only after independent evidence of a meaningful improvement should a separately versioned category-conditioned sentiment model or a gated post-processor be proposed, with explicit roll-back and resource checks on the VM. Do not modify the existing ONNX files/manifest or fake qualification flags.

## Local/CI checks

```bash
PYTHONPATH=backend/sentiment-analysis python -m unittest discover -s tests -p 'test_category_sentiment_shadow.py' -v
PYTHONPATH=backend/sentiment-analysis python -m unittest discover -s tests -p 'test_product_category.py' -q
```

Full regression and frontend build are run by `.github/workflows/category-sentiment-shadow.yml`.

**Research only. Do not merge into production as a claimed sentiment improvement or deploy a new model based on these synthetic tests.**
