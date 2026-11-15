# Product-specific conclusions: release gates and owner handoff

**Updated:** 2026-11-15. **Scope:** `feature/product-specific-conclusions`, not the deployed site.

## Current decision

**STAGING CANDIDATE ONLY — PRODUCTION BLOCKED.** Phase 3 C3 is the frozen research baseline, not proof of product-level completeness. Fresh non-electronics F (104 reviews) measured product-feature precision **0.852**, recall **0.371**, F1 **0.517**. These are *single Claude-assisted reference* scores, not independently human verified. Do not claim the goal of >=0.80 precision, recall and F1 was met. No staging environment or production deployment has been demonstrated.

## Gates, in order

| Gate | Required evidence | Current status |
| --- | --- | --- |
| 1. Research integrity | Historical locked pack, D1/D2/F and frozen C3 hashes unchanged; annotation provenance preserved. Any new candidate on separate Phase 4 data. | **Preserve** |
| 2. Automated regression | Both Python 3.11 and 3.12 tests, Svelte check/build, evidence audit, saved verdict/decision equality, known browser baseline and off-switch checks on the **same commit**. | PRs #4–#6 were checked individually; run and record combined-tip checks |
| 2b. Reproducible dependencies | Keep `package-lock.json` aligned and require `npm ci` + Svelte/build + extension tests on the reviewed commit; record Python dependency lock used for staging. | Frontend lock repaired and `npm ci` proved on PR #10 repair job; **combined-commit CI and staged Python lock proof remain pending** |
| 3. Independent judgement | Two independent human annotation sets or a prior dated written protocol amendment; card/claims/features/words scored, with safety and unsupported claims, intervals and disagreement analysis. | **BLOCKED** — one Claude-assisted set only |
| 4. Category validity | Fresh real reviews and human-reviewed claims for every enabled category, including footwear and motorcycle parts if enabled. Language split reported. | **BLOCKED** — some groups lack real data |
| 5. Isolated staging | Machine matched to intended 2-vCPU production size, reproducible benchmark on its actual resources, older saved reports, secrets/privacy audit, off/on rollback. | **BLOCKED** — no staging host verified |
| 6. Sync dry run | `scripts/sync_backend.py --dry-run` against the actual original app; each conflict reviewed, no forced overwrite. | **BLOCKED** |
| 7. Recommendation policy | Written decision record retaining current policy or independently validating a versioned alternative. | **BLOCKED** — default retain live policy |
| 8. Release approval | Named accountable person signs off after all above; explicit production deployment decision in separate PR. | **NOT REQUESTED** |

Do not reclassify a *passing code test* as a scientific validation. A failed scientific target does not justify editing annotations, reducing the held-out set or silently changing the adoption rule. Do not promote production merely because the feature branch has been pushed.

## Execution sequence

1. Run combined-commit CI and preserve its SHA, job outcomes and any failures.
2. Keep existing judgments and Phase 3 results immutable. Use `phase4/protocol.md` to create **new** development/validation/final data before writing additional extraction rules.
3. Make two independently completed human evaluation sets (without private keys or each other's outputs), label provenance and disagreement. No synthetic or guessed ratings.
4. Provision an isolated staging machine with sanitized test data and run `staging_procedure.md`. Save the real performance artifacts and verify the off-switch and real sync dry run.
5. Resolve category evidence and recommendation-policy choices. If any gate remains open, retain staging-only status; if necessary keep explanations disabled for unvalidated categories.

## Provenance and change control

- Phase 3 protocol, frozen extractor hashes, labels and F results are in `phase3/`; all earlier evaluation references are historical, not reusable training data.
- The documented analysis identifies low **recall**, especially indirect statements, service experiences, and some Filipino text, as the main feature risk.
- Experimental research code should use separate feature/research branches, small independently reviewable PRs, no force pushes or direct production merges.
- Because GitHub Issues are disabled for this repository (HTTP 410 on 2026-11-15), this file is the canonical release-blocker register until a tracking system is enabled.
