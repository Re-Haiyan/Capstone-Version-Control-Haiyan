# Phase 5B: Controlled training-label sensitivity — executed results

Status: RESEARCH ONLY. Three predeclared label-selection/weighting comparisons completed on 2026-11-15 in GitHub Actions. This is a word/character TF-IDF plus LinearSVC text baseline, NOT a retrained XLM-RoBERTa model.

## Reproducibility

- Source branch: research/phase5b-sensitivity-cv, CI run 43719556765.
- Script: phase5/phase5b_sensitivity.py; the full per-seed confusion matrices, supports and metrics are in GitHub Actions artifact phase5b-lexical-sensitivity/sensitivity.json.
- Original v1 Claude annotations remain unchanged. Second GPT-6 annotation disagreements are used only for training-set exclusion or weight selection.
- Missing Phase 4 embedding caches and private product-ID mapping prevent exact XLM-RoBERTa experiments from GitHub alone. This experiment instead uses NORMALIZED PRODUCT TITLES as a group proxy and is NOT verified marketplace product-ID disjoint.
- 3,400 original development rows; 122 mixed/unclear omitted; 35 missing product titles omitted; 3,243 eligible rows across 285 normalized title groups.
- The GPT-6-reviewed samples cover 90 title groups; all these groups are excluded from every evaluation subset. Evaluation n=1,695 (natural dev n=310, non-tag-list n=498).
- Three seeds (11/12/13), 5-fold StratifiedGroupKFold, same train/validation folds for all three variants. No customer review text, production weights or model outputs are committed.

## Mean development scores across seeds

| Variant | All unreviewed Macro F1 | Natural dev Macro F1 | Natural dev Neutral F1 | Non-tag-list Macro F1 | Filipino+Taglish Macro F1 | Filipino+Taglish Neutral F1 |
|---|---:|---:|---:|---:|---:|---:|
| A: unchanged labels | 0.8526 | 0.8332 | 0.8251 | 0.7782 | **0.7582** | **0.4900** |
| B: exclude 71 disputed training cases | 0.8489 | 0.8296 | 0.8199 | 0.7720 | 0.7093 | 0.3449 |
| C: B plus 0.25 weight for S4 tag lists | 0.8505 | **0.8368** | 0.8100 | **0.7883** | 0.7234 | 0.4120 |

Evaluation class supports: natural dev n=310, negative=91, neutral=62, positive=157; non-tag-list n=498, negative=143, neutral=85, positive=270; Filipino+Taglish n=248, negative=80, neutral=12, positive=156. Specifically Filipino neutral=7, Taglish neutral=5. The language-specific Neutral results are unstable; 0.80 is not demonstrated on independent data.

## Decision

**Reject the automatic adoption of B or C.** B consistently loses ground in most subsets. C has only a small development Macro F1 improvement in natural and non-tag lists while reducing Neutral F1 and worsening Filipino/Taglish performance. This pattern is too mixed to justify using it as a default, changing model weights, or changing product conclusions.

The user-facing shipped XLM-RoBERTa is not evaluated here. P4A and top-two-layer models remain research candidates only, and deployment is blocked. This experiment does not solve ambiguity of S4 buyer-selected tags or replace independent human/reference data.

## Required next steps

1. Obtain a documented team/adviser decision on S4 and register a separate approved annotation policy version; do NOT overwrite frozen policy v1.
2. Blindly double-label additional *real* Filipino and Taglish Neutral customer reviews, plus natural positive/negative controls. They must be sourced with permission; never fabricate or relabel automatically.
3. Restore/recreate Phase 4 data/head embedding caches and authentic product-ID grouping maps in a secure, reproducible environment. Record hashes and training protocol rather than committing sensitive local files.
4. Run nested product-ID-grouped comparisons and preserve a fresh authorized held-out final set; this run uses only proxy title-grouped development data.
5. Independently evaluate category-specific product conclusions and hazard/negative stability before any customer-facing rollout.

Research integrity: frozen 400-review test, used Phase 3 confirmation, and heldout v2 were not used. No production code or trained inference artifacts changed.
