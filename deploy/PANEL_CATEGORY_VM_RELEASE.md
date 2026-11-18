# DeFaketive panel category pipeline — guarded VM readiness and rollback

**Status:** feature branch under evaluation, NOT an instruction to deploy immediately.
PR: https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan/pull/45
Feature: `feature/panel-category-sentiment-gated-20261118`.

## What is and is not in this change

The five-stage panel presentation is Product → original XLM-RoBERTa sentiment → product category-aware check → independent hazard checking → final report. Backend title identification may happen before sentiment inference so the existing hazard code can use it. This does **not** mean only Negative reviews are sent to hazard checking: every review is checked. Initial Neutral remains supported.

The pc6 category selector retains 49 categories plus Other, incorporating specific-title disambiguation and MPPT solar/game-controller separation. A small category-specific sentiment signal is opt-in, **shadow-only and unable to overwrite the live label**. No ONNX, tokenizer, learned hazard weights, threshold or stored database schema is changed.

## Current evidence

- CI for original PR #45 passed Python 3.11 and 3.12, full backend regression, frontend typecheck and build.
- First **paired** audit against the deployment-branch pc4 baseline passed on 178 electronics-heavy saved development products and 359 selected reviews: 0 categories changed, 0 sentiments changed, 0 hazard flag changes, 0 sampled verdict changes. This is developer data and NOT a meaningful cross-category accuracy estimate.
- Extended paired audit includes historical development reviews beyond gadgets. Check the latest `panel-category-pipeline.yml` run and its `panel-category-audit-summary` artifact for *the exact candidate SHA* before signoff.
- No claim of independent category accuracy, improved sentiment macro-F1, hazard F1 ≥0.80, VM health, or staging equivalence is currently made.
- The separate VM-conclusions immutable-engine scope job was written for **conclusions-only** code releases and failed for PR45 by design. It is now kept strict for `release/vm-conclusions-*` work, while this feature has its own dedicated five-hazard paired gate. Do not treat the old conclusions-only gate as a substitute for the category audit.

## Actual VM check — no deployment, no secrets shared

Only from an authenticated administrator session on the real VM. Do not execute on the production checkout with `git reset`, `git checkout`, `git pull`, or `git merge` before passing all gates.

1. Establish the **actual live SHA** using `git -C "$HOME/defaketive" rev-parse HEAD`, verify service health and backups and compare it with the deployment branch. If the live SHA differs from PR45's `fc56fa9` base, **reconcile the two histories in a separate release checkout**; do not assume the branch already represents the live installation.
2. Fetch the reviewed candidate commit with the existing operator-configured GitHub credentials and create a separate detached **staging worktree** outside the live directory. Ensure the worktree's HEAD matches the reviewed CI-green SHA.
3. Run the built-in **read-only paired audit** from the staging checkout. Use exact 40-hex SHAs and paths:

```bash
export DEFAKETIVE_REPO="$HOME/defaketive"
export DEFAKETIVE_CANDIDATE="$HOME/defaketive-category-stage"
export EXPECTED_VM_SHA="PUT_VERIFIED_LIVE_40_HEX_SHA_HERE"
export CANDIDATE_SHA="PUT_CI_GREEN_CANDIDATE_40_HEX_SHA_HERE"
export DEFAKETIVE_AUDIT_REVIEWS=900
bash "$DEFAKETIVE_CANDIDATE/deploy/panel-category-vm-preflight.sh" --paired
```

The script verifies both SHAs, service HTTP, clean tracked trees and ONNX asset hash; it checks disk/memory, then processes the **same** live SQLite review rows on the two checkouts in separate Python processes using SQLite read-only mode. Temporary outputs contain hashes and aggregates only and are removed automatically; no raw customer review text is printed or uploaded.

4. Review any changed product category, hazard or sampled verdict with authorized analysts. The **strict** audit aborts on any changed sentiment, hazard flag, or sampled verdict. That is intentionally conservative; if triggered, make a documented, human-reviewed case-by-case decision, add regressions, rerun against the exact candidate, then seek permission to promote. Do not weaken the rule to silence the failure.
5. Test important real listings (MPPT solar controller, Xbox/PS5 controllers, cosmetics, toy cars, whey supplement, apparel, phone accessory, charger) including customer reports of heat, charging failure, fake items and delivery-only comments. Inspect both review-linked flags and final report in an **isolated staging app**, not merely a unit-test console.
6. Obtain human-adjudicated product-disjoint samples for category and sentiment accuracy claims. Category-aware sentiment predictions remain shadow-only until they outperform the stronger generic adapter on independent evaluation with no safety regressions.
7. Confirm snapshot integrity and rollback rehearsal **before** changing production. For SQLite use the application team's existing `deploy/vm-guarded-update.sh` online-backup procedure as a reference (it is for a different release and must NOT be reused unchanged for a category release). Back up both `backend/defaketive.db` and `backend/instance/accounts.db` with `sqlite3.Connection.backup`, verify `PRAGMA integrity_check`, store exact old code SHA, never overwrite the live database with starter data.
8. Only after approval, create a release commit based on the **verified live SHA** and use a separate authorized deployment procedure with a service-restart/HTTP/saved-report smoke test and one-command code rollback. Keep `DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW` **unset** in production.

## Release gates (all required)

- [ ] Dedicated PR branch CI all green on **exact head SHA**.
- [ ] Paired development-corpus scan has no unreviewed hazardous changes across non-gadget examples.
- [ ] Live VM current SHA, model SHA, disk/memory and dependencies verified by operator.
- [ ] VM SQLite read-only paired audit passed or all differences adjudicated with added tests.
- [ ] Isolated staging E2E + saved-report/versioning + safety smoke tests passed.
- [ ] Both SQLite DBs backed up with verified integrity and rollback tested.
- [ ] Explicit release review/signoff; category shadow still OFF.
- [ ] Production rollout monitored and verified with real HTTP and saved reports.

**Failure of any gate: NO-GO, leave the VM as-is.** A green GitHub build or an exact development-corpus prediction match is not proof that the live VM is ready. A PR merge does not change the Azure VM.
