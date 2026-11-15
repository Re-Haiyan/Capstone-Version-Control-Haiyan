# Error analysis of the deployed model (ONNX int8)

Data: `results/error_analysis__onnx_int8__{market_test_v3,market_train_v3,firecs_test}.json` from `error_analysis.py` (generated from `predictions/onnx_int8__*.csv`). An "error" is a **disagreement with the label**: marketplace labels are team-supplied and unverified, so part of every error class below may be the label's fault. Tags are transparent regular-expression heuristics, not annotations; a review can carry several. The data contain no reviewer names or identifiers; examples are shortened.

## 1. Where the errors are (confusion cells)

| True label to predicted | `test_v3` (846; 292 errors, 34.5%) | `train_v3` (3,946; 1,162 errors, 29.4%) | FiReCS test (3,147; 524 errors, 16.7%) | Severity |
|---|---:|---:|---:|---|
| neutral to positive | **129** (44% of errors) | **415** (36%) | 164 (31%) | high: hides a middling or empty review as praise and inflates the positive share |
| negative to neutral | 61 | 265 | 142 | high: a complaint disappears from the negative share |
| positive to neutral | 50 | 186 | 70 | low |
| neutral to negative | 31 | 146 | 134 | medium |
| negative to positive | **19** | 133 | 13 | **highest**: a complaint read as praise |
| positive to negative | 2 | 17 | 1 | low |

Neutral is the failure class on marketplace data: F1 0.19 (`test_v3`) and 0.24 (`train_v3`) against 0.76 on FiReCS, with 129 of the 191 neutral reviews of `test_v3` predicted positive. Negative recall on `test_v3` is 0.67 (0.78 to 0.81 on the older 300 and the fresh sets), and 19 of 240 negative reviews are predicted positive.

## 2. Error rate by text feature (`test_v3`; `train_v3` agrees in direction)

| Feature | Reviews | Error rate `test_v3` | `train_v3` | FiReCS |
|---|---:|---:|---:|---:|
| contrast marker ("pero", "but", "kaso") | 144 | **0.535** | 0.440 | 0.224 |
| star rating contradicts the label (4-5 stars labelled negative, or 1-2 stars labelled positive) | 84 | **0.643** | 0.602 | n/a |
| three-star review | 40 | **0.625** | 0.498 | n/a |
| short (4 to 6 words) | 64 | 0.547 | 0.332 | 0.094 |
| Filipino (heuristic) | 161 | 0.472 | 0.347 | 0.172 |
| unknown language (heuristic) | 89 | 0.472 | 0.393 | 0.171 |
| Taglish (heuristic) | 167 | 0.329 | 0.309 | 0.166 |
| English (heuristic) | 424 | 0.276 | 0.249 | 0.124 |
| delivery or seller mentioned | 233 | 0.300 | 0.299 | 0.157 |
| listing template or feature list | 247 | 0.296 | 0.267 | n/a |
| emoji | 139 | 0.345 | 0.283 | n/a |
| negation | 342 | 0.275 | 0.278 | 0.183 |
| failure words ("sira", "broken", "not working") | 103 | 0.214 | 0.275 | 0.188 |
| "not yet used / will update" | (46 in `train_v3`) | n/a | 0.391 | n/a |
| elongation or capitals | 48 | 0.104 | 0.211 | 0.100 |

Reading: mixed opinions, middling reviews, short reviews and Filipino text are the hard cases; clear failure words and shouted praise are easy.

## 3. Taxonomy with examples and likely cause

| Error type | Count (`test_v3`) | Example (shortened) | Likely cause |
|---|---:|---|---|
| Neutral labelled, predicted positive: **listing feature lists and template fields** | within the 129 | "Adjustable temperature settings, LED display for easy operation, Sleek and modern design" (5 stars) | Domain mismatch: the model reads promotional adjectives as praise; the label says no opinion. **Annotation policy** (is a feature list neutral?) decides who is right. |
| Neutral labelled, predicted positive: **lukewarm or hedged** | within the 129 | "maliit pala pero keri lang sa bag ... malakas naman din" | Mixed or lukewarm text; FiReCS-style neutral is one third of its data but only 6 to 23% here; **insufficient neutral training examples** and a prior mismatch. |
| **Labels that are questionable** | several | "super cool 😎 👌 and super" labelled neutral; "dumating na parcel ko wala naman damage sana epektib" labelled neutral; "thanks po ... walang sira o butas ... yummy Creamy and delicious cheese" labelled negative | **Annotation ambiguity or error**; one reader's impression, not a measurement. The model is arguably right in these. |
| Negative labelled, predicted neutral or positive: **polite opening, complaint later** | 61 + 19 | "ok namn Yung item Kaso ... para dipo mag leak"; "the unit is functioning well ... but the right fender was broken ... " | Mixed clauses: the model follows the first clause. **Model limitation** plus the missing `mixed` class in a three-class scheme (the reviewer is mixed; the label says negative). |
| Star rating contradicts the label | 84 (54 errors) | 5 stars, label negative: "sobrang nipis lang pala nya sakto lang sa price" | The stars are not sentiment; the **model correctly ignores stars** and the labels are inconsistent with them. Do not use stars as ground truth. |
| **Delivery or seller complaints** versus the product | 233 mention delivery (70 errors) | "Damaged, partially opened box. Rider must have mistakenly delivered ... " (neutral to negative) | Policy question (is delivery-only sentiment about the product?) (`annotation_policy.md` S2). |
| Fixed-field or past-problem text | few | "nung una tumatagas sya pero ngayon goods na" (labelled negative, text now praises) | Temporal contrast; model limitation. |
| Short and ambiguous | 64 (35 errors) | "okay okay Pero kulang ibang parts" | **Insufficient context**: a person would need the listing; `unclear` in the policy. |
| Sarcasm | not separable by heuristic | none found reliably | Not measured. |
| Quantisation | n/a | no int8-versus-FP32 comparison is possible because the fine-tuned FP32 checkpoint is missing | See `model_audit.md`. |

## 4. What the analysis supports and what it does not

* Supported: neutral is the dominant failure on this marketplace data, the model hides neutral as positive and misses part of negative text when a polite opening comes first, Filipino and mixed-opinion reviews are the hardest, and stars are a poor proxy.
* **Not supported:** that the model is wrong in every counted error. The labels are unverified, the neutral policy is undefined, and `mixed` has no class. The only way to settle individual cases is the two-annotator workflow (`annotation_execution_guide.md`).
