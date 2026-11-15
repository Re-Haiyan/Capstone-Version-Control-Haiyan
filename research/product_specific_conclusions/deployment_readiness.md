# Deployment readiness

## Verdict: **READY FOR STAGING. NOT READY FOR PRODUCTION.**

Why staging: the feature is complete, backward compatible, switchable off, covered by 393 passing tests (on Python 3.11 and on Python 3.12 with the VM's library versions), and its main risks (a changed
decision, a hidden hazard, an untraceable claim, a slow first page) have each been checked and found clean on the saved products.
Putting it on a staging copy exposes nobody and is the only way to measure the two things that cannot be measured from this PC.

Why not production: **no independent human has judged it**, five of seven new product types have had only informal testing by the person
who wrote the rules, two have had none, the Azure VM has not measured the feature, and the decision-policy question is open. Those are
not formalities: they are the evidence the panel's requirement ("explain why, from actual review evidence, without inventing claims")
rests on beyond the mechanical checks.

Nothing was committed, pushed, merged or deployed. No database, model, checkpoint, evaluation set or production service was touched.
The only things done to the production VM were read-only: `git log`, `nproc`, `free`, `uptime`, `lscpu`, and one one-second CPU
micro-benchmark at the lowest priority (a temp file, removed afterwards).

## Checklist

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | Work isolated on `feature/product-specific-conclusions` in its own worktree; the XLM-R work in the main folder untouched | done | `git worktree list`, `git status` in both |
| 2 | Production commit checked | done, read-only | VM is at `2c6e056`; `b18898c` (product categories) is an ancestor; service active |
| 3 | Decisions and verdicts unchanged on the saved products | **verified** | `test_the_explanation_changes_no_verdict_and_no_decision`: 182 of 182 equal to the baseline taken before any change |
| 4 | Hazard checker, thresholds, models, category classifier unchanged | **verified** | `git diff deployment` for `backend/sentiment-analysis`, `accounts.py`, `data_store.py` is empty |
| 5 | Safety warnings cannot be hidden by praise | **verified** | tests on a grid of 5,000+ states (candidate policy) and on the live path; card shows warnings in the open (browser test) |
| 6 | Every displayed claim traces to a review | **verified mechanically** | `evidence_verification.md`: 3,535 lines, 5,837 quotations, 13,558 ids, **0 problems** (0 invalid spans) on three pools (182 saved, 21 real read while tuning, 16 real never read) |
| 7 | Claims are the *right* claims | **not verified independently** | developer-judged only (`aspect_validation.md`); annotation pending |
| 8 | Existing saved reports still load | **verified** | `test_saved_report_compat`, `test_saved_pool`, the 182-product regression; a report without review text falls back to the plain wording |
| 9 | Missing evidence handled | **verified** | empty, missing-id, no-text, no-category tests; `evidence_status` "limited"/"unavailable" |
| 10 | Backend tests | **393 pass, 0 fail**, on Python 3.11.9 and on Python 3.12.10 with the VM's NumPy 2.4.6, scikit-learn 1.9.0, joblib 1.5.3, onnxruntime 1.31.0 | `regression_results.md` |
| 11 | Front-end build | passes | `npm run build` |
| 12 | Browser test, 360 / 390 / 1280 px, 7 cases incl. 3 real non-electronics | **passes** | `tests/e2e/product-conclusion.mjs`: no horizontal scroll, long names, warnings visible and outside any collapsed section, quotations exact |
| 13 | Accessibility | axe (WCAG 2.0/2.1 A and AA) passes on the card at every width; **no manual screen-reader test** | same test |
| 14 | Type check | **0 errors, 0 warnings (1,409 files).** The earlier 3 `./$types` errors were an environment artifact: SvelteKit writes the shared `$app/tsconfig` into `node_modules` with relative `rootDirs`, and my worktree shared the main checkout's `node_modules` by junction, so TypeScript looked for route types in the wrong project. A local `$app` copy gives 0. Not run in the main checkout on the final code | run `npm run check` after merging |
| 14b | Existing e2e suite (24 files) | 481 pass, 36 fail on the feature; the unmodified commit, same environment: 394 pass, 40 fail; 23 of 24 files identical, no failure only on the feature (`final_report.md` §C, §I). The cause is mainly a pre-existing splash-screen click blocker | |
| 15 | Backend sync cannot overwrite newer work or drop the feature | **verified in isolation** | `test_sync_backend` (14 tests): no overwrite, no deletion of local modules, feature runs after the sync. **Never run against the real original** (it is not on this PC): the first real run must be `--dry-run`; it will report 18 locally modified files as conflicts |
| 16 | Performance | measured on this PC and in the VM's runtime limited to 2 CPUs (an emulation); **not on the VM or a staging copy** | `performance_benchmark.md`: first read 72 ms median / 256 ms p95 (3.12, 2 CPUs: 72 / 249), cached 1 ms, no model loaded, cold start 0.4 s |
| 17 | Operator off-switch | done | `DEFAKETIVE_CONCLUSION_REASONS=0` (read at start) returns every page to the plain conclusion; tested |
| 18 | Reviewer privacy | **verified** | no author or reviewer field in any payload (test + `evidence_verification`); quotations are public review text, so check the team's data policy before publishing any in the thesis |
| 19 | Human evaluation | **not done** | sheets ready, scoring refuses without annotators (`human_evaluation.md`) |
| 20 | Category validation | partial | hair, skin, apparel, food, appliance: some real reviews; footwear and motorcycle: none (`aspect_validation.md`) |
| 21 | Decision-policy change | **not adopted** | candidate is experimental and not wired in; 1 of 182 saved products would differ (`recommendation_policy_comparison.md`) |

## Known open defects (not blockers for staging)

- Four real-review error classes are open (`aspect_validation.md` §5): dryness read from "frizzy, dry hair" when the product fixes it; "hindi umiinit ang taas" read as a complaint in appliances; "gumagana" about a person; lowercase tag lists.
- The category classifier mislabels some listings (lipsticks as kitchenware, toy cars as automotive); a product in the wrong type is read with the wrong aspect table. The classifier is outside this work.
- Coverage is low (12 to 25% of real reviews carry a product claim), so the conclusion explains the product from a minority of reviews. It says so ("reviewers praised…", counts of distinct reviews) and never claims to summarise all of them.
- The existing verdict line beneath the card (before this work) still uses its own hazard phrasing ("fire, explosion or a swollen battery" on a rice cooker). Not changed here.
- A burst of uncached first page reads queues (about 9 per second per process on this PC).

## What staging must show before production

1. The same `benchmark.py --cpus 2 --tag staging` on a staging VM of production's size; first-read p95 under about a second and a burst of 8 uncached reads under a few seconds is a reasonable bar (the team's to set).
2. A run of `scripts/sync_backend.py --dry-run` against the real original, with every conflict resolved by a person.
3. The two-annotator evaluation with `human_eval_pack/` (35 real products, 80 claims; `human_evaluation.md`), and a labelled claim sample on a **fresh** real set for each category the team wants to ship (`dataset_specification.md`). Categories without it should ship with reasons switched off or labelled experimental.
4. A decision on the recommendation policy, ideally from part 4's evidence.
5. `npm run check` in the main checkout after the merge.

## Rollback

- Fastest: set `DEFAKETIVE_CONCLUSION_REASONS=0` and restart the service. The card returns to the plain conclusion; decisions and verdicts do not change either way.
- Full: redeploy the previous commit (the VM is on `2c6e056`; the git bundle method used before works if GitHub still refuses pushes from this PC).

## Who must act

Someone with write access to the GitHub repository must push the branch (this PC's login gets a 403), and the team must decide whether to commit this work to the `deployment` branch. Neither was done.
