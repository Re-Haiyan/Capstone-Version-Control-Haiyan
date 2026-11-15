# Sentiment annotation policy v1 (APPROVED by the owner; FROZEN before labelling)

**Status: approved.** The owner approved decisions S1 to S4 with the clarifications written below. This text is version **v1**. Its SHA-256 is recorded in `annotation/policy_v1.lock.json`; any change to this file after labelling starts is a **new version (v2)** and must be written under a new file name, never over this one. Both annotators and the adjudicator use v1 only; the version is named in every file name and provenance line. Nothing in this folder has been labelled by a person.

Purpose: independent human labels of the **sentiment of a marketplace review**, to train, select and finally test a three-class (positive, neutral, negative) sentiment model on labels whose provenance is known. Defect, counterfeit, safety, quality, delivery and not-as-advertised **flags** are a different task (`research/annotation_policy_v2.md`) and are not labelled here.

## 1. What the annotator records (three kinds of information, kept separate)

| Column | Values | Meaning |
|---|---|---|
| `sentiment` | `positive`, `neutral`, `negative`, `mixed`, `unclear` | the three-class label, or `mixed` only when neither polarity dominates (S1), or `unclear` |
| `tags` | zero or more of `mixed`, `delivery-only`, `no-opinion`, joined with `;` (blank if none) | what kind of review it is |
| `positive_aspect`, `negative_aspect` | a few words each | required when `mixed` is in `tags`: the favourable and the unfavourable thing, as aspect-level evidence |
| `confidence` | `high`, `low` | a `low` row is not scored as a disagreement; it costs nothing |
| `rationale` | free text | why, in a few words |

## 2. The decisions (S1 to S4)

**S1. Mixed sentiment.** The model stays three-class. `mixed` is recorded as a **tag**, and the review's positive and negative experiences are preserved as aspect-level evidence (`positive_aspect`, `negative_aspect`).
* One polarity clearly dominates (the reviewer's overall verdict is plain): put that polarity in `sentiment` and add the tag `mixed`. Example: "maganda ang tunog, medyo mahina lang ang bass, sulit pa rin" is `positive` + `mixed`.
* Neither dominates: `sentiment` = `mixed` (with the tag). Such a review is kept in a **separate mixed evaluation set** and is **never forced into `neutral`**. It is excluded from the three-class scores and reported separately.
* A mixed review is **one review**. It is never counted as two independent reviews. In any sentiment percentage it adds 1 to exactly one three-class bucket (its dominant polarity) or, if neither dominates, to the separate mixed count, so shares of reviews never exceed 100%. Its two aspects are counted only in aspect-level tallies, which are reported separately and never summed with review percentages.
* `neutral` plus `mixed` is not allowed (neutral means no clear evaluation; mixed means two clear ones).

**S2. Delivery-only feedback.** Label the sentiment the reviewer explicitly expresses and add the tag `delivery-only` when the review is only about delivery, packing, the rider or the seller. A review about both delivery and the product is not `delivery-only`.
* Sentiment performance is reported **both including and excluding** `delivery-only` reviews.
* Positive delivery feedback is **not** evidence that the product performs well. Product-level conclusions must separate delivery satisfaction from product satisfaction; a `delivery-only` review is not product evidence.

**S3. "Okay lang".** A standalone, lukewarm expression ("okay lang", "so-so", "pwede na") is `neutral`. Read the whole review: explicit praise ("okay lang pero sulit na sulit") or dissatisfaction ("okay lang pero sira agad") justifies another label.

**S4. Feature lists without opinions.** Feature descriptions with no expressed opinion ("Adjustable temperature settings, LED display") are `neutral` with the tag `no-opinion`. The star rating is hidden and is never evidence: a five-star review is not proof of a positive product experience.

## 3. Labels in detail

| `sentiment` | Use it when | Do not use it when |
|---|---|---|
| `positive` | The reviewer clearly evaluates the product or purchase favourably and the favourable side dominates. | Praise is only a polite closing with nothing else, or is contradicted. |
| `negative` | The reviewer clearly evaluates it unfavourably and the unfavourable side dominates. A report that something broke, is fake, is wrong or is unsafe is negative. | The reviewer only worries ("baka masira") or asks a question. |
| `neutral` | No clear positive or negative evaluation: facts, a feature list, "not yet used", a question, a standalone lukewarm remark. | Two clear opposite evaluations exist. |
| `mixed` | Two clear opposite evaluations and **neither dominates**. | One side dominates (use that side plus the tag). |
| `unclear` | A person cannot decide from the text alone (too short, unintelligible, needs the listing). | You can decide but are unsure: label it and use `low` confidence. |

## 4. What to judge

* Judge **the text only**. The star rating is hidden. Read the product title first.
* Sarcasm: label the intended opinion. Negation and double negation by meaning. Emojis count only when they carry an explicit opinion. Listing text copied into a review and template fields ("Performance: ok") are judged by what they say.
* Filipino, English and Taglish are all in scope. A word you do not know: say so in the rationale and use `low` confidence.
* Never edit any column other than the six above.

## 5. Disagreement, adjudication and agreement

A third person (`A03`) who has not labelled the reviews sees both labels, tags, aspects and rationales (not model output, not stars) and decides each disagreement in `adjudication_sheet.csv`, writing the final label, tags, rule or reason, policy version and date. The original sheets are never changed. Agreement (Cohen's kappa with an interval, per-class agreement, the confusion table, and agreement on each tag) is computed from the two untouched sheets before adjudication and reported in full, including low agreement.

## 6. Reporting rules that follow from the approval

1. Three-class scores use only rows both annotators (or the adjudicated label) mark `positive`, `neutral` or `negative`; `mixed` (no dominant) rows form a separate evaluation set.
2. Every sentiment score is reported with and without `delivery-only` reviews.
3. No sentiment percentage may exceed 100%; a review is one unit.
4. No label is fabricated, simulated or machine-completed. The frozen final test is scored once, after labels and adjudication exist, and never used to select a model.
