# Phase 4 preregistration: product-feature recall study

**Written:** 2026-11-15 **before** any Phase 4 data collection, annotation, model candidate, or scoring. This document states intended methods; **Phase 4 has not run.** Changes must be appended under a dated amendment *before* inspecting validation/final errors. Never rewrite thresholds after seeing final results.

## 1. Baseline and isolation

- Frozen Phase 3 baseline: asp3 C3, measured once on fresh F (104 non-electronics reviews): **T1 precision 0.852 / recall 0.371 / F1 0.517**; T0 F1 0.459, T2 F1 0.333. Reference: one Claude-assisted annotation set, *not independent or human*. Product verdicts for 182 saved items are unchanged.
- Phase 3 locked 150-review pack, D1, D2 and F, along with their raw reviews, labels, misses, and hashes, are **historical data**. No Phase 4 candidate is developed, tuned, selected, or prompted using their rows, labels, or error lists. Report Phase 3 only as history, never re-open F as a 'fresh' test.
- Do not change the sentiment model, safety/hazard thresholds, recommendation policy, persisted reports or production path under this research protocol.

## 2. New data required (before candidate changes)

Collect rights-compliant *new* real reviews from *new* product listings not found in any locked, development, or final Phase 3 packs. Retain no reviewer IDs, contact information or seller private data. Record collection date, marketplace/source class, product hash, category/group, detected language and review hash; restrict raw access to authorized annotators.

Aim for **at least 300 development reviews (D3), 150 validation reviews (V3), and 200 untouched final reviews (F2)** across distinct products. These are collection targets, not a license to weaken rules if supply is short. Prioritize adequate positive and negative examples per product-feature type and report pair counts (not just reviews). Seek electronics, apparel, food, appliance, hair and skin; footwear and motorcycle parts require their own real review collections before validation or release. Include English, Filipino and Taglish, contrast/negation, labelled prompt answers, implied praise/complaints, and ambiguous service/trust references. Do not fabricate 'real' observations.

Assign an entire **product** to one split by a reproducible salted hash of canonical listing identifier. Check each new listing against all historical product IDs/hashes and previously reviewed listings. Remove exact and near-duplicate review texts within and across all splits (normalized text and token Jaccard >=0.80). If source records cannot establish disjointness, exclude the item. Never sample F2 from products whose reviews influenced rules or annotation prompts.

## 3. Blinded reference labels

Two independent human annotators are the preferred standard. They read review text without model output, one review at a time, and label (review, aspect_id, polarity) pairs separately for **product**, **service**, and **unverified authenticity report**. Use a single documented, prospective rubric; allow `none`, `unclear` and an explicit disagreement record. Empty or incomplete rows remain pending, never guessed.

If an AI-assisted set is made, record model ID, interface, complete instructions/prompt, date, human corrections, and which outputs were visible. Report it as **AI-assisted reference**, not human or independent ground truth. Agreement or a consensus between correlated AI sessions does not replace independent humans. Keep blind adjudication and raw A/B sheets intact; document how uncertain rows affect metrics.

## 4. Candidate families (development only)

- **C6:** Repair hypothetical/expectation handling, distinguishing `works as expected` and `faster than expected` from wishes, plans, or untested products.
- **C7:** Add carefully scoped implicit product-feature statement handling: e.g., capacity inferred from *reviewer-observed fit*, overly-small items described without an explicit adjective cue, and contextual Filipino/Taglish expressions. Do **not** treat advertising/suggestion lists or star ratings alone as aspect evidence.
- **C8:** Contrast, negation and multi-clause attribution with separate product vs service reference handling and safety preservation.
- **C9:** Lightweight classifier/hybrid *only if* labelled pair counts per relevant class, adequate separate products, and independence permit it; otherwise mark **not evaluated** rather than train on insufficient examples.

The baseline C3 is rerun on the **same new rows** for comparison. Use D3 to inspect misses and write rules. V3 is used only for predeclared candidate selection, not ongoing error-driven rewriting. Do not read F2 reference or candidate output until a candidate is frozen with code SHA and file hashes.

## 5. Prospective candidate selection (on V3)

A candidate can replace C3 for further evaluation only when **all** hold:

1. T1 F1 absolute improvement at least **0.03** over C3 on V3, with T1 precision no more than **0.03 lower**.
2. Independently reviewed unsupported statements no more than **0.02** higher in absolute rate than C3 on V3; zero new unqualified safety or authenticity claims.
3. T2 service F1 does not regress by more than **0.05** absolute; T3 authenticity counts and errors reported explicitly, even when too sparse for a rate.
4. Evidence verifier and quality audit show zero critical problems, unchanged saved-product decisions (182/182), safety/off-switch, and all automated regression checks pass.
5. Candidate first-read p95 on the specified performance test remains under 1 second on a comparable staging host and no more than 2x baseline without explicit measured justification. Local 2-CPU emulation is not sufficient to call the staging gate passed.

If multiple candidates pass, select the highest T1 F1 on V3 with precision as tie-breaker. If none pass, **stop** and report that no candidate was adopted.

## 6. Final evaluation (F2, one time)

Freeze chosen code/sha256, annotator instructions and data manifest before opening F2; compare frozen candidate vs C3 on **exactly identical F2 rows** once. Publish TP/FP/FN and P/R/F1 separately for T0 all kinds, T1 product, T2 service, T3 authenticity, and by category and language with denominators. Report 95% Wilson intervals for P/R, product-cluster bootstrap for uncertainty where feasible, unsupported statement and serious safety error rates. Do not treat undefined sparse metrics as zero or claim a new result on categories without adequate reference examples.

The **0.80 target** for precision, recall and F1 remains a target; unmet targets remain unmet. A better point estimate does not automatically authorize production. Preserve all outputs, whether positive or negative, in a reproducible, dated research report with raw label provenance.

## 7. Deployment gates remain separate

Even a successful F2 result does not waive independent human evaluation of the product card/words, real category coverage, staging benchmark, original-backend sync dry run, or the written recommendation-policy decision. The production default remains **off / no promotion** until `../RELEASE_GATES.md` is satisfied.

## Amendments

None.
