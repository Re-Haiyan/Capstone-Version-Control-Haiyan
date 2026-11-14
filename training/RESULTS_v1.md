# Review-flag model v1: first run

XLM-RoBERTa base (cardiffnlp/twitter-xlm-roberta-base-sentiment) fine-tuned on 3,328 team-labelled reviews (validation 377, cut by product), tested on 766 held-out high-confidence rows from 47 products the model never saw. Input: product category, title, stars and the review. Four epochs, 83 minutes on the CPU. Epoch 3 was kept (best validation).

Test F1 (precision / recall):

| Label | Positives | Rules | Model alone | Best combination, chosen on validation |
|---|---|---|---|---|
| Defect | 60 | 0.61 (0.49 / 0.80) | 0.56 (0.51 / 0.62) | 0.60 (0.51 / 0.73) |
| Counterfeit | 52 | 0.94 (0.94 / 0.94) | 0.79 (0.92 / 0.69) | 0.94 (rules alone) |
| Safety | 12 | 0.56 (0.41 / 0.92) | 0.26 (0.17 / 0.50) | 0.62 (0.50 / 0.83) |
| Not as advertised | 60 | 0.61 (0.77 / 0.50) | 0.64 (0.56 / 0.75) | 0.70 (0.58 / 0.88) |
| Quality | 52 | 0.74 (0.62 / 0.92) | 0.70 (0.64 / 0.77) | 0.85 (0.82 / 0.88) |

The model alone does not beat the rules. Combined with them it helps quality and not-as-advertised. Combination per label was picked on the validation slice (few positives for counterfeit and safety, so those choices are noisy); the test rows were not used to choose.

Defect precision is limited by a labelling policy gap, not only by the rules: the rules also flag overheating and smoke as defect, while the annotators marked these as safety only (or none when "mabilis uminit" is not alarming). 19 rule false alarms on validation, 8 of them heat or smoke.

Files: train_label_model.py, dump_probs.py, dump_rules.py. Runs are in training/runs (not committed).
