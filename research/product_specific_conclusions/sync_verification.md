# Backend synchronization: verification

`scripts/sync_backend.py` copies the part of an older "original" app into `backend/`. Before this work it copied every listed file
unconditionally, which would have reverted work done here. It now copies a file only when that is safe and reports everything else.
Rules, states and flags are in the script's docstring.

## What was verified, and what could not be

| # | Requested check | Result | How |
|---|---|---|---|
| 1 | Dry run against the original checkout | **Done against a stand-in, not the real original.** The real original (`..\Capstone-Version-Control-Version-1.1`, commit `09daafe`) is **not on this PC and not in this repository**, so a dry run against it is impossible here. As the nearest legitimate substitute the `backend/` of the last commit that touched the manifest (`5acd571`, extracted with `git archive` into a temp folder) was used as the "older original" | `DEFAKETIVE_ORIGINAL=<temp>/backend python scripts/sync_backend.py --dry-run` |
| 2 | Comparison of source and destination | 93 listed files: **75 unchanged, 18 conflicts**, 0 new, 0 updated, 0 removed, 0 kept | same run |
| 3 | Locally edited files remain protected | **Yes.** The 18 conflicts are exactly the files edited here since the manifest was written (`webapp.py`, `accounts.py`, `dashboard_utils.py`, `templates/index.html`, four static files, nine files of the sentiment package including `extra_labels.py`, `hazard_model.py`, `model.py`, `safety_lookalikes.py`, and `lazada_scraper.py`). None was copied; the SHA-256 of `webapp.py`, `dashboard_utils.py` and the manifest was identical before and after; exit code 1 | the run's output and hashes |
| 4 | All new conclusion modules are included | **Yes.** `LOCAL_MODULES` lists `category_copy.py`, `aspect_profiles.py`, `aspects.py`, `recommendation_policy.py`, `conclusion_text.py`; they are recorded in the manifest as local, are never copied over or deleted, and the script stops with an error if one is missing. A test checks every module the conclusion code imports is either copied or local | `tests/test_sync_backend.py` |
| 5 | Isolated synchronization test in temporary directories | **Yes**, 14 tests, all in temp folders | `tests/test_sync_backend.py` |
| 6 | Destination containing newer files | **Yes**: an edited file is left byte for byte; a file never recorded but different is a conflict, not a replacement | `test_a_file_edited_here_is_not_overwritten_by_the_older_original`, `test_a_file_never_recorded_but_different_is_a_conflict_not_a_replacement` |
| 7 | Conflicting changes | **Yes**: reported on every run until resolved (the old hash is kept in the manifest so the file stays visible as edited); `--force` overwrites but still never touches a local module | `test_a_conflict_is_reported_again_on_the_next_run`, `test_force_overwrites_a_conflict_but_never_a_local_module` |
| 8 | The feature survives a sync | **Yes**: the real new modules are placed beside the *older production* `webapp.py` and `dashboard_utils.py` as the original; the sync leaves all untouched; then the real conclusion generator runs from the synced folder in a separate process | `test_the_conclusion_generator_survives_a_sync_against_older_originals` |

No synchronization was run against the main repository, this worktree's `backend/` (every real run was `--dry-run`, and the tests use temp
folders), or production. `git status` for `backend/` after the dry run shows only this branch's own edits.

## The dry run's output (real)

```
backend/: plan only, nothing written: 0 new, 0 updated, 75 unchanged, 0 removed, 0 kept, 18 conflict(s).
  CONFLICT  webapp.py  (edited here since the last sync; the original's version was NOT copied)
  ... 17 more ...
Exit 1: the files above differ from the original and were edited here. Merge them by hand, or use --force for a file you mean to discard.
```

## What is still open

- The first run against the **real** original must be a `--dry-run` by someone who has it; expect the same 18 files (plus any the team has edited since) as conflicts.
- Whether `backend/` should keep being a copy at all is a team decision: the diverged files now outnumber the untouched ones among the Python sources.

## Conflict report: files that would need a person (2026-11-15, from the recorded hashes)

**The real dry run was not performed.** The original app (`..\Capstone-Version-Control-Version-1.1`, or `DEFAKETIVE_ORIGINAL`) is not on this PC; `scripts/sync_backend.py --dry-run` stops with "The original DeFaketive app was not found" and writes nothing (checked again today). Nothing below was compared with the original.

What can be established without it: comparing every file in `backend/BACKEND_FILES.json` (93 files) with the SHA-256 the last sync recorded, **18 files differ**, that is, they were edited in this repository after the last sync. If the original has also changed any of them, the sync would report a conflict and leave the file alone; if the original is unchanged, there is nothing to do.

| File | Edited by |
|---|---|
| `dashboard_utils.py`, `webapp.py` | this feature (conclusion wiring; `webapp.py` one line) |
| `accounts.py`, `static/css/figma.css`, `static/css/public.css`, `static/css/tokens.css`, `static/js/app.js`, `templates/index.html`, `lazada-scraper/src/lazada_scraper.py` | earlier project work (not this feature) |
| `sentiment-analysis/defaketive_sentiment/` `analyze_reviews.py`, `extra_labels.py`, `fault_rules.py`, `hazard_model.py`, `lexicons/taglish_variants_v1.tsv`, `model.py`, `product_badges.py`, `risk_heads.py`, `safety_lookalikes.py` | earlier project work (sentiment and hazard; not touched by this feature) |

Resolution rule for a person doing the first real sync: run `--dry-run`, and for each reported conflict diff the original's version against `backend/`'s; keep `backend/`'s unless the original holds a fix this repo lacks. Do not use `--force` on any of the 18. The five feature modules (`aspect_profiles.py`, `aspects.py`, `conclusion_text.py`, `recommendation_policy.py`, `category_copy.py`) are listed as local modules and are never touched or deleted (tested).
