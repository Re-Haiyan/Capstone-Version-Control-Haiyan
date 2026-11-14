# Annotation policy: proposed revision (v2 draft, NOT in force)

**Status:** proposal for the annotators and the project owners to approve. The policy in force is v1 (the labelling guides in `evaluation/README_nongadget_labelling.md` and the round-3 README). Historical labels were **not** changed. Each proposed change names the evidence that suggests it; the evidence is the team's own labels, so a change here is a decision about what the label *should* mean, not a correction of an error.

## Principles (unchanged)

1. Label what the reviewer reports **about the product itself**; seller, courier, packing and refund disputes are not product flags.
2. Praise, denials and hypotheticals are not reports ("no rash", "hindi mukhang mumurahin", "baka masira").
3. A review can carry several flags; a 5-star review can still carry one.
4. Doubtful rows are marked `confidence = low` and are not scored.
5. Product context decides: the same words differ between a power bank, a shirt and a serum.

## Flags

| Flag | Definition (v2 proposal) | Exclusions | Needs the listing? |
|---|---|---|---|
| defect | The product does not work, stopped working, arrived broken, leaks, tears, or a part is faulty | Damage that is only to the box or packing (use `delivery`); fast battery drain on its own; an effect that did not show (a serum that did not whiten) | No |
| counterfeit | The reviewer says it is fake, a copy or not the original brand | "I thought it was fake but it is genuine"; a product named "replica" | Sometimes (brand claims) |
| safety | A hazard to a person, pet or home: fire, smoke, burn, shock, sharp edge, choking, skin reaction, spoiled or expired goods, illness | Weather heat; the normal heat of a hair tool or pan; praise ("safe and non-toxic"); feature claims ("leak-proof"); a far-off expiry date | No |
| not_as_described | What arrived differs from the listing: wrong or different item, size, colour, material, brand, variant; fewer items or parts than ordered or advertised | A fit complaint ("too small for me"); a freebie that was not part of the listing; "malaki pala" as a pleasant surprise | Yes where the wording is "too small", "half empty", "missing freebie" |
| quality | It works but is weak, flimsy, thin, rough, fades, wobbles or looks cheap | "Manipis pero okay" (thin with a concession); packing quality ("packing quality is awful") | No |
| delivery (new) | A complaint about delivery, packing or the seller: late, courier, box opened/wet/crushed, missing packing, no reply, refused refund | Praise of fast delivery | No |

## Decisions that the data suggests (each needs a yes or no from the owners)

| # | Question | What the team's labels show (training file, 3,946 rows) | Proposed rule |
|---|---|---|---|
| 1 | Damage to the box or packing: defect or delivery? | Damage words and packing words together: defect in 83 of 343 rows (24%), delivery in 91 | `delivery` only; add `defect` only if the item itself is damaged |
| 2 | Fast battery drain: defect, quality or none? | 68 rows: quality 6, defect 18, none 43 | None, unless the reviewer says the product is faulty |
| 3 | "Too small / too big / too tight" | 52 rows: not_as_described in 9 (17%) | A fit remark (none) unless the size differs from the listing |
| 4 | Missing freebie | 61 rows: not_as_described in 11 (18%) | Only if the listing promised the freebie |
| 5 | Half-empty pack ("kalahati lang laman") | 16 rows: not_as_described in 7 (44%), an inconsistent split | not_as_described if the listing states the amount; otherwise none |
| 6 | Fear of fire without an incident ("nakakatakot, baka masunog") | Labelled safety in some rows and none in others (see the annotation audit) | safety when the product is the stated cause and the fear is about heat, smoke or burning; mild "umiinit lang" with no worry is none |
| 7 | "Manipis pero okay" | Thin with a concession: quality in 29 of 75 rows (39%); thin without one: 64 of 79 (81%) | A concession ("pero okay", "lang") means none |
| 8 | Heat or smoke already labelled safety: also defect? | Defect co-occurs with safety in 10 of 399 defect rows | safety only, unless a real fault is also stated |
| 9 | A counterfeit report: also defect? | 12 of 121 counterfeit rows also carry defect | counterfeit only, unless a real fault is also stated |
| 10 | Product-effect complaints ("hindi umepekto", "walang epekto") | Seen labelled both none and defect in the error review (not counted) | none (a possible future label `effectiveness`) |

## Ambiguous and multi-label cases

* A review about the box **and** the item: label both (delivery plus defect).
* "I ordered white but they sent black": not_as_described, and delivery only if the reviewer blames shipping or the seller.
* A review mixing praise with one fault: label the fault.
* When the decision depends on the listing and the annotator cannot see it, mark `confidence = low`.

## Procedure for adopting the proposal

1. The owners decide rows 1 to 10 above (yes/no per row).
2. Two annotators label the 300-review agreement sheets (`research/agreement.py make`) independently; agreement per flag is computed (`research/agreement.py score`).
3. The adjudication queue (`annotation_audit.md`, `suspected_label_errors.csv`) is worked through with the new policy; every changed label keeps its original in a new column.
4. Only then is the training file versioned as `v4` and the rules and tests aligned with it. Until then, tests that encode v1 behaviour stay as they are, and any test that contradicts a proposed rule above is a documented disagreement, not a failure to fix.
