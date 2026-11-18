# PR #49 / pc7 VM read-only release gate

Current production baseline at PR creation: `dc196d5f8435f6b33bfac65ec7ba7d1c82b8cc26`.
Do **not** assume this remains current: verify the VM's actual SHA and both DB paths.

## What can safely be checked

Run from an authenticated Azure VM session, using an **isolated candidate
checkout** at the PR's latest reviewed SHA. Use existing VM paths and service
names; never modify or swap the live checkout for a test.

```bash
export EXPECTED_VM_SHA="$(git -C "$HOME/defaketive" rev-parse HEAD)"
export CANDIDATE_SHA="$(git -C "$HOME/defaketive-pc7-stage" rev-parse HEAD)"
export DEFAKETIVE_CANDIDATE="$HOME/defaketive-pc7-stage"
# Override DEFAKETIVE_REPO / DEFAKETIVE_DB / DEFAKETIVE_SERVICE if live paths differ.
bash "$DEFAKETIVE_CANDIDATE/deploy/pc7-vm-preflight.sh" --check
bash "$DEFAKETIVE_CANDIDATE/deploy/pc7-vm-preflight.sh" --paired
```

The script uses SQLite in read-only mode for **saved-report compatibility** and
**paired original-vs-candidate review scoring**. It compares actual saved
product categories, current/stale counts, every sentiment prediction, all five
hazard flags, sampled verdicts and model binary hashes. It also records a
non-identifying aggregate of category-context v2 statuses from real reviews.

**NO-GO:** unexpected stale reports, any previously current category-changing
report still marked current, any unexplained sentiment/flag/verdict difference,
unmatched model/threshold artifacts, 0 eligible real reviews, failed tests,
missing backups, high latency/memory usage, or unauthorized production edits.

If category changes legitimately affect a newly analyzed hazard flag, the
strict paired audit intentionally stops. Review the exact cases independently
before any release decision; do not silence the gate.

## Separate release safeguards

1. Freeze and review exact candidate SHA and all green GitHub checks.
2. Back up **both** SQLite databases through the online backup API; verify
   `PRAGMA integrity_check`, plus a scratch restore/rollback.
3. Recheck saved reports: current pc6/pc4 reports with unchanged categories
   remain current; air-conditioner reports formerly marked haircare must become
   historical until explicit recheck; do not bulk re-analyze.
4. Confirm production `DEFAKETIVE_CATEGORY_SENTIMENT_SHADOW` remains unset,
   and no other sentiment override/calibrator has been activated.
5. Only deploy after VM checks, manual review of any category flips, and
   explicit operator release approval. PR #48 shopper wording stays separate.

**Evidence limitation:** the local historical marketplace corpus is a
repeatedly inspected development dataset with unverified label provenance.
The paired audit measures behavior and contradictions, **not** independent
sentiment F1, accuracy, or the 0.80 target. A valid production sentiment
override requires a new product-disjoint human-adjudicated evaluation.
