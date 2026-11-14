# research/: index

> **Label provenance caveat.** Every score in this folder is a score against *team-supplied labels of unverified provenance*. The labels returned in the 2026-11-13/14 rounds came back far faster than row-by-row manual labelling allows (0.3 to 1.5 seconds per review), and the repository holds no annotator record. They are silver labels until a human-labelled subset confirms them. See `annotation_provenance.md`.


The research round of the review-classification work. Start with `final_implementation_summary.md`.

| Document | What it answers |
|---|---|
| `finalization_round_summary.md` | **Start here for the latest round**: what was implemented, run, demonstrated, uncertain, blocked and ready |
| `annotation_policy_v2.md` | The ten owner decisions compared with v1, the label data and the current rules (supersedes `annotation_policy_proposal.md`) |
| `evidence_completeness.md` | Evidence states, why model-only flags are 17% right, the opt-in evidence policy |
| `clause_context.md` | Clause-level context: the mechanism, its switch and its measured cost |
| `sentiment_calibration_review.md` | Calibrator audit, shortcut test, shadow-mode effect on 60 products |
| `product_conclusion_evaluation_protocol.md` | How to judge product conclusions independently (sheets in `conclusion_eval/`) |
| `fresh_eval/README.md` | The proposed fresh evaluation set, its roles and what more data is needed |
| `final_implementation_summary.md` | What was implemented, run, demonstrated, left uncertain, blocked on annotation, ready to deploy |
| `evaluation_report.md` | The numbers: rules with confidence intervals, per group, sentiment, conclusions, thresholds, what a valid final claim still needs |
| `baseline_comparison.md` | Sparse, embedding, fusion, stacking and weak-supervision baselines against the rules |
| `experiment_log.md` | Every experiment with hypothesis, setup, result and decision |
| `architecture_audit.md` | How a review becomes a flag, component inventory, leakage audit, evidence-span audit |
| `annotation_audit.md` | 285 suspicion entries over 280 unique training reviews (16 high priority) for human adjudication (CSV: `annotation_audit_queue.csv`). An earlier version reported 534 entries / 502 reviews: 219 of them were a substring bug ("amag" matched inside "damage"); see `annotation_audit.md` |
| `suspected_label_errors.csv` | 192 confident-learning suspects (129 high priority) |
| `annotation_policy_proposal.md` | A proposed v2 labelling policy (not in force) with the evidence for each decision |
| `annotator_agreement_template.csv`, `agreement/` | Independent annotation sheets and `agreement.py` for kappa, AC1 and agreement per flag |
| `active_learning_candidates.csv` | 200 informative unlabelled reviews for the next labelling round |
| `deployment_benchmark.md` | Latency, memory and throughput on the real 2-CPU VM and on the training PC |
| `annotation_provenance.md` | Who or what produced the labels: the evidence, what is unknown, what it means for every score |
| `remaining_limitations.md` | What is blocked, what is uncertain, what was deliberately not done |

Results behind the numbers: `results/*.json`. Cached inputs (rule decisions, probabilities): `cache/`. Artifacts: `artifacts/` (the opt-in sentiment calibrator). Shared code: `common.py`.

Rules of the round: no training or tuning on the historical test; thresholds from product-grouped out-of-fold predictions; every label-dependent split is by product; nothing was deployed or pushed to the team repository.
