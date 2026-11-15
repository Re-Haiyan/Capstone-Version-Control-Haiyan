# Final evaluation report

**Status: PENDING. The final XLM-RoBERTa evaluation was NOT run. No score on the frozen test exists, and none is claimed.**

| Prerequisite | Status | Evidence |
|---|---|---|
| Human provenance verified | **NOT MET** | `annotation_provenance.md`: templated rationales ("Team Label N:"), 50 of 50 mixed rows with identical aspect text on both sheets, both files written within one second and 13 minutes after the blanks were created; no declaration or annotator record |
| Both sheets validated | met (structure and policy v1) | `validation_report.md` |
| Agreement reported | **withheld** (provenance) | `inter_annotator_agreement.md` |
| Adjudication completed by A03 | **NOT MET** (sheet prepared, on hold) | `adjudication_sheet.csv` (37 disagreements, final fields empty) |
| Leakage audit passed | partly: no overlap with candidate training or selection data; about 100 frozen reviews have earlier AI or team labels | `leakage_audit.md` |
| Model selection frozen | met | `model_selection_lock.json` (the shipped model; candidates stay exploratory) |
| Evaluation protocol frozen | met | the lock file (scripts hashed; sensitivity analyses prespecified) |

Two prerequisites are unmet, so the protocol forbids building the reference dataset and scoring. `final_test_metrics.json`, `final_test_classification_report.csv` and `final_test_confusion_matrix.csv` were not generated.

## What exists

* The frozen 400-review test, not labelled by any verified human (hash in `annotation/frozen_final_test.json`).
* The approved, frozen policy v1, and the validated returned sheets (kept unchanged).
* The locked plan: the shipped ONNX int8 model, one review at a time, no calibration, scored once on all 400, then excluding delivery-only reviews, then excluding reviews with prior labels, mixed reviews reported separately, macro F1 against the 0.80 target reported as measured.

## Next step that requires humans

Supply the provenance evidence listed in `annotation_provenance.md`, or label afresh. Then A03 adjudicates, the reference dataset is built and checksummed, and the shipped model is scored once. Earlier results (FiReCS 0.833, older marketplace 0.836 on 150 reviews, historical 0.570 on 846 reviews, candidate d1 0.684 on the 846) remain historical or development figures against unverified labels and are not final-test results.
