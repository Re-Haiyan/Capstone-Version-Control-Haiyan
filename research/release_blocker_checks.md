# Release blocker checks before approving deployment

Nothing was deployed, merged or pushed. Production is still `d74589a`. Four checks were requested; each result is below, with the decision at the end.

> **Label provenance caveat.** Team-supplied labels are of unverified provenance. They were used here only to find the first list of 29 reviews; no label was treated as correct and no rule was tuned to a label. "Genuine hazard" below is one reader's reading of the text, not an annotation.

## 1. Safety regression investigation

### 1.1 The 29 reviews that lose their safety flag (`research/safety_regression_audit.csv`)

The CSV lists, for each of the 29: the review text, product and group, the old and new safety decision, the rule responsible, whether it describes a genuine hazard, and whether adjudication is needed.

| Reviews | Text is | Old decision | Rule responsible | Genuine hazard? | Adjudication |
|---:|---|---|---|---|---|
| 20 | Baby-bottle listing line "Ribbed texture prevents collapse" (feature boilerplate) | safety (keyword "collapse", learned 0.92 to 0.97) | `product_category.py` `_FEATURE_CLAIM` | No | No |
| 6 | "calories burned" (fitness tracker, 5) or a monitor "burn test" (1) | safety (keyword "burn") | `lexicons/categories/all.tsv` burn exemption | No | No |
| 2 | "Relieves itching instantly" (an advertised benefit of a skin cleanser) | safety (keyword "itch") | `lexicons/categories/all.tsv` itch exemption | No | No |
| 1 | Cheese: "the expired date September 2026 ... is too early" | safety (keyword "expired") | `product_category.py` `_PRAISE_SAFE` (a stated date) | **Probably not, but ambiguous** | **Yes** |

None of the 29 carries a safety label in the supplied labels (0 of 29), which is consistent but is not evidence that the labels are right.

**Confirmed safety regressions among the 29: none.** **Unresolved: 1** (the cheese review, T30250): the reviewer complains that the expiry date is early, which reads as a short shelf life, but the review date is unknown and a September 2026 date may already have passed when it arrived. A person should decide whether it is "short shelf life" (not a hazard) or "arrived expired" (a safety flag). I did not claim all 29 are safe.

### 1.2 Wider search for regressions (no labels used)

The 29 come from labelled rows only, so I compared the old and new checker on unlabelled text (`research/safety_regression_scan.py`, outputs in `research/results/safety_scan_diff_*.csv`):

| Corpus | Reviews | Safety flag lost | Gained | Result |
|---|---:|---:|---:|---|
| Saved reviews, local database (gadgets only) | 8,000 | 0 | 0 | identical |
| Evaluation folder, every review that names its product, non-gadget categories included (unique text) | 4,968 | 26 | 0 | 17 listing boilerplate, 5 "calories burned", 1 "burn test", 2 itch claims, 1 cheese date: all benign or the one above |
| Production VM database copy (includes Shopee), seeded sample | 6,000 | 1 | 0 | "calories I burned": benign |

### 1.3 Demonstrable regressions the search found, and the fixes

All three came from generic wording, not from labelled rows:

1. **A past expiry year silenced real reports.** The date rule treated any year 2020 to 2099 as a safe date, so "Expired yung natanggap ko, expiry date March 2024 pa" and "the expiry date was 2023, it was already expired" lost their safety flag (production flagged both). **Fix:** a date no longer clears a sentence that says the item itself is expired (`_EXPIRED_REPORT`: "already expired", "expired na", "expired when it arrived", "nag-expire"; the noun "expired date" is not such a report).
2. **A wish to prevent a burnt smell was read as a product feature.** "Anyone know what to do to prevent that burnt plastic smell?" matched the feature-claim pattern "prevent ... burn". **Fix:** the pattern now needs the third-person verb ("prevents", "resists", "stops", "avoids") and not a demonstrative or pronoun before the hazard word.
3. While fixing 1, my first version also flagged "safe na safe 2028 pa yung expired" (praise with a far date). Caught by the scan before it left the machine; "yung/ung expired" was removed from the report pattern.

Regression tests: `tests/test_safety_regression.py` (7 tests): benign listing wording stays unflagged; real collapse, burn, itching and rash, a burnt-smell wish, and expired items (with a quoted date) stay flagged.

### 1.4 Remaining risk

The scans cover about 19,000 reviews, mostly gadgets; the exemptions in `all.tsv` apply to every category, so a category with no scanned reviews could still hide a case. The expiry rule cannot compare a date with the review date. The one unresolved review needs a person.

## 2. Saved-report compatibility (`pc4`)

### 2.1 What the version change does to the 71,690 existing reviews

* **Nothing is changed in the database at deployment.** Reports, reviews and accounts stay byte for byte as they are.
* The app shows each saved report **as stored**, and every report made by the older checker carries `checked_with_current: false`, which the front end turns into the existing notice (`src/lib/product.ts`). Reports made or re-checked by the new checker carry `true`.
* **No request re-analyses a saved report.** The public server replaces the two code paths that could (`server.py` replaces the saved-product preparation; `protections.py` replaces the initial catalog, so the older scan result files in `backend/` are never re-analysed on a request). This is now a test: `tests/test_saved_report_compat.py` forbids `analyze_products` during `/api/saved/products`, `/api/saved/detail` and `/api/picks` on the real database and passes.
* Rehearsed on the production hardware with a copy of the production database (396 products, 71,690 reviews) and the release-candidate code: first `/api/picks` 2.2 s, then 0.12 s; `/api/saved/products` (an 11 MB list, unchanged behaviour) 2.3 s, then 0.22 s; server memory about 1.0 GB, which is what production uses today. There was no blocking analysis.

### 2.2 The strategy (validated)

1. **Deploy without re-checking.** Saved reports stay visible and are marked "not checked with the current checker".
2. **Re-check gradually, off peak, with limits.** `scripts/recheck_products.py` was changed for this (the old version analysed every product in memory and saved only at the end: all-or-nothing, 71,690 reviews held at once, one long CPU burst):
   * `--max-products`, `--max-reviews`, `--max-minutes`: stop after a bounded amount; run again later, because a re-checked report is current and is not chosen again.
   * `--duty 50`: sleep as long as each product took. `--max-load 1.5`: wait (up to 10 minutes, then stop) while the machine is busy. Run it with `nice -n 19`.
   * `--order recent|small`; a dry run lists what would be done and writes nothing.
   * **One product per transaction:** each report is saved right after it is analysed, so a stop at any moment (a crash, Ctrl-C, a reboot) loses nothing and leaves nothing half done.
   * The database is streamed one report at a time (peak memory 676 MB on the rehearsal, against about 2 GB or more to hold the 415 MB database parsed).
   * A lock file allows one run at a time; a verified database backup is made once per 12 hours.
3. **Review the changes.** Run with `--verdicts` on a window to count verdicts before and after, and read the products whose card changed (the Shopee mini power bank is one: caution to mixed).
4. **Rollback without corrupting data**, three levels:
   * *Per run, product by product, site running:* each replaced report is appended to `backups/recheck-journal-*.jsonl` (flushed to disk before the replacement); `--rollback <journal> --apply` restores them. Tested.
   * *Whole database:* copy the verified backup back with the service stopped.
   * *Code:* `git reset --hard d74589a && bash deploy/setup-server.sh`. Reports re-checked with `pc4` stay valid (same schema, verified key by key on 16 production products); the old code shows them as "not checked with the current checker". No data is corrupted.

### 2.3 Verification

* **Tests** (`tests/test_saved_report_compat.py`, 5 tests): the app never re-analyses on a request and marks the old reports; a dry run writes nothing (SHA-256 of the database unchanged); a held lock stops a second run and changes nothing; a run limited to 2 of 3 products re-checks exactly 2 and then the remaining 1 on the next run; row counts of products and reviews never change; the site's own reader (`saved_pool`) polls continuously during the run without an error and sees exactly the re-checked reports as current; a rollback of the first run restores exactly those two reports.
* **Benchmark on the production VM** (`research/results/recheck_rehearsal_vm/`, a copy of the 2026-11-14 database, the live site serving at the same time, `nice -n 19`, `--duty 50 --max-load 1.9 --max-reviews 900`): 4 products, 851 reviews, 114 s wall, 50% of one core, peak memory 676 MB, machine load average at most 0.61 (2 vCPUs), memory available never below 1.79 GB. The live `/api/picks` answered in median 0.25 s, 95th percentile 1.2 s, maximum 2.4 s during the run, against 0.35 s before. Occasional slow answers (1.3 s) also occur after the run ended, so I do not attribute them to the re-check, but I did not test the effect of a database write on a live reader on the real database (the tests do it on a copy).
* **Duration.** One thread does about 15 reviews per second when working all the time; at `--duty 50` the effective rate is 7.5 per second, so the 71,690 reviews take about 2.7 hours of wall time at half a core, for instance two off-peak windows of `--max-minutes 90`.

### 2.4 Recommended commands (after approval)

```
nice -n 19 backend/.venv/bin/python scripts/recheck_products.py                     # dry run: what is behind
nice -n 19 backend/.venv/bin/python scripts/recheck_products.py --apply --max-minutes 90 --duty 50 --max-load 1.5
backend/.venv/bin/python scripts/recheck_products.py --rollback backups/recheck-journal-<time>.jsonl            # lists; add --apply to restore
```

## 3. Production security prerequisite: the default administrator password

* The main admin email and its default password are hardcoded in `admin_api.py` and published in `README.md` (lines about the admin account). I did not print the credential here.
* **Production check (read only, on the live accounts database, yes/no only): the default password is NOT active.** The main admin exists and its password was changed. The daily backups show it was changed between 2026-11-09 and 2026-11-10: the backups of 2026-11-08 and 2026-11-09 **still contain the default**, so restoring one of them would bring it back. There are 2 admin accounts in the live database.
* So production deployment is **not blocked by an active default credential.** It remains a **standing risk**: the credential is public in the repository and its history, `ensure_admin` creates the account with that password whenever no admin exists (a fresh install, an empty database, or a restore of a backup from before 2026-11-10), and every developer database has it (my local development database does).
* **Check tool:** `scripts/check_admin_default.py [accounts.db]` prints only whether the default is active (exit code 1 if it is). Run it before and after every deployment and on any backup before restoring it.
* **Proposed first-time provisioning without a hardcoded credential** (not implemented: it changes production sign-in and needs its own tests and your approval):
  1. Delete `ADMIN_PASSWORD` from the source and the README. `ensure_admin` never creates an account with a known password; with no admin it only logs "no admin exists: run scripts/create_admin.py".
  2. `scripts/create_admin.py --email you@example.org` runs on the server, reads the password with `getpass` (or from a file named by `DEFAKETIVE_ADMIN_PASSWORD_FILE`, mode 0600), requires at least 12 characters and refuses a password equal to the email or on a short common list, stores only the hash, and refuses to run if an admin exists.
  3. At every start the server compares the admin hash with the old default and logs a CRITICAL line (and refuses admin sign-in) if they match, so an old backup restored by mistake is caught.
  4. Treat the old default as compromised everywhere: rotate any other deployment, and tell anyone who holds a database copy.
  5. The tests that sign in as the default admin use a fixture account created with a random password.

## 4. Release decision

See the closing report of this round (and `release_manifest.md`): the exact commit, the test results, the performance impact and the GO or NO-GO are recorded there and in the manifest.
