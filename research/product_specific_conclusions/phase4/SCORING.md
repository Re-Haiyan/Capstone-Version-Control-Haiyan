# Phase 4 — prospective paired aspect evaluation

**Status (2026-11-15): preparation only. No new D3/V3/F2 reviews, annotations or candidate model are claimed.** The frozen historical C3 product-feature recall of **0.371** and F1 **0.517** have **not** improved.

The standalone scorer in phase4/score_pairs.py compares supplied C3 and candidate predictions on the **exact same new reviews**, by product, category and language. It does not fabricate reviews, generate labels, train a classifier, or authorize a release. Its synthetic unit tests must never be reported as empirical model results.

## Precondition: genuinely new annotated data

Use the rights-cleared real reviews produced by phase4/intake.py. The source CSV (D3.csv, V3.csv or the sealed F2 file), and the separate annotation/prediction files, must remain in restricted folders **outside the Git repository**.

Reference labels must be created by the project's declared **AI-assisted exploratory** annotation procedure, with exact model version, complete rubric, date and whether predictions were visible. Empty/unknown/incomplete review labels do **not** count as completed annotations, and cannot be silently excluded.

The scorer expects exactly one JSONL row for **each review ID** in the accepted CSV. The reference format is:

    {"review_id":"actual-review-id","status":"complete","pairs":[{"kind":"product","aspect_id":"build_quality","polarity":"positive"}]}

Predictions use an identical row without the status field. Use an empty pairs array when the reviewer/model finds **no aspects**, not when a reviewer hasn't read the review. Kind is one of product/service/trust, polarity positive/negative. Actual aspect IDs must follow the preregistered vocabulary. The scorer validates pair syntax and duplicate detection; it **does not** verify vocabulary membership or whether the model really generated a supplied prediction file.

## Mandatory reference provenance

Create a private provenance JSON with the following fields:

- reference_type: exactly ai_assisted (do not claim an independent human reference)
- annotator_model: complete **real** model/version name
- annotation_date: actual date
- rubric_sha256: complete 64-character SHA256 of the frozen annotation instructions
- accepted_csv_sha256: full SHA256 of the precise accepted split CSV
- blind_to_predictions: true or false as actually conducted

Example command (all paths below are local and private, not committed):

    python research/product_specific_conclusions/phase4/score_pairs.py --split V3 --reviews /private/phase4/V3.csv --reference /private/labels/V3.jsonl --baseline /private/predictions/C3_V3.jsonl --candidate /private/predictions/C6_V3.jsonl --provenance /private/labels/provenance_V3.json --out /private/results/v3_comparison.json

The report includes TP/FP/FN and P/R/F1 for T0 all kinds, T1 product, T2 service, T3 authenticity, 95% Wilson intervals for P/R, paired product-cluster bootstrap for T1 F1 difference, breakdowns by category/language and the descriptive threshold check for whether all T1 P/R/F1 reach 0.800.

**A high proxy score does not establish independent or human accuracy.** Even if the threshold is reached, source-linked unsupported claim review, serious-safety checks, saved verdict parity, actual staging benchmark, category/language coverage and owner deployment sign-off are additional independent gates. The report always sets production approval to false.

## Sealed final F2

The final test is **one-time**, after a candidate code version and rubric have been frozen. The scorer refuses F2 without a separate freeze manifest and a fresh exclusive score-ledger file. Freeze manifest required fields:

- accepted_csv_sha256: checksum of the accepted, sealed F2 input file
- candidate_commit_sha and baseline_commit_sha: actual full 40-character Git commit IDs
- rubric_sha256: hash of the unchanged annotation instructions
- frozen_before_final_reference: true only when the chronology is genuinely documented
- feature_policy: unchanged

Example extra CLI arguments for F2:

    --split F2 --freeze /private/final/freeze.json --final-ledger /private/final/one_time_score_ledger.json

The tool verifies the dataset and rubric hashes but **cannot prove a human/operator truthfully froze the code first** or that a model produced any supplied predictions. Preserve the code commit, prediction-generation commands and run logs in separate access-controlled records. The final-ledger exclusive write is not tamperproof against a privileged operator.

Keep the original 0.80 target; do not use the old Phase 3 F review rows as a new final. Do not deploy or alter the recommendation policy as a byproduct of this evaluation.

## Synthetic-only checks

    python -m unittest discover -s tests -p 'test_phase4_score_pairs.py' -q

These synthetic tests measure software correctness **only**. Until a rights-cleared D3/V3/F2 exists, every new model-performance claim remains **not evaluated**.
