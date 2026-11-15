# Annotation execution guide

For the two human annotators and for the person who runs the study. One page per role. The aim is **independent human labels with a recorded provenance**, so that agreement can be measured and the existing labels (whose origin is unverified, `annotation_provenance.md`) can be checked against people. Nothing in this folder has been labelled by a person yet, and no agreement figure exists.

## Before you start (the person running the study)

1. Choose two annotators and give each an ID (`A01`, `A02`). Fill `research/agreement/annotator_register_template.csv`: ID, name or handle, start date, the policy version they will use, and the declaration below.
2. Decide the policy version. **Use v1** (`docs/annotation_guides/round1_nongadget_README.md` and `round3_delivery_and_safety_README.md`) unless the owner has approved v2 in `research/policy_owner_decisions.md`. Both annotators must use the **same** version, written in the file name.
3. Give each annotator **only** their own blank sheet: `research/agreement/sheet_A.csv` or `sheet_B.csv`. **Never** give them `id_map.csv`, anything in `evaluation/`, `research/*.csv` other than their sheet, or the repository. They contain the existing labels and the sampling strata.
4. Tell them the declaration: *"I label alone, by reading, without an AI assistant, without a script, without looking at any earlier label."*

## The annotator (one page)

* **Work alone.** No talking to the other annotator, no AI tool, no script. If you use a translator for a word, write it in `notes` of the register.
* Open your sheet (`sheet_A.csv` or `sheet_B.csv`) in a spreadsheet. It holds 300 reviews, each with the star rating and the product name. Read the product first: the same words mean different things on a power bank and a shirt.
* For **every** review you can decide, fill the three empty columns:
  * `sentiment`: `positive`, `neutral` or `negative`, the reviewer's overall feeling about the product. (`neutral` includes a review that states no opinion, such as a feature list.)
  * `flags`: one or more of `defect`, `counterfeit`, `safety`, `not_as_described`, `quality`, `delivery`, joined with `;` (for example `defect;delivery`), or `none` on its own. **Never leave it blank**: a blank row is treated as "not done", not as "none". `none` is never combined with another flag.
  * `confidence`: `high`, or `low` when the review is unclear or needs the listing you cannot see. Low rows are not scored; a skipped row costs nothing and a wrong label does.
* One line per flag (v1): `defect` it does not work, broke, leaks or tears. `counterfeit` the reviewer says it is fake. `safety` a hazard to a person, pet or home (fire, smoke, burn, shock, sharp edge, choking, skin reaction, spoiled goods). `not_as_described` size, colour, material, amount or items differ from the listing. `quality` it works but is weak, flimsy, thin or cheap. `delivery` a complaint about delivery, packing or the seller. Praise, denials ("no rash") and worries ("baka masira") are not reports. A review can have several flags.
* Do not edit `id`, `stars`, `product` or `review_text`. Save as CSV (UTF-8) under a new name: `sheet_A_done.csv` (or `sheet_B_done.csv`). Partial sheets are fine.
* When finished, send your file to the person running the study. **Do not** send it to the other annotator.

## After the sheets come back (the person running the study)

1. **Check each sheet** (this validates values and catches edited text; it never changes the file):
   ```
   python research/agreement.py check research/agreement/sheet_A_done.csv --annotator=A01 --policy=v1
   python research/agreement.py check research/agreement/sheet_B_done.csv --annotator=A02 --policy=v1
   ```
   A problem list means the annotator must fix and resend; otherwise the call appends one line to `research/agreement/provenance_log.csv`: UTC time, annotator ID, policy version, file name, rows completed, rows marked low confidence, and the file's SHA-256 (so later edits are detectable). Keep the log in the repository with the files.
2. **Agreement** (needs at least 30 reviews completed by both):
   ```
   python research/agreement.py score   research/agreement/sheet_A_done.csv research/agreement/sheet_B_done.csv
   python research/agreement.py compare research/agreement/sheet_A_done.csv research/agreement/sheet_B_done.csv
   ```
   `score` prints, per flag and for sentiment, raw agreement, Cohen's kappa with a 95% interval, Gwet's AC1, positive agreement, negative agreement and the 2x2 table, for all completed reviews, for each sampling stratum and for the rows both marked high confidence. `compare` also reports each annotator against the team-supplied labels. Nothing is reported if fewer than 30 reviews are complete in both sheets.
3. **Adjudicate disagreements.** A third person (`A03`) sees both answers (not the team-supplied label) and decides each disagreement; record every decision in `research/agreement/adjudication_log_template.csv` (copy it to `adjudication_log.csv`): the review ID, both labels, the adjudicator, the final label, the rule or reason, the policy version and the date. **Keep the original labels untouched** in their own files; the adjudicated label goes in a new column or file, never over the old one.
4. **Record the outcome** in `research/evaluation_report.md` with the words "independent human annotations, two annotators, policy v1, agreement kappa ..." only once steps 1 to 3 are complete and the log exists.

## What must be written down (provenance)

| Item | Where |
|---|---|
| Who labelled (annotator ID, role, declaration) | `annotator_register` |
| Which policy version | the register, the file name and each `provenance_log.csv` line |
| When | `provenance_log.csv` (UTC) and the register |
| That the file was not altered afterwards | the SHA-256 in `provenance_log.csv` |
| Disagreements and how each was decided | `adjudication_log.csv` |
| That the original labels were preserved | the original files unchanged; adjudicated labels in a separate column or file |

## What must NOT be done

* Do not fill a sheet with an AI model or a script and call it human annotation. The first provenance finding of this project was exactly that the origin of the existing labels cannot be shown.
* Do not show annotators the team-supplied labels, the model's output, or the stratum.
* Do not compute or quote an agreement figure from fewer than two completed independent sheets.
* Do not overwrite a label to resolve a disagreement; adjudicate in a new column.
