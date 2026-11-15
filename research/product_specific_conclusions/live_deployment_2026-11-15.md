# Live VM deployment record: 15 November 2026 (UTC)

**Outcome: the release code is deployed; the product-specific explanations are OFF on the live site.** They were switched on, checked against real production data, found to cite reviews that do not support their claims, and switched off again as the rollout rule requires. No verdict, decision, hazard flag or database record changed at any point.

| | |
|---|---|
| Site | https://defaketive.duckdns.org |
| VM commit before | `2c6e056befe0ad7a24652bd12d4d28f7af236a8f` (as documented; working tree clean) |
| VM commit now | `d8cedf1a90e7414f7814830800b8c453ff194a56` (`deployment` on Re-Haiyan/Capstone-Version-Control-Haiyan; fast-forward) |
| Explanations | **DISABLED**: `/etc/systemd/system/defaketive.service.d/00-conclusions-off.conf` sets `DEFAKETIVE_CONCLUSION_REASONS=0`; confirmed in the running process's environment |
| Backups (SQLite online backup, integrity-checked, with SHA-256) | `/home/azureuser/defaketive-release-backup-20261115T155339Z/` (`defaketive.db`, `accounts.db`, `old.sha`, `sha256.txt`) |
| Deployment log on the VM | `/home/azureuser/deploy-d8cedf1.log` |
| Database | 397 products, 71,889 reviews before and after; no migration, no re-check, latest product update still 14 November |
| Service | active; 0 errors or tracebacks in the journal since the deployment; restarted three times (the deployment, switching on, switching off) and came back each time |

## What was done, in order
1. **Inspection (read-only).** VM at the documented commit, clean tree, service active, 15 GB disk and 2.1 GB memory free, no existing override.
2. **Release review.** `d8cedf1` is the tip of `deployment`, descends from the VM's commit, and changes only the conclusion feature and the guarded script; nothing under `backend/sentiment-analysis`, no model, threshold or category file.
3. **A fetch problem caught before it mattered.** The VM's `origin` is the older RovicRetuya repository, whose `deployment` is `5b7d2b8`, not the approved release. The guarded script fetches `origin`. It was run with a one-invocation URL rewrite (`GIT_CONFIG_*` `insteadOf`) so it fetched the approved repository; the VM's git configuration was not changed. The fetched SHA was verified equal to the approved one before and after.
4. **Guarded update** (`deploy/vm-guarded-update.sh` taken from the approved commit, SHA-256 verified on the VM): pre-checks, backups, off-switch installed, fast-forward, rebuild, restart, local and public checks. All passed.
5. **Checks with explanations off.** 120 randomly chosen saved products through the live route `/api/saved/detail`, compared with a capture taken before the deployment: verdict state, decision, headline, assessment, hazard badges, reviews analysed: **0 differences**. 36 browser page views of 12 diverse reports at 1280, 390 and 360 px on the public site: no console error, no failed API call, no horizontal overflow.
6. **Explanations switched on**, confirmed in the process environment.
7. **Finding 1: the explanations did not appear.** 0 of 120 saved reports carried one. Cause: the report page reads `/api/saved/detail` (`server.py`), which never asked for the explanation; only the older session route did. A real integration defect that unit tests (which call the function directly) and the browser test (recorded payloads) had not exercised.
8. **Deployed code checked on all production data** (on the VM, read-only, low priority): explanations on versus off for all 397 products: **0 changed verdicts or decisions**, 395 explained, 6,829 lines, **11,523 quotations all verbatim in their source review**, 0 errors; first read median 51 ms, p95 290 ms, one product 5.2 s.
9. **Finding 2: quotations that do not support their claim.** Reading 71 quoted claims of 12 diverse products against the source reviews, about 18 (a quarter) were wrong or unsupported. Examples: "How well it works: supporting" citing *"diko pa siya nagagamit"* (not used yet) and *"ayaw nmn gumana"* (it will not work); "Charging: 15 reviews supporting" citing a complaint that the charger is slow; "Build quality: supporting" from *"Quality: mura pero d quality"*; "Durability: supporting" from a wish (*"sna tumagal"*) and from marketplace tags; "not very satisfied" read as praise; "the store is legit" filed as product authenticity; a processor called "this appliance". One reader's judgement, not an independent evaluation.
10. **Explanations switched off** and confirmed; the same 120 products re-checked: identical to the baseline.

## What a visitor sees now
The same verdicts, decisions and hazard badges as before. The plain conclusion's wording did change with the release even with explanations off (for example "According to the reviews, think twice before buying this product." is now "Think twice before buying this product.", and the summary states the shares of positive, neutral and negative reviews); 100 of 120 sampled products show the new wording. No "Why this conclusion?" section is shown.

## Not verified
- Administrator sign-in: no administrator credentials were available; the script confirmed the default password is not active, and the admin data route is not exposed to guests.
- Signing up or signing in as a user: not done, because it would write to the production accounts database.

## Before the explanations can be switched on
1. Wire `/api/saved/detail` (done on the feature branch with a test, `tests/test_saved_detail_reasons.py`; **not deployed**; needs review and a release).
2. Fix the extraction defects above. Each is pinned as an expected-failure test in `tests/test_phase3_rules.py`. They are extractor changes, so they need a new candidate evaluated on new data (`phase3/protocol.md`), not a patch on the server.
3. Repeat this live check (`tests/e2e/live-check.mjs`, `live/vm_verify.py`) with explanations off, then on.

## Research integrity
The extractor's measured result is unchanged and is not a production accuracy claim: product-feature F1 0.517 (precision 0.852, recall 0.371) on a Claude-assisted reference, not independent human validation; the 0.80 target is not met. The live reading above is consistent with that and adds a warning the reference did not show clearly: review counts shown to the public can include reviews that say the opposite.

## Rollback
- Explanations: already off. To stay off, leave the override file as it is.
- Code: `cd ~/defaketive && git merge --ff-only` is not a rollback; to return to the previous release, check out `2c6e056befe0ad7a24652bd12d4d28f7af236a8f` (recorded in `old.sha`), run `bash deploy/setup-server.sh`, and confirm the site. No database restore is needed for that, because nothing was migrated; the backups are there if one is ever wanted.
