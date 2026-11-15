# Phase 3 protocol: improving feature extraction (written before any extractor change)

Written 2026-11-15, before the development data was annotated and before any rule was edited. Nothing in this file may be revised after the final evaluation to make a result look better; a change must be added as a dated amendment at the bottom.

## 1. The historical baseline is kept
The locked evaluation (150 reviews, 80 claims, `human_eval_pack/`, one Claude-assisted annotation set in `ai_annotation/claude_session_1/`) is the **historical baseline** of extractor version `asp2`: features precision 0.718, recall 0.285, F1 0.408; claims 63 of 80 correct. It is unchanged. Its reviews, labels, misses and per-row outputs are **not used** to write rules, choose thresholds or select a candidate. (A summary by kind and by profile was computed after scoring and is descriptive; it is not a rule source.) Any claim of improvement is made on separate data.

## 2. What is evaluated: three tasks, decided now
The extractor reports three kinds of statement, taken from the aspect tables' `kind`:

| Task | Kinds | Why separate |
|---|---|---|
| **T1 product features** | `product` (softness, battery life, fit, taste ...) | what the product-specific conclusion is about; the primary task |
| **T2 service experiences** | `service` (delivery, packaging, seller, freebies, condition on arrival) | about the shop and courier, shown separately on the card |
| **T3 authenticity reports** | `trust` (authenticity) | a safety-relevant claim, qualified as an unverified customer report |
| **T0 all kinds** | all | the overall figure used in the baseline; kept for continuity |

T0, T1, T2 and T3 are all reported for every candidate, with the baseline's decomposition for reference. The 0.80 target is stated for each. **No task, category or difficult example is removed from any score**; the baseline's 0.408 is the T0 figure and stays so.

## 3. Data (all new; nothing from the locked sample)
- **Source:** the team's own public Lazada scans (`backups/pool-scans`, scraped 2026-11-13 to 14 by the team; reviewer names are never read or stored) for hair, skin, apparel, food and appliance; and the saved electronics products for powerbank, earbuds, phone and general. Collection date and source file are recorded per row.
- **Exclusions:** every product in the locked pack; every review of the locked sample or its near-duplicates (same text after normalisation, or token Jaccard 0.8 or more); near-duplicates inside the new samples; reviews under 20 characters. Reviews drawn from products whose reviews were read while tuning earlier (electronics; the 21 real products analysed first) are **development-only**, never final.
- **Product-grouped splits** (a product's reviews never straddle splits; assignment by hash of the product link with the salt `phase3`):
  - **D1 development, inspected:** may be read, mis-extractions studied, rules written.
  - **D2 development validation, not inspected:** used only to compare candidates and to apply the adoption rule; its mis-extractions are not read until the candidate is frozen.
  - **F final, fresh:** drawn now, annotated only after the extractor is frozen, scored once. Its reviews are never read before the freeze.
- Annotation is Claude-assisted (Claude Sonnet 5.5 via Claude Code), blind to the system's output, with the six interpretation rules of `annotation_process_record.md` unchanged. It is **not** independent and **not** human; the record names the model. If a second annotator (a person, or another AI that is named as such) labels a subset, it is reported separately.

## 4. Candidates, fixed in advance
| ID | Approach |
|---|---|
| C0 | the committed extractor `asp2` (baseline) |
| C1 | expanded lexicons: cues for product vocabulary and Filipino/Taglish phrasings found missing in D1 |
| C2 | C1 + improved clause handling (contrast conjunctions, labelled prompt answers such as "Charging Speed: ...", multi-clause reviews) |
| C3 | C2 + context-sensitive rules (for example "sira" or "ayaw gumana" read as a functionality fault; star-aware reading of one-word verdicts) |
| C4 | C3 + hybrid topic-plus-polarity: where a feature **topic** is named and the clause has a polarity from the project's existing lexicon, but no explicit cue pair exists |
| C5 | lightweight trained aspect classifier |

C5 is **not built unless the labelled data supports it**: a classifier needs on the order of hundreds of labelled examples per class, and the development set will hold a few hundred labelled pairs in total across more than 100 aspect labels. If that is still true after annotation, C5 is reported as "not evaluated: insufficient training data", not as a failed model.

## 5. Adoption rule (prospective)
A candidate replaces the baseline only if **all** hold on D2 (the uninspected development validation):
1. T1 F1 improves by at least 0.03 absolute over C0.
2. T1 precision falls by no more than 0.03 absolute from C0's (more recall may not buy many false statements).
3. Unsupported-claim rate on the claims the candidate shows does not rise above C0's by more than 0.03 absolute, judged on a sample of 60 new claims drawn from D2 output.
4. Evidence verification: 0 problems; quality audit: 0 issues; all existing tests pass; decisions and verdicts for the 182 saved products unchanged; hazards and the off-switch unchanged.
5. First-read p95 stays under 1 second and does not more than double.
If several qualify, the one with the best T1 F1 on D2 is chosen. A candidate that finds more but fails 2 or 3 is **rejected**. Then F is annotated and the frozen extractor is scored once; the result is reported whatever it is, beside the baseline's.

## 6. What this protocol cannot promise
0.80 for precision, recall and F1 are optimisation goals. A rule-based extractor that is deliberately conservative may not reach 0.80 recall without unacceptable false statements; the final report will say what was reached and what it cost.

## Amendments (dated; none changes a rule after seeing the final result)

**2026-11-15, before F was opened:**
1. **Candidate contents.** C3 also carries profile-specific vocabulary found missing in D1 (food taste phrases such as "best taste" and "taste is top notch"), not only context rules. Reason: it was found in D1 while writing C3 and fits no other candidate.
2. **Unsupported-claim rule (criterion 3).** The protocol said "a sample of 60 new claims from D2 output". After the freeze, **every** D2 detection absent from the reference was read instead (C3: 12, C0: 15), which is a stronger check than a sample. Result: C3 9 of 100 detections unsupported, C0 12 of 60. Judged by the annotator, not independently.
3. **D2 use.** D2 metrics were looked at once per candidate (C0 to C4, five times) and the false detections of C0 and C3 once, after the freeze. D2 is therefore a *validation* set that influenced the choice between candidates, not an untouched test; F is the untouched test.
4. **Fresh final set composition.** F contains no electronics, because every electronics review in the project was read while tuning in earlier rounds; F is real non-electronics reviews from products absent from the locked pack and from D1 and D2.
5. **Apparel in D2.** D2 has no apparel products (the hash split put the few apparel products in D1 and F); apparel is represented in F.
6. **Annotation additions.** Prompt answers in the reviewer's own words ("Price: good") count; bare thanks to a seller or rider is not a statement; the absence of a problem ("not irritating") is a positive statement. These were fixed before F and are in `annotated/provenance.json`.
7. **C5** was not built (about 170 reference pairs over more than 100 aspect labels).
