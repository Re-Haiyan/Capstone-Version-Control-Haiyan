# Annotation execution guide (sentiment study)

For the person running the study and for the two annotators. **Nothing here has been labelled by a person, and no agreement figure exists.** Read `annotation_policy.md` first; the owner must approve it and both annotators must use the same version.

## What was prepared (all in `annotation/`)

| File | For | Content |
|---|---|---|
| `final_test_sheet_A.csv`, `final_test_sheet_B.csv` | annotator A, annotator B | the **same 400 reviews** of 73 products, anonymous ids `T001`..`T400`, shuffled differently, empty `sentiment`, `confidence`, `rationale`. No stars, no model output, no existing label. |
| `dev_pool_sheet.csv` | later, for training and validation | 400 more reviews of 76 other products (ids `D001`..`D400`) |
| `PRIVATE_id_map.csv` | the person running the study only | review key, product link, stars, group, platform, sampling weight |
| `frozen_final_test.json` | everyone | the SHA-256 of the frozen final-test list and the sampling plan, written **before any model was selected** |

**The final test is frozen.** It is scored once, with the final chosen model, after the sheets are labelled. It must never be used to tune, select, threshold or compare repeatedly. The sample is stratified by star group and category group (weights are in the private map) and is **not** representative of every category: the production database holds almost only electronics, and products already labelled elsewhere were excluded, so only 25 of the 400 are not electronics (`dataset_audit.md`). A representative test needs a new scan of home, fashion, beauty, food and automotive products.

## Steps for the person running the study

1. Choose two annotators (`A01`, `A02`) and a third person for adjudication (`A03`). Tell each annotator: *"You label alone, by reading, without an AI assistant, without a script, and without looking at any earlier label or at the other annotator's sheet."*
2. Give each annotator **only** their own blank sheet. Never give them the private map, model predictions or the repository.
3. Annotators return `final_test_sheet_A_done.csv` / `final_test_sheet_B_done.csv` (UTF-8 CSV, only the three label columns filled; partial sheets are allowed).
4. Validate and record provenance (the same for B and `A02`):
   `python research/xlmr_optimization/sentiment_agreement.py check <A_done.csv> --blank <final_test_sheet_A.csv> --annotator A01 --policy v1`.
   A problem list means the annotator must fix and resend. Otherwise one line (UTC time, annotator, policy, rows, SHA-256) is appended to `annotation/provenance_log.csv`.
5. Agreement, from the two **untouched** sheets (refuses below 30 shared reviews): `python research/xlmr_optimization/sentiment_agreement.py score <A_done.csv> <B_done.csv>`.
6. Disagreements: `... adjudication <A_done.csv> <B_done.csv>` writes `adjudication_sheet.csv`; `A03` fills the final label, adjudicator, rule, policy version and date. The originals stay untouched.
7. Only after steps 4 to 6, build the adjudicated final-test file (a new file, with the policy version and the log) and score the chosen model **once**.

## For the annotator (one page)

* Work alone. Read the product title first. The star rating is not shown: judge the words.
* For every review you can decide, fill `sentiment` (`positive`, `negative`, `neutral`, `mixed` or `unclear`), `confidence` (`high` or `low`) and `rationale` (begin with `[product]`, `[delivery-only]`, `[both]`, `[no-opinion]`, `[mixed]` or `[unclear]`, then a few words).
* `mixed` means one clear good point and one clear bad point; it is not `neutral`. `unclear` means a person cannot decide from the text. If you can decide but are unsure, label it and mark `low`.
* Do not edit any other column. Save as UTF-8 CSV under the name given and send it to the person running the study, not to the other annotator.

## What must not be done

* Do not fill a sheet with an AI model or a script and call it human annotation. Do not quote an agreement figure from fewer than two completed independent sheets. Do not overwrite a label to resolve a disagreement. Do not score the frozen test with any model before the labels exist, and never more than once.
