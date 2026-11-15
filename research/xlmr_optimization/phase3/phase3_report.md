# Phase 3: policy-v1-consistent neutral recovery (report)

Branch `research/neutral-phase2`. The frozen 400-review test and held-out v2 were **not** used for anything here (labels, predictions or errors); the shipped production model is unchanged; nothing was deployed. All new labels are **AI-assisted by Claude** (not ChatGPT), recorded in `annotation/ai_labelled/PROVENANCE.md` and `annotation/ai_annotation_log.csv`; they are not independent human annotations.

## 1. Policy

Policy v1 is unchanged (hash `annotation/policy_v1.lock.json` re-verified). S4 stays the default: feature descriptions without the reviewer's own opinion are neutral and tagged `no-opinion`. The v1.1 clarification (`phase2/policy_s4_recommendation.md`) stays a **separate pending proposal**; it was not applied to any label. The prompt used for annotation is the v1 prompt. Observed boundary problem, stated for the adviser: Lazada's pre-written tag lists (for example "Convenient wireless design, Comfortable fit, ...") may be tags a buyer chose, which is an endorsement; v1 S4 and my reading treated 3 or more such claims without personal experience as `no-opinion`, and marked uncertain ones `low`.

## 2. Annotation status (Claude, policy v1, blind batches, all imported and validated)

| Set | Rows annotated | Positive | Neutral | Negative | Mixed | Unclear |
|---|---:|---:|---:|---:|---:|---:|
| Dev pool (400) | 400 | 195 | 75 | 106 | 20 | 4 |
| Neutral candidates (3,000) | **200** (4 batches: 2 "not yet used", 2 feature-list) | 69 | 95 | 29 | 5 | 2 |
| Confirmation (frozen first, 200) | 200 | 86 | 41 | 57 | 14 | 2 |

Remaining: **2,800 neutral candidates** are unannotated; the neutral yield of annotated candidates is 95 of 200 (47%), about 70% in the two feature-list batches, so about 1,700 neutral rows are plausible from the 2,464 feature-list candidates **if** all were annotated; the target of 1,500 diverse neutral rows is not reached (neutral rows available under v1: 75 dev + 95 candidates + 41 confirmation = 211).

## 3. Training-corpus audit and the documented exclusion (policy-based, not metric-driven)

| Source | Rows | Neutral | Feature-list-shaped rows (neg / neu / pos) |
|---|---:|---:|---|
| FiReCS train | 7,340 | 2,549 (35%) | 0 (no listing text) |
| Marketplace team labels | 3,629 | 667 (18%) | 1,064 (156 / **223** / **685**) |
| AI pool (older rubric) | 6,778 | 146 (2%) | 1,517 (316 / **18** / **1,183**) |

* Feature-list-shaped rows in the two older sources were labelled under rubrics that conflict with policy v1 S4 (21% and 1% neutral). **Procedure:** they are **excluded from v1 training, not relabelled** (2,581 rows), as are 73 rows equal to a v1-labelled review (these include the 73 dev-pool reviews that were already in the old corpus, which are also removed from the validation set).
* FiReCS neutral rows (2,549) follow another convention (negative and mixed text appear in them; `phase2/neutral_error_analysis.md`): compared with and without them. Excluding them is justified by policy v1 (mixed is not neutral); the data comparison below shows the effect.
* Duplicates and near-duplicates: texts equal to any v1 review were removed from the corpus; the frozen test's matches had already been removed in Phase 2 (59 rows). Product overlap: dev pool, frozen test and annotated candidates are product-disjoint from each other; the confirmation set is **text-disjoint from everything but not product-disjoint from the older corpora and the unannotated candidates** (nearly every production product is in them); this treats T0 and T7 alike.

## 4. Strategies compared (development data; `results/phase3_experiments.json`)

Development validation: 303 three-class dev-pool rows (74 negative, 62 neutral, 167 positive; the 73 old-corpus overlaps and 24 mixed/unclear excluded), logistic head on the shipped encoder embedding, C 0.003. The 200 annotated candidate rows are training-only. The 5-fold product-grouped cross-validation is over all 496 eligible v1 rows (dev non-overlap + candidates), training = filtered corpus + the v1 training folds.

| # | Configuration | Dev acc | Macro P / R | Macro F1 (95%) | F1 neg / neu / pos | Neutral P / R | CV macro F1 (neutral F1) |
|---|---|---:|---|---|---|---|---|
| T0 | previous head (old corpus; = `sentiment_head_v1` setting) | 0.729 | 0.540 / 0.607 | 0.568 (0.542 to 0.591) | 0.90 / 0.00 / 0.80 | 0.00 / 0.00 | 0.550 (0.06) |
| T1 | T0 + class weights | 0.710 | 0.599 / 0.603 | 0.592 | 0.90 / 0.09 / 0.78 | 0.15 / 0.06 | |
| T2 | v1-filtered corpus | 0.729 | 0.533 / 0.609 | 0.566 | 0.90 / 0.00 / 0.80 | 0.00 / 0.00 | 0.544 (0.06) |
| T3 | T2, FiReCS neutral excluded | 0.752 | 0.646 / 0.629 | 0.584 | 0.91 / 0.03 / 0.81 | 0.33 / 0.02 | |
| T4 | T2 + 200 v1 candidate rows | 0.743 | 0.633 / 0.631 | 0.604 | 0.90 / 0.11 / 0.81 | 0.29 / 0.06 | 0.639 (0.31) |
| T5 | T4 + class weights | 0.769 | 0.731 / 0.690 | 0.701 | 0.90 / 0.38 / 0.83 | 0.49 / 0.31 | 0.767 (0.61) |
| T6 | T4, FiReCS neutral excluded | 0.756 | 0.733 / 0.638 | 0.602 | 0.90 / 0.09 / 0.81 | 0.60 / 0.05 | 0.679 (0.38) |
| **T7** | **T6 + class weights** | **0.795** | **0.794 / 0.795** | **0.777 (0.719 to 0.829)** | 0.83 / **0.65** / 0.86 | 0.53 / 0.84 | **0.788 (0.72)** |

Findings: the filter alone changes nothing; neutral only appears when **policy-v1 neutral examples are present** (T4 against T2) and **class weights** are used (T5, T7); excluding FiReCS neutral lets the small, policy-consistent neutral set carry the class (T7 against T5). Balanced sampling, hard-example mining and calibration were compared on the older corpus in Phase 2 (`phase2/candidate_comparison.md`) and were not repeated; a separately evaluated **no-opinion detector** (binary, product-grouped cross-validation over the v1 rows): 154 positives in 496 rows, precision 0.81, recall 0.86, F1 0.84 (`no_opinion_detector_cv`; small and single-annotator). Full or parameter-efficient fine-tuning was **not run**: the head ceiling was the labels, and this compares configurations at the cost of seconds rather than hours; fine-tuning the encoder is the next experiment once more v1 labels exist.

**These development scores are optimistic**: T7 was chosen among eight configurations on the same 303 rows, and its training and validation labels come from one annotator.

## 5. Confirmation (frozen before annotation; two locked configurations, scored once, nothing tuned afterwards; `results/phase3_confirmation.json`)

`phase3_lock.json` (artifact hashes) was written before the confirmation set was built. Three-class rows: 184 (57 negative, 41 neutral, 86 positive); mixed 14 and unclear 2 kept apart. Reference: Claude, policy v1 (AI-assisted).

| Metric (target 0.80) | T0 `sentiment_head_v1` | **T7** |
|---|---:|---:|
| Accuracy | 0.745 | 0.761 |
| Macro precision / recall | 0.671 / 0.655 | 0.749 / 0.744 |
| Macro F1 (95% product bootstrap) | 0.626 (0.566 to 0.694) | **0.743 (0.672 to 0.795)** |
| Weighted F1 | 0.691 | 0.769 |
| F1 negative / neutral / positive | 0.939 / 0.157 / 0.782 | 0.889 / **0.543** / 0.798 |
| Neutral precision / recall | 0.40 / 0.10 | 0.49 / 0.61 |
| Re-weighted to the usable population | 0.644 | 0.740 |

Confusion matrices (rows true negative, neutral, positive): T0 [54, 2, 1], [1, 4, 36], [3, 4, 79]; T7 [48, 9, 0], [1, 25, 15], [2, 17, 67]. By stratum (macro F1): cue rows 0.589 (T0) and 0.738 (T7); no-cue rows 0.679 and 0.721.

**Targets: not met.** T7 reaches 0.80 for none of accuracy (0.761), macro precision (0.749), recall (0.744), macro F1 (0.743), weighted F1 (0.769), neutral F1 (0.543); positive F1 is 0.798 (no interval computed for it) and negative F1 0.889. The improvement over T0 is clear on neutral (0.157 to 0.543) and macro F1 (+0.12), at a cost in negative F1 (0.939 to 0.889).

## 6. Leakage findings

* Phase 2 audit unchanged: dev pool, neutral candidates and frozen test share no text or product; 73 dev-pool texts were in the old corpus and are now excluded from validation (and from training of every configuration that is scored on the dev rows).
* Confirmation set: text-disjoint from the frozen test, dev pool, all 3,000 candidates, the old corpus and every v1 label (5,782 equal and 494 near-duplicate texts removed); not product-disjoint from old corpora (stated above). No v1 row used in training (the 200 candidate rows) is in it.
* The frozen test and held-out v2 were not read.

## 7. Held-out v2

Still **blocked**: new products must come from an authorised fresh scan, which was not performed (no authorisation was given to scan marketplaces and the production database has no unused products). Protocol and builder are ready (`phase2/heldout_v2_protocol.md`, `build_heldout_v2.py`). The confirmation set above is an intermediate, AI-annotated, not product-independent check, not a replacement.

## 8. Remaining work

1. Annotate the other 2,800 neutral candidates (ChatGPT per the owner's designation, or Claude recorded as such) and retrain; fine-tune the encoder on v1-consistent labels (2 to 3 seeds).
2. A second annotator (human or a second AI session) on a sample, to measure annotator agreement on the neutral boundary; adviser decision on v1.1.
3. Fresh scan and held-out v2; human check of AI-assisted references.
4. T7 is a candidate only: it changes product conclusions (neutral share rises), so it needs the conclusion-impact study (`research/xlmr_optimization/conclusion_impact.py`) and a deployment decision; it is **not deployed**.
