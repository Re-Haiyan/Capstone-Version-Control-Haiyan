"""Writes the status documents of the final human evaluation (validation, provenance, agreement status, leakage audit, model lock, reference manifest).
Text only; every figure comes from _forensics.json, leakage_audit.json, the policy and manifest locks, or the sentiment_agreement check. No label is created."""
import datetime, hashlib, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "final_human_evaluation"
ROOT = HERE.parent.parent


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


(OUT / "validation_report.md").write_text("""# Validation report: the two returned sentiment sheets

Files (as found, never modified; copies and hashes are in `annotation/returned/` and `annotation/provenance_log.csv`):

| Sheet | Path | SHA-256 | Run by (named by the owner) |
|---|---|---|---|
| A | `C:/Users/cabal/Downloads/team_label_1_final_test_sheet_A_v1.csv` | `5e3670e36c82d51a...` | team 1, Caballero |
| B | `C:/Users/cabal/Downloads/team_label_2_final_test_sheet_B_v1.csv` | `2e3cb2a41d39c7d1...` | team 2, Guyo |

Method: `sentiment_agreement.py check` (records matched by review ID against the frozen blank sheets) and `provenance_forensics.py`.

## Structural and policy-v1 validation: PASSED

| Check | Sheet A | Sheet B |
|---|---|---|
| Rows | 400 | 400 |
| Same 400 review IDs as the frozen blank | yes | yes |
| Duplicate or missing IDs | 0 | 0 |
| Product, category, platform, language and review-text columns unchanged (matched by ID) | 0 rows edited | 0 rows edited |
| Columns equal to the blank | yes | yes |
| Row order | each follows its own blank sheet's order (A and B were shuffled differently); agreement code matches by ID, never by position | same |
| Allowed `sentiment` values, valid tags, valid `confidence` | 0 invalid | 0 invalid |
| Mixed rules (mixed needs the tag; the mixed tag needs both aspects; no neutral plus mixed; no-opinion only on neutral or unclear) | 0 violations | 0 violations |
| Completed rows / low-confidence rows | 400 / 27 | 400 / 25 |

No invalid row exists, so no corrected sheet is requested on structural grounds. No label was changed.

## Provenance: NOT SUBSTANTIATED (see `annotation_provenance.md`)

The structural checks cannot show who produced a label. Provenance fails: the returned files carry machine-generated patterns, and no annotator identity record, declaration or time record exists. Consequence under the protocol: **no human inter-annotator reliability is reported, adjudication is on hold, and the final test is not scored.**
""", encoding="utf-8")

(OUT / "annotation_provenance.md").write_text("""# Annotation provenance audit (policy v1)

Source of the figures: `_forensics.json` (`provenance_forensics.py`). No model prediction was read and no model was scored. The stars were read from the private map only to examine how the labels relate to them.

## What is documented

| Requirement | Evidence found |
|---|---|
| Annotator identity records | None per annotator. The owner states that team 1 is run by Caballero and team 2 by Guyo (recorded in `annotation/provenance_log.csv` as `TEAM1-run-by-Caballero` and `TEAM2-run-by-Guyo`). That names the team leads, not who read each review. No annotator register entry was completed. |
| Annotation dates | File modification times only: sheet A 2026-11-15 12:52:01, sheet B 12:52:02. The blank sheets were created at 12:39. |
| Policy version | The file names carry `v1`. |
| Declaration (alone, no AI, no script, no model output, no stars, no other sheet) | **Not given.** |
| Visibility of predictions or existing labels | No evidence either way; **not confirmed**. |
| Text and IDs unchanged | Yes (`validation_report.md`). |

## Forensic findings

1. **Both 400-review sheets were written within one second of each other (12:52:01 and 12:52:02), 13 minutes after the blank sheets were created.** That is about 2 seconds per review per sheet, each row with a rationale.
2. **The rationale column is templated.** Every rationale on sheet A begins "Team Label 1:" and every one on sheet B "Team Label 2:". Sheet A has 60 distinct rationale strings in 400 rows and sheet B 61, built from a short list of category sentences (202 rows of sheet A read "Favorable evaluation of product, function, value or purchase experience."). The policy asked for neither a team prefix nor a fixed sentence per category.
3. **Fifty of fifty rows tagged `mixed` carry word-for-word identical `positive_aspect` and `negative_aspect` text on both sheets**, and the mixed tag set is identical on all 50. Two people working independently would not type the same aspect phrases in 50 of 50 cases.
4. **Near-identical confidence:** 394 of 400 rows have the same `high` or `low` value on both sheets.
5. **The file format matches the project's own CSV writer** (UTF-8 with byte-order mark, CRLF line endings, same column order and quoting). That alone is not conclusive (a spreadsheet can write the same), but together with 1 to 3 it points to a script producing both files from one source.
6. **Relation to the hidden stars:** the labels follow the stars closely in aggregate (33 of 34 one-star rows negative on A; 231 of 290 five-star rows positive), as a text-reading process would; this neither supports nor contradicts independence.
7. **No file hash match** with another file on this machine. **Comparison with the known AI-generated drafts:** 69 of the 400 frozen reviews also exist in the 10,000-review pool that carries AI "direct" sentiment annotations (`D:/cvc-annotations`, branch `annotations-10000`). On those 69, sheet A's label equals the AI label for 55 and sheet B's for 50 (80% and 72%; the AI scheme has `mixed` as a label, so differences are expected). This neither shows nor excludes copying.

## Conclusion

**Independent human annotation cannot be substantiated.** The evidence points to machine-generated or template-generated sheets from a shared source, labelled with team names: the pattern of the earlier unverifiable labels. It is not proof of misconduct (a team could have applied its own rubric with a script, or exported from a shared spreadsheet), and the submitted labels were not changed.

## Evidence still needed

1. For each sheet, the name of the person who read and labelled the reviews and a signed declaration that they labelled alone, without an AI assistant or script, without model predictions, stars or the other sheet.
2. The original working file (spreadsheet with edit history, or the export log) and how long the labelling took.
3. An explanation of the "Team Label N:" prefix, the repeated rationale sentences and the identical aspect text on the 50 mixed rows.
4. Alternatively: fresh independent labelling by two named people on blank sheets made from the same frozen list, without any content of these sheets shared with them.
""", encoding="utf-8")

(OUT / "inter_annotator_agreement.md").write_text("""# Inter-annotator agreement: NOT REPORTED

**Status: WITHHELD.** Human provenance is not substantiated (`annotation_provenance.md`), so no inter-annotator reliability figure (raw agreement, Cohen's kappa, interval, per-class agreement, tag agreement) is reported as human agreement, and `agreement_confusion_matrix.csv` was not generated. The scoring code (`sentiment_agreement.py score`) is ready and was exercised on synthetic fixtures only (`tests/test_sentiment_agreement.py`); it will run on genuine sheets once provenance exists.

What can be stated without claiming human reliability: the two returned files differ on 37 of 400 reviews in the label (and in the same 37 reviews' tags): 31 positive versus neutral, 4 unclear versus classified, 1 negative versus neutral, 1 mixed versus single-polarity. Low-confidence rows: 27 (sheet A) and 25 (sheet B). These describe the two files; they do not measure how reliable human annotators are. See `disagreement_cases.csv`.

(An earlier chat message quoted a kappa from these files; it was explicitly marked unverified and is not carried into any research document.)

Table A of `chapter4_objective5_results.md` stays NOT YET VERIFIED until two independent, declared human sheets exist.
""", encoding="utf-8")

lk = json.load(open(HERE / "annotation" / "policy_v1.lock.json"))
fr = json.load(open(HERE / "annotation" / "frozen_final_test.json"))
model_dir = ROOT / "backend/sentiment-analysis/models/sentiment_onnx/xlmr_firecs_v1"
lock = {"locked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "rule": "Locked from development evidence only, before any adjudicated final label exists. The frozen final test was not used to choose between models and has not been scored.",
        "selected_model": "the shipped model (prespecified primary)",
        "selection_reason": "There is not enough trustworthy development evidence to replace it: every marketplace comparison uses team-supplied labels of unverified provenance; the candidates win on the 846-row benchmark (+0.10 to +0.11 macro F1) and lose by 0.09 to 0.11 on the older 150 team-labelled rows; seed noise is about 0.02; the best candidate d1_mix_ce_rep2_s1 is 0.010 below the shipped model on FiReCS; no independent final labels exist. Candidates stay exploratory and are not scored on the final test.",
        "model_file": "backend/sentiment-analysis/models/sentiment_onnx/xlmr_firecs_v1/model.onnx", "model_file_sha256": sha(model_dir / "model.onnx"),
        "tokenizer_sha256": sha(model_dir / "tokenizer.json"), "model_version": "defaketive-xlmr-firecs-v1-onnx-int8-e04da4c2",
        "production_vm_commit": "2c6e056", "research_commit_at_lock": "branch deployment, documentation commits after d7af5fa",
        "preprocessing": "raw review text, stripped; no normalisation; tokenizer.json with truncation at 128 tokens; stars, product title and category are not inputs",
        "inference_configuration": "ONNX Runtime CPU, 1 intra-op thread, one review per call (int8 activation scales depend on the batch), softmax over logits, argmax",
        "class_mapping": ["negative", "neutral", "positive"], "calibration": "none (no temperature, no decision-rule bias)",
        "random_seed": "not applicable (no training); bootstrap intervals use seed 0",
        "evaluation_scripts_sha256": {n: sha(HERE / n) for n in ("inference.py", "metrics_x.py", "sentiment_agreement.py")},
        "policy_v1_sha256": lk["sha256"], "frozen_test_manifest_sha256": fr["final_test_ids_and_texts_sha256"],
        "exploratory_candidates_not_scored": {"d1_mix_ce_rep2_s1": "D:/defaketive-train/xlmr/d1_mix_ce_rep2_s1/best", "c2_mix_weighted_s1": "D:/defaketive-train/xlmr/c2_mix_weighted_s1/best"},
        "final_test_scored": False,
        "sensitivity_analyses_prespecified": ["all 400 reviews", "excluding delivery-only reviews", "excluding reviews present in review_pool_10000, fresh_eval_sheet or al_pool (prior AI or team labels)", "mixed (no dominant polarity) reported separately"]}
json.dump(lock, open(OUT / "model_selection_lock.json", "w"), indent=1)
json.dump({"status": "NOT BUILT: PENDING INDEPENDENT HUMAN ADJUDICATION AND UNRESOLVED PROVENANCE",
           "reason": "The two returned sheets have unsubstantiated human provenance and no completed A03 adjudication exists; no final ground truth was created.",
           "policy_v1_sha256": lk["sha256"], "frozen_test_manifest_sha256": fr["final_test_ids_and_texts_sha256"], "eligible_reviews": None, "reference_checksum": None,
           "returned_sheet_hashes": {"A": sha(HERE / "annotation/returned/team_label_1_final_test_sheet_A_v1.csv"), "B": sha(HERE / "annotation/returned/team_label_2_final_test_sheet_B_v1.csv")}},
          open(OUT / "final_reference_manifest.json", "w"), indent=1)
print("written")
