# Final recommendation

## Decision: **INSUFFICIENT EVIDENCE. Do not adopt any candidate now; keep the shipped model.**

## Why

1. **No verified marketplace labels exist**, so no claim of real-world improvement can be made. Every marketplace gain is agreement with team-supplied labels of unverified provenance. The frozen 400-review final test and the 400-review dev pool are prepared (`annotation/`) but unlabelled; no human annotation was produced or simulated.
2. **The evidence that exists is contradictory.** On the 846-row historical benchmark every marketplace-trained candidate beats the shipped model by 0.10 to 0.11 macro F1 (paired interval about +0.05 to +0.16), with neutral F1 0.19 to about 0.43 and negative recall 0.67 to about 0.78. On the older 150 team-labelled rows the same candidates are 0.09 to 0.11 **worse** (interval excludes zero). The label files disagree about neutral; the winner depends on which unverified labels one trusts.
3. **The primary target is not reached and cannot be verified.** Best marketplace macro F1 on data the model was not fitted to: 0.684 (benchmark), neutral F1 0.43. The 0.80 macro and per-class targets are **NOT ACHIEVED**; the final-test cells are **NOT YET VERIFIED**.
4. **The secondary target is partly met.** Against the shipped int8 (FiReCS 0.833) `c2` is +0.007 and `c1` +0.004 (within noise), `d1` -0.010. The original 0.846 cannot be reproduced as an artifact (its FP32 checkpoint is missing); a re-fine-tune of the same recipe reproduces 0.844.
5. **The adoption would change customer-facing conclusions**: 12 to 24 of 60 products move from "recommended" to "mixed" with the best candidates, with no way to say whether that is more accurate.
6. **Seed noise is about 0.02**; the best configuration was chosen from few runs.

## What is worth keeping

* The marketplace-fine-tuned family (`c2`, `d1`, `c1`) is the most promising direction: it fixes neutral and negative recall on the larger benchmark without hurting FiReCS (except `d1`), and it is as cheap to run as the shipped model once pruned and quantised.
* Best model identified (by the pre-declared rule): **`d1_mix_ce_rep2_s1`**, checkpoint `D:/defaketive-train/xlmr/d1_mix_ce_rep2_s1/best` (not in the repository; hashes recorded in `results/inventory.json` only for the sources, not for this checkpoint: add them when it is archived). Runner-up preserving FiReCS: `c2_mix_weighted_s1`; compression artifacts of `c2` in `D:/defaketive-train/xlmr/c2_onnx` (pruned int8 per-channel, 114.7 MB).
* Expected VM impact if adopted as pruned int8: latency about the same (41 ms against 43 ms median per review), memory in the model process 262 MB against 187 MB, model file 115 MB against 95 MB, cold start 0.47 s against 0.37 s; fits the 3.8 GB machine. Not tested under concurrency.

## Exact next steps before any production deployment

1. ~~The owner approves the sentiment annotation policy~~ **Done (2026-11-15): policy v1 approved with clarifications and frozen** (`annotation_policy.md`, hash in `annotation/policy_v1.lock.json`).
2. Two independent annotators label `final_test_sheet_A/B.csv` and a third adjudicates (`annotation_execution_guide.md`); provenance and agreement are recorded. Also label the dev pool.
3. Scan home, fashion, beauty, food and automotive products so the test represents more than electronics; freeze that sample the same way.
4. Re-fine-tune (3 or more seeds) on FiReCS plus **verified** marketplace labels, selecting on a verified validation split; vary learning rate and epochs; consider continuing from a recovered FP32 checkpoint if the team still has it.
5. Score the frozen final test **once** with the chosen model and the deployed one; report macro F1 and per-class F1 with product-grouped intervals, and compare the 0.80 targets.
6. Only then: re-evaluate the conclusion thresholds against independently labelled product conclusions; export the pruned int8 artifact; repeat the VM benchmark with concurrency; deploy behind a shadow switch first.

Nothing was deployed, pushed or merged; the production release candidate (`2c6e056`) was not touched.
