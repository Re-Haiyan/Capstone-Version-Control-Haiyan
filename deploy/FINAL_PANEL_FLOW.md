# Final panel process: shared XLM-RoBERTa + category context + independent hazards

**Candidate branch:** `feature/panel-flow-pc6-compatible-20261118` / PR #47
**Deployment status:** NOT LIVE; frozen deployment remains `40aa8c6` until VM staging gates pass.
**Business decision:** The category step is implemented. **Automatic sentiment correction is NOT qualified** and MUST stay disabled.

## The five-stage processing flow

1. **Product** — Extract the product listing title and review texts; pc6 identifies a title-derived product category (49 named categories + Other). Never assume an uncertain listing is a particular category.
2. **Shared XLM-RoBERTa** — Analyze every included review for initial Positive, Neutral or Negative sentiment. Do not prefix category to the encoder input; the shipped ONNX and tokenizer are unchanged.
3. **Category-context check (read-only and always enabled in NEW candidate analyses)** — Look up the product's category profile and match short, explicitly contextual review phrases, including Taglish.
   - `agrees`: an example suggests the same sentiment as the initial model.
   - `differs`: an example suggests a different interpretation; this is NOT proof the initial model is wrong.
   - `ambiguous`: the sample is negated or contains conflicting cues; abstain.
   - `no_signal`: no exact example; abstain.
   - `unclassified`: the title classified as Other; abstain.
   - The stage emits audit metadata `sentiment.category_context` with `used_for_decision=false` and `sentiment_overridden=false`.
   - The 49 examples are illustrative, not 49 independently validated sentiment classifiers. There is no unconditional label flip and no separate `on` switch.
4. **Independent five-label Hazard Checker** — Process **all** included reviews regardless of sentiment or context status. Maintain all existing flags for safety, defect, counterfeit, quality and not-as-described, including their existing category-aware rule exemptions and qualifiers. No positive sentiment exempts a review from hazard checks.
5. **Final product conclusion** — Existing counts, warnings, supporting reviews, recommendation, and disclaimer. Under the Category chip, a small truthful diagnostic count appears when NEW reviews have step-3 metadata: matched vs. checked and number of differing suggestions. The diagnostic says explicitly that sentiment and warning outcomes are unchanged.

## Example contexts, NOT authoritative labels

| Listing | Exact phrase | Context signal |
|---|---|---|
| Smartphone | Ang nipis, ang ganda | Positive |
| Clothing | Sobrang nipis ng tela | Negative |
| Powerbank | Sobrang init habang nagcha-charge | Negative |
| Food | Mainit at bagong luto | Positive |

An ambiguous phrase alone has no meaning: a heater being hot could be intended or defective. Negations such as "hindi sobrang init" abstain. Sentences matching both positive and negative cues also abstain. The checks use whole phrases, not substring matching in another word.

## Release constraints

- The earlier 846-review historical category-aware adapter was worse than the generic comparator: macro-F1 0.7131 vs 0.7215. Narrow rule suggestions changed just one label in that historical test. These results do **not** meet the team's >= 0.80 or independent validation requirements.
- `DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW` is separate from the always-on *read-only* profile check. It can record narrow additional experiments but cannot make automatic production corrections.
- Include all profile mappings from `category_context_profiles.json` (49 categories) and preserve `other` fallback.
- Before a VM merge/deploy: all Python 3.11/3.12 backend and Svelte/Node tests pass, baseline/candidate paired audit shows no lost hazard reports or changed verdicts, exact-model files have matching SHA, and VM read-only audits confirm saved-report compatibility against the actual database.
- The pc6 saved-report handler preserves historical report data rather than automatically rerunning the entire 412-product catalog. Reports whose categories changed are marked older and should be explicitly rechecked.
- Stage new scans in isolation; verify product-specific outcomes, CPU/RAM/latency and rollback on the 2-vCPU VM. Back up both DBs before any approved release. No live DB edits are needed merely to expose context metadata on fresh scans.

## When to enable real automatic category corrections in the future

Freeze the candidate first, obtain a **new independently human-adjudicated and product-disjoint holdout**, verify its ONNX predictions and label provenance, and demonstrate improved macro-F1 (team threshold >= 0.80) without increasing negative/hazard misses. Only then add a separately reviewed, off-by-default override policy with a new model/version stamp and safe report-backfill plan. Until then **all authoritative sentiment labels remain from shipped XLM-RoBERTa**.

**Do not present this feature as an independently validated sentiment correction in the capstone paper or UI.** It is an implemented, auditable *category-context interpretation* step.
