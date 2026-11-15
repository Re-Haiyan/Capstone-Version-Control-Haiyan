# Protocol amendment A1: AI-assisted annotation (requires adviser confirmation on record)

The approved protocol (`annotation_execution_guide.md`, policy v1) assumed two independent human annotators, a declaration of no AI use, a third human adjudicator and a human-verified final reference. The research panel and adviser have since approved AI-assisted annotation with ChatGPT as primary annotator (owner's statement, 2026-11-15). Policy v1 itself is **not edited** (it is frozen); this amendment changes how it is applied.

| # | Requirement in the original protocol | Amendment A1 | Status |
|---|---|---|---|
| 1 | Two independent human annotators, no AI | The labelling sets are AI-assisted (ChatGPT). They are described as such everywhere; no "independent human" wording. | applied in all documents |
| 2 | Declaration of labelling without AI | **Withdrawn.** Replaced by a process record (`annotation_process_record_template.md`) documenting the actual process: model, prompts, sources, scripts, human review. | form replaced; **team must fill it** |
| 3 | Inter-annotator reliability (Cohen's kappa) from two independent humans | Agreement between the two AI-assisted sets is reported descriptively and labelled "not independent reliability". | applied |
| 4 | Third human adjudicator decides disagreements | Kept: a human reviewer decides the disagreements, originals preserved. | **needs a named human reviewer** |
| 5 | Final reference = adjudicated independent human labels | The final reference is an **AI-assisted reference standard**. It is called "verified" only after the human adjudication above plus a documented random human check of agreed rows. | **needs adviser confirmation of the verification sample size** |
| 6 | Annotators blind to model predictions and stars | Kept in principle (stars hidden in the sheets); whether the AI saw them is recorded in the process record. | to be recorded |
| 7 | Frozen final test never used for training, tuning or selection | **Unchanged and strict.** | in force |
| 8 | Retrain only after genuine human annotations | Retraining may use AI-assisted labels of the development data (not the frozen test), labelled as AI-assisted training data. | applied |

**Items that still need independent validation or adviser confirmation before a defence claim of "verified ground truth":** the human adjudication of the 37 disagreements; a random human check of agreed rows; the process record for each set; the written panel and adviser approval attached to this file; the clean-test question raised by `final_human_evaluation/leakage_audit.md` (about 100 frozen reviews had earlier AI or team labels).

Adviser confirmation reference: ______________________ (date, name). Until it is attached, the status of this amendment is "approved by the owner's statement; written confirmation pending".
