# Phase 4: neutral classification recovery (report)

Branch `research/neutral-phase2`. Production runs `2c6e056` with the shipped ONNX int8 model (`e04da4c2…`); **nothing here was deployed, merged or changed in production**. The frozen 400-review test and held-out v2 were not used. The Phase 3 confirmation set was not used for training, tuning or selection; it was scored once for the two locked heads as a non-selecting check (section 6).

## 1. Annotation (priority 1)

All 3,000 neutral candidates are now labelled under policy v1 by **Claude** (`claude-sonnet-5-5`, directly, in-session; logged as Claude, **not ChatGPT**, and **not independent human annotation**): 2,800 in this phase (batches 03-29, 31-44, 46-60) plus 200 in Phase 3. Provenance: `annotation/ai_labelled/PROVENANCE.md`, `annotation/ai_annotation_log.csv` (hashes per batch). Candidates were not assumed neutral.

| Label | Rows |
|---|---:|
| Neutral | **1,612** (1,538 tagged `no-opinion`, 74 other: not tried yet, lukewarm, questions) |
| Positive | 1,031 |
| Negative | 259 |
| Mixed / unclear | 67 / 31 |

Target of about 1,500 neutral rows: reached in count (1,612), **not in diversity**: 95% are pre-written Lazada tag lists, 1,612 distinct texts from 185 products, English-heavy.

Neutral yield: production database 54% (2,950 rows), 10,000-review pool 24% (50 rows). By language hint: English 66% (1,345 of 2,050), unknown 53%, very short 20%, Taglish 11% (24 of 228), Filipino 13% (19 of 143). Genuine neutral opinions in Filipino and Taglish are therefore scarce in the data.

Limitation stated in the provenance file: long rows were shown truncated at about 170 characters; for many truncated tag lists I read only the visible part (and the tail of rows that looked like they might end in personal text). A minority of long rows labelled neutral by default may hide a personal ending. This is label noise in favour of neutral; it was not corrected.

## 2. False neutral analysis (priority 2; `results/phase4_false_neutral.json`)

Model R2 (T7 recipe retrained on the v1 training folds), split seed 11, rows true negative / neutral / positive: `[[307,52,6],[16,1568,103],[22,300,904]]`.

* Neutral to positive: 103 of 1,687 neutral. 73 carry `no-opinion`, 59 are tag-list shaped, 54 are low-confidence labels, 20 have lukewarm wording ("ok naman"). Typical: tag list plus "thanks seller", "ok na sya", a tag list with a gift remark.
* Positive to neutral: 300 of 1,226 positives; **267 are tag-list shaped**, 153 low-confidence. These are the buyer-selected Lazada tags: the annotator treated a list with no personal experience as no-opinion, but when the tags were possibly chosen by the buyer, or ended in praise, the label is positive. This is the S4 boundary; the model cannot separate them because the labels themselves are not consistent there. Natural-distribution dev-pool rows only: 9 neutral-to-positive, 21 positive-to-neutral.
* Negative to neutral: 52 of 365 (questions, "it would have been nice if...", delivery-only, hopeful wording). Neutral to negative: 16.
* English / Filipino / Taglish: neutral F1 is 0.89 in English but **0.43 in Filipino and 0.39 in Taglish** (macro F1 0.83 / 0.74 / 0.72). The neutral class is learnt mainly from English tag-list shape.

Two-stage pipeline against the one-stage head (identical folds, 3 split seeds; `phase4_experiments.py`): R6 (binary no-opinion detector, else three-class head) macro F1 0.848 against 0.846 for R2; R7 (head trained without no-opinion rows) 0.843, and its natural-distribution macro F1 drops to 0.796. **Two-stage gives no gain.** The binary no-opinion detector alone is reported separately in the JSON (`no_opinion_detector_binary`); its F1 is not a three-class score.

## 3. Development comparison (priority 3)

New development split: all three-class v1 rows (3,278: 365 negative, 1,687 neutral, 1,226 positive; 340 products; dev pool 376 + candidates 2,902), `StratifiedGroupKFold` by product, 5 folds, split seeds 11, 12, 13 (asserted: no product in both train and validation). Training = policy-filtered old corpus (same Phase 3 rule) + v1 training folds. Mean over seeds (spread across seeds at most 0.004):

| Config | Acc | Macro P / R | Macro F1 | Weighted F1 | F1 neg / neu / pos | Natural-dist. macro F1 |
|---|---:|---|---:|---:|---|---:|
| R1 v1 rows only, balanced (**P4A**) | 0.881 | 0.864 / 0.889 | **0.876** | 0.881 | 0.87 / 0.90 / 0.86 | 0.895 |
| R2 T7 recipe retrained | 0.847 | 0.865 / 0.835 | 0.846 | 0.845 | 0.86 / 0.87 / 0.81 | 0.854 |
| R3 R2 + FiReCS neutral | 0.857 | 0.859 / 0.859 | 0.859 | 0.857 | 0.87 / 0.87 / 0.83 | 0.849 |
| R4 tag-list rows down-weighted | 0.835 | 0.864 / 0.812 | 0.831 | 0.832 | 0.84 / 0.86 / 0.79 | 0.819 |
| R5 R2 without class weights (**P4B** recipe) | 0.865 | 0.856 / 0.876 | 0.865 | 0.866 | 0.87 / 0.88 / 0.85 | 0.880 |
| R6 two-stage | 0.850 | 0.871 / 0.835 | 0.848 | 0.848 | 0.86 / 0.87 / 0.81 | 0.850 |
| R7 two-stage, head without no-opinion | 0.852 | 0.878 / 0.820 | 0.843 | 0.850 | 0.83 / 0.87 / 0.82 | 0.796 |
| Locked T7 on 3,012 v1 rows it never saw | 0.774 | | 0.776 | | | |
| Locked T0 (`sentiment_head_v1`), same rows | 0.459 | | 0.494 | | neutral F1 0.04 | |

Fine-tuning (CPU, 12 threads; one fixed product-grouped split = fold 0 of seed 11: 2,623 train rows, 655 dev rows; epoch chosen on that dev fold; PEFT library not installed, so LoRA was **not** run; the parameter-efficient variant is top-2-layer tuning):

| Run | Trainable params | Time | Acc | Macro P / R | Macro F1 | Weighted F1 | F1 neg / neu / pos | Natural-dist. macro F1 (neutral F1) | Confusion (rows neg, neu, pos) |
|---|---:|---:|---:|---|---:|---:|---|---|---|
| top-2 layers, seed 1 | 14.8M | 1,115 s | 0.893 | 0.882 / 0.903 | 0.892 | 0.894 | 0.89 / 0.91 / 0.87 | 0.888 (0.84) | [68,0,5] [3,298,36] [8,18,219] |
| top-2 layers, seed 2 | 14.8M | 589 s | 0.896 | 0.885 / 0.904 | 0.894 | 0.896 | 0.89 / 0.92 / 0.87 | 0.888 (0.84) | [68,1,4] [3,303,31] [8,21,216] |
| full, seed 1 | 86.0M (word embeddings frozen) | 1,252 s | 0.925 | 0.912 / 0.924 | 0.917 | 0.926 | 0.90 / 0.94 / 0.91 | 0.853 (0.74) | [67,3,3] [2,310,25] [7,9,229] |
| full, seed 2 | 86.0M | 1,189 s | 0.930 | 0.922 / 0.926 | 0.924 | 0.930 | 0.91 / 0.95 / 0.91 | 0.848 (0.78) | [67,1,5] [2,317,18] [5,15,225] |

Precision / recall by class and confusion matrices for every head run are in `results/phase4_experiments.json`; per-epoch fine-tuning histories in `runs/p4_*.json`.

Reading: all development macro F1 values exceed 0.80, but (a) the dev set is 51% neutral and 95% of those are tag lists, so the neutral class is mostly a template detector; (b) full fine-tuning is better on the whole dev fold but **worse on the natural-distribution dev-pool rows** (0.85 against 0.89 for top-2 and heads), i.e. it fits the tag-list-heavy distribution; (c) the epoch and configuration were chosen on the same fold they are reported on (optimistic); (d) one annotator labelled everything, so the scores measure agreement with this annotator's reading of policy v1. They are **not** evidence of 0.80 on independent data.

## 4. Held-out set (priority 4)

Still **blocked**: new products must come from an authorised fresh marketplace scan, which was not authorised. Protocol and builder are ready (`phase2/heldout_v2_protocol.md`, `build_heldout_v2.py`). The final candidate was **not** locked for a final test. Two heads (P4A, P4B; `phase4_lock.json`, artifact hashes) were locked before they were scored once on the Phase 3 confirmation set, which is Claude-annotated, already used for T0/T7, and not product-independent (only 8 of 184 rows have a product absent from the Phase 4 training data), so it is a consistency check only: P4A accuracy 0.891, macro F1 0.883 (95% 0.828 to 0.931), neutral F1 0.81; P4B accuracy 0.848, macro F1 0.821 (0.749 to 0.878), neutral F1 0.67 (`results/phase4_confirmation.json`). Not used to select anything.

## 5. Product-level impact (priority 5; same 60 saved products, real conclusion pipeline, nothing saved; `results/conclusion_impact__{p4a,p4b,t7}.json`)

| | Deployed | P4A | P4B | T7 |
|---|---:|---:|---:|---:|
| Mean positive / neutral / negative share | 0.802 / 0.117 / 0.081 | 0.550 / 0.309 / 0.142 | 0.600 / 0.267 / 0.134 | 0.542 / 0.356 / 0.103 |
| Conclusions changed (less / more favourable) | n/a | 31 (30 / 1) | 26 (25 / 1) | 32 (31 / 1) |
| Recommended / mixed / caution / not recommended | 25 / 4 / 22 / 9 | 3 / 16 / 16 / 25 | 4 / 17 / 20 / 19 | 1 / 17 / 17 / 25 |
| Spearman of positive share with deployed order | 1 | 0.10 | 0.17 | 0.24 |
| "Recommended" despite an issue warning | 0 | 0 | 0 | 0 |

Complaint visibility and hazard warnings: issue-warning states are untouched by the sentiment candidate and no recommended card sits on a product with a warning; the negative share rises (0.08 to 0.10-0.14), so complaints are not hidden. The neutral share roughly triples and product order is almost reshuffled, because the conclusion thresholds were set around the shipped model's neutral behaviour. This measures behaviour change, not accuracy (no independently labelled product conclusions exist).

**Recommendation: do not deploy any of these models.** Reasons: labels are from one AI annotator and are dominated by tag lists; the S4 boundary (buyer-selected tags) is unresolved and drives the errors; Filipino/Taglish neutral is weak; no independent held-out result exists; the conclusion policy is not neutral-invariant and would flip many product conclusions.

## 6. Tests, leakage, provenance (priority 6)

295 existing tests plus 11 new (`tests/test_phase4_annotation.py`: completeness, policy-v1 validity, provenance wording, helper parsing, lock hashes, no product shared between folds). Leakage: the frozen test and held-out v2 untouched; dev folds asserted product-disjoint; corpus rows equal to a v1 review removed from training; the confirmation set is text-disjoint but shares products with the training candidates (stated above). Secret scan of new files: no matches.

## 7. Remaining blockers

1. Authorised fresh scan for the new held-out set (and ideally human or second-AI labels on a sample).
2. Adviser decision on S4 / v1.1 (buyer-selected Lazada tags) and a second annotator to measure agreement on that boundary.
3. More genuine neutral opinions in Filipino and Taglish.
4. A conclusion policy that is robust to a better neutral class, and independently labelled product conclusions, before any customer-facing switch.
