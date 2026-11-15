# Annotation provenance (updated 2026-11-15 under the panel- and adviser-approved AI-assisted methodology)

**Classification: Team Label 1 and Team Label 2 are AI-assisted annotation sets** (primary annotator: ChatGPT, per the owner; approved by the research panel and adviser). They are **not independent human annotations** and are not described as such. Methodology and limits: `../ai_assisted_annotation_methodology.md`. Protocol changes: `../protocol_amendment_ai_assisted_annotation.md`.

## Recorded facts

| Item | Record |
|---|---|
| Files | `annotation/returned/team_label_1_final_test_sheet_A_v1.csv` (SHA-256 `5e3670e36c82d51a...`), `team_label_2_final_test_sheet_B_v1.csv` (`2e3cb2a41d39c7d1...`); copied unchanged from Downloads |
| Run by | team 1: Caballero; team 2: Guyo (owner's statement; research team members) |
| Annotator | ChatGPT (primary AI-assisted annotator, owner's statement); model version, interface, prompts and session dates **not recorded**: to be entered in `annotation/annotation_process_record_template.md` |
| Rubric | policy v1, frozen (`annotation/policy_v1.lock.json`) |
| Dates | files written 2026-11-15 12:52:01 and 12:52:02, 13 minutes after the blank sheets were created |
| Human review | extent unknown; no record of any row changed by a person |
| Declaration of "no AI" | **withdrawn** (it would be false); replaced by the process record |
| Text and IDs unchanged | yes, matched by review ID (`validation_report.md`) |

## Observed characteristics (consistent with AI-assisted generation; they also show the sets are not independent of each other)

1. Every rationale starts "Team Label N:" followed by one of about 60 category sentences (60 distinct strings on sheet A, 61 on B).
2. All 50 `mixed` rows have identical aspect text on both sets; the `mixed` tag is identical on all 50.
3. Confidence agrees on 394 of 400 rows; the two files were written one second apart, 13 minutes after creation.
4. The file format equals the project's CSV writer (BOM, CRLF).
5. 69 of the 400 frozen reviews also exist in the 10,000-review pool that carries AI annotations (annotator model not recorded in the files): Team Label 1 matches that AI label on 55 and Team Label 2 on 50 of the 69.

## What this means for use

* Agreement between the two sets is descriptive (`inter_annotator_agreement.md`), not reliability.
* The reference standard of the final test is AI-assisted; it becomes verified only after human adjudication and a documented human check of agreed rows.
* Original labels, texts and records are preserved; any later correction is an explicit adjudication decision recorded in separate columns.
