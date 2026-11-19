# Remaining fan evidence review

This follow-up starts at `73646d04df47a8cb043d7a7127a92449d933dbb2`, on isolated branch `feature/fan-remaining-evidence-73646d0`. Production was verified at `4eab8ea1b3d7ffa7660343a82cfe969436cbd80b`, service `defaketive` active, unchanged PID 322622. It is not deployed or restarted by this review.

## Complete concern ledger

The [JSON ledger](fan_remaining/remaining-flag-audit.json) and [CSV ledger](fan_remaining/remaining-flag-audit.csv) enumerate every concern association in the prior and candidate 503-review fan reports. Each row includes the marketplace review ID, original full excerpt, product category, concern category, detector source, model score where available, evidence sentences, literal spans and offsets, adjudication and reason. No reviewer/account identities are included. The [changed-evidence ledger](fan_remaining/changed-evidence-audit.json) records every changed flag or supporting span against production and the prior candidate, plus counts, conclusions and supporting quotes.

Prior: **53 associations: 40 supported, 11 unsupported, 2 ambiguous**. Candidate: **42 supported associations, all with literal evidence; no unsupported or ambiguous concern assertions remain**. One formerly supported quality association also contained an unsupported span about the external power bank being cheap; that span is removed while the fan's actual output limitation remains. Ambiguous original wording remains visible in the review and interpretation notes; it is not rewritten.

Judgments are review-reported claims, not independent verification of product incidents. Qualified weak-output comparisons remain qualified; a failure on one low-capacity power bank is recorded as a source-dependent operating limitation, not a diagnosis of a broken motor. Delivery of only one of two units is recorded with the original qualification that the other unit is still in tracking.

## Detector changes and every delta from 73646d0

| Review index | Change | Evidence and interpretation |
|---|---|---|
| 11 | Add quality | Previously missed `Walang hangin`: actual missing airflow. |
| 12 | Evidence only | Existing quality complaint now includes a literal `Walang hangin` span, replacing model_only support. |
| 13 | Remove defect; add quality | `Not sure if it defective` is speculation. `the fan air is weak and no air is blowing out` supports quality. |
| 24 | Remove mismatch | `kahapon kulang na order received na agad` is ambiguous timing/typo wording; abstain rather than assert a shortage. Full short-wire feedback remains available. |
| 36 | Remove mismatch | `only 5w` explains normal operating output, not an advertised-versus-received discrepancy. |
| 41 | Evidence only | Remove `mumurahin` as fan-quality evidence: it describes the reviewer's power bank. Retain the stated lower fan output and failure on one low-capacity source, with successful operation on two other sources. |
| 122 | Remove mismatch | `only 5 watts` describes minimal consumption. |
| 238 | Remove mismatch | `5watts lang` describes low consumption and power-bank use. |
| 289 | Remove mismatch | `5watts lang` sets output expectations, without disputing a promised rating. |
| 317 | Remove mismatch | `since 5w lang` sets expectations, without disputing a promised rating. |
| 355 | Remove mismatch | `mas mahal sia sa ibang same product` compares prices, not delivered-product identity. |
| 359 | Remove defect | `dito sa lugarnmin laging walang power` describes neighborhood outages; fan operation is successful. |
| 408 | Remove quality | `mahina din sya Kumain Ng charge` describes low battery consumption. |
| 427 | Remove defect | `Quiet:it almost no sound` describes quiet operation, not missing intended audio. |
| 435 | Remove quality | `Mahina lang ang consume ng kuryente` describes low electricity consumption. |
| 441 | Remove quality | `kala ko mahina lang malakas Pala` retracts the weak-output expectation. |

That is **13 removed associations, 2 supported additions, 14 reviews with flag changes, plus 2 reviews with evidence-only changes**. There are no unreviewed output deltas. Exact IDs/full excerpts/before-and-after spans are in the linked ledgers.

Rules interpret the specific cue and grammatical subject, restricted to `small_appliance`; they do not exclude whole reviews based on praise, stars, sentiment, category alone or missing keyword support. Other cues in the same sentence still run. The original full review is supplied to the wattage interpretation so that a sentence splitter cannot hide `rated 25W but only 5W` across a clause boundary. Explicit disputed ratings and genuinely different ordered/delivered quantities remain concerns. Normal 5 W ratings, including a matching rated 5 W/actual 5 W statement, are not mismatches.

Controls include English, Filipino and Taglish: a plug melting during an outage; smoke during otherwise normal operation; a real fan motor failure; a speaker with no audio; weak airflow despite successful power-bank operation; low consumption plus actual weak airflow; reversed expectation (`kala ko malakas pero mahina pala`); advertised/ordered 25 W versus actual 5 W; wrong brand; and actual missing quantities. The new literal rules also preserve previously missed no-airflow, barely-moving-air and delivered-quantity complaints.

## Complete three-version replay

All three versions reanalyze the same ordered **503** saved reviews from a verified read-only database copy, with identical original ratings, content and sampling metadata. All 503 initial sentiment labels, three probabilities and sampling weights match across all three versions. No automatic correction is enabled.

| Concern | Production 4eab8ea | Prior 73646d0 | Candidate |
|---|---:|---:|---:|
| Safety | 3 | 0 | 0 |
| Defect | 9 | 5 | 2 |
| Quality | 35 | 31 | 30 |
| Counterfeit | 1 | 1 | 1 |
| Not as described | 16 | 16 | 9 |

Prior and candidate both have backend `no_warning_signs` / `recommended`, rendered as **Consider**. Production had `possible_safety_issue` / `caution`. The three production fan safety removals concern ambient heat at the reviewer's location, weak daytime cooling, and electricity savings/power-bank use. None describes device overheating or shock; the weak-airflow concern remains. The other inherited false-flag removals are documented in the [previous audit](FAN_CONCERN_PRECISION_REVIEW.md). Production review 4 also gains a previously missing literal mismatch span (`dumating ibang quality`) without a flag change; this was already present in 73646d0.

**The review evidence supports Consider** under the existing recommendation rules: predominantly positive feedback, no genuine safety report identified in these 503 reviews, and remaining concerns supported and presented as review-reported signals. It does not establish that the product is safe, flawless, or free of delivery/brand/output issues. The two remaining operation-issue reports, 30 qualified quality reports, one counterfeit claim and nine mismatch/delivery reports remain available with context and literal evidence.

## Acceptance results

* **466 backend unittest tests, zero skips**, including 11 new regression methods; focused fan suite 20 methods, with multilingual and mixed-complaint subcases.
* **65 frontend tests**; Svelte check passes with three pre-existing unused splash CSS warnings; production build passes.
* **34 real-checkpoint multilingual safety controls**, including the six original removed warnings, pass. The additional outage/melted-plug/smoke, no-audio speaker and mixed-airflow controls pass in the new tests.
* **49-category / 833-case representative regression matrix**, no gaps. This is fixture coverage, not an empirical accuracy claim for all real products in those categories.
* All remaining evidence spans reproduce the source substring at their recorded review offsets. Every concern quote shown in the backend shopper summary belongs to a review carrying that supported flag.
* Staged API and CSV serialization retain all 503 reviews, flags, original sentiment and interpretation notes. All 42 remaining associations have literal spans; none depends solely on an unexplained learned label.
* Headless Chromium checks the five-stage explanation, every remaining flagged review and all its flag badges/excerpts, all six earlier corrected reviews, current and historical fan reports, and a six-review mixed/melted control report. JSON download preserves the entire product object exactly; zero browser errors.
* The melted-plug review retains its safety flag, literal melted-plug span, initial Neutral prediction and probabilities in both the shopper report and download. Normal-use and ambient-heat controls remain unflagged; genuine weak airflow and intermittent faults survive mixed feedback.
* Eight historical reports retain original category, summary and every original per-review analysis, are marked older, and never infer on GET/export. No saved report is rewritten. All before/after comparisons use identical sampling data.

Model remains `defaketive-xlmr-firecs-v1-onnx-int8-e04da4c2`, SHA256 `e04da4c268bc8ab94e27da2e0fb4206f38dadc43e9cfb52050818a5bb40c3478`; tokenizer SHA256 `27dea7a8dd6fe22d3913c719dd962f283f7bb2d91f023abf3b1e644df39ca49e`. The checker revision is `fan-concern-context-2`. Model artifacts, initial sentiment code and correction settings are unchanged.

## Exact-commit release gate

Private VM evidence is retained at `/home/azureuser/defaketive-fan-remaining-evidence-20261119`. Fresh backups of both databases under `databases/2026-11-19` use read-only source connections; files are mode 0400. Each backup passes SQLite integrity plus independent in-memory restoration with all table row counts/content hashes compared. The baseline build is copied and its 264 files hashed. Raw database/account data are not committed.

The exact candidate is recorded after commit in private `new.sha` and `final-gate.json`, along with both database hashes, unchanged production PID/model/settings/build, candidate build backup and isolated rollback evidence. The rollback rehearsal starts at that exact GitHub commit, restores baseline code plus all 264 baseline build files, and checks `/`, `/scan`, `/api/saved/products` using an isolated test client. It does not restart production or restore a live database. GitHub CI must also pass on the exact pushed SHA before GO is recommended.

Evidence acceptance is PASS. Final GO depends on the exact-commit backup/rollback and CI gates recorded alongside this review; any failed gate is NO-GO. Deployment still requires explicit user approval. No merge, deployment, service restart or saved-report rewrite is part of this change.
