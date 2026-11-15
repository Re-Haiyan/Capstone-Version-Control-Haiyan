# Product-specific conclusions

The panel asked that every analysed product carry a conclusion that says whether customers recommend it **and why**, from the actual reviews,
without inventing anything. This folder is the technical record of the feature that does that.

Written for: the capstone team and the review panel. Status: **built and tested; ready for staging, not for production; one local commit (ec0b53c), nothing
pushed, merged or deployed.** Start with `final_report.md`; the production checklist is `deployment_readiness.md`.

## What it does, in one paragraph

The decision (`recommended`, `mixed`, `caution`, `not_recommended`, `not_enough`) and the hazard verdict are made exactly as before. What changed
is what the card says. A small, auditable extractor reads each review one clause at a time and records which feature (softness, battery life, fit,
freshness, ease of use …) a reviewer praised or criticised, with the review's id, their exact words and where those words sit. A writer then
builds the headline and paragraph only from features that **distinct reviews** support, in wording that follows how many reviews that is; safety and
authenticity reports from the existing hazard checker are shown in their own always-visible block, worded as unverified customer reports; and an
expandable "Why this conclusion?" shows every count with the original quotations. No new model, no paid API, no database change.

## Results at a glance (and how much to trust each)

| Result | Value | Trust |
|---|---|---|
| Saved products whose verdict and decision are unchanged | 182 of 182 | verified mechanically |
| Quotations checked against their reviews (182 saved + 37 real non-electronics) | 6,639 of 6,639 verbatim, right position, 0 problems in 3,948 lines, 18,210 ids | verified mechanically |
| Backend tests | 429 pass, 0 fail, on Python 3.11 **and** on Python 3.12 with the VM's library versions | verified |
| Browser test, 3 widths, 7 cases (3 real non-electronics), accessibility | passes | verified |
| First read of a product page | 72 ms median, 256 ms p95 (this PC); 72 / 249 ms in the VM's Python 3.12 limited to 2 CPUs; cached 1 ms; cold start 0.4 s | measured here and emulated; **no staging or VM measurement** |
| "Mostly negative" said without a negative majority | 3 → 0 of 182 | verified |
| Aspect claims judged correct, real non-electronics, first look | 80% (56 of 70) | **developer-judged, one person** |
| … after fixes, new draw | 89% (62 of 70) | developer-judged, optimistic (same judge, informed) |
| **Phase 3: extractor asp3 on fresh data (F, 104 reviews, non-electronics)** | product features precision 0.852, recall 0.371, **F1 0.517** (baseline asp2 on the same reviews 0.800 / 0.258 / 0.390); all kinds 0.850 / 0.315 / 0.459; **target 0.80 not met (recall)** | **Claude-assisted reference, one set, not independent**; `phase3/results.md` |
| AI-assisted evaluation (Claude-assisted, one set, not independent) | features P 0.72 / R 0.29 / **F1 0.41 (target 0.80 not met)**; claims 63 of 80 correct (78.8%, 68.6 to 86.3%) | **AI-assisted, not human**; card and words sheets pending |
| Independent human evaluation | none | **PENDING HUMAN EVALUATION** (pack of 35 real products, 80 claims and 150 reviews for recall/F1 is built; AI-assisted labelling is approved and, when done, is reported as an AI-assisted reference with provenance, not as human annotation) |
| Footwear, motorcycle parts | no real reviews exist in the project | **unvalidated** |

## Files here

| File | What it is |
|---|---|
| `final_report.md` | Overall findings, what is verified versus judged versus pending, mistakes found and fixed, recommendations |
| `deployment_readiness.md` | The production checklist, verdict, rollback |
| `architecture.md` | How it works, module by module; how to extend it |
| `aspect_validation.md` | Real versus constructed testing per category; error classes found on real reviews; data still needed |
| `recommendation_policy_comparison.md` | Live versus candidate decision policy on the same products (generated) |
| `evidence_verification.md` | Every claim checked against its review (generated) |
| `human_evaluation.md` | The final independent-evaluation pack (`human_eval_pack/`: 35 real products, 80 claims, blind sheets), what the scorer computes; **PENDING HUMAN EVALUATION** |
| `research_integrity.md` | The three evaluations kept apart (sentiment F1, hazard F1, conclusion quality), what software tests do and do not prove, a register of every reported result, and a paper-ready methods description with no findings |
| `quality_audit.md` | Automatic audit of the generated text on all three real pools (contradictions, count words, hazards, invented benefits …), and what the manual reading found beyond it |
| `sync_verification.md` | The backend sync checks: a real dry run against a stand-in original, isolated tests, what could not be done |
| `dataset_specification.md` | What real data footwear, motorcycle parts and the unseen categories still need, and the rules for using it |
| `performance_benchmark.md` | Latency, memory, scaling, concurrency, VM read-only measurement |
| `regression_results.md` | All tests, per file (generated) |
| `real_examples.md`, `examples.md` | Before and after: real non-electronics products with traceable reviews; constructed review sets (labelled synthetic) |
| `precision_check.md` | The earlier developer precision rounds on electronics (historical: the extractor has changed since) |
| `before_after.csv`, `before_after_summary.json` | Old and new text of every saved product |
| `phase3/` | The feature-extraction improvement study: protocol written in advance, new development and fresh final data, candidates, results, freeze record |
| `ai_annotation/` | Annotation records and tooling (provenance, single-set scoring, product-level batches for the card and words sheets) |
| `staging_procedure.md` | The reproducible staging procedure (not yet performed) |
| `rating/`, `aspect_validation_sample.csv` | Blind annotation sheets (empty) |
| `*.py` | `before_after`, `examples`, `real_examples`, `aspect_validation`, `analyse_real_nongadget`, `evidence_verification`, `recommendation_policy_compare`, `text_rating`, `benchmark`, `make_ui_fixture`, `run_regression` |

## Code

`backend/aspect_profiles.py` (data), `backend/aspects.py` (extractor), `backend/conclusion_text.py` (writer),
`backend/recommendation_policy.py` (live rules re-stated; experimental candidate, **not wired in**), `backend/dashboard_utils.py` and
`backend/webapp.py` (integration), `src/lib/components/report/verdict-block.svelte` and `src/lib/types.ts` (the card),
`scripts/sync_backend.py` (now safe), tests `tests/test_product_conclusion.py`, `test_sync_backend.py`, `test_recommendation_policy.py`,
`test_text_rating.py`, `tests/e2e/product-conclusion.mjs`.

## Reproduce

```
python -m unittest discover -s tests -p "test_*.py"                       # or: python research/product_specific_conclusions/run_regression.py
python research/product_specific_conclusions/evidence_verification.py
python research/product_specific_conclusions/before_after.py
python research/product_specific_conclusions/recommendation_policy_compare.py
python research/product_specific_conclusions/benchmark.py --tag local     # --cpus 2 to emulate a small server
npm run build; python serve.py --port 8099; BASE=http://localhost:8099 node tests/e2e/product-conclusion.mjs
# real non-electronics (needs the project's backups/pool-scans; about 8 minutes, inference only):
python research/product_specific_conclusions/analyse_real_nongadget.py && python research/product_specific_conclusions/real_examples.py
```

## Switching it off

`DEFAKETIVE_CONCLUSION_REASONS=0` (read at start) returns every product page to the plain conclusion. Decisions and verdicts are the same either way.
