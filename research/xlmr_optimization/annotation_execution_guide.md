# Annotation execution guide (sentiment study, policy v1)

For the person running the study and for the two annotators. **Nothing here has been labelled by a person, and no agreement figure exists.** The policy is `annotation_policy.md`, **version v1, approved by the owner and frozen** (SHA-256 in `annotation/policy_v1.lock.json`). Both annotators and the adjudicator use v1 only. Changing it later means a new version under a new file name.

## What was prepared (all in `annotation/`)

| File | For | Content |
|---|---|---|
| `final_test_sheet_A.csv`, `final_test_sheet_B.csv` | annotator A, annotator B | the **same 400 reviews** of 73 products, anonymous ids `T001`..`T400`, shuffled differently. Empty columns to fill: `sentiment`, `tags`, `positive_aspect`, `negative_aspect`, `confidence`, `rationale`. No stars, no model output, no existing label. |
| `dev_pool_sheet.csv` | later, for training and validation | 400 more reviews of 76 other products (ids `D001`..`D400`), same columns |
| `PRIVATE_id_map.csv` | the person running the study only (git-ignored) | review key, product link, stars, group, platform, sampling weight |
| `frozen_final_test.json`, `policy_v1.lock.json` | everyone | hashes of the frozen test list and of the policy; the frozen list was fixed **before any model was selected** and the policy before any label existed |

**The final test is frozen.** It is scored once, with the final chosen model, after labels and adjudication exist. It is never used to tune, select, threshold or compare repeatedly. The columns `tags`, `positive_aspect` and `negative_aspect` were added (empty) after the policy was approved; no id, text or row order changed (`frozen_final_test.json` records this). The sample is stratified by star group and category group and is not representative of every category (25 of 400 are not electronics); a representative test needs a new scan.

## Steps for the person running the study

1. Choose two annotators (`A01`, `A02`) and a third person for adjudication (`A03`). Fill a register line for each (ID, start date, policy `v1`) in `research/agreement/annotator_register_template.csv`. Give each annotator **identical instructions**: this guide's annotator page and `annotation_policy.md`, and the sentence: *"You label alone, by reading, without an AI assistant, without a script, and without looking at any earlier label, model output or the other annotator's sheet."*
2. Give each annotator **only** their own blank sheet. Never give them `PRIVATE_id_map.csv`, any prediction file, `research/xlmr_optimization/predictions/`, or the repository: the annotators stay blinded to model predictions and to the stars.
3. Annotators return `final_test_sheet_A_v1_done.csv` / `final_test_sheet_B_v1_done.csv` (UTF-8 CSV; the policy version in the name; only the six label columns filled; partial sheets are allowed).
4. Validate each sheet and record provenance (`A02` for B):
   `python research/xlmr_optimization/sentiment_agreement.py check <A_done.csv> --blank annotation/final_test_sheet_A.csv --annotator A01 --policy v1`.
   It checks allowed values, unchanged review text, and the v1 rules (mixed needs the tag and both aspects; neutral and mixed together are not allowed; no-opinion needs neutral or unclear). A problem list means the annotator must fix and resend. Otherwise a line (UTC time, annotator, policy, rows, SHA-256) is appended to `annotation/provenance_log.csv`.
5. Agreement from the two **untouched** sheets (refuses below 30 shared reviews): `python research/xlmr_optimization/sentiment_agreement.py score <A_done.csv> <B_done.csv>`. It reports the three-class kappa with an interval and per-class agreement **with and without delivery-only reviews**, the **separate mixed set**, agreement on each tag, and the unclear count. Report every figure, including low agreement.
6. Disagreements (in the label or in any tag): `... adjudication <A_done.csv> <B_done.csv>` writes `annotation/adjudication_sheet.csv`; `A03` fills the final label, final tags, adjudicator id, rule or reason, policy version `v1` and date, seeing both answers but not model output or stars. The original sheets stay untouched; the adjudicated labels live only in the new file.
7. Only after steps 4 to 6, build the adjudicated final-test file (a new file referencing the policy hash and the log) and score the chosen model **once**. Three-class scores use positive, neutral and negative rows; mixed (no dominant polarity) rows form a separate set; every score is reported with and without delivery-only reviews.
8. Retrain and evaluate **only** after genuine human annotations exist (dev pool labelled the same way).

## For the annotator (one page; the same for A and B)

* Work alone. Read the product title first. The star rating is not shown: judge the words.
* Fill, for every review you can decide:
  * `sentiment`: `positive`, `neutral`, `negative`, `mixed` or `unclear`.
  * `tags`: any of `mixed`, `delivery-only`, `no-opinion`, joined with `;`, or blank.
  * `positive_aspect` and `negative_aspect`: a few words each, **required whenever the tag `mixed` is used**.
  * `confidence`: `high` or `low`. `rationale`: a few words.
* **Mixed.** Two clear opposite opinions. If one side clearly wins, put that polarity in `sentiment` and add the tag `mixed` and both aspects. If neither wins, put `mixed` in `sentiment` (and the tag, and both aspects). Never use `neutral` for a mixed review.
* **Delivery-only.** The review is only about delivery, packing, the rider or the seller: label the feeling it states and add `delivery-only`. A review that also judges the product is not delivery-only.
* **"Okay lang"** on its own is `neutral`; read the whole review, because praise or dissatisfaction next to it changes the label.
* **Feature list with no opinion**: `neutral` with the tag `no-opinion`.
* `unclear`: a person cannot decide from the text. If you can decide but are unsure, label it and mark `low`.
* Do not edit any other column. Save as UTF-8 CSV under the name given and send it to the person running the study, not to the other annotator.

## What must not be done

* Do not fill a sheet with an AI model or a script and call it human annotation. Do not quote an agreement figure from fewer than two completed independent sheets. Do not overwrite a label to resolve a disagreement. Do not show annotators predictions or stars. Do not score the frozen test before the labels exist, never more than once, and never use it to select a model. Do not deploy a model.
