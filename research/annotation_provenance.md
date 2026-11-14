# Annotation provenance

**Bottom line.** For every labelled file used in this project's evaluation, **the repository cannot show who or what produced the labels**. For the labels returned during the 2026-11-13/14 sessions, the time between creating a blank file and receiving it back was too short for row-by-row manual labelling. Until a human-labelled subset confirms them, these labels must be called **team-supplied labels of unverified provenance (silver labels)**, not "independently human-annotated gold labels". The project owner has stated that the team labelled them; the repository contains nothing that confirms or contradicts the statement except the timing below, which is hard to reconcile with it. No label value was changed in this audit.

## 1. What was checked

* The blank files created for each round (when they were created, which columns they carry).
* The labelled files returned (when they arrived, their format, any author metadata inside the spreadsheets).
* Git history for the older gold files.
* Whether the labels look copied from the rule engine.

## 2. Evidence

### Time between creating a blank file and receiving it labelled

Blank files were created by this project's scripts at the times in the third column; the labelled files appeared in the Downloads folder at the times in the fourth. A file cannot be labelled before it exists, so the interval is an upper bound on the labelling time (it includes any transfer).

| Round | Reviews | Blank file created | Labelled file saved | Upper bound | Seconds per review (at most) |
|---|---:|---|---|---:|---:|
| Non-gadget batch, parts 1 and 2 | 570 | 2026-11-13 23:19:26 | 23:32:20 to 23:32:34 | 13 min | 1.4 |
| Fresh batch 1 | 310 | 2026-11-14 00:29:57 | 00:37:50 | 8 min | 1.5 |
| Fresh batch 2 | 270 | 2026-11-14 14:43:03 | 14:49:53 | 7 min | 1.5 |
| 3,863-row pool (train parts 1 to 7, two test files) | 3,863 | 14:58:24 and 15:00:59 | 15:20:25 to 15:20:32 | 22 min | 0.34 |
| Round 3: delivery check (1,184) and safety rows (397) | 1,581 | 17:03:00 | 17:18:10 to 17:18:21 | 15 min | 0.57 |

For each review the labeller had to read a short Taglish text, judge sentiment, choose zero to five issue flags and a confidence. At 0.3 to 1.5 seconds per review that is not a realistic manual pace. It does not prove how the labels were made: a team could have prepared answers in advance, shared a spreadsheet, or used a tool. It does show that the returned files were not the product of ordinary manual labelling in that window.

### Other signals

* **No per-row provenance exists** in any labelled file: no annotator identifier, no timestamp, no tool or version, no edit history. Columns are `id, stars, product, review_text, sentiment, flags, confidence`.
* **No author metadata.** The returned spreadsheets carry no creator, last-modified-by or application fields.
* **Naming.** `annotated_*_combined.csv`, `annotated_reviews_all_3863.xlsx` and `annotated_nongadget_all_570.csv` are concatenations of the parts, so the files were assembled by a script or a person with tooling after labelling.
* **The blanks were not pre-labelled.** The files given out had empty label columns and were selected by keyword lists and random sampling, not by the model's flags (`research/cache/` and the scripts in the session history). So the labels were not simply a copy of rule output.
* **The labels do not look copied from the rules.** Against the deployed rules the labels agree only partly (F1 from 0.53 to 0.94 by flag on the test file), and ten policy questions are labelled inconsistently (`annotation_policy_proposal.md`). Not copying the rules does not establish human origin.
* **Self-consistency.** Exact-duplicate review texts never carry conflicting labels (0 of 343 repeated texts), and only 6 of 489 near-duplicate pairs disagree. Consistency is expected of a script or a careful person alike.

### Older gold files

`evaluation/gold_labels_200.csv` and `evaluation/heldout_labels_100.csv` were committed by a teammate on 2026-11-02 (commit `44473f0`, "Shopee review collection, sentiment and report updates, UI polish, evaluation data"). The repository records no labelling process for them. Provenance: **unknown**.

## 3. Classification of each labelled set

| Set | Rows | Independently human-annotated | Machine-assisted | Rule-assisted | Human-reviewed | Adjudicated | Verified provenance |
|---|---:|---|---|---|---|---|---|
| Non-gadget batch (parts 1 and 2) | 570 | not shown | not excluded | no sign of copying | unknown | no | **unknown** |
| Fresh batches 1 and 2 | 580 | not shown | not excluded | no sign of copying | unknown | no | **unknown** |
| 3,863-row pool (training and test files) | 3,863 | not shown | not excluded | no sign of copying | unknown | no | **unknown** |
| Round 3 (delivery, extra safety) | 1,581 | not shown | not excluded | no sign of copying | unknown | no | **unknown** |
| `gold_labels_200`, `heldout_labels_100` | 300 | unknown | unknown | unknown | unknown | no | **unknown** |

"Not shown" means the repository has no evidence either way, not that the answer is no. **No label in the repository has been adjudicated.**

## 4. Consequences for the research claims

1. Every score in `research/` is a score against **team-supplied labels**. A system that matches the labels well is shown to match them; if they were produced by an automated labeller, the scores partly measure agreement with that labeller's habits, not with human judgement.
2. Rule tuning was done on those labels. If the labels carry a systematic bias, the rules inherited it.
3. The 846-row test file shares the provenance of the training file, so it cannot check the labeller either.
4. **What would settle it:** the two-annotator sheets in `research/agreement/` (the reviews are the same ones that carry labels, with the labels hidden). If two people label them independently and their labels agree with the team-supplied ones at a rate close to their agreement with each other, the labels are confirmed as human-quality; if they agree with each other much more than with the supplied labels, the supplied labels are a different kind of label and should be used as silver data only. `agreement.py score` handles the two-annotator part; comparing a person's labels with the supplied labels is added in `research/agreement.py compare`.
5. Wording rule for future reports: say **"team-supplied labels (provenance unverified)"**; reserve **"gold"** and **"human-annotated"** for labels with a record of who made them (annotator IDs, dates, an agreement figure).
