# Validation report: the two returned sentiment sheets

Files (as found, never modified; copies and hashes are in `annotation/returned/` and `annotation/provenance_log.csv`):

| Sheet | Path | SHA-256 | Run by (named by the owner) |
|---|---|---|---|
| A | `C:/Users/cabal/Downloads/team_label_1_final_test_sheet_A_v1.csv` | `5e3670e36c82d51a...` | team 1, Caballero |
| B | `C:/Users/cabal/Downloads/team_label_2_final_test_sheet_B_v1.csv` | `2e3cb2a41d39c7d1...` | team 2, Guyo |

Method: `sentiment_agreement.py check` (records matched by review ID against the frozen blank sheets) and `provenance_forensics.py`.

## Structural and policy-v1 validation: PASSED

| Check | Sheet A | Sheet B |
|---|---|---|
| Rows | 400 | 400 |
| Same 400 review IDs as the frozen blank | yes | yes |
| Duplicate or missing IDs | 0 | 0 |
| Product, category, platform, language and review-text columns unchanged (matched by ID) | 0 rows edited | 0 rows edited |
| Columns equal to the blank | yes | yes |
| Row order | each follows its own blank sheet's order (A and B were shuffled differently); agreement code matches by ID, never by position | same |
| Allowed `sentiment` values, valid tags, valid `confidence` | 0 invalid | 0 invalid |
| Mixed rules (mixed needs the tag; the mixed tag needs both aspects; no neutral plus mixed; no-opinion only on neutral or unclear) | 0 violations | 0 violations |
| Completed rows / low-confidence rows | 400 / 27 | 400 / 25 |

No invalid row exists, so no corrected sheet is requested on structural grounds. No label was changed.

## Provenance: NOT SUBSTANTIATED (see `annotation_provenance.md`)

The structural checks cannot show who produced a label. Provenance fails: the returned files carry machine-generated patterns, and no annotator identity record, declaration or time record exists. Consequence under the protocol: **no human inter-annotator reliability is reported, adjudication is on hold, and the final test is not scored.**
