# Baseline comparison

All numbers come from saved result files in `research/results/` and can be regenerated with the scripts named. **Cross-validation (CV)** = product-grouped 5-fold on the 3,946 training rows (rare flags spread across folds); thresholds and hyper-parameters are chosen on the out-of-fold predictions, so CV scores are slightly optimistic. **Historical test** = the 846-row file inspected during earlier development; it is *reported*, never used to choose anything here. Intervals are 95% product-level bootstrap (resampling products, not reviews).

## 1. The systems compared

| System | What it is |
|---|---|
| Rules (deployed) | The keyword and rule layer with the learned gates, product category files, commit `831f22f` + a robustness fix (no score change) |
| Sparse | Word + character TF-IDF with class-weighted logistic regression, one model per flag (`exp_tfidf.py`) |
| Embedding | Frozen multilingual encoder embeddings + logistic regression (`exp_embed.py`) |
| Embedding + rules | The same, with the rule decisions as extra input features |
| Fusions | Rules OR / AND the sparse model; a regularised stacker over the rule decision and the out-of-fold sparse probability (`evaluate_all.py`, `exp_stacking.py`) |
| Weak labels | Gold training rows plus weakly labelled unlabelled reviews (`weak_supervision.py`) |

## 2. Experiment A: sparse text baselines (CV macro F1 over six flags, best of 18 configurations)

| Features | Best C | Macro F1 (CV) |
|---|---:|---:|
| word 1-2-grams | 16 | 0.629 |
| character 2-5-grams | 4 | 0.620 |
| word + character | 4 | **0.645** |
| word + character, **with category + title prefixed** | 16 | 0.616 |

Putting the product category and title in front of the text made every sparse configuration worse (about 0.02 to 0.04 macro F1), most likely because the extra tokens dilute the word weights; the rule layer uses the category instead. Training takes about 2 seconds per flag; inference about 0.002 ms per review.

Best per flag (CV F1 / historical test F1 with interval): defect 0.71 / 0.65 [0.55, 0.72]; counterfeit 0.87 / 0.88 [0.76, 0.95]; safety 0.36 / 0.40 [0.21, 0.57]; not-as-advertised 0.71 / 0.66 [0.56, 0.75]; quality 0.66 / 0.68 [0.35, 0.84]; delivery 0.58 / 0.50 [0.28, 0.63].

## 3. Experiment B: frozen multilingual embeddings (licences: e5-small MIT, MiniLM Apache-2.0)

| Encoder + input | Macro F1 (CV, six flags) |
|---|---:|
| e5-small, review alone | 0.525 |
| e5-small, category + title + review | 0.507 |
| MiniLM, review alone | 0.436 |
| MiniLM, category + title + review | 0.366 |
| **e5-small + structured features (rule flags, stars, group)** | 0.714 |

Embeddings alone are clearly **worse than the sparse baseline** (0.525 against 0.645). The jump to 0.714 comes from the rule flags in the structured features, not from the embeddings. Those rules were tuned on these same training rows, so a model that sees them in training over-trusts them; that row of the table is therefore not evidence that embeddings help. On the historical test the embedding + rules model scores defect 0.72, counterfeit 0.94, safety 0.53, not-as-advertised 0.70, quality 0.71 (delivery 0.44), which is within the rules' own intervals (section 5). e5-small costs 12.7 ms per text on 10 CPU threads in PyTorch, and no ONNX export exists, so it could not run in production without a new export step. Not adopted.

## 4. Experiments C, D and E: SetFit, larger models, distillation

**Not run.** The gate in the brief was "only if the embedding baseline performs competitively". It did not: frozen embeddings alone were 0.12 macro F1 below the sparse model, and the previous session's fine-tuned XLM-R base runs (about 3,500 rows, 50 to 85 minutes each) were unstable between runs and added at most 2 points to the tuned rules (`training/RESULTS_v1.md`). A larger model or LoRA adds hours of CPU training for an unproven gain; distillation needs a teacher that has shown a repeatable advantage, and none has.

## 5. Rules, sparse model and fusions on the historical test (F1 [95% product-bootstrap interval])

| Flag (positives) | Rules | Sparse | Fusion selected on the validation slice | Stacker | Stacker minus rules (95% paired interval) |
|---|---|---|---|---|---|
| defect (68) | **0.69** [0.60, 0.76] | 0.65 [0.55, 0.72] | sparse model | 0.71 [0.60, 0.79] | -0.05 to +0.08 |
| counterfeit (53) | **0.94** [0.86, 0.99] | 0.88 [0.76, 0.95] | rules | 0.96 [0.91, 1.00] | 0.00 to +0.06 |
| safety (16) | **0.53** [0.31, 0.67] | 0.40 [0.21, 0.57] | rules | 0.53 [0.29, 0.67] | 0.00 to 0.00 |
| not as advertised (60) | **0.72** [0.62, 0.81] | 0.66 [0.56, 0.75] | rules | 0.76 [0.66, 0.84] | -0.02 to +0.11 |
| quality (57) | **0.73** [0.42, 0.83] | 0.68 [0.35, 0.84] | rules | 0.74 [0.50, 0.83] | -0.05 to +0.11 |

* Macro F1 over the five flags: rules 0.722 (micro 0.740); the validation-selected fusion 0.715 (micro 0.731).
* **No fusion reliably beats the rules.** Every stacker difference interval includes zero (counterfeit's lower end is exactly zero). Where the validation slice picked the sparse model for defect, the test shows it slightly worse (0.65 against 0.69, interval -0.14 to +0.05). That is a documented example of validation noise: the slice has few positives per flag.
* The stacker weights the rule decision (coefficients 2.8 to 4.4) and the out-of-fold sparse probability (2.2 to 5.5) about equally and gives the star rating a negative weight (-0.8 to -1.7); its small gains are not distinguishable from noise.

## 6. Weak supervision (Part 7)

* 250 labeling functions fire (every row of the shared and group addition files); 816 of their same-flag pairs overlap by Jaccard >= 0.8. The group files repeat the same shared wording, so these are not independent evidence and were not counted as such.
* A precision-weighted vote has high precision and low recall against the human labels (defect 0.80 / 0.37; counterfeit 1.00 / 0.02; safety 1.00 / 0.01; not-as-advertised 0.90 / 0.70; quality 0.79 / 0.06): the counterfeit and safety vocabulary lives in the core lexicon, not in the addition files that were turned into functions. It abstains on 56% of training rows.
* **Adding weakly labelled reviews did not help.** Grouped-CV macro F1 (five flags): gold only 0.625; gold + 500 weak rows 0.620; gold + 2,000 weak rows 0.623. The weak rows come from the same rule patterns the model already learns from the gold data. Inconclusive at best; gold-only is retained.

## 7. Conclusion

On this data and size, the **tuned rule layer is the strongest and the most explainable system**; sparse and embedding models are close on defect and not-as-advertised but never reliably better, and fusions add nothing that is distinguishable from noise. Targets of 0.80 per flag were not reached by any system for defect, safety or quality; counterfeit exceeds its target, and not-as-advertised is at 0.72 to 0.76. The honest reading of the intervals is that quality and safety cannot be ranked against each other at this test size.
