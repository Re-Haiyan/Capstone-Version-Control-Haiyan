# Final report: product-specific conclusions (release-candidate validation)

Written for: the capstone team and the review panel. This report replaces the earlier version. Every figure says where it came from; anything that is
only developer-judged, emulated, or pending is labelled as such. Nothing here is a human-validated result.

## Release recommendation (§J, stated first)

**READY FOR STAGING.** Not ready for production. The reasons are in §J; in one line: the engineering and every mechanical check hold, but **no independent human has judged the
conclusions yet**, two product categories have no real reviews at all, and no staging or VM measurement of the feature exists.

## A. Final implementation status

| Piece | State |
|---|---|
| `backend/aspect_profiles.py` (data), `aspects.py` (extractor), `conclusion_text.py` (writer) | complete; this round added the relief rule for problem-type aspects, guards that combine instead of replace, the "may/might" hypothetical, `natuyo`/`hindu`/`non greasy` fixes, headline de-duplication and quantity-free warnings |
| `backend/recommendation_policy.py` | the live rules re-stated (tested equal to the live ones) and the **experimental** candidate; **not wired into the live card** |
| `backend/dashboard_utils.py`, `webapp.py` | integration; `DEFAKETIVE_CONCLUSION_REASONS=0` off-switch (tested in fresh processes) |
| Card (`verdict-block.svelte`, `types.ts`) | "Why this conclusion?", quotations, warnings as their own always-visible block |
| `scripts/sync_backend.py` | rewritten; never overwrites a locally edited file; verified in isolation and by a real dry run (`sync_verification.md`) |
| Evaluation tooling | `final_eval_pack.py` (blind sheets for two annotators, scoring that refuses without real annotations), `quality_audit.py`, `evidence_verification.py`, `aspect_validation.py`, `recommendation_policy_compare.py`, `benchmark.py`, `run_regression.py` |
| The live recommendation policy and hazard thresholds | **unchanged** (and `git diff deployment` for `backend/sentiment-analysis`, `accounts.py`, `data_store.py` is empty) |

What the feature does is described in `README.md` and `architecture.md`.

## B. Git status

| | |
|---|---|
| Branch | `feature/product-specific-conclusions` (worktree `D:\DeFaketive-conclusions`), based on `e06c98a` |
| Local commit | **ec0b53c** (`feat: add evidence-grounded product-specific review conclusions`), on `feature/product-specific-conclusions`, based on `e06c98a`. Not pushed, not merged. Since then `deployment` advanced (63eb05f, later de39603; the XLM-R study); the only overlapping file is `research/README.md`, a trivial merge. This SHA line is the only edit made after the commit, so the working tree has this one uncommitted documentation change. |
| Branch history | Pull request #2 ("category accuracy and scoped product analysis", by another contributor) was merged into this branch on the remote while Phase 3 ran (233a466); it was merged here, not overwritten (b738dbe). It narrows the profile used for supplements, bags, home textiles, charger cables and some device categories and changes the category classifier. Measured on the Phase 3 samples it changes nothing on F and one detection on D2 (`phase3/results.md`). |
| Pushed / merged / deployed | **The feature branch is pushed to the Haiyan repository; not merged into `deployment` or `main`; not deployed.** Production is on `2c6e056` (read-only check this round) |
| XLM-R work | the main checkout's untracked `research/xlmr_optimization/` and `tests/test_sentiment_agreement.py` were never touched |
| Before staging | a secret and personal-data scan of every file in the commit was run (no keys, tokens, passwords, phone numbers; the only email is the project's pre-existing default admin address in `CHANGELOG.md`; reviewer names are not in any file) |

## C. Regression results

| Check | Result |
|---|---|
| Backend tests, Python 3.11.9 (this PC) | **429 run: 429 passed, 0 failed, 0 skipped** (re-run 2026-11-15 on the merged branch tip, including the category-accuracy tests merged from pull request 2; 393 before the staging-preparation work) |
| Backend tests, **Python 3.12.10 with the VM's exact library versions** (NumPy 2.4.6, scikit-learn 1.9.0, joblib 1.5.3, onnxruntime 1.31.0) | **429 run: 429 passed, 0 failed, 0 skipped** (same suite, re-run 2026-11-15 on the merged branch tip) |
| New test files | `test_product_conclusion`, `test_sync_backend`, `test_recommendation_policy`, `test_text_rating`, `test_final_eval_pack` |
| Existing sentiment, hazard, category tests | pass, unchanged |
| Verdict and decision for the 182 saved products | **182 of 182 identical** to the baseline taken before any change |
| Production frontend build | passes |
| `svelte-check` | **0 errors, 0 warnings, 1,409 files.** The three `./$types` errors reported before were **an environment artifact**, not source errors: SvelteKit writes the shared `$app/tsconfig` into `node_modules`, with `rootDirs` relative to it; my worktree shared the main checkout's `node_modules` through a junction, so TypeScript looked for the generated route types in the *main* project. Giving the worktree its own `$app` copy gives 0 errors (the identical unmodified branch showed the same three errors before, and 0 in the main checkout) |
| Feature browser test (`product-conclusion.mjs`) | 360 checks pass: 7 cases (3 of them real non-electronics) at 360, 390 and 1280 px; no horizontal scroll, long names, warnings visible and outside any collapsed section, exact quotations, axe WCAG 2.0/2.1 A and AA |
| Extension tests | 20 pass |
| Frontend unit and component tests | **none exist** (no Vitest or similar); the project's frontend tests are the e2e suites |
| Whole existing e2e suite (24 files) | **481 checks pass, 36 fail.** The identical **unmodified `deployment` commit**, run the same way in the same environment, gives 394 pass, 40 fail. **23 of 24 files give identical (passed, failed) counts and no failing check occurs only on the feature**; the one differing file (`admin`) is better on the feature (4 filter checks fail on the baseline run, none on the feature run: timing flakiness). So all 36 failures are pre-existing (explained below) |
| Off-switch, enabled and disabled | tested in fresh processes with the variable unset, `1`, `0` and `off`: on by default; off returns exactly the original conclusion with the same decision and headline |
| Rollback | no migration needed: producing a conclusion never modifies the saved report (checked on 25 products) and the modules write nothing to disk |

Every remaining failure is listed in `regression_results.md` and, for the browser suites, explained in §I.

## D. Evidence audit (mechanical; every number computed by `evidence_verification.py`)

| | Count |
|---|---|
| Products checked (182 saved electronics, 21 real read while tuning, 16 real never read) | 219 |
| "Why this conclusion?" lines | 3,948 |
| Quotations | 6,639 |
| Review identifiers listed | 18,210 |
| **Invalid spans, missing reviews, non-verbatim quotations, double-counted reviews, wrong-profile aspects, reviewer fields in a payload** | **0** |

`quality_audit.py` (rules about what the text may say, run on the same three pools): **0** contradictions between headline, paragraph and assessment, **0** count words stronger
than the evidence policy allows, **0** negative-majority claims without a majority, **0** missing or unmarked hazard warnings, **0** invented benefit words (hair growth, whitening,
cure, immunity, weight loss …), **0** delivery praise standing in for product praise, **0** statements that a product *is* genuine or fake.

**What this does not show.** It shows traceability and obedience to rules. It does not show that an aspect is the right reading of a sentence. Reading the generated conclusions of the 16
never-read real products by hand found real defects that every automatic check had passed, and they were fixed:
1. On an **anti-hair-fall** shampoo "Many reviewers reported hair fall": at least half of those 17 "complaints" were praise ("less hairfall", "super effective for hair fall"). Fixed for every problem-type aspect (spot-checked afterwards: 9 left, the sampled ones genuine; not precision-measured).
2. A headline listing "defects" and "faults or failure to work" together, then more (redundant, ungrammatical).
3. "Some reviewers report …" when a concern had a single report (an uncounted quantity word); headlines now say "the reviews include reports of …".
4. "hindu" (typo of "hindi") read as itching; "for my rashes, I still use steroid cream" and "some people may experience irritation" read as reactions; "non greasy" read as greasy; "natuyo" about the product drying read as dryness.

Hair growth, skin and cosmetic effects, food quality and safety, battery, charging, authenticity, durability and defects were the topics read for. **No conclusion on the 16 products claims a growth, whitening, immunity, muscle or medical benefit** (the products' titles do; the text does not echo them), and safety and authenticity appear only as "possible … not independently verified" and "questions whether the product is genuine". Four error classes remain open and are listed in `aspect_validation.md` §5.

## E. Category coverage (real versus constructed)

Categories were confirmed from product titles, not from the project's classifier (which mislabels 15 listings in the scans). Toy cars are not motorcycle parts and are excluded.

| Profile | Real reviews | Real products (read while tuning / never read) | Status |
|---|---|---|---|
| hair | shampoo only | 1 / 3 analysed (9 in the coverage runs) | **experimental**; conditioners, masks unseen |
| skin | cleanser, lipstick, sunscreen, serum | 6 / 5 analysed (25) | **experimental**; moisturisers, toners, lotions unseen |
| apparel | dresses only | 4 / 2 analysed (8) | **experimental, thin**; shirts and pants unseen |
| food | protein, vitamins only | 5 / 2 analysed (19) | **experimental**; snacks, drinks, groceries unseen |
| appliance | air fryers, rice cookers only | 5 / 4 analysed (19) | **experimental**; fans, kettles, blenders unseen |
| **footwear** | **none** | 0 | **constructed unit tests only; not validated** |
| **motorcycle parts** | **none** (the project's 7 "automotive" listings are kids' toy cars) | 0 | **constructed unit tests only; not validated** |
| phone, earbuds, power bank, general | saved electronics (182) | tuning data | tested on real reviews; **not untouched** (the first tables came from reading this pool) |

`dataset_specification.md` is the specification for collecting the real data footwear and motorcycle parts (and the unseen categories) need. No review was invented anywhere.

## F. Recommendation comparison (existing live policy versus the experimental candidate)

Run on all 182 saved products: **1 of 182 decisions changes**, not_recommended to caution (a Bluetooth speaker with 14 defect reports, 48% positive, 26% negative: the hazard
warning stays on the card, but the label is weaker; the report flags it). **Why it differs:** the live rule returns `not_recommended` whenever a hazard concern is present and positive reviews do not clearly dominate; the candidate returns `caution` when fewer than a third of reviews are negative (here 26%). Whether that is better is untested without independent labels; the candidate is not wired in and was not enabled. The constructed scenarios, including every example you listed, are in `recommendation_policy_comparison.md`:

| Scenario (positive / neutral / negative) | Existing | Candidate | Safety protected |
|---|---|---|---|
| 45 / 20 / 35 | not_recommended | mixed | n/a |
| 25 / 65 / 10 | not_recommended | mixed | n/a |
| 70 / 20 / 10 | mixed | mixed (no change) | n/a |
| 30 / 10 / 60 | not_recommended | not_recommended (no change) | n/a |
| 5 / 90 / 5 (little product experience) | not_recommended | not_enough (needs new card wording) | n/a |
| 95 / 3 / 2 with `possible_safety_issue` | caution | caution (no change) | yes |
| 30 / 60 / 10 with `possible_safety_issue` | not_recommended | caution | yes, **but a weaker label** |
| 95 / 3 / 2 with `safety_warning` | not_recommended | not_recommended | yes |

The candidate never promotes a product to `recommended` and never lowers a `safety_warning` (tested over 5,000+ combinations). **It is not adopted.** There are no independent
product-level judgements, the thresholds are round numbers, and the saved pool barely contains the contested cases, so the evidence **cannot establish which policy is better**; that uncertainty is the finding.

## G. Human evaluation

## **PENDING HUMAN EVALUATION.**

**AI-assisted evaluation: approved by the panel and adviser, not yet performed.** The pipeline now accepts AI-assisted reference labels (Team Label 1 and Team Label 2; primary AI-assisted annotator ChatGPT, per the owner) and refuses to score without a `provenance.json` that records type, annotator, model version, interface, dates, prompt file and human review; the output is then labelled an AI-assisted reference standard, never independent human annotation, and the independent-human requirement stays open until two humans finish the sheets or the panel amends the protocol in writing. A review-level features sheet (150 reviews, blind) was added so recall and F1 can be computed; the 0.80 F1 target is printed beside the result and is not a licence to change labels, samples or thresholds. Nothing was labelled by Claude Code. See `human_evaluation.md`.

No annotation exists, so **no human-evaluation number is reported anywhere**. The pack is built and tested: 35 real products (16 unread real non-electronics, 19 stratified electronics; all five
assessments; 24 with safety reports, 23 with authenticity reports, 28 with at least 25% Filipino or Taglish reviews), 80 claims, blind sheets for two annotators, a rubric with examples of supported, partly
supported and unsupported statements, and a scorer that computes exact agreement, Cohen's kappa, per-dimension scores, claim precision with Wilson intervals, unsupported-claim and safety-error rates, and
recommendation agreement, and refuses to run without real, complete annotations. See `human_evaluation.md`. The developer's own judgements (80% then 89% on real non-electronics claims; 88, 86, 94% on electronics with an
earlier extractor) are **developer-judged, single-judge, optimistic and not independent**.

### Re-validation of 2026-11-15 (staging-preparation round)

Repeated on the staging-preparation commit (asp2): 400 of 400 backend tests on Python 3.11.9 and on Python 3.12.10 (VM library versions); `svelte-check` 0 errors in 1,409 files; `npm run build`; the feature browser test (all checks pass at 360, 390 and 1280 px);
the whole existing e2e suite **481 passed, 36 failed**, the same totals and the same failing files as the first run on this code. The unmodified-baseline comparison (394 passed, 40 failed; 23 of 24 files identical, no failure only on the
feature) was **not repeated**: its throw-away worktree no longer exists and no feature or front-end source changed since it was made (only tests, research scripts and documents), so the earlier comparison is cited, not re-measured.
Evidence verification: 0 problems in 3,948 lines. Quality audit: 0 issues in all 8 categories on 3 pools. Behaviour probes on constructed reviews (English, Filipino, Taglish, neutral, negation, hypothetical, contradiction inside one review,
repetition inside one review, copy-pasted reviews) found no failing example, so no extraction code was changed.

### AI-assisted evaluation (Claude-assisted annotation; one set; not independent; not human)

Source: Claude Sonnet 5.5 via Claude Code, 2026-11-15, no person reviewed the labels, ChatGPT did none of it (`ai_annotation/claude_session_1/`). Features, 150 reviews: precision 0.718, recall 0.285, **F1 0.408**; **target 0.80 not met**, nothing tuned or relabelled in response. Claims, 80: 63 correct (78.8%, 95% interval 68.6 to 86.3%); direction accuracy 63 of 67 (94.0%); 7 of 80 (8.8%) not supported by their quotation; 10 unclear. Card sheet, words sheet (unsupported-statement rate, safety-error rate, preference, usefulness) and agreement between annotation sets: **pending**. Independent human evaluation: **still pending** (no written amendment). Details and caveats: `human_evaluation.md`.

## H. Benchmark

**Staging benchmark: PENDING (no staging environment exists).** Local rerun 2026-11-15 (`performance_results_local_rerun.json`, Python 3.11, limited to 2 CPUs by emulation, an emulation and not the server): first read median 34.8 ms, p95 129.5 ms; cached 0.58 ms median, 1.3 ms p95; plain verdict without reasons 0.19 ms median; peak memory of the benchmark process 448.6 MiB (includes the loaded test data); CPU time equals wall time (single-threaded); no errors. The earlier run on the same code measured 72 ms median, 256 ms p95, cached 1 ms. **The two differ by about 2x on one PC: the figures depend on machine load, so no figure here predicts the VM.** Feature disabled versus enabled is the 0.19 ms versus 34.8 ms first-read figure (disabled skips extraction entirely).

**No staging benchmark was run: no isolated staging environment matching production exists here** (no Docker, no WSL, no staging VM), and running experimental code on production is excluded.
Measured instead (details and the exact procedure to produce a real staging run in `performance_benchmark.md`):

| | This PC, Python 3.11 | VM's runtime (Python 3.12, pinned libraries), 2 CPUs emulated |
|---|---|---|
| First read, 182 saved products, median / p95 | **72 ms / 256 ms** | **72 ms / 249 ms** |
| Cached read | 1.1 ms | 1.0 ms |
| Cold start (import + first product) | 0.34 s + 13 ms | 0.39 s + 19 ms |
| 3,000 reviews | 1.8 s, 656 KiB | 1.8 s, 622 KiB |
| Eight simultaneous uncached reads, p95 | 2.2 s (throughput about 9 per second) | 2.3 s |

Read-only on the production VM: 2 vCPUs, 3.8 GB, Python 3.12.3, commit `2c6e056`; a one-second regex micro-benchmark ran 2.4 times **faster** there than on this PC (indicative only). The historical figures
(68 ms / 252 ms, about 1 ms, 0.4 s) were reproduced: 72 ms / 256 ms (+6% and +2%), 1.1 ms, 0.34 s. The risk is bursts of uncached reads, not the single read.

## I. Security and deployment

| Topic | Finding |
|---|---|
| Backward compatibility | API changes are additive and optional; decisions and verdicts identical on 182 saved products; saved reports unchanged and unmodified by generating a conclusion; a report with no review text falls back to the plain wording |
| Production state (read-only) | `2c6e056`, clean tree, service active; `category_copy.py` and `product_category.py` present; the new modules absent as expected; Python 3.12.3; the 416 MB `defaketive.db` is never read or written by the feature |
| Dependencies | the new modules import only the Python standard library (checked statically): **no new package** |
| Python version | tests (including the whole suite) pass under Python 3.12.10 with the VM's versions; everything compiles with warnings as errors |
| Feature flag | `DEFAKETIVE_CONCLUSION_REASONS=0` (read once at start) disables the reasons; the original conclusion, decision and headline are unchanged; on by default. The VM's service unit shows no value for it today (its environment variable names could not be listed read-only; if the service uses an environment file, check it) |
| Rollback | set the flag to `0` and restart, or redeploy the previous commit; **no database migration**, no stored data changed |
| Synchronization | locally edited files are never overwritten and local modules never deleted; real dry run against a stand-in original: 75 unchanged, **18 conflicts reported, nothing written**; the real original is not on this PC, so the first real run must be a `--dry-run` by someone who has it |
| Existing e2e suite | see §C and below |
| Secrets and personal data | scanned before the commit; none found; no reviewer fields in any payload (tested) |
| Outstanding risks | no independent validation; categories without real reviews; low coverage (12 to 25% of real reviews carry a product claim) so conclusions explain a minority of the reviews and say so; uncached bursts; the category classifier mislabels some listings (outside this work) |

### The existing browser-suite failures, explained

The first failing check in most files is the **landing splash screen** intercepting a click (`<div class="collage"> from <div role="dialog" class="splash"> subtree intercepts pointer events`) in the guest flow. Because a
file stops at its first thrown error, how many checks a file executes depends on timing, which is why raw totals differ between runs (a first, unequal comparison also differed because the throw-away baseline had no
saved products in its local database; it was repeated after giving it the same ignored dev database). The other failing check names are about route opening for guests and signed-in users (`lock`), the logo mark colour (`brand`),
the zip download button (`uiux`), card widths in a responsive suite, and similar; **none concerns the conclusion card**, and every one of them fails identically on the unmodified commit. They are not fixed here: they belong to other
features, and fixing unrelated working code was out of scope. The splash blocker is worth a separate fix because it hides the rest of those suites.

## J. Release recommendation

**READY FOR STAGING.**

Why not READY FOR PRODUCTION: (1) the requirement that matters most to the panel, that the explanations are *true* of the reviews, has no independent evidence, only mechanical checks and one developer's judgement;
(2) footwear and motorcycle parts have no real reviews and the other five new categories have only informal testing on a small number of products; (3) the feature has not been measured on a machine like production; (4) the decision-policy
question is open. Why not NEEDS MORE VALIDATION or NOT READY: a staging deployment exposes nobody, it is the only way to obtain the staging measurement, the feature can be switched off without a redeploy, no verdict or decision changed,
and every known defect is documented. **Staging is the right next step; production is gated on the items below.**

## K. Phase 3: feature-extraction improvement (2026-11-15)

Goal: raise product-feature precision, recall and F1 toward 0.80 without touching evidence grounding, safety wording, decisions or the sentiment model. Full record: `phase3/protocol.md` (written before any change), `phase3/results.md` (generated from stored results), `phase3/frozen_extractor.json`.

| | Result |
|---|---|
| Locked baseline (asp2, 150 reviews, electronics included) | precision 0.718, recall 0.285, F1 0.408; unchanged and kept as the historical baseline |
| New data | D1 144 + D2 104 development reviews (product-grouped), F 104 fresh final reviews (non-electronics), none from the locked pack or its near-duplicates |
| Candidates | C0 baseline; C1 lexicons; C2 clause handling (labelled prompt answers, lowercase suggestion lists); **C3 context and vocabulary (adopted)**; C4 hybrid topic and polarity (rejected: no gain); C5 trained classifier (not built: too little labelled data) |
| Adopted on D2 (uninspected) | product-feature F1 0.366 to 0.623; precision 0.811 to 0.861; unsupported detections 20% to 9%; first-read p95 208 to 333 ms |
| **Fresh final F, scored once after the freeze** | **product features: precision 0.852, recall 0.371, F1 0.517** (C0 on the same reviews 0.800, 0.258, 0.390); all kinds 0.850, 0.315, 0.459 (C0 0.667, 0.259, 0.373); service 0.818, 0.209, 0.333; authenticity too few to interpret |
| **Target 0.80** | **not met**; precision for product features is at the target, recall (0.37) is far from it |

**Merged branch tip.** The extractor scored on F is the frozen version at commit c163605 (hashes in `phase3/frozen_extractor.json`). The branch tip now also contains the other contributor's category changes; re-scored on the same samples it gives the same F figures and one detection fewer on D2 (T1 F1 0.616 against 0.623), so the figures above describe the tip as well. Caveats that matter: the reference is one Claude-assisted annotation set (not independent, not human); D2 influenced the choice between candidates and F is the figure to quote; F has no electronics; the gain on F is smaller than on D2; a detection missing from the reference counts as false, so precision is a lower bound. Known defects found and left unfixed because the extractor is frozen are listed in `phase3/results.md`. Decisions (182 of 182), hazard checker, thresholds, sentiment model and the off-switch are unchanged; 424 backend tests, svelte-check, build, browser tests, evidence verification (0 problems in 3,948 lines and 6,639 quotations) and the quality audit (0 issues) were re-run on the adopted extractor. Existing browser suite (24 files): three full runs on this code gave 481 passed and 36 failed (earlier run), 363 passed and 38 failed (two files, `admin` and `extension-browser`, timed out under the long run; re-run alone they pass, 133 of 133 and 25 of 25), and, on the merged branch tip, 479 passed and 37 failed. The merged-tip differences were one colour-contrast check in `lock` that did not reproduce (re-run: identical to the earlier counts) and one `report-flow` check that the **other contributor's** pull request made out of date by adding an 'Auto-detected category' row above the report numbers; the expectation in `tests/e2e/report-flow.mjs` was updated to include that row. All 36 remaining failures are the pre-existing ones (mainly a splash-screen click blocker), the same files and counts as the unmodified-baseline comparison (394 passed, 40 failed; cited, not repeated); no failure is caused by the feature. Feature browser test: 360 of 360 at 360, 390 and 1280 px. The card and words annotation workflow was prepared in product-level batches (`human_evaluation.md`) and is **not annotated**.

## Remaining blockers for production, and the next step

1. **Next specific step:** hand `human_eval_pack/` to two independent annotators (35 products, 80 claims, a few hours each), then run `final_eval_pack.py score`.
2. Deploy the branch to a staging VM of production's size and run `benchmark.py --cpus 2 --tag staging`.
3. Have someone with the original app run `scripts/sync_backend.py --dry-run` and resolve the conflicts.
4. Collect real footwear and motorcycle-part reviews (`dataset_specification.md`); until then ship those categories with reasons labelled experimental or off.
5. Decide the recommendation-policy question using independently judged products; do not adopt the candidate before that.
6. Someone with write access must push the branch (this PC's login gets a 403) after the team reviews the commit.
