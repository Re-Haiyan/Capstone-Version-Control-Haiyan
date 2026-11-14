# How two annotators complete the agreement sheets

**Purpose.** To find out (1) how often two independent people agree on these labels, and (2) whether the team-supplied labels used in all the earlier evaluation are as good as human labels (`research/annotation_provenance.md`). Your honest, independent judgement is what is needed, not agreement with anyone.

## Rules

1. **Work alone.** Do not talk to the other annotator, do not compare answers, and do not look at the repository's labelled files (`evaluation/annotated/`, `research/*.csv`). Do not use an AI tool to label: the point is a human reference.
2. Annotator A fills `sheet_A.csv`, annotator B fills `sheet_B.csv`. They hold the same 300 reviews in a different order. You will not see model predictions, earlier labels, or any hint of how a review was chosen.
3. Fill the three empty columns on **every** row you can decide:
   * `sentiment`: `positive`, `neutral` or `negative`, the reviewer's overall feeling about the product.
   * `flags`: one or more of `defect`, `counterfeit`, `safety`, `not_as_described`, `quality`, `delivery`, joined with `;` (for example `defect;delivery`), or `none`. **Never leave it blank**: a blank row is treated as "not done", not as "none".
   * `confidence`: `high`, or `low` when the review is unclear or depends on information you do not have.
4. Do not edit `id`, `stars`, `product` or `review_text`. Save as CSV (UTF-8) under a new name, for example `sheet_A_done.csv`. Partial sheets are fine: only reviews completed in **both** sheets are compared, and at least 30 are needed.
5. Use the policy that is in force: **v1** (`docs/annotation_guides/round1_nongadget_README.md` and `round3_delivery_and_safety_README.md`), not the v2 draft, unless the owners approve v2 first. If v2 is approved, both annotators must use the same version, and the version must be written in the file name.

## The flags in one line each (v1)

* `defect`: it does not work, stopped working, arrived broken, leaks or tears.
* `counterfeit`: the reviewer says it is fake or not the original brand ("I thought it was fake" is not a report).
* `safety`: a hazard to a person, pet or home: fire, smoke, burn, shock, a sharp edge, choking, a skin reaction, spoiled goods.
* `not_as_described`: size, colour, material, amount, flavour or items differ from the listing.
* `quality`: it works but is weak, flimsy, thin or looks cheap.
* `delivery`: a complaint about delivery, packing or the seller.
* Praise, denials and worries ("baka masira") are not reports. When unsure, mark `confidence = low`.

## After both sheets are done (the person running the study)

```
python research/agreement.py score   research/agreement/sheet_A_done.csv research/agreement/sheet_B_done.csv
python research/agreement.py compare research/agreement/sheet_A_done.csv research/agreement/sheet_B_done.csv
```

* `score` prints, for each flag and for sentiment: raw agreement, Cohen's kappa with a 95% interval, Gwet's AC1, positive agreement, negative agreement and the 2x2 table, for all completed reviews, for each sampling stratum and for the rows both annotators marked high confidence.
* `compare` prints kappa between A and B and between each annotator and the team-supplied labels. If the supplied labels are human-quality, the second and third columns are close to the first.
* The file `id_map.csv` (sheet id, original id, stratum) is needed for both commands and must **not** be given to the annotators.
* No agreement figure is reported before `score` has run on two completed sheets.

Interpretation of kappa (Landis and Koch, a convention, not a law): below 0.40 poor to fair, 0.40 to 0.60 moderate, 0.60 to 0.80 substantial, above 0.80 almost perfect. For rare flags (safety, counterfeit) read AC1 and the positive agreement beside kappa, because kappa falls when a flag is rare.
