# research/: index

The research round of the review-classification work. Start with `final_implementation_summary.md`.

| Document | What it answers |
|---|---|
| `final_implementation_summary.md` | What was implemented, run, demonstrated, left uncertain, blocked on annotation, ready to deploy |
| `evaluation_report.md` | The numbers: rules with confidence intervals, per group, sentiment, conclusions, thresholds, what a valid final claim still needs |
| `baseline_comparison.md` | Sparse, embedding, fusion, stacking and weak-supervision baselines against the rules |
| `experiment_log.md` | Every experiment with hypothesis, setup, result and decision |
| `architecture_audit.md` | How a review becomes a flag, component inventory, leakage audit, evidence-span audit |
| `annotation_audit.md` | 534 label suspicions for human adjudication (CSV: `annotation_audit_queue.csv`) |
| `suspected_label_errors.csv` | 192 confident-learning suspects (129 high priority) |
| `annotation_policy_proposal.md` | A proposed v2 labelling policy (not in force) with the evidence for each decision |
| `annotator_agreement_template.csv`, `agreement/` | Independent annotation sheets and `agreement.py` for kappa, AC1 and agreement per flag |
| `active_learning_candidates.csv` | 200 informative unlabelled reviews for the next labelling round |
| `deployment_benchmark.md` | Latency, memory and throughput on the real 2-CPU VM and on the training PC |
| `remaining_limitations.md` | What is blocked, what is uncertain, what was deliberately not done |

Results behind the numbers: `results/*.json`. Cached inputs (rule decisions, probabilities): `cache/`. Artifacts: `artifacts/` (the opt-in sentiment calibrator). Shared code: `common.py`.

Rules of the round: no training or tuning on the historical test; thresholds from product-grouped out-of-fold predictions; every label-dependent split is by product; nothing was deployed or pushed to the team repository.
