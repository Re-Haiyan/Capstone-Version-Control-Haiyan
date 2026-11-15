# Recommendation-policy decision record — retain the deployed policy

**Recorded:** 2026-11-15  
**Scope:** pre-VM repository preparation for `feature/product-specific-conclusions`  
**Decision:** **RETAIN EXISTING**; do not wire in `candidate_decision` and do not change saved or live product verdicts.

## Why this is the default for the next deployment

The existing production decision policy lives in `backend/dashboard_utils.py`, and `backend/recommendation_policy.py::current_decision` reproduces it for research and testing. The alternative `candidate_decision` has **not** been approved for users.

The historical comparison in `recommendation_policy_comparison.md` found a difference on **1 of 182** saved products. That comparison demonstrates a *potential decision change*, not a correctness improvement. It does not establish that a weaker or stronger decision is better for the customer, and it does not independently adjudicate safety concerns. The candidate thresholds are unvalidated, and its neutral-majority `not_enough` semantics conflict with the existing "too few reviews" text.

The source-linked safety audit has further outstanding context checks. Because unsupported safety claims and misleading severity labels could change decisions in either direction, no policy promotion is warranted by the current evidence.

## Implementation boundary

1. Continue using the existing deployed recommendation and verdict path. **No runtime code change is authorized by this record.**
2. Keep `candidate_decision` in the research module only. Do not import it into `dashboard_utils.py`, `webapp.py`, `server.py`, or `serve.py`.
3. Product-specific *explanations* are a separate experimental feature; while they remain unvalidated they must be **disabled for public users** by `DEFAKETIVE_CONCLUSION_REASONS=0`. Test the off-switch on an isolated staging instance before any production promotion.
4. Never remove or weaken existing hazard overrides, sentiment results, report storage, customer account controls or daily limits as part of this policy decision.
5. Reconsider the policy only in a **separate versioned proposal** supported by properly collected blind/reference evidence, changed-decision case studies, safety review, and explicitly documented customer-facing wording. Compare it against the live policy on exactly the same legitimately new data.

## Evidence already available

- `recommendation_policy_comparison.md`: saved-product comparison, scenarios, and candidate concerns
- `tests/test_recommendation_policy.py`: current decision parity and hazard tests
- `phase3/results.md`: historical product-feature recall remains **0.371**, T1 F1 **0.517** against *one AI-assisted reference*, not verified accuracy
- `ai_annotation/SAFETY_SOURCE_AUDIT.md`: non-adjudicated source-linked safety triage
- `RELEASE_GATES.md`: staging, data, privacy, and release approval remain separate gates

## Accountability and release status

This is the conservative engineering choice **to preserve behavior**, not a statement that the product is independently validated. The user requested completing pre-VM prerequisites; that request is **not an explicit approval to deploy to production**. Named release approval is still absent and production is **BLOCKED**.

This record resolves which recommendation policy to *keep* while we test; it does not resolve the absent independent validation, real category coverage, VM benchmark, sync dry run, secrets audit, rollback rehearsal or release sign-off.
