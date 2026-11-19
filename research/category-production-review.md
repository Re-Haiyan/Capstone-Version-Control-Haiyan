# Production-baseline category review (2026-11-19)

Review only. Do not deploy this branch without reviewing the USB fan verdict difference.

Baseline: `ed91291bf1f2779d2e7d683f3899c218ec999f0d`, copied from the running VM because GitHub could not resolve it. Source: draft [PR #55](https://github.com/Re-Haiyan/Capstone-Version-Control-Haiyan/pull/55), `0692a8326c0057bd29bc06b98dff4d69a92421b2`. This branch ports the classifier and historical-report compatibility changes onto the exact baseline, preserving its category-alias fallback. The PR workflows and unrelated audit changes were not ported.

Production remained at pc7, active PID 310671, start 2026-11-19 06:28:53 UTC. No restart, deployment, merge, or saved-report write was performed. Candidate checker revision is pc8. The rest of the checker stamp is unchanged.

## Model and settings

Pinned XLM-R: `defaketive-xlmr-firecs-v1-onnx-int8-e04da4c2`.
Model SHA256: `e04da4c268bc8ab94e27da2e0fb4206f38dadc43e9cfb52050818a5bb40c3478`.
Tokenizer SHA256: `27dea7a8dd6fe22d3913c719dd962f283f7bb2d91f023abf3b1e644df39ca49e`.
Production and replay use the default hazard_badges / xlmr / learned configuration; calibrator, category sentiment adapter, and shadow settings are unset. No automatic sentiment corrections were enabled. No hazard implementation, model artifact, dependency, database, or sentiment rule was changed.

## Read-only backup and replay

Verified the release backup at `/home/azureuser/defaketive-release-shopper-ed91291-20261119/databases/2026-11-19/defaketive.db` through SQLite `mode=ro`: integrity check OK, 491147264 bytes, 421 products, 77155 review-table rows. SHA256 `53f0b8f6dc7291cc3082afe37d8381e6d17db3ab8a6375148995344ca51df678` remained identical after API checks.

Compared all 421 stored titles. Seven change: HP notebook (phone to laptop), POCO Pad (phone to tablet), two CCTV listings mentioning cellphone viewing (phone to camera), two replacement LCD listings (phone to accessory), and Vone USB ceiling fan (charger_cable to small_appliance). All other inventory classifications match. Exact titles and nearby phone/case/charger/mount controls are covered by regression tests.

Replayed all stored comments for these seven products plus four related controls, including a one-review fan: 11 products, 1454 reviews. Each version received a deep copy of the same full raw product JSON, retaining sampling metadata and review order. Input hashes matched per product. No reconstruction from the reviews table or resampling was used. The actual pinned checkpoint ran in independent baseline/candidate processes.

Sentiment labels AND raw probabilities match for all 1454 reviews. All five flags (safety, defect, counterfeit, quality, not_as_described) match except four changes on the Vone fan. Other ten verdicts and backend purchase decisions match. Fresh shopper guidance matches for all eleven products using the actual frontend recommendation function.

## USB ceiling fan: separate review concern

503 reviews, unchanged stratified sampling metadata. Safety 3 to 1, defect 9 to 8, quality 35 to 34; counterfeit 1 and listing mismatch 16 unchanged. These counts are against ed91291, not the older baseline quoted in PR #55.

Inspected both lost safety flags: review indices 48 and 84 refer respectively to relieving ambient heat and daytime heat overwhelming the fan's airflow. Both category exclusions retain the text and their exclusion audit. They are not affirmative overheating reports. The removed defect at index 269 describes intended cooling/continuous use; removed quality at index 355 says the fan is not noisy. No other safety flag is lost.

The retained safety flag at index 260 describes electricity savings, not shock. It is a pre-existing context false positive involving the literal phrase `tipid a kuryente` and the neighboring text. Synthetic probes retain real Filipino electric-shock and English spark/burn reports; negated spark/overheat and ambient-heat relief have no safety flags. A clean `Tipid sa kuryente ang fan.` probe has no flag, showing that the saved wording/context matters.

Backend verdict changes `possible_safety_issue` to `no_warning_signs`; backend purchase decision changes `caution` to `recommended`. Fresh shopper guidance stays `caution` because one review-level safety signal remains. This discrepancy and false positive remain a release-review concern; hazard rules were deliberately left unchanged. This branch is not a deployment approval.

## Historical reports and tests

Isolated GET `/api/saved/detail` checks against the read-only backup verified all seven reclassified reports return 200, retain original category, sentiment summary, every review's analysis and text, and have `checked_with_current=false`. Inference was patched to fail if called by GET. The API's existing author anonymization decorates responses; it does not change saved analysis. The backup hash stayed identical. Saved reports require an explicit recheck to replace their results.

- `python -m unittest discover -s tests`: **431 passed, zero skips**, using deployed Python 3.12.3 environment and a copy of the served static build in the isolated checkout.
- Focused frontend recommendation/category/context tests: **23 passed**.
- New production-port tests cover exact affected titles, neighboring products, preserved fallback aliases, and non-mutating historical compatibility with all five flags populated.
- Real-model paired replay: 11 products / 1454 reviews; six additional fan context probes.

Private replay outputs remain in the isolated VM audit directory and are not committed. Coverage is limited to this saved inventory, fixtures, and probes; no marketplace scrape or production write was needed.
