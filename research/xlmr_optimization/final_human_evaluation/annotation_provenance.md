# Annotation provenance audit (policy v1)

Source of the figures: `_forensics.json` (`provenance_forensics.py`). No model prediction was read and no model was scored. The stars were read from the private map only to examine how the labels relate to them.

## What is documented

| Requirement | Evidence found |
|---|---|
| Annotator identity records | None per annotator. The owner states that team 1 is run by Caballero and team 2 by Guyo (recorded in `annotation/provenance_log.csv` as `TEAM1-run-by-Caballero` and `TEAM2-run-by-Guyo`). That names the team leads, not who read each review. No annotator register entry was completed. |
| Annotation dates | File modification times only: sheet A 2026-11-15 12:52:01, sheet B 12:52:02. The blank sheets were created at 12:39. |
| Policy version | The file names carry `v1`. |
| Declaration (alone, no AI, no script, no model output, no stars, no other sheet) | **Not given.** |
| Visibility of predictions or existing labels | No evidence either way; **not confirmed**. |
| Text and IDs unchanged | Yes (`validation_report.md`). |

## Forensic findings

1. **Both 400-review sheets were written within one second of each other (12:52:01 and 12:52:02), 13 minutes after the blank sheets were created.** That is about 2 seconds per review per sheet, each row with a rationale.
2. **The rationale column is templated.** Every rationale on sheet A begins "Team Label 1:" and every one on sheet B "Team Label 2:". Sheet A has 60 distinct rationale strings in 400 rows and sheet B 61, built from a short list of category sentences (202 rows of sheet A read "Favorable evaluation of product, function, value or purchase experience."). The policy asked for neither a team prefix nor a fixed sentence per category.
3. **Fifty of fifty rows tagged `mixed` carry word-for-word identical `positive_aspect` and `negative_aspect` text on both sheets**, and the mixed tag set is identical on all 50. Two people working independently would not type the same aspect phrases in 50 of 50 cases.
4. **Near-identical confidence:** 394 of 400 rows have the same `high` or `low` value on both sheets.
5. **The file format matches the project's own CSV writer** (UTF-8 with byte-order mark, CRLF line endings, same column order and quoting). That alone is not conclusive (a spreadsheet can write the same), but together with 1 to 3 it points to a script producing both files from one source.
6. **Relation to the hidden stars:** the labels follow the stars closely in aggregate (33 of 34 one-star rows negative on A; 231 of 290 five-star rows positive), as a text-reading process would; this neither supports nor contradicts independence.
7. **No file hash match** with another file on this machine. **Comparison with the known AI-generated drafts:** 69 of the 400 frozen reviews also exist in the 10,000-review pool that carries AI "direct" sentiment annotations (`D:/cvc-annotations`, branch `annotations-10000`). On those 69, sheet A's label equals the AI label for 55 and sheet B's for 50 (80% and 72%; the AI scheme has `mixed` as a label, so differences are expected). This neither shows nor excludes copying.

## Conclusion

**Independent human annotation cannot be substantiated.** The evidence points to machine-generated or template-generated sheets from a shared source, labelled with team names: the pattern of the earlier unverifiable labels. It is not proof of misconduct (a team could have applied its own rubric with a script, or exported from a shared spreadsheet), and the submitted labels were not changed.

## Evidence still needed

1. For each sheet, the name of the person who read and labelled the reviews and a signed declaration that they labelled alone, without an AI assistant or script, without model predictions, stars or the other sheet.
2. The original working file (spreadsheet with edit history, or the export log) and how long the labelling took.
3. An explanation of the "Team Label N:" prefix, the repeated rationale sentences and the identical aspect text on the 50 mixed rows.
4. Alternatively: fresh independent labelling by two named people on blank sheets made from the same frozen list, without any content of these sheets shared with them.
