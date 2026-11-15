# GPT-6 provisional annotation and summary risk audit (2026-11-15)

**Status: AI-assisted, NON-BLIND, non-human research triage. Do not cite as independent human accuracy, Cohen's kappa, the final evaluation or production approval.**

This folder contains a real review-based preliminary analysis of the existing, fixed 35-product / 5,946-review evaluation pack. It is useful for spotting missed defects, unsafe summaries, and ambiguous claims *after* independent human reviewers finish. It does **not** fill, modify or replace `human_eval_pack/`.

## Outputs

| File | Scope | Meaning |
| --- | --- | --- |
| `card_preannotations_ai.csv` | 35 products | Provisional five-way card judgment, reported-safety yes/no, repeated counterfeit-allegation yes/no, rationale, confidence, and product-specific original `review_no` evidence |
| `summary_triage_ai.csv` | All 70 text variants | Provisional QA flags, priority and evidence review numbers for both randomized summary texts. **Numeric seven-dimension human ratings are intentionally NOT fabricated.** |
| `provenance.json` | Entire pass | Annotator = OpenAI GPT-6 in ChatGPT, observed method, source Git blob hashes, limitations and absence of human validation |

Every reference such as `F020 / review 6` means `reviews.csv` for that `product_id` and `review_no`, **not** a verified physical fact. The model programmatically scanned every review text and directly inspected selected excerpts. It did not read and professionally adjudicate every full review individually. The product assessment printed in the official words sheet was visible to the AI during this research pass, making the provisional cards **non-blind**.

## Most important human checks

1. **Unsupported or reversed safety evidence.** Examples include `F002` review 73 (explicitly *no* smoke or overheating, yet both summaries mention a safety event); `F014` review 190 (unrelated song lyrics with a word about fire in a vitamin review); `F030` (16 reviews, no direct overheating report found in sampled inspection). These are **suspected** mismatches, not final adjudications. A human should inspect every claim and full review context before changing code.
2. **Underwarning despite direct hazards.** `F020` review 6 describes an alleged charging-case fire while the conclusion presents only "too few reviews"; `F017` review 44, `F024` reviews 15/18 and `F027` review 5 contain other first-hand reports. A warning's presence is not evidence that the event was externally verified.
3. **Category/recommendation mismatch.** `F011` reports generally favorable cleanser experiences but the system calls it "not recommended" and references many possible safety incidents; `F029` has numerous suspected fake-supplement and misrepresented-quantity claims but "well reviewed" language; `F026` reports half-filled bottles despite favorable headline language. Do not alter the live recommendation policy on the basis of this QA alone.
4. **Marketplace suggestion lists and rating mismatch.** Some 5-star reviews are merely item-description-like lists; some 1-star reviews actually praise the item. Do not infer product feature truth from stars, a seller's tag suggestion, or generic "safe to use" language.
5. **Privacy review.** The locked review pack contains at least one unrelated OTP-like message in a review. Do not circulate a raw copy outside an approved restricted research workflow. Prepare a sanitized human-review copy if sharing is needed without changing or overwriting the historical locked pack.

## How this relates to formal evaluation

**Do not give these files to annotators A and B before they have submitted their own independent sheets.** They would bias the blinded evaluation.

The official protocol still requires two independent human reviewers to complete `features_sheet_A/B.csv`, `card_sheet_A/B.csv`, `claims_sheet_A/B.csv`, and `words_sheet_A/B.csv`, with the prescribed order. That task includes reading every applicable review and assigning the **seven 1–5 word ratings**; no human submission has been supplied. Human annotators may disagree with every provisional AI label, and those disagreements should be retained and adjudicated, never silently overwritten.

After humans complete their forms, run the existing `final_eval_pack.py score DIR_WITH_FILLED_SHEETS` scorer on their actual submitted files with genuine human provenance. Do not substitute this QA folder or call its suggestions ground truth. Status of the original release gate stays **BLOCKED**.

## Limitations

This pass is model-assisted and non-blind, its candidate cards can be wrong, and a regex/pattern scan will miss paraphrases, negations or implicit claims. `summary_triage_ai.csv` is a **review queue**, not 70 formally graded summaries. The P/R/F1 values from historical Phase 3 are not changed or remeasured here. No production code, thresholds, locked evaluation data, or staging configuration is touched.
