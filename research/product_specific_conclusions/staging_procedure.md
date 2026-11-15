# Staging procedure (not yet performed: no staging environment exists)

**Status: PENDING.** No staging VM, container host, or WSL is available to this project from the development PC, and none was used. Nothing below has been run on a staging machine. Never run any of it against production.

## What a valid staging environment is
A machine that is not production, with production's size (2 vCPUs, same RAM), Python 3.12 and the library versions in `backend/requirements.txt` as pinned on the VM (NumPy 2.4.6, scikit-learn 1.9.0, joblib 1.5.3, onnxruntime 1.31.0), serving a copy of the app with a **copy** of the saved-products data. Production's database and accounts are never used or copied with personal data.

## Steps
1. **Get the code (no merge):** on an isolated staging machine, run `git fetch origin feature/product-specific-conclusions`, then `git checkout --detach 2529f8bfdcb4b828b0e17ae87179e718576550de`, then `git rev-parse HEAD`; verify the full SHA matches. Do not merge into `deployment` or `main`. Pinning the commit prevents branch changes from altering the evaluation mid-run.
2. **Backend tests on the staging runtime:** `python -m unittest discover -s tests -p "test_*.py"` (expected: 429 pass, as reported on Python 3.11 and 3.12 for this commit). A failure here is a staging finding, not a reason to edit tests.
3. **Front end:** `npm ci && npm run build && npm run check` (expected: 0 errors).
4. **Run the app on a staging port** with the feature on (default): `python serve.py --port 8099`.
5. **Feature switch:** restart with `DEFAKETIVE_CONCLUSION_REASONS=0`; open a saved report and a product page: the plain conclusion appears, with the same decision and verdict. Restart with the variable unset: the explained conclusion returns. Compare the saved product list before and after: identical (rollback needs no migration; `test_product_conclusion` checks the same in-process).
6. **Saved reports:** open at least five saved reports created before the feature; they load, with the plain wording where a report has no review text.
7. **Browser tests:** `BASE=http://<staging>:8099 node tests/e2e/product-conclusion.mjs` (expected: all pass at 360, 390 and 1280 px); then `npm run test:e2e` and compare with the recorded baseline in `final_report.md` section C (481 pass, 36 known failures; a splash-screen click blocker explains most).
8. **Benchmark (the supported command):** `python research/product_specific_conclusions/benchmark.py --cpus 2 --tag staging`. Record: first-read median and p95, cached median, peak memory, CPU over wall time, errors, 8-way simultaneous reads, and feature enabled versus disabled (disabled = plain verdict, about 0.19 ms locally). Latest local Phase 3 C3 reference (this PC with 2 CPUs emulated, **not** staging): first-read median 86.24 ms, p95 333.02 ms; cached median 0.8 ms; see `phase3/results.md`. Judge the true staging measurements against the team's predeclared bar (first-read p95 under about 1 second; a burst of 8 uncached reads under a few seconds), not as though the local figures were staging results.
9. **Backend sync dry run** (needs the original app on that machine): `DEFAKETIVE_ORIGINAL=<path> python scripts/sync_backend.py --dry-run`; expected conflicts are the 18 files listed in `sync_verification.md`; resolve each by a person; never `--force`.
10. **Privacy and secrets:** scan the checkout and the staging logs; no reviewer names, phone numbers, tokens or private keys.
11. Write results to `performance_results_staging.json` and a dated section in `performance_benchmark.md`, labelled with the machine, date and commit. Report failures as found.

## Rollback
Set `DEFAKETIVE_CONCLUSION_REASONS=0` and restart (decisions and verdicts do not change); or redeploy the previous commit. No database migration in either direction.
