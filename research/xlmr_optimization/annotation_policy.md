# Sentiment annotation policy (proposed v1, for the owner's approval)

Purpose: independent human labels of the **sentiment of a marketplace review**, so that a sentiment model can be trained, selected and finally tested on labels whose provenance is known. This policy is **sentiment only**. Defect, counterfeit, safety, quality, delivery and not-as-advertised flags are a different task (`research/annotation_policy_v2.md`) and are not labelled here.

**Status:** a proposal. It becomes "v1" only when the owner approves it in writing; both annotators must use the same version, named in their file names. Nothing in this folder has been labelled by a person.

## Labels (sentiment column)

| Label | Use it when | Do not use it when |
|---|---|---|
| `positive` | The reviewer clearly evaluates the product or purchase favourably, and states no clear complaint. | Praise is only a polite closing ("thank you seller") with nothing else, or is contradicted later in the text. |
| `negative` | The reviewer clearly evaluates it unfavourably, and states no clear praise. A report that something broke, is fake, is wrong or is unsafe is negative. | The reviewer only worries ("baka masira") or asks a question. |
| `neutral` | No clear positive or negative evaluation: facts or a feature list, "not yet used", a question, a lukewarm "okay lang / so-so / pwede na" with nothing good or bad stated. | The text states a clear good point and a clear bad point (that is `mixed`). |
| `mixed` | At least one clear favourable and one clear unfavourable evaluation, usually of different aspects ("maganda pero mabilis masira"). | Only one side is clear. Do **not** turn mixed into neutral to make a choice easy. |
| `unclear` | A person cannot decide from the text alone (too short, unintelligible, needs the listing). | You can decide but are unsure: label it and set `confidence` to `low`. |

`mixed` and `unclear` are **not** collapsed into `neutral` by this project's tools. The three-class model labels (negative, neutral, positive) are scored on reviews both annotators labelled with those three; `mixed` and `unclear` are reported separately. How a mixed review counts in a product conclusion is an owner decision (below).

## What to judge

* Judge **the text only**. The star rating is hidden on purpose: a star rating is not sentiment ground truth, and stars often contradict the words (a 5-star "sira agad" is negative).
* Read the product title first: "mabilis uminit" is bad on a charger and may be good on a phone.
* **Kinds of review.** Start every `rationale` with one tag so the kinds can be counted later: `[product]` an opinion of the item, `[delivery-only]` only about delivery, packing or the seller, `[both]` product and delivery opinions, `[no-opinion]` facts, a feature list or "not yet used", `[mixed]`, `[unclear]`. For a delivery-only review, label the feeling it states (positive or negative) and tag it `[delivery-only]`.
* Sarcasm: label the intended opinion. Negation and double negation ("hindi naman pangit") by meaning. Emojis count only when they carry an explicit opinion. Listing text copied into the review ("Ribbed texture prevents collapse") and template fields ("Performance: ok") are judged by what they say; a list of features with no opinion is `neutral` with `[no-opinion]`.
* Filipino, English and Taglish are all in scope. A word you do not know: say so in the rationale and use `low` confidence.

## Columns the annotator fills

`sentiment` (one label above, lower case), `confidence` (`high` or `low`; a `low` row is not scored as a disagreement and costs nothing), `rationale` (a tag from above plus a few words). Never edit any other column. Never leave `sentiment` blank for a review you can decide.

## Disagreement and adjudication

After both sheets are returned (`annotation_execution_guide.md`), a third person who has not labelled the reviews sees both labels and rationales (not the model output, not the stars) and decides each disagreement in `adjudication_sheet.csv`, writing the final label, the rule or reason, the policy version and the date. The original sheets are never changed. Agreement (Cohen's kappa, per-class agreement, the confusion table) is computed from the two untouched sheets before adjudication.

## Decisions the owner must make before labelling (recommended answers)

| # | Question | Recommended |
|---|---|---|
| S1 | Is `mixed` a fourth class for the model, or does the model stay three-class with `mixed` handled in product aggregation? | Keep the model three-class; score `mixed` separately; count a mixed review as one positive and one negative mention in aggregation. |
| S2 | Does a delivery-only review count as sentiment about the product? | Label the feeling, tag `[delivery-only]`, and report model scores with and without delivery-only reviews. |
| S3 | Is a lukewarm "okay lang" neutral? | Yes. |
| S4 | Is a feature list with no opinion neutral? | Yes (`[no-opinion]`). |
