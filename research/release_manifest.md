# Release manifest, deployment checklist, smoke-test plan and rollback

**Nothing described here has been deployed, pushed or merged.** The blocker checks (safety regression, saved-report migration, default admin password) are in `release_blocker_checks.md`; after them the release candidate gained a safety fix (`product_category.py`) and a gradual re-check tool (`scripts/recheck_products.py`), so the recommended commit named below is the one that contains both. The production VM is still at `d74589a` (verified read-only: `git log` and a clean tree). This document prepares a release for the owner's explicit approval.

## 1. What is being compared

| Role | Commit | Note |
|---|---|---|
| **Production today** | `d74589a` | on the Azure VM, the only version users see |
| Previous rule update | `831f22f` | rules tuned on the labelled training rows; **never deployed** |
| Research implementation | `c3d20ed` | evidence states, clause context, calibrator and policy switches |
| **Release candidate (code)** | `27598e4` | the last commit that changes code or lexicon files; every measurement in `release_validation.md` is of this code |
| **Recommended deployment commit** | **`825de6d`** | `27598e4` plus documentation, tests and research tooling only (no code or lexicon file differs from `27598e4`; checked with `git diff 27598e4 825de6d -- backend deploy src scripts/requirements-lock.txt package.json package-lock.json`) |

## 2. Every production-affecting change between `d74589a` and the release

All production-affecting files are inside the sentiment-analysis package (`backend/sentiment-analysis/defaketive_sentiment/`). **No front-end file, no deploy script, no dependency file (`scripts/requirements-lock.txt`, `package.json`, `package-lock.json`, `backend/requirements.txt`) and no model file changed** (the six model and tokenizer files have identical SHA-256 in both commits).

| File | What changed | Default behaviour |
|---|---|---|
| `evidence.py` (new) | `review_evidence`: a state per flag and quoted spans with absolute offsets; the opt-in evidence policy and its shadow mode | evidence field **on** (an extra key); policy **off** |
| `hazard_model.py` | evidence field; feared-fake and order/arrival handling; clause resolution switch; learned-model gates (a category exception, packing damage, a counterfeit sentence, heat already reported as safety); calibrator hook; policy hooks | gates and feared-fake **on**; clause resolution, calibrator and policy **off** |
| `product_badges.py` | optional `shadow_sentiment` and `shadow_evidence_policy` blocks in the summary | blocks appear **only** when the matching switch is set |
| `product_category.py` | `PRODUCT_CATEGORY_REVISION` `pc3` to `pc4`; shared `all` files; span-level packing-damage guard; denial and praise guards; sentence-level exemption for the learned model | on |
| `sentiment_calibration.py` (new) | the opt-in sentiment calibrator | **off** (needs `DEFAKETIVE_SENTIMENT_CALIBRATOR`) |
| `lexicons/categories/all.add.tsv`, `all.tsv` (new) | wrong, different and missing items; not-as-pictured; plain defect words; spelling and spacing variants of "does not work"; battery drain (a bare remark is not a defect, abrupt or measurable failure is); feared fake; calories, itch claims | on |
| `lexicons/categories/group_*.add.tsv` (9 files), `group_beauty_health.tsv` | the same wrong-item and size rows in every group; "damaged hair" is not a defect | on |
| `research/artifacts/sentiment_calibrator_v1.joblib` | the calibrator artifact (1.5 MB) | **inert**: loaded only if the environment variable names it |

**What a `git pull` brings that does nothing at runtime:** about 17 MB of `research/` (11.5 MB), `evaluation/` (5.4 MB), `tests/` and `docs/` (no code path imports them). The VM has 15 GB free.

## 3. Switches, defaults, and what each should do

| Environment variable | Default (unset) | Set it to | Recommendation |
|---|---|---|---|
| `DEFAKETIVE_EVIDENCE_POLICY` | `keep`: nothing changes | `shadow`: records what `require` would drop and the verdict it would give, changes nothing; `require`: stops counting model-only defect, quality and not-as-advertised flags (never safety) | **Keep off now. Enable `shadow` first** (`evidence_policy_decision.md`) |
| `DEFAKETIVE_CLAUSE_RESOLVE` | none | `safety`, `quality` or both | **Keep off**: it costs F1 on the supplied labels |
| `DEFAKETIVE_SENTIMENT_CALIBRATOR` (+ `_MODE`) | off | the artifact path; `shadow` or `on` | **Keep off** for customer-facing conclusions (15 of 60 cards would change); `shadow` is safe for logging |

**Checked:** with all four variables unset (as the service runs: the unit file sets none, verified below), the release behaves as the tests and the comparisons in `release_validation.md` describe. `research/release_compare.py` and `research/api_compat.py` clear every `DEFAKETIVE_*` variable before running, so the measurements are of defaults.

## 4. The one deployment effect to plan for: the saved reports become "not checked with the current checker"

* The model version stamp changed from `...+pc3+...` to `...+pc4+...` (the rules changed; the old release kept `pc3` although its behaviour had moved, so saved reports could not be told apart). `tests/test_release_version.py` fixes this.
* **After deployment every saved report is shown as stored, with the app's existing notice that it predates the current checker, until it is re-checked** (`scripts/recheck_products.py`). Nothing is re-analysed automatically for the saved-report screens; the app keeps serving. Verified locally: the app answers every checked route with the same status codes and latencies after the stamp change.
* **Do not re-check everything at once.** Use the gradual, limited, journalled `scripts/recheck_products.py` (`release_blocker_checks.md` section 2): `--max-minutes 90 --duty 50 --max-load 1.5`, with `nice -n 19`; each product is saved on its own and can be rolled back from a journal.
* **Re-check cost on the VM:** the daily backup of 2026-11-14 holds 396 products (325 Lazada, 64 Shopee, 7 Temu) and 71,690 reviews. One thread does about 15 reviews per second, so it is about **84 minutes of one core** when working all the time, or about **2.7 hours at `--duty 50`** (measured on a copy of the production database, peak memory 676 MB); run it off-peak in limited windows. Until it runs, the saved verdicts are those of the old rules.

## 5. Deployment checklist (every step needs the owner's go-ahead)

**Before**
1. Owner approves deploying commit `825de6d`; confirm the branch and hash: `git rev-parse --short HEAD`.
2. `backend/.venv/Scripts/python.exe -m unittest discover -s tests` passes (274 tests at `825de6d`).
3. Record the baseline on the live site: `python scripts/smoke_test.py https://defaketive.duckdns.org --save-baseline before.json`.
4. On the VM: note the running commit (`git -C ~/defaketive log --oneline -1`, expect `d74589a`), `systemctl is-active defaketive`, and `systemctl show defaketive -p Environment` (expect no `DEFAKETIVE_` switch).
5. Run `python scripts/check_admin_default.py` on the VM (expect: not active). Back up both databases: `~/defaketive/backend/.venv/bin/python scripts/backup_databases.py` (or confirm today's file under `~/defaketive/backups/daily/`).
6. Build the bundle on the PC: `git bundle create release.bundle d74589a..825de6d`.

**Deploy** (the procedure used for earlier releases)
7. `scp -i <key> release.bundle azureuser@defaketive.duckdns.org:~/`
8. On the VM: `cd ~/defaketive && git pull ~/release.bundle deployment && bash deploy/setup-server.sh`. The script reinstalls from the unchanged lock file, rebuilds the site, restarts the service and never touches an existing database.
9. `systemctl is-active defaketive` returns `active`; `curl -s -o /dev/null -w "%{http_code}" https://defaketive.duckdns.org/` returns `200`.

**After**
10. Smoke test with the comparison: `python scripts/smoke_test.py https://defaketive.duckdns.org --compare before.json` (all checks pass and **no pick changed verdict or card**, because saved reports are shown as stored).
11. Run the manual smoke checks of section 6.
12. Watch `journalctl -u defaketive -n 100 --no-pager` and `free -m` for 15 minutes (expect about 380 MB for the model process).
13. Schedule the off-peak re-check (section 4); afterwards run the smoke test again and review the changed cards.
14. Run `scripts/check_admin_default.py` again; never restore a backup older than 2026-11-10 without running it on the backup first.
15. Optional, with approval: set `DEFAKETIVE_EVIDENCE_POLICY=shadow` in the service environment to collect the evidence-policy shadow data.

## 6. Smoke-test plan

**Automatic (`scripts/smoke_test.py`, public read-only requests, standard library only):** home page 200 and HTML; security headers; a built asset; public stats; the sign-in state route; `/api/picks` not cached, every pick has a report and a conclusion card with a known decision, every highlighted range inside its quote; the saved-report list; and with `--compare`, no pick changed. Exit code 0 only if every check passes (verified: 11 of 11 pass on a local app; a dead port fails with exit code 1).

**Manual (about 15 minutes, after step 11):**
| Check | Expect |
|---|---|
| Open a saved Lazada report and a saved Shopee report | The report loads, with the conclusion card and the notice that the report was made with an earlier checker (until the re-check) |
| Open the evidence of one flag | The quoted sentence is real text of a review; highlighted words are inside it |
| Scan one new Lazada link (a listing with at least 100 ratings) | The scan completes; the report shows a verdict, a conclusion card and evidence; no error in the log |
| Send one Shopee report through the extension | It is accepted and analysed; the report matches the listing |
| Guest quota, sign-in, `/admin` | Unchanged |
| `free -m` during a scan | The service stays under about 1.2 GB (it uses about 1.1 GB with the site idle plus the models) |

## 7. Rollback

**Trigger:** the smoke test fails, the log shows repeated errors, memory climbs past 2.5 GB, or the owner asks.

1. On the VM: `cd ~/defaketive && git reset --hard d74589a && bash deploy/setup-server.sh` (rebuilds and restarts on the old code, no database change).
2. Check: `systemctl is-active defaketive`, HTTP 200, and `python scripts/smoke_test.py https://defaketive.duckdns.org --compare before.json` (the picks equal the baseline).
3. If the re-check had been applied: undo it product by product with `scripts/recheck_products.py --rollback backups/recheck-journal-<time>.jsonl --apply` (the site may keep running), or restore the databases from the backup the re-check script made (`backups/` under the project, named in its output) with the service stopped: `sudo systemctl stop defaketive; cp <backup>/defaketive.db ~/defaketive/backend/defaketive.db; sudo systemctl start defaketive`. The old code reads old reports as current again (the stamp is back to `pc3`).
4. Nothing else needs undoing: no dependency, model, schema or environment change was made, and the three switches were never set.

**Time to roll back:** about 3 to 5 minutes (the site rebuild dominates). The release changes no stored data, so step 3 is needed only after a re-check.

## 8. What was not done, on purpose

No deployment, merge or push. No change to the live service environment. The three disabled features are untouched and unset.
