# Fan concern precision review — NO-GO

Production was read-only: `4eab8ea1b3d7ffa7660343a82cfe969436cbd80b`, systemd `defaketive` active, PID 322622. Work starts at `23b1090627c0c42900b81ecac6f911371800b7a5`, on `feature/fan-concern-precision-23b1090`. Resolve the tested candidate with `git rev-parse HEAD`; the VM rollback manifest records that exact commit after publication. No merge, deployment, restart or saved-report rewrite is authorized or performed.

## Exact audit reconciliation

Indices below are zero-based in the verified 503-review Vone fan input. All are `small_appliance`. The VM's four were 33, 67, 304 and 501, not the same set described by the local replay. Four learned flags and two related keyword flags are corrected. No star-rating, positive-sentiment, category-wide or model-only exclusion was added.

| Review | Original review, verbatim | Flag/source before | Trigger sentence/span | Expected and candidate result |
|---|---|---|---|---|
| 33 | Performance:good. Best Feature:very nice product. Product Quality:very good nice quality. Malakas yung hangin at hindi maingay. Order ako ulit. | quality; learned extra classifier, 0.9402; model_only | Sentence 3: `Malakas yung hangin at hindi maingay.` No keyword span. | Strong airflow and denied noise: quality flag removed. |
| 67 | Product Quality:10 Performance:10 Best Feature:10 Sakto ito sa camping namin. Okay ang product sakto lang ang lakas wag kang mag expect na sobrang lakas pero pde na. Gumagana naman magdamag ko ginamit sa powerbank. At okay na okay. | defect; learned hazard classifier, 0.7288; model_only | Sentence 3: `Gumagana naman magdamag ko ginamit sa powerbank.` No keyword span. | Successful overnight operation: defect removed. Moderate airflow wording is retained in full. |
| 304 | Bili na kayo magagamit nyo to sa brown out or outing.. kasi powerbank lng gagana na | defect; learned hazard classifier, 0.7017; model_only | Sentence 1: `kasi powerbank lng gagana na`; normalized `kasi powerbank lang gagana na`. No keyword span. | Power-bank sufficiency: defect removed. Original negative sentiment retained. |
| 501 | gumagana nga s powerbank | defect; learned hazard classifier, 0.8751; model_only | Sentence 0, whole review. No keyword span. | Successful operation: defect removed. Original neutral sentiment retained. |
| 173 | Quality:good Performance:good Tahimik lang at di sya malakas sa kuryente kaya maganda talaga sya gamitin. Thank you seller, highly recommended, hopefully more vouchers next transactions. | quality; keyword_rule | `di sya malakas`, original offsets 46:60 | Low electricity consumption: quality removed. |
| 444 | Performance:it runs quitely Quality:I found the plastic material Maganda cya pwede lang sa powerbank at Hindi cya malakas Kumain Ng kuryente | quality; keyword_rule | `Hindi cya malakas`, original offsets 104:121 | Low electricity consumption: quality removed. Original neutral sentiment retained. |

Local replay review 12, `Parang pang bugaw lang ng langaw. Walang hangin`, remains a quality complaint. The classifier triggers on sentence 0 (0.9394); sentence 1 supplies explicit no-airflow context. It remains honestly marked model_only, with the complete review available; no keyword span is invented.

Full-clause operation interpretations abstain on added faults, limitation or ambiguous wording. Separate clauses still run independently. The category consumption exemption retains airflow/motor context. Tests also repair previously missed explicit weak-airflow and intermittent-operation phrases. Literal interpretation excerpts/reasons appear in the shopper review details, JSON download and CSV serializer.

## Paired replay and safety audit

All three versions consume the identical ordered 503 reviews, original ratings and sampling metadata from a fresh read-only database backup. All initial sentiment labels, probabilities and sampling weights match across all 503 rows. Automatic corrections remain off. No additional flag changes occurred beyond the following.

| Concern | Production 4eab8ea | Prior 23b1090 | Candidate |
|---|---:|---:|---:|
| Safety | 3 | 0 | 0 |
| Defect | 9 | 8 | 5 |
| Quality | 35 | 34 | 31 |
| Counterfeit | 1 | 1 | 1 |
| Not as described | 16 | 16 | 16 |

Candidate versus prior: exactly six removals above, no additions, no backend verdict change. Production versus candidate: eleven changed review rows: 33, 48, 67, 84, 173, 260, 269, 304, 355, 444, 501. Prior fixes also remove the ordinary continuous-operation defect at 269 and quiet/sturdy quality flag at 355. Production's backend possible_safety_issue/caution becomes no_warning_signs/recommended; the shopper says Consider. The historical stored report keeps its old findings/category and asks for an explicit recheck.

The original six removed safety warnings were re-examined against their complete reviews and replayed as controls:

* YUTU 1096: `Matipid sa kuryente...malakas ang hangin n ibinubuga nya` — electricity savings and strong airflow; old span `kuryente...malakas`.
* YUTU 1213: `Matipid sa kuryente,at wise gamitin..` — electricity savings; old span `kuryente,at`.
* YUTU 3531: `Okay.. tipid sa kuryente.5nnÿ` — electricity savings plus stray text; old span `kuryente.5nnÿ`.
* Vone 48: `okay na pantanggal init sa pwesto ko` — relief from ambient heat, not device overheating. Clipboard boilerplate supplies no hazard.
* Vone 84: `pag araw Kasi talo Ng init,mahina lang e..` — weak airflow on a hot day, not device overheating. Its quality flag remains.
* Vone 260: `very useful at tipid a kuryente,kaya dn mga power bank..` — low consumption and power-bank operation, not electrical shock.

None reports a genuine or ambiguous device hazard. The 34 multilingual safety controls include these six originals, genuine overheating, smoke, sparks, burns, shocks, negated hazards, ambient heat, and hazards mixed with normal operation. All pass using the real checkpoint. `Gumagana nang maayos pero sobrang init at natunaw ang plug.` retains safety, literal melted-plug evidence, initial Neutral and its original probabilities in the shopper report and download. All five concern paths remain independent.

## Acceptance completed

* Backend: `python -m unittest discover -s tests`: **455 tests, no skips**, including nine new regression methods with multilingual/star-rating/mixed-complaint subcases.
* Category matrix: **49 categories, 833 cases, no gaps** in this existing representative fixture matrix. This is not a claim of empirical accuracy across every real product/category.
* Safety controls: **34/34**, real pinned checkpoint.
* Frontend: **65 tests**, no skips; check passes (three pre-existing unused splash CSS warnings); production build passes.
* API/CSV: current report 200, all 503 rows/scores/flags/available excerpts/interpretations preserved; 53 remaining concern associations, 52 with literal spans and the supported model_only quality complaint at review 12.
* Eight saved historical reports: original category, summary and per-review analysis unchanged, marked older, inference forbidden on GET/export. Backup hash unchanged after all reads.
* Headless Chromium on the staged build: current 503-review report, historical 503-review report and six-review mixed/melted control report; download JSON exactly preserves every product field/review, zero browser errors. The six corrected rows show interpretation excerpts and original scores; melted plug stays a safety concern; mixed weak airflow and intermittent fault remain flagged.
* Model unchanged: `defaketive-xlmr-firecs-v1-onnx-int8-e04da4c2`; ONNX SHA256 `e04da4c268bc8ab94e27da2e0fb4206f38dadc43e9cfb52050818a5bb40c3478`; tokenizer `27dea7a8dd6fe22d3913c719dd962f283f7bb2d91f023abf3b1e644df39ca49e`. No calibration or automatic-correction setting changed.

## Release blockers found while auditing remaining flags

The requested six fixes pass, but **NO-GO for production**: the complete remaining-concern inspection found additional wording problems outside those six changes. They are retained, not silently suppressed or represented as verified complaints:

| Review(s) | Existing output | Evidence requiring follow-up |
|---|---|---|
| 36, 122, 238, 289, 317 | not_as_described | `only 5w`, `only 5 watts`, `5watts lang`, `5w lang` describe the operating rating/limitations without an explicit advertised-versus-actual mismatch. |
| 355 | not_as_described | `ibang same product` is part of a price comparison, not a received-item mismatch. |
| 359 | defect | `dito sa lugarnmin laging walang power` describes local outages while the fan works. |
| 427 | defect | `Quiet:it almost no sound .bot disturbing. Quality:it is good .` describes quiet operation. |
| 408, 435 | quality | `mahina din sya Kumain Ng charge`; `Mahina lang ang consume ng kuryente` describe low consumption. The current narrow fix handles the audited `di/hindi ... malakas` form only. |
| 441 | quality | `kala ko mahina lang malakas Pala` retracts an expectation of weak airflow. |
| 24 | not_as_described | `kahapon kulang na order received na agad` is ambiguous punctuation/wording; keep unresolved rather than erase a possible shortage report. |

Other remaining rows include genuine weak-airflow, failed operation, incorrect brand/cord and missing-item reports; they remain available in full. The existing Consider outcome is supported by predominantly positive feedback and removal of false safety reports, but the remaining concern presentation is not clean enough to approve release. Do not equate no warning-level threshold with no complaints or a verified-safe product.

## Backup and rollback evidence

Private VM evidence directory: `/home/azureuser/defaketive-fan-concern-evidence-20261119` (restricted access). Fresh backups under `databases/2026-11-19` use read-only source connections and mode 0400. Both integrity checks pass; each database was restored into an independent SQLite database in memory and every table row count/content hash compared. Review DB SHA256: `78fb1acdbd538aaf21ec2fbb671e65177f7b71515795d8dd62cc93927f2abe19`. Accounts backup hash is recorded in private `preflight.json`.

The current baseline build is copied and all 264 files hashed. Exact-candidate code/build backup, isolated candidate-to-baseline rollback rehearsal and final production guard are recorded alongside `rollback-rehearsal.json` after this commit is pushed. Rehearsal restores 4eab8ea plus the baseline build and checks `/`, `/scan`, `/api/saved/products` in an isolated test client. No live rollback is run. Production rollback would require explicit authorization: restore the baseline code/build pair using that manifest and restart only then. Database restore is not part of this code-only rollback.

Private raw reviews, user/account data and database files are deliberately not committed. CI and the exact final candidate/rollback manifest must be consulted with this report; passing tests do not remove the release blockers above.
