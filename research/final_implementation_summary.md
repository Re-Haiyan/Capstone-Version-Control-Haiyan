# Final implementation summary

Branch `research-improvements` (base `831f22f`), local commits, pushed to the owner's repository at their request. Nothing was deployed. All figures link to files in `research/results/` and are reproducible with the scripts in `research/`.

## What was actually implemented

**Production code (small, tested, no API change)**

* `lexicons/categories/all.tsv`: a "feared fake resolved as genuine" exception.
* `hazard_model.py`: a review-level guard `_feared_not_fake` ("akala ko peke, pero original pala": the sentence splitter separates the two clauses, so a sentence-level exception cannot see the resolution). No score on any labelled file changed (0 of 4,792 rows flipped); it fixes a real false positive found by the new regression matrix.
* `sentiment_calibration.py` (opt-in, off by default, falls back to the model's own label on any problem) and its trained artifact `research/artifacts/sentiment_calibrator_v1.joblib` (1.5 MB, scikit-learn 1.9.0 like the VM).

(The rule tuning from the earlier part of the session, commit `831f22f`, is also on this branch: shared `all.add.tsv` / `all.tsv`, packing damage is delivery, battery-drain policy, learned-model gates. Five tests that encoded the earlier policy were changed on purpose there: two file-name checks now allow the shared `all` files; the "burn fat and calories" power-bank case, the "iba ang flavor" cross-product contrast and the haircare battery quality case were removed; and "battery drains fast is still a defect on a gadget" was inverted. Each reflects the labels' measured behaviour, documented in `training/RESULTS_v1.md` and `annotation_policy_proposal.md`.)

**Research tooling** (all in `research/`): `data_audit.py`, `annotation_audit.py`, `agreement.py`, `label_noise.py`, `exp_tfidf.py`, `exp_embed.py`, `evaluate_all.py`, `exp_stacking.py`, `weak_supervision.py`, `al_simulation.py`, `active_learning.py`, `evidence_check.py`, `exp_sentiment.py`, `sentiment_eval.py`, `threshold_stability.py`, `bench_deploy.py`, shared helpers in `common.py`.

**Tests:** 206 pass (179 at an earlier milestone of the session). New: `test_regression_matrix.py` (23 review cases plus span validity and quotability), `test_agreement.py` (hand-computed statistics), `test_sentiment_calibration.py`.

**Deliverables (all 12 written):** `architecture_audit.md`, `annotation_audit.md` (+ queue CSV), `annotation_policy_proposal.md`, `annotator_agreement_template.csv` (+ `research/agreement/` sheets), `suspected_label_errors.csv`, `baseline_comparison.md`, `experiment_log.md`, `active_learning_candidates.csv`, `evaluation_report.md`, `deployment_benchmark.md`, `remaining_limitations.md`, this file.

## Experiments actually executed

E00 to E13 in `experiment_log.md`: leakage audit; sparse TF-IDF baselines (18 configurations); frozen multilingual embeddings (two encoders, four inputs); rule and model fusions; a stacker; weak supervision; an active-learning simulation (5 seeds); sentiment evaluation and recalibration; confident-learning audit; threshold stability; evidence-span audit; regression matrix; deployment benchmark on the real VM. **Not run:** SetFit, LoRA, larger encoders, distillation (their gate was not met).

## What was demonstrated

* **The tuned rule layer is the strongest system on this data** and the only explainable one; no sparse, embedding, fused or stacked model beat it reliably (every paired interval for the difference includes zero).
* **Sentiment recalibration helps clearly:** macro F1 0.605 to 0.718 in cross-validation and 0.570 to 0.717 on the historical test; neutral F1 0.19 to 0.49.
* **Active learning beats random** in simulation by more than the seed spread (for example +100 rows: 0.447 random against 0.501 to 0.533).
* **Evidence spans are valid** (1,912 checked, 0 invalid) but 155 of about 1,700 flags have none.
* **Deployment is fine:** 62 ms median per review, 14.4 reviews/s, 377 MB peak on the real 2-CPU VM.
* **The product-level aggregation already corrects per-star sampling** (inverse-probability weights) and uses Wilson lower bounds.

Historical-test F1 of the deployed rules (not an untouched test, intervals are product-bootstrap): counterfeit 0.94 (0.86, 0.99), not-as-advertised 0.72 (0.62, 0.81), quality 0.73 (0.42, 0.83), defect 0.69 (0.60, 0.76), safety 0.53 (0.31, 0.67). **The 0.80 aspiration is met for counterfeit only;** the research target "counterfeit >= 0.90" is met.

## What remains uncertain

Whether 0.80 is achievable at all for defect, safety and quality (label noise and ten undecided policy questions cap it); every small difference between systems (all within noise); whether the sentiment calibrator's gain holds on a fresh sample; whether the shipped classifiers saw any labelled review (provenance not in the repository).

## What requires human annotation

Two independent annotators on the 300-review agreement sheets; adjudication of the queues under an approved policy; a fresh product-disjoint labelled test set (start from the 200 active-learning candidates); labelled product conclusions.

## What is ready for deployment (needs the owner's explicit approval)

* The rule changes in `831f22f` plus the feared-fake guard: tested (206 tests), no regression on any labelled file, score changes documented. The VM is still at `d74589a`.
* The sentiment calibrator is **not** recommended for deployment yet: it changes the positive share that drives the buying conclusion; it should first be checked on a fresh sample and the owner's decision on the neutral definition.

## What to investigate next

1. Decide the ten policy questions, then re-adjudicate and measure agreement.
2. Collect the fresh test set and the 200 active-learning labels; re-measure with the intervals in `evaluation_report.md`.
3. Profile the pipeline per component to find where the 62 ms goes.
4. Add clause-level context to the exception mechanism ("manipis | pero oks") instead of more single-purpose guards.
5. Verify the provenance of the two shipped classifiers.
