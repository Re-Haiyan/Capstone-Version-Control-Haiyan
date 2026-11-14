# Release validation

Everything here is of the release-candidate **code at `27598e4`** (documentation commits after it change no code; see `release_manifest.md`). Nothing was deployed. Every run used defaults (all `DEFAKETIVE_*` variables cleared) unless a row says otherwise. The production code is `d74589a`.

> **Label provenance caveat.** Every F1 below is agreement with *team-supplied labels of unverified provenance* (`annotation_provenance.md`). The training rows (3,946) are development data; the 846 "test" rows are a **historical benchmark** that was inspected during development, not an untouched test. No human-verified labels and no fresh independent test exist. A gain on them is a measured change in agreement with those labels, not proof of real-world accuracy.

## 1. Test suite

`backend/.venv/Scripts/python.exe -m unittest discover -s tests`: all tests pass (270 at `27598e4`, plus `tests/test_agreement_check.py`; the final count is in the closing report of the round). `tests/test_release_version.py` fixes the model-version stamp (`pc4`).

## 2. What changes for users (behaviour of the RC against production, same inputs)

`research/release_diff.py` over all 4,792 labelled reviews (`results/release_behaviour_diff.json`):

* **Sentiment labels changed: 0.** No key of the analysis was removed; one key was added (`review_evidence`).
* 362 of 4,792 reviews (7.6%) have a different set of flags. Gained: not-as-advertised 160, defect 46, quality 4. Lost: defect 109, quality 29, safety 29, not-as-advertised 9.
* Agreement with the supplied labels, training rows then historical test, production to RC: defect F1 0.642 to 0.740 and 0.613 to 0.693; not-as-advertised 0.599 to 0.772 (train); safety 0.553 to 0.638 (train, unchanged on the historical test 0.533); counterfeit unchanged. These are not independent confirmation; the rules were tuned on the training rows.
* **Safety recall unchanged** on both sets (0.769 train, 0.750 historical), but 29 safety flags (across all 4,792 reviews) are no longer raised, and safety precision rises on training rows (0.43 to 0.55). The owner should know that fewer safety flags are raised than in production; the changed examples are in `research/results/release_behaviour_diff.json` (`changed_examples`). None of the 29 carries a safety label in the supplied labels (0 of 29), consistent with unchanged labelled recall; the labels' own provenance is unverified, and I did not read all 29 texts.

## 3. Flask API compatibility

`research/api_compat.py` runs the real `/api` card, view and summary builders from both versions on the same saved products and compares the key paths.

| Where | Products | Result |
|---|---|---|
| Local DB (10 Lazada) | 10 | no key removed, new keys only |
| **Production VM DB, same hardware** (8 Lazada, 8 Shopee, `d74589a` tree vs RC tree, read-only) | 16 | the same top-level and card key sets; added `evidence[].terms[].source` / `.rule` (new optional detail on term objects); `.terms[].excluded` is not present in the RC sample: it exists only when a term was excluded for that review, so it is data-dependent, not a removed field (`hazard_model.py:1102`, unchanged logic). The front end does not read it. |

**Verdict and card changes on the 16 VM products: 1 of 16.** A Shopee mini power bank (86 reviews) goes from *possible counterfeit or defect / caution* to *no warning signs / mixed*. This is the intended battery-drain rule (a bare "mabilis malowbat" is not a defect; abrupt or measurable failure still is). It is a real product-level change and shows that the rule update does move verdicts; it appears only after a re-check, because saved reports are shown as stored (`release_manifest.md` section 4). All other 15 keep verdict state and decision. 8 of the 16 are Shopee, which the local DB lacks.

## 4. Exact evidence quotation

`research/release_checks.py` (`results/release_evidence_quotes.json`): over 4,792 labelled reviews, 1,979 quoted spans, **0** offsets that do not reproduce the quoted text (7 spans have no review-level offset because the sentence cannot be located exactly; they keep a sentence offset). Over 1,294 saved Lazada reviews, 463 spans, 0 bad. Served to the app: 10 products, 145 quotes, 164 highlights, **0 outside the quote, 0 empty**.

## 5. Product aggregation and representative scans

* Aggregation (`product_badges.summarize`) is unchanged in logic; the optional `shadow_*` blocks appear only with their switch. With all switches unset the summary has the same keys as production plus evidence terms.
* Representative scans: 60 Lazada gadget products (the local DB holds only gadgets, `results/shadow_evidence_policy_local.json`) and 8 Lazada + 8 Shopee products on the VM were run through the RC; every product produced a report, card and evidence; no errors. A live new-link scan and an extension submission are in the manual smoke checks (`release_manifest.md` section 6), not run here because they would write to the live database.

## 6. Latency, throughput, memory, cold start: equivalent production hardware

Run on the production VM itself (Azure, 2 vCPU, Linux, same Python and ONNX runtime), exact trees of `d74589a` and the RC, twice each, not reusing the earlier benchmark (`results/bench_vm_final/`):

| | Production run 1 | Production run 2 | RC run 1 | RC run 2 |
|---|---|---|---|---|
| Cold start (s) | 2.13 | 2.09 | 2.17 | 2.12 |
| Memory after load (MB) | 366.9 | 369.0 | 401.8 | 381.5 |
| Peak memory (MB) | 375.1 | 378.7 | 404.8 | 384.6 |
| Single review median / p95 (ms) | 61.9 / 133.4 | 61.4 / 133.3 | 62.2 / 133.9 | 61.6 / 134.0 |
| 200-review batch (s) | 13.92 | 13.84 | 14.01 | 13.91 |
| Reviews per second | 14.4 | 14.5 | 14.3 | 14.4 |

Latency and throughput are equal within run-to-run noise (about 1%). Memory is about 5% higher (roughly +15 to +35 MB; the first RC run's 401.8 MB is the high end, the second 381.5 MB) because the evidence layer and the calibrator module are loaded. With the evidence policy `require`: 14.3 per second, 382.5 MB; with every shadow switch on: 14.1 per second, 390 MB (the calibrator adds about 1.3 ms per review). Fits the 3.8 GB machine with large margin. The benchmark ran while the production service was running, which adds noise but the same noise to both.

## 7. Environment and dependency check

* No dependency file changed between `d74589a` and the RC; no model or tokenizer file changed (SHA-256 identical); no front-end or deploy file changed.
* The live service sets no `DEFAKETIVE_` variable (checked read-only on the VM), so the three disabled features stay off. A `git pull` adds about 17 MB of files that nothing imports.
* `research/artifacts/sentiment_calibrator_v1.joblib` is inert unless an environment variable names it.

## 8. Not verified here

A deployment, a live new-link scan, a live extension submission, a front-end change in the browser (none was made) and the re-check run (about 84 minutes) were not performed; they need the owner's approval and are in the checklist.
