# Phase 2: neutral sentiment recovery (status report)

Continues from local commit `de39603`. Frozen-test results (shipped model and `sentiment_head_v1`) are preserved unchanged and remain AI-assisted-reference scores. Nothing in this phase used the frozen test (labels or texts) for optimisation, selection, annotation revision or thresholds. The shipped model is unchanged; nothing was deployed or pushed.

| Task | Outcome | Files |
|---|---|---|
| 1. Annotation consistency | Denominators reconciled (400 / 383 / 351 / 37 = 32 + 5). S4 retained with proposed clarification v1.1 (needs adviser confirmation; v1 and the frozen labels untouched). | `denominator_reconciliation.md`, `policy_s4_recommendation.md` |
| 2. Neutral training data | 400-review dev pool and a 3,000-review neutral candidate pool prepared as blind batches (68 files of 50), prompt and import/validation tool with provenance logging built. **No ChatGPT annotation exists yet; none was fabricated.** Candidate sources counted (14,155 cue-bearing unused reviews). | `annotation/chatgpt_prompt_policy_v1.md`, `annotation/chatgpt_batches/`, `import_ai_annotations.py`, `neutral_sources_report.json` |
| 3. Classifier strategies | Class weighting, balanced resampling, hard-example mining, calibration and the combination compared on a separate development validation set and grouped cross-validation. Best neutral F1 0.37 (baseline 0.30). Full fine-tuning not run (reason documented). | `candidate_comparison.md`, `strategy_*.csv` |
| 4. Targets (macro F1, neutral F1, positive F1, negative F1, accuracy at least 0.80) | **Not met** on development data (best marketplace macro F1 0.665, neutral F1 0.37). Causes below. | |
| 5. Evaluation and deployment protection | Held-out v2 protocol and builder written; **blocked on a fresh scan**. Leakage audit done. | `heldout_v2_protocol.md`, `build_heldout_v2.py`, `phase2_leakage_audit.json` |

## Why the neutral target is out of reach on current data (evidence)

1. **The training labels contradict policy v1 on feature-list reviews**: 21% neutral in the marketplace team labels, 1% in the AI pool, against the v1 rule that makes them neutral. The head learns "feature list is positive" (`neutral_error_analysis.md`).
2. **FiReCS neutral is not policy-v1 neutral** (it holds negative and mixed text) and supplies 76% of the corpus's neutral rows.
3. **Strategy changes shift recall by about 0.1** but cannot repair precision when labels conflict.

## Data leakage audit (Phase 2 pools)

Dev pool, neutral candidate pool and the frozen test share **no exact or near-duplicate text and no product** (`phase2_leakage_audit.json`). The neutral candidates are also disjoint from the training corpus. **One issue found:** 73 dev-pool reviews (77 near-duplicates) also appear in the AI-pool training corpus; they are listed in `annotation/dev_pool_overlap_with_training.csv` and must be excluded from any validation use of the dev pool (or from training when the dev pool is the validation set).

## Deliverables

Neutral error analysis (`neutral_error_analysis.md`), S4 recommendation, candidate comparison table, per-class report and confusion matrices (CSV), updated pipeline scripts (`neutral_candidates.py`, `neutral_strategies.py`, `import_ai_annotations.py`, `build_heldout_v2.py`, `phase2_tables.py`), leakage audit. **Annotated development dataset: not available**: it requires ChatGPT to annotate the prepared batches.

## Remaining blockers (all need you or the adviser)

1. **ChatGPT annotation** of `dev_pool_batch_01..08` and then the neutral candidate batches, using `annotation/chatgpt_prompt_policy_v1.md` unchanged; import each returned file with `import_ai_annotations.py --model ... --submitted-by ... --date ...` (records provenance as stated). I cannot run ChatGPT and did not label any row.
2. **Adviser decision on S4** (retain v1 as is, or adopt v1.1) before annotation, because the prompt must match the policy used.
3. **Process record** for Team Label 1 and 2 and the dev annotation (`annotation/annotation_process_record_template.md`).
4. **Decision on FiReCS neutral** (exclude from policy-v1 neutral training, or sample it through a v1 annotation pass).
5. **Fresh scan** for held-out v2 (and authorisation to scan), plus the human-check sample size for the AI-assisted reference.
6. Human adjudication of the 37 frozen-test disagreements (original blocker).

Order of work once 1 to 4 are done: import labels, rerun `optimize_head.py`/`neutral_strategies.py` on the v1-consistent corpus, fine-tune the encoder (2 to 3 seeds) if the head ceiling remains, lock the candidate, then score the new held-out v2 once.
