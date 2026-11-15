# Neutral-class error analysis (training data, out-of-fold; the frozen test is not used)

Source: `results/neutral_strategies.json`, baseline head, grouped 5-fold out-of-fold predictions over the 17,747-row corpus. Cues are regular expressions (`neutral_candidates.cues`), not annotations.

## Where neutral rows go wrong

| Source (neutral rows) | Neutral rows missed | Predicted positive | Predicted negative | Of the misses, with a feature-list cue |
|---|---:|---:|---:|---:|
| FiReCS (2,549) | 365 | 129 | 236 | 0 |
| Marketplace team labels (667) | 563 | **384** | 179 | **206 of 563 (180 predicted positive)** |
| AI pool (146) | 108 | 63 | 45 | 15 |

(Neutral recall: FiReCS 0.86, marketplace 0.16, AI pool low and unreliable with 146 rows.)

## Findings

1. **On marketplace text neutral is mostly hidden as positive** (384 of 667 neutral rows), and nearly half of those have the listing-copy shape (a list of short claims without first person). The model reads promotional wording as praise.
2. **The same shape is labelled positive far more often than neutral in the training data**: among feature-list-shaped reviews only 21% of the marketplace team labels are neutral (223 of 1,064; 685 are positive) and 1% of the AI-pool labels (18 of 1,517). So the training data disagree with policy v1 S4 (which makes such reviews neutral) and with each other. A classifier trained on these labels learns "feature list is positive"; the frozen-test failure (36 of 45 neutral reviews predicted positive) reproduces exactly this.
3. **FiReCS "neutral" is a different thing.** The misses there are mostly predicted negative (236 of 365), and examples show negative or mixed text filed as neutral ("sira ang celphone stand", a review praising the item and complaining about shipping, "wrong product ... does not serve its purpose"). This is consistent with a convention that mixed reviews are neutral; policy v1 forbids that. FiReCS neutral rows are therefore not policy-v1 neutral and their share (2,549 of 3,362 neutral rows in the corpus) dominates the neutral class the model sees.
4. **Short reviews and "not yet used"** are a minor part of the misses (a few dozen).
5. **Class weighting, balanced resampling and mining move neutral recall from 0.23 to about 0.35** on the marketplace validation slice but not precision (about 0.4): the separation is limited by the label conflict, not by the sampling scheme.

## What would fix it (legitimate)

1. Annotate neutral candidates under policy v1 (the prompt, batches and import tool are ready: `annotation/chatgpt_batches/`, `import_ai_annotations.py`). Candidate pool: 3,000 reviews; the share that policy v1 calls neutral is unknown until annotated.
2. Treat FiReCS neutral as a different label (do not mix it into the policy-v1 neutral class): either train FiReCS only for positive/negative, or sample FiReCS neutral rows through a v1 annotation pass to measure how many are really neutral.
3. Confirm S4 and its clarification (`policy_s4_recommendation.md`), then retrain on v1-consistent labels and validate on the labelled dev pool.
