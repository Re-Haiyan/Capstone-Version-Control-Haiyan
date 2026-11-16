# Category-aware RoBERTa sentiment — first paired comparison

Date: 2026-11-16. All numbers below are **research-only**, not deployment validation.

## Model setup

- **Baseline:** existing qualified XLM-R ONNX model, raw text, three probabilities.
- **Generic adapter:** logistic regression over word/character TF-IDF, unchanged RoBERTa probabilities, and star ratings.
- **Category-aware adapter:** identical generic adapter + group/category and group × ambiguous-word indicators derived from the product title; unchanged ONNX model weights and text input.
- The same training/validation rows are used for paired comparisons. Train: 3,946 **team-supplied, provenance-unverified SILVER labels**, 302 products in five product-disjoint stratified folds. Historical test: 846 labels, 82 products, previously inspected during development (not independent).
- Candidate selection is forbidden on the historical test. The preexisting probability cache is not independently tied to an audited inference run; comparisons are exploratory.

## Results

| Metric | Original XLM-R | Generic adapter | Category-aware adapter |
|---|---:|---:|---:|
| Training-set 5-fold product-disjoint out-of-fold macro-F1 | 0.6047 | 0.7102 | 0.7135 |
| Training-set out-of-fold accuracy | 0.7055 | 0.7737 | 0.7739 |
| Training-set out-of-fold neutral F1 | 0.2436 | 0.4670 | 0.4742 |
| Historical test macro-F1 | 0.5697 | **0.7215** | 0.7131 |
| Historical test accuracy | 0.6548 | **0.7707** | 0.7671 |
| Historical test neutral F1 | 0.1862 | **0.4937** | 0.4675 |

Product-cluster bootstrap delta, **category-aware − generic**, 95% interval:
- Product-disjoint OOF: **−0.0063 to +0.0143**, point estimate +0.0033 macro-F1.
- Historical test (descriptive only): **−0.0292 to +0.0153**, point estimate −0.0084 macro-F1.

Both intervals include zero. Therefore there is **no demonstrated reliable benefit** to category-awareness on top of generic calibration in these data. Indeed the historical aggregate result favors the generic adapter.

Other caveats:
- Category-aware model changes 881/3,946 historical training OOF predictions relative to raw XLM-R and 194/846 historical test predictions; those shifts are material and cannot be pushed without independent review.
- A product title (e.g. a solar inverter containing the word controller) can be misclassified. The research adapter abstains on this known ambiguous case; complete title-category quality remains unmeasured.
- Safety/hazard flags must remain independent of sentiment; these experiments did not measure independent real-world safety failure rates.
- User-visible data in the screenshot such as "Small Appliance" is a UI concern: category can remain hidden from shoppers while being used as internal model context.

## Deployment decision: NOT QUALIFIED

`qualified_for_integration = false` and `enable_production_predictions = false` are intentional. **Neither the RoBERTa encoder nor any category-aware adapter should be changed in production based on this comparison.**

The architecture is implemented in research as shadow-only; tests ensure the current positive/neutral/negative label and hazard signals are unchanged. No activation switch is provided.

### Necessary remaining steps

1. Verify title-to-category accuracy with a diverse, human-checked marketplace sample (including accessories, cross-category descriptions, solar equipment and ambiguous listings). Fix misclassification with versioned rules and tests.
2. Establish review label provenance: two independent human annotators and an adjudicated reference sample, including Taglish/Filipino and neutral examples across groups. Ensure product and review-text disjointness from model development.
3. Freeze the candidate and test on a **new, untouched product-disjoint reference set**, with per-class F1/recall, confusion matrices, group-specific metrics, product-cluster 95% confidence intervals and error categories. Compare category-aware against the stronger **generic adapter**, not just raw XLM-R.
4. Require a meaningful preset improvement over the stronger generic baseline **and no important regressions** for neutral, safety-related negative reviews or any substantial category. If it fails, use the stronger generic system only after *its own* gate.
5. Audit model artifact SHA, runtime memory on the Azure VM, inference latency, rollback and versioned reanalysis. Never bypass the original XLM-R encoder hash gate required by the learned hazard model.

### Reproduction

```bash
python research/category_sentiment/compare_roberta_adapters.py --output /tmp/category_metrics.json
```

GitHub Actions (initial complete comparison): https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan/actions/runs/43797182120

This report is a transparent research evaluation, not a final capstone accuracy claim.
