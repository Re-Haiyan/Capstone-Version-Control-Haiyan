# Five-stage evidence candidate — 19 November 2026

Status: **draft review candidate; not an empirically certified release**. The synthetic regression matrix passes for all 49 named categories. Each category still has an explicitly recorded empirical coverage gap in [category-coverage.csv](./category-coverage.csv). No merge, deployment, service restart, automatic sentiment correction, or historical-report rewrite was performed.

## Baseline and boundaries

Production baseline: `4eab8ea1b3d7ffa7660343a82cfe969436cbd80b`, checked directly on the VM. The `defaketive` service remained active at PID 322622, started 09:24:10 UTC on 19 November, with zero automatic restarts and a clean tracked production checkout. Production is Flask/Waitress with a Svelte shopper frontend. This candidate descends from that exact revision and targets GitHub branch `feature/validated-category-release-ed91291` for review, not the older `deployment` branch.

The feature branch is `feature/five-stage-evidence-4eab8ea`. The exact candidate SHA is the PR head SHA. The previous HP notebook, POCO Pad, two CCTV and two LCD fixes remain covered by their existing exact-title and accessory-control regressions. No heater PR #52 changes or other draft branches were merged.

Pinned model: `defaketive-xlmr-firecs-v1-onnx-int8-e04da4c2`, one shared cached XLM-R model across categories. Label indices remain negative, neutral, positive. Raw text/128-token sentiment input is unchanged. ONNX SHA256 `e04da4c268bc8ab94e27da2e0fb4206f38dadc43e9cfb52050818a5bb40c3478`; tokenizer SHA256 `27dea7a8dd6fe22d3913c719dd962f283f7bb2d91f023abf3b1e644df39ca49e`. The production process uses default hazard_badges/xlmr/learned settings. Calibration and automatic category sentiment corrections remain off. Model artifacts, sentiment implementation, thresholds, requirements, database code and deployment code are unchanged. See [production-readonly.json](./production-readonly.json).

## Changes and observed causes

1. **Product identity:** pc9 adds narrowly guarded identities for the live-discovered ride-on toy, cotton yarn, eVoucher and circuit breaker; the USB ceiling fan; wired/wireless mice whose titles mention other devices; a CPU/Windows-qualified ThinkPad title mentioning its webcam; eye balm mentioning juice; and the juice-and-vegetable extractor whose ampersand split hid its object. Tests cover accessories, replacement parts, milk/juice, real phones and the deployed category fixes. Ambiguous titles still require review; these rules do not establish catalog-wide category accuracy.
2. **Initial model result:** the original label and all three probabilities remain visible in review details and exports. No sentiment override is introduced. The known neutral probe “Not yet tested, hindi ko pa nagagamit.” remains an uncorrected model miss.
3. **Category interpretation:** advisory observations now retain literal raw excerpts and offsets for explicit praise, explicit complaint, expected behavior and ambiguous traits. Mixed feedback keeps both observations and abstains from a single interpretation. Negated wording remains identified. Unmappable normalized wording abstains instead of inventing a source quote. Reviews over 5,000 characters no longer lose category context. Unknown items retain generic/Unclassified handling. These observations are not inputs to hazard decisions.
4. **Independent concerns:** full reviews still pass through all five concern paths regardless of initial sentiment. A punctuation/provenance edge case treated energy-saving “kuryente,kaya” as a shock cue; f10a narrowly recognizes explicit savings without removing separate shock/spark/burn reports. The food exception no longer treats sparks/explosions or arbitrary smoke as flavor. Explicit flavor/aroma and ordinary serving temperature retain their guarded exceptions. Positive, negated and beyond-sentiment-window concern regressions pass.
5. **Conclusion and evidence:** the shopper UI shows literal category excerpts beside the original model scores. Exports retain observations, mixed feedback, initial probabilities, all five flags and concern source spans. Existing evidence-grounded highlight and recommendation functions are unchanged. The replay checks their actual outputs, including the fan's changed guidance below.

## Evidence and split

The source backup was opened through SQLite `mode=ro`, with integrity check OK and SHA256 verified before/after: `/home/azureuser/defaketive-release-4eab8ea-20261119/databases/2026-11-19/defaketive.db`, 491,147,264 bytes, SHA256 `53f0b8f6dc7291cc3082afe37d8381e6d17db3ab8a6375148995344ca51df678`. Inventory: 421 saved product records and 77,155 review-table rows. Replays use entire saved `raw_json` objects, preserving available reviews, ordering and sampling metadata rather than rebuilding products from the review table.

The saved inventory initially contained 36 named categories plus Unclassified. The repository Lazada scraper filled 13 nominal category gaps using bounded keyword/direct-link samples in the isolated checkout. Initial unauthenticated attempts encountered marketplace login; a read-only copy of the existing session allowed the bounded retries. There were 21 live report observations (20 unique listings; one repeat) containing 68 review observations. The selected health-supplement and medical-device listings returned no written reviews even on the additional samples: these remain real-review gaps, not passes. Shopee/Temu live behavior was not reassessed in this audit.

The final separately labeled validation set contains **947 deduplicated rows from 120 products**, disjoint from the current development report titles. Sources are the repository's `evaluation/annotated/test_all.csv` and `evaluation/fresh/label_batch_fresh.csv`. Product-title discoveries late in the audit were explicitly removed before the final validation run. The split was amended transparently; it is not a claim that no earlier evaluation run existed. Labels were not used to tune the new rules. Model-training disjointness and historical label provenance are not verified.

Observed agreement with those historical labels: initial sentiment **687/947**; exact five-flag set **807/947**. These are agreement counts, not a newly adjudicated accuracy estimate. Flag disagreements (prediction without label / label without prediction): safety 18/3; defect 33/14; counterfeit 8/3; quality 32/6; not-as-described 21/23. They remain validation gaps, not automatic corrections or silently accepted model decisions. Independent adjudication and complete category-specific ambiguous/English/Filipino/Taglish coverage are still required.

## Complete paired replay and manual delta review

**44 complete saved report observations / 7,353 review observations**, plus **21 live report observations / 68 reviews**, were paired against exact baseline 4eab8ea. Total: **65 / 7,421**. Duplicate listing observations are counted as observations, not unique products. Every pair retained identical input hashes, review counts/order, initial sentiment labels and probabilities. Synthetic data was not substituted into these replays.

All six removed safety flags were inspected in their complete source reviews:

| Saved report index | Review index | Finding supporting removal |
| --- | --- | --- |
| 182, YUTU fan | 1096 | Electricity-saving praise with strong airflow; no reported shock or burn. |
| 182 | 1213 | Electricity-saving/affordability praise; no incident. |
| 182 | 3531 | Electricity-saving phrase followed by stray text; no incident. |
| 202, Vone fan | 48 | Relief from ambient heat at the reviewer's location; appended clipboard boilerplate. |
| 202 | 84 | Weak daytime airflow versus ambient heat; not overheating. The airflow complaint remains in the raw review. |
| 202 | 260 | Electricity-saving/power-bank operation; no incident. |

The YUTU fan remains safety_warning/not_recommended. **The Vone USB ceiling fan is the only changed backend verdict and shopper recommendation:** charger_cable → small_appliance; safety 3 → 0, defect 9 → 8, quality 35 → 34; counterfeit 1 and not-as-described 16 unchanged. Backend possible_safety_issue/caution → no_warning_signs/recommended. Actual shopper guidance caution → consider. The previous replay that retained one safety flag stayed at shopper caution; that is not this candidate's result. All three removed fan safety flags above are nonincident wording. This recommendation change is an explicit draft review item, not authorization to deploy.

Other flag deltas were inspected too. The fan's removed defect describes continuous successful operation, and its removed quality signal describes quiet/sturdy operation. One balm defect removal came from “I already opened the package,” the reviewer's own action, not an arrived-open seal; the misleading-listing concern remains. Two balm sticky-texture complaints gain quality flags. Two mouse thinness quality flags disappear under the existing peripheral exception after correct reclassification; their meaning is ambiguous, including price-qualified mixed wording. **Those thinness interpretations remain unresolved**, with original reviews and negative/mixed model feedback preserved. The lack of a claimed balm cooling effect is also a semantic coverage gap, even though the report retains a misleading-listing concern. No further recommendation changes occur.

The actual frontend recommendation function was replayed for all 65 report observations. Any remaining safety count was asserted never to yield “consider.” **397 positive-highlight source quotes** were checked against their available product reviews. See [shopper-guidance.json](./shopper-guidance.json) and [acceptance-summary.json](./acceptance-summary.json).

## Verification

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests` | 444 passed on the isolated VM candidate; real pinned checkpoint loaded. |
| 49-category synthetic matrix | 833 cases passed: praise, normal operation, complaint, ambiguity/abstention, mixed feedback, Filipino/Taglish safety, and affirmative/negated pairs for each of five flags. Literal excerpts verified. |
| Positive model prediction + independent safety | 99 matrix cases retained a safety flag with an actual initial positive prediction. |
| `node --test tests/*.test.mjs` | 65 passed. |
| `npm run check` | 0 errors; 3 existing unused-CSS warnings in the splash component. |
| `npm run build` | Passed. |
| Isolated browser shopper report | Passed: initial label/scores, literal mixed observations, hazard source and review-reported qualification, Common concerns and safety-aware purchase guidance; no browser errors. GET-only fixture server, no saved-data writes. |
| Saved-report API preservation | 50 GETs passed with inference patched to fail if called. Original categories, review text, analyses and summary retained; marked older until explicit recheck. Backup hash unchanged. |
| Pinned model/automatic rules/deployment diff guard | Unchanged. Production SHA and PID unchanged. |

The matrix is derived from category profiles and is a regression test, not independent semantic accuracy evidence. [category-coverage.csv](./category-coverage.csv) records every named category separately, including nominal inventory counts, live review counts, held-out polarity counts, label disagreements, synthetic pass and unresolved empirical status. Inventory categories may themselves contain remaining misclassifications; their counts cannot certify actual-item coverage.

Additional title-audit gaps include a desktop processor mentioning a fan, a pool cleaner mentioning its cable, an ice-cooling handheld fan, solar garden lights, a drill with a carrying case, and some helmet-intercom/VR/watch/part listings. Strong identities and ambiguous taxonomy decisions were not all adjudicated. Brand-only unclear listings remain Unclassified. No claim is made that all 421 saved categories are correct.

## Reproduction and review

Private raw inputs, reviews, cookies, individual validation rows and full paired results remain only in `/home/azureuser/defaketive-five-stage-evidence-20261119` (restricted directory). Only aggregate evidence is included in Git. Do not copy that private directory into a public PR.

Portable audit entry points:

- [five_stage_audit.py](../five_stage_audit.py): verify read-only backup, freeze/select inputs, run matrix, complete replay, compare both versions, and evaluate the separately labeled set. `--only-indices` refreshes complete reports, never a truncated review sample.
- [five_stage_preservation.py](../five_stage_preservation.py): forbid inference during historical saved-report GETs and verify backup immutability.
- [five_stage_summary.py](../five_stage_summary.py): publish aggregate category coverage without raw reviews.
- [five-stage-guidance.mjs](../five-stage-guidance.mjs): replay actual shopper guidance and check highlight grounding.
- [five-stage-evidence.mjs](../../tests/e2e/five-stage-evidence.mjs): isolated GET-only browser test, using [five_stage_ui_fixture.py](../five_stage_ui_fixture.py) to generate a real-model synthetic fixture.

Use the same verified input directory for both baseline and candidate replay processes. Set `OMP_NUM_THREADS=1`; use the deployed Python environment and pinned model. Run the full unittest command above, then matrix/holdout and Node guidance/browser checks. The feature workflow runs Python and frontend regressions with guards against changing the model, sentiment and deployment code.

**Review disposition:** retain as draft. Regression checks pass; independent empirical category/language adjudication, the mouse-thinness ambiguity, remaining catalog identity gaps, and the fan recommendation change are explicit review items. Production stays on 4eab8ea.
