# Combined live Category UI + pc6 panel flow: guarded release notes

**Status: draft for isolated VM staging; production must remain at 40aa8c6 until these gates pass.**
PR: https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan/pull/47

## Architecture

1. Product listing title + reviews.
2. Existing shipped XLM-RoBERTa initial three-class sentiment (Positive / Neutral / Negative).
3. Refined pc6 title classification (49+Other). Category-specific *sentiment suggestions* are strictly shadow-only and opt-in; default production mode is OFF, and no sentiment label is overwritten.
4. Shipped five-label Hazard Checker runs on **all** review texts regardless of sentiment. Category terms/exemptions can still affect its outputs when the title category changes.
5. Existing final conclusion, advice, evidence, summary and saved Category chip.

No ONNX/tokenizer/learned-hazard/threshold replacement is proposed. Do not claim improvement in sentiment F1; the independent evidence is insufficient.

## Saved-report compatibility change

`backend/dashboard_utils.analysis_is_current` accepts a pc4 stamped report as current **only** when:
- Its saved title-based product category equals the current pc6 classifier's category.
- Its stored group (if present) still matches.
- Every included review carries the *exact* current model-version string with just the `+pc6+` component replaced by `+pc4+`.

A pc4 report with a missing/changed category, an older unrelated model, changed weights or thresholds is stale. It remains served as a **historical report**, with no optimistic purchase guidance, until the user explicitly rechecks. The saved Category chip still displays the historical category on those reports, not the guessed pc6 category.

`backend/webapp._analysed` now loads existing saved reports and imported files without silently running a massive synchronous reanalysis on app startup. New scans and explicit uploads can still run the current model as before. This avoids a 2.7-hour implicit bulk recheck of the shared database.

**Expected:** A small number of saved reports may correctly become stale (Claude previously observed one category change among 376 products, plus two missing category fields across 412 saved records). We must measure the exact current/stale counts again on the actual 412-product VM corpus; do not claim all 412 remain current unless verified.

## GO/NO-GO checks

1. Full CI on *exact* PR47 SHA: Python 3.11/3.12 regressions, 25+ category cases, explicit saved-report compatibility tests, frontend check/build, unchanged model assets and the read-only paired hazard audit versus live base `40aa8c6`.
2. On actual VM, verify live SHA, files, disk/memory and databases with the dedicated `deploy/panel-category-vm-preflight.sh` command in a separate candidate checkout. Use `--paired` on a read-only SQLite connection; compare at least 900 saved reviews when available. No raw reviews are uploaded.
3. Count saved reports **before and after** using the exact same 412 DB records, without writing. For each newly stale report, record the category mismatch or missing/older stamp. All other previously current reports must stay current. Fail if there are unexpected stale reports or a changed hazard/verdict.
4. Exercise fresh solar inverter, genuine Xbox/PS5 controller, supplements, skincare, apparel and accessory scans in isolated staging. Verify their categories, five hazard flags, sentiment and recommendations. All reviews are analyzed for hazards; test both positive and negative text.
5. Verify saved reports load quickly without reanalysis and their stored flags/recommendations remain unchanged. Compare first-load RAM/latency to the live version.
6. Snapshot both SQLite DBs with online backup API, verify integrity, rehearse restoring exact previous code/build, and get explicit release approval. No DB backfill is planned.
7. Shadow sentiment stays OFF in production (`DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW` unset), no ONNX swaps, no deployment without signoff.

**Any unexpected lost safety report, unrelated model version accepted as current, implicit DB rewrite, stalled startup, or failed validation is an immediate NO-GO.** No GitHub PR merge equals deployment to Azure.
