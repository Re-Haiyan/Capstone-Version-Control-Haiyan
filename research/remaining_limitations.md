# Remaining limitations and blockers

## Blocked on human work (nothing here was faked)

| Item | Why it is blocked | What is ready |
|---|---|---|
| Inter-annotator agreement | Needs two independent completed annotation sheets | `research/agreement.py` (sheets, kappa, AC1, positive/negative agreement, intervals, bootstrap), 300 review sheets in `research/agreement/`, math unit-tested on hand-computed cases; `score` refuses to run on fewer than 30 reviews labelled in both |
| A fresh final test set | No untouched, product-disjoint labelled data exists | `research/active_learning_candidates.csv` (200 reviews from 129 products) and the existing scan tooling |
| Product-conclusion accuracy | No independently labelled conclusions | Scenario tests of the verdict logic; thresholds unchanged |
| Adjudicated labels | Needs a policy decision and annotators | `annotation_audit.md` / `annotation_audit_queue.csv` (534 suspicions, 29 high priority), `suspected_label_errors.csv` (192, 129 high), `annotation_policy_proposal.md` |
| Measuring active learning on new labels | Needs a labelling round | A simulation on existing labels (E07) |

## Scientific limits of what was measured

1. **No untouched test exists.** The 846-row file was inspected in earlier rounds; its numbers are a historical benchmark with wide intervals (quality 0.42 to 0.83; safety 0.31 to 0.67). Differences of a few points between systems are not resolvable at this size.
2. **The rules were tuned on the training rows**, so their training and cross-validation-adjacent scores are optimistic (defect 0.74 on the tuned rows against 0.69 on test). Any model that takes the rule flags as input (the "embedding + rules" model, the stacker) inherits that optimism in training.
3. **Label noise and policy drift cap every score.** Ten policy questions (`annotation_policy_proposal.md`) are decided inconsistently in the labels; until two people label the same reviews we cannot say what ceiling is achievable, and 0.80 per flag may be unreachable on defect, safety and quality.
4. **Rare flags.** Safety has 78 training and 16 test positives (11 test products): no model or rule change can be shown to help it at this size. Report it as "12 of 16 found (95% interval 0.51 to 0.90), 17 false alarms".
5. **Distribution shift.** The test file is concentrated in beauty/health, home and food and has no `other` or pet reviews of substance; the group table in `evaluation_report.md` shows results swing between groups (defect 0.47 on beauty/health, 0.77 on home).
6. **Repeated templates.** 343 repeated review texts inside training slightly inflate cross-validation.
7. **Provenance of two shipped classifiers** (`hazard_classifier_v6`, `extra_labels_v1`): their training data is not in the repository, so any overlap with the labelled files cannot be ruled out.
8. **Sentiment.** Neutral is poorly recognised (F1 about 0.2) because the team's neutral reviews are mostly 5-star reviews without a stated opinion; the opt-in calibrator helps (0.57 to 0.72 macro F1 on the historical test) but learns this team's definition and this sample, and is not wired in.
9. **Evidence for model-only flags.** 111 defect, 22 not-as-advertised, 21 quality and 1 safety flags (of about 1,700) come from the learned layers and carry no highlighted words; a probability is not an explanation, and the UI should say so for them.
10. **Segmentation.** The sentence splitter breaks at "pero", so keyword exceptions cannot see a resolution in the next clause; one review-level guard (feared fake) was added, others ("manipis | pero oks") remain.
11. **Deployment numbers** come from one VM run with the site idle; no per-component profile or load test was done.

## Things deliberately not done

* No push to the team repository (it returns 403) and **no deployment** to the VM from this round. The work is on the owner's own repository (branches `research-improvements` and `deployment`) at the owner's request.
* No historical label was changed; no test was edited to fit new behaviour in this round. In the round before (rule tuning, commit `831f22f`) five existing tests that encoded the earlier battery, flavour and calories policy were changed on purpose; they are listed in `final_implementation_summary.md`.
* SetFit, LoRA, larger encoders and distillation were not run because their gate (a competitive embedding baseline) was not met.
