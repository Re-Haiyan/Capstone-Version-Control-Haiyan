# Annotation process record: Claude session 1 (Team Label 1)

**Classification: Claude-assisted annotation. Not human annotation. Not ChatGPT.** ChatGPT performed none of these labels. The research adviser permitted AI-assisted annotation; no written approval replacing the independent-human requirement exists in this repository, so that requirement stays **pending** (see `deployment_readiness.md`).

| Item | Record |
|---|---|
| Annotator | Claude (Anthropic), working as the coding assistant that built and tested this feature |
| Model name and version | Claude Sonnet 5.5, model id `claude-sonnet-5-5` |
| Interface | Claude Code, VS Code extension session; labels typed by the model into a Python dictionary and merged into the sheets by a script; no API batch, no other AI |
| Session date | 2026-11-15 |
| Dataset | `human_eval_pack/` as built by `final_eval_pack.py make` (35 products, 80 claims, 150 sampled reviews); sheet A order; input hashes in `provenance.json` |
| Policy version | `human_eval_pack/INSTRUCTIONS.md` (hash in `provenance.json`), plus the six interpretation rules below, fixed **before** any system output was compared |
| Human review involvement | **None.** No person read, changed or approved any label before scoring |
| Annotation method | One pass, reviewing the 150 review texts (features sheet) and 80 quotations (claims sheet) in the order shown; the full review was opened for 7 uncertain claims |
| Original returned data | `raw/labels_features.txt` (the labels as typed) and `raw/labels_claims.txt` (labels and notes as typed); the sheets in this folder are the merge of those |
| Validation outcome | every feature id belongs to the row's profile vocabulary (checked by script); all 150 feature rows and all 80 claim rows labelled; the scorer ran once on the result; no label was changed afterwards |

## The prompt

The instruction that started this work was the task message from the project owner. Its operative lines were: *"Use legitimate AI-assisted annotation to evaluate: 1. Correct feature identification 2. Feature sentiment direction 3. Quotation relevance 4. Unsupported statements 5. Missed product features 6. Review evidence counts 7. Safety and authenticity wording 8. Overall conclusion usefulness. Ensure annotation is completed without exposing system predictions or private answer keys where the protocol calls for blindness. Use the same documented evaluation policy across batches. Never invent missing annotations."* and *"If Claude performs annotation itself, label the source accurately as Claude-assisted annotation. Never claim that ChatGPT completed work it did not perform."* The annotation rules given to the annotator are `human_eval_pack/INSTRUCTIONS.md`. No separate system prompt was written for the annotation.

## Blindness, honestly stated

- **Not opened before labelling:** `key_private.csv`, `features_key_private.csv`. The features sheet contains no system output. The scorer read the key only after the labels were final.
- **Shown by design:** the claims sheet shows the system's claims (aspect, direction, quotation); that is what is being judged.
- **Not blind in the sense that matters for independence:** the annotator is the same assistant that wrote the extractor and the pack, in the same working session. It knows how the system is built and which kinds of phrase it was designed to exclude. This can bias labels toward or against the system in ways that cannot be measured here. A person or a different AI with no knowledge of the system would be more independent.
- **Not an independent two-annotator design:** only one set exists. Agreement between annotation sets is **pending**.

## Interpretation rules (fixed before scoring; applied to every row)

1. A **marketplace suggestion list** ("Transform your hair into silky perfection!, Say goodbye to frizziness!") is not the reviewer's statement and is ignored; the row is flagged `menu-tag list ignored`. A prompt answered in the reviewer's own words ("Charging Speed: so fast, 15 mins full charge") counts.
2. A bare "ok" or "okay", and generic praise ("nice", "very good", "recommended") with no feature, are neutral: no label.
3. A bare "thank you seller" is not a statement about service; praise of the service ("mabait na rider", "kudos to the seller") is.
4. Not yet used, hopes, and hypotheticals state nothing.
5. Wrong item, missing items and a differing amount or colour are `matches_listing:negative`; damage on arrival is `arrival:negative`; "sira" (broken) or "doesn't work" is `functionality:negative`.
6. A review can state a feature in both directions; both are listed.

Rule 1 matches a design decision of the system (it also excludes suggestion lists). It is stated so a reader can judge whether it flatters the system; the scorer therefore reports a sensitivity figure on the 93 reviews with no suggestion list.

## What was not annotated

- **Card sheet (35 products)** and **words sheet (35 products, two texts each)**: not done. Judging an overall assessment, or whether a count such as "several reviews" is accurate, requires reading all 5,946 reviews of the 35 products (about 190,000 tokens); a sample would not answer the protocol's question and no rating was guessed. The unsupported-statement rate, safety-error rate, conclusion preference and overall usefulness from the words sheet are therefore **pending**. They can be completed in batches by product with the same rules.
- **Review evidence counts** are not annotated by anyone; they are verified mechanically (distinct review ids, `evidence_verification.md`).
