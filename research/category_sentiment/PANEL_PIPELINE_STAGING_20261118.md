# Panel-aligned Product → Sentiment → Category → Hazard → Output pipeline

Prepared: 2026-11-18. Source base: deployment `fc56fa956732c46d9b2d0149ff9c28dbb1bb814c`.
Status: **feature branch / candidate for isolated staging, NOT deployed or qualified**.

## What changed

1. **Product:** The existing listing title and review texts enter the unchanged backend.
2. **Initial sentiment:** Existing production XLM-RoBERTa ONNX classifies every review as Positive, Neutral, or Negative. No model/tokenizer/weights were replaced. Neutral stays a first-class result.
3. **Category-aware check:** Refined product-title categorizer `pc6` recognizes the existing 49 product categories (+ `other`) and handles high-specificity product heads (toy car, lipstick, shampoo, serum, protein supplement) and MPPT solar controllers. The opt-in `DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW=shadow` module proposes a contextual sentiment label for **narrow, explicit** phrases only. It never overwrites initial sentiment; all stored output remains on production labels. Category is taken only from the product title, never the review, user-supplied category, or product description.
4. **Hazards:** The existing hazard detector still examines **every** review independently of its initial or proposed sentiment. Its model files and learned-hazard hash gate are untouched.
5. **Final output:** Existing report/vetting decisions and review sentiment remain the source of truth; proposed category corrections are additional nonauthoritative metadata only when explicitly enabled.

Stage 3 is a **logical interpretation stage** after initial sentiment. Title classification can be computed earlier in the actual backend to support existing hazard rules. Do not change model input order or make all hazard checks contingent on a Negative label.

## Category revision, saved reports, and safety

- `PRODUCT_CATEGORY_REVISION` changes from `pc4` to `pc6`: **new analyses may have different category-specific hazard exemptions or additions**. Therefore changing category selection is NOT a harmless UI-only modification; a proper before/after hazard and verdict audit is needed.
- Existing stored categories and previous verdicts must stay traceable; do not rewrite old SQLite rows or relabel saved reports on display. Re-run a fresh scan only when authorized and preserve the previous version for comparison.
- Both changed-category and unchanged-category examples need checking for safety false negatives; especially include PowMr inverter, actual game controllers, charger/cables, phones, cosmetics, toys, clothing, and appliances.
- Set `DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW` to empty or leave unset in production. There is **no production label-overriding mode** in this proposal. Unrecognized titles fall back to `other`.
- Existing 49-category taxonomy and data collection remain unchanged; product-specific conclusions and frontend UI are untouched.

## Actual evaluation evidence

The separate 2026-11-16 category adapter experiment in PR #35 did **not** establish that category-aware sentiment is more accurate than generic calibration. On historical, already-inspected 846 reviews (not independent), generic-adapter macro-F1 = 0.7215, category-aware adapter macro-F1 = 0.7131; the 95% comparison interval included zero. The earlier 15/15 known-title category result was on already selected development examples, not an independent accuracy estimate. **No new independent category accuracy, sentiment macro-F1, or hazard F1 is claimed by this change.**

## Validation and VM staging handoff

1. **CI:** Inspect the exact feature SHA and GitHub Actions matrix results for Python 3.11 and 3.12 plus frontend check/build. Run product-category and shadow no-effect tests. Do not merge a failing build.
2. **Compare categorization:** On a local/isolated copy of rights-cleared product title snapshots, score category confusion and coverage for current `pc4` vs `pc6` across all 11 groups. Sample actual ambiguous product names. Resolve unintended category changes.
3. **Compare live risk:** On a **private, access-authorized staging copy only**, re-run the existing production sentiment/hazard pipeline at the pinned baseline and this candidate for the same review/title pairs. Compare all five hazard flags, safety recall, flagged quotations, verdicts, and positive/neutral/negative labels; check that labels and final sentiment are unchanged. Reconcile *every* lost safety flag and unapproved verdict change.
4. **Evaluate sentiment candidate:** Use a new product-disjoint, rights-cleared, independently human-adjudicated review set, including Filipino and Taglish. Predeclare tests; compare raw XLM-R, generic adapter, and category-aware shadow on the **same reviews**, with coverage, macro-F1, per-class F1, group metrics, and confidence intervals. Do **not** optimize to historical/frozen tests, mistake AI labels for independent gold, or auto-enable corrections from an apparent development gain.
5. **VM footprint:** Verify the deployed VM commit, free RAM, model hashes and backup integrity. On isolated staging run memory, latency, full E2E, old-report recheck handling and rollback rehearsal. The live service remains unchanged until signed-off.
6. **Authorized release:** After all gates pass, use a reviewed, fast-forwardable deployment commit and separate authenticated VM access. Snapshot both databases and the previous exact commit, deploy with shadow **OFF**, run real HTTP/saved-report/safety smoke tests, monitor, and roll back if warning behavior differs unexpectedly. Never force push or modify production from CI.

No SSH/Azure credentials are available in this ChatGPT session. Creating this branch or PR **does not deploy** to `defaketive.duckdns.org`.

## Safety decision

Safe next step: independent **staging evaluation** of refined title categorization with the sentiment shadow disabled (and optional isolated shadow measurement). Unsafe next step: turning on automatic Positive/Negative flips in production before validation.
