# Phase 6D: completed GPT-6 second AI annotations for 200 random development reviews

Status: The full 200-review AI annotation pass is complete. It is NOT independently human-verified ground truth and must not replace the original Claude labels.

## Files and reproducibility

- phase6d_random200_ids.csv: fixed sample with Python random.Random(20261115).sample(sorted(all_3400_development_ids), 200), committed at 9f0a4ad0ac5e5f22481ee38d77d5073dd3f87e7f BEFORE viewing the selected reviews.
- phase6d_gpt6_random200_batch01.csv through batch05.csv: five full-text GPT-6 AI review decisions locked separately at a42e10e, 91b21fd, 8c99947, fda7f2a, 526f974, each exactly 40 IDs with labels, tags, mixed aspects, confidence, concise rationale and AI provenance.
- phase6d_gpt6_random200_v1.csv: exact consolidated 200-row version. Audit fails if any original batch differs or a row is missing.
- PHASE6D_PROVENANCE.md: how the selected samples were reviewed and the AI/human distinction.
- phase6d_audit.py: checks protected source Git blobs, original development review text, label constraints, exact sample coverage, four-source integrity, agreement and bootstrap confidence intervals; no model evaluation.
- phase6d-random200.yml: Python 3.11/3.12 CI with metadata-only artifacts.

## Comparison

| | Claude v1 | GPT-6 second AI |
|---|---:|---:|
| Negative | 24 | 26 |
| Neutral | 93 | 18 |
| Positive | 74 | 148 |
| Mixed | 2 | 1 |
| Unclear | 7 | 7 |
| TOTAL | 200 | 200 |

Raw five-class sentiment agreement: **120/200 (60%)**, Cohen kappa approximately **0.401**. There are **80 sentiment disagreements**, of which **74 are Claude Neutral to GPT-6 Positive**, mostly positive-sounding template/tag review lists. Most such GPT-6 Positive readings are low confidence. This does not prove Claude or GPT-6 is correct.

**Prior exposure:** 13 sampled review IDs were in earlier GPT-6 sets. Those original decisions were not intentionally opened during the new annotation pass, but previous conversation context may have exposed them. Thus this is not a strictly blinded or independent human study. Report agreement excluding those 13 as sensitivity.

## Why S4 remains unsettled

Approved Policy v1 treats feature lists without opinions as Neutral, but genuine evaluative adjectives may express Positive textual sentiment. The buyer-chosen-vs-platform-generated origin of those adjectives is unknown. Two AI annotators can reasonably differ. No automated relabeling should follow without documented approved policy clarification.

A better v2 would separately label expressed text sentiment, proven evidence of the customer's own experience, source/provenance uncertainty, and service-only feedback. Do not silently overwrite approved v1. Human review of the full 200 under Phase 6C and an adviser S4 decision remain important.

The 200 rows were random only within an intentionally Neutral-candidate-heavy 3,400-row development pool, NOT a natural marketplace sample. Agreement is not model F1 and does not show independent 0.80 performance.

No original annotation, frozen final test, already-used confirmation, heldout v2, trained model, deployed service or product conclusion has changed.
