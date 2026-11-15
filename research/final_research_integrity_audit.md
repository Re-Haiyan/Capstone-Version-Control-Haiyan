# Final research integrity audit

Purpose: every result in this project is classified by the kind of evidence behind it, wording that overclaimed was corrected, and the claims that cannot be made are listed. Nothing was deployed or pushed in this round.

## 1. The five evidence classes

| Class | What it is in this project | May be called |
|---|---|---|
| **A. Verified human annotation** | Labels with annotator IDs, policy version, time and checksum (`agreement/provenance_log.csv`) | "independent human annotations", only with a complete log |
| **B. Unverified-provenance labels** | The team-supplied files: returned 7 to 22 minutes after creation for 270 to 3,863 reviews each, no annotator records (`annotation_provenance.md`) | "team-supplied labels (provenance unverified)"; never "gold" or "human-annotated" |
| **C. Training / development data** | 3,946 high-confidence rows of B used to build and tune rules and models (the rules were written after reading their errors) | "development" or "training"; scores on it are optimistic |
| **D. Historical benchmark** | The 846-row `test_v3` of B, 82 products, inspected and reused adaptively during development | "historical benchmark"; not "test" without that word, never "untouched" |
| **E. Fresh independent test** | Unseen, product-disjoint, human-labelled (class A) data scored once | the only class that supports a generalisation claim |

**Today class A and class E are empty.** Class A exists only as tooling: `research/agreement.py` (sheets, check, score, compare, provenance log), tested but never run on human data. Every F1, precision, recall, flip rate and gain in the repository is class B/C/D.

## 2. Classification of the main results

| Result | Source | Class | Claim that is allowed |
|---|---|---|---|
| Defect/quality/safety/counterfeit/not-as-advertised F1 of the deployed rules | `evaluation_report.md`, `final_implementation_summary.md` | C and D | "agreement with team-supplied labels"; the D intervals are product-bootstrap resampling intervals of an inspected set |
| Rule update `831f22f` and the RC changes: F1 gains | `release_validation.md` | C (rules tuned here), D (confirmation of direction only) | "improves agreement with the supplied labels on training rows; direction repeated on the historical benchmark" |
| Evidence-state precision (keyword 0.79; model-only 5 of 70 train, 0 of 18 test) | `evidence_completeness.md` (split table) | C and D, kept apart | "model-only flags rarely agree with the supplied labels" |
| Evidence policy `require`: F1 0.738 to 0.791 train, 0.680 to 0.773 historical | `evidence_policy_decision.md` | C and D | Not a claim of real-world gain; policy not enabled |
| Sentiment calibrator and its effect on 15 of 60 cards | `sentiment_calibration_review.md` | B labels, local gadget products | A report of change, not of correctness |
| Clause-resolution switch cost | `clause_context.md` | C and D | measured cost on the supplied labels |
| Latency, throughput, memory, cold start | `release_validation.md`, `deployment_benchmark.md` | measured on the production VM, no labels | an engineering measurement; two runs each |
| Behaviour diff, API compatibility, quotation checks | `release_validation.md` | no labels (code behaviour) | deterministic comparisons on the stated inputs |
| Product-conclusion policies P0 to P3 | `conclusion_policy_review.md` | scenario tests and 60 local products; no human-judged conclusions | "behaviour under constructed scenarios"; no accuracy claim |
| Inter-annotator agreement | none | none | **No figure exists. None may be stated.** |

## 3. Corrections made in this round

| Where | Overclaim or stale number | Correction |
|---|---|---|
| `evidence_completeness.md`, `finalization_round_summary.md`, `experiment_log.md`, `remaining_limitations.md`, `README.md` | "17% right", policy F1 0.733 to 0.767, "interval +0.044 to +0.162", "recommended for approval" | Final-code split figures (5 of 70 train, 0 of 18 test; 0.738 to 0.791; 0.680 to 0.773; +0.046 to +0.162), labelled historical benchmark, and the recommendation changed to "do not enable, shadow first" |
| `evidence_completeness.md` table 4 | The earlier precision table pooled training and test rows | Replaced by the split table; the pooling is stated in the text |
| Release candidate model version | The RC had the same `model_version` as production although its behaviour had moved | Bumped to `pc4`; test added |
| `annotation_policy_proposal.md` | Presented as the proposal | Marked superseded by `annotation_policy_v2.md` and `policy_owner_decisions.md` |
| Battery-drain exemption | Removed true power-bank defects (VM verdict change) | Guard added; documented |

## 4. Wording rules adopted for all future text

1. Say "team-supplied labels (provenance unverified)". "Gold", "ground truth" and "human-annotated" are reserved for class A.
2. Say "historical benchmark" for the 846 rows. "Test set" alone, "held-out" and "untouched" are not used.
3. A bootstrap interval on class D is "resampling interval of an inspected set". It is **not** evidence of significance on new data, and no "statistically significant" claim is made anywhere in this project.
4. A gain on training rows after rules written from their errors is "improved agreement with the labels", not "improved accuracy".
5. A product-level change (verdict, card) is "a change", not an improvement, until humans judge the conclusions (`product_conclusion_evaluation_protocol.md`).
6. No agreement score may be quoted from fewer than two completed independent sheets (`agreement.py` refuses below 30 shared rows).

## 5. Adaptive reuse of the historical benchmark

The 846 rows were read in earlier rounds, the first rule round used their scores, and this round used them to confirm direction (evidence policy, release diff). Each additional use makes them less informative, and none of the confidence intervals accounts for that selection. The training result is the basis of every decision recorded in this audit; the historical benchmark confirms or contradicts direction only. A decision would change if the benchmark contradicted the training result (it did not), but a fresh test is the only way to know the size.

## 6. What cannot be claimed

* That any label set is human-verified, or that the labels' accuracy is known.
* Any inter-annotator agreement, kappa, ceiling on achievable F1, or "human-level" comparison.
* Any generalisation of F1 gains to new reviews, to Shopee (no labelled Shopee rows exist; Shopee is checked structurally only, 8 products on the VM), or to categories with few labelled defects.
* That the product conclusion card is accurate: no human-judged conclusions exist.
* That the evidence policy improves anything in production.

## 7. What would make claims supportable

1. Two independent annotators label the 300-review sheets (`annotation_execution_guide.md`), with the log, then agreement is computed and disagreements adjudicated.
2. A fresh, product-disjoint, human-labelled sample is scored once with the frozen release code (no tuning afterwards): that is class E.
3. Human-judged product conclusions (`product_conclusion_evaluation_protocol.md`) before any conclusion policy is activated.
4. The owner's decisions in `policy_owner_decisions.md` (freebies D, thin reviews G) written down before labelling, so the policy version is fixed.
