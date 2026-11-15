# Policy S4 (feature lists without an opinion): recommendation

Basis: annotation validity (what a review actually asserts, and what the label is used for), policy logic, and examples from **training-side data** (FiReCS train, marketplace team labels). The frozen test was not used to shape this recommendation, no frozen label is revised, and policy v1 is **not edited**; this is a proposal for a documented amendment (v1.1) that needs adviser confirmation and applies only to **new** annotation (the development pool and later sets).

## The distinctions as policy v1 states them

| Kind of review | v1 label and tags | Defining test |
|---|---|---|
| Description or feature list, no opinion ("Adjustable temperature, LED display") | neutral + `no-opinion` | The text states properties of the product and **no experience or evaluation by the reviewer** |
| Satisfaction ("sulit", "ang ganda", works well) | positive | an explicit favourable evaluation, or a reported good experience |
| Dissatisfaction | negative | explicit unfavourable evaluation or a reported problem |
| Both | positive or negative + tag `mixed`, or `mixed` when neither dominates | two clear opposite evaluations |
| Delivery-only | the stated feeling + `delivery-only` | about delivery, packing, seller only |
| Lukewarm ("okay lang") | neutral | standalone, no evaluation beyond acceptable |
| Not yet used / will update | neutral + `no-opinion` | no experience yet |

## Why S4 is valid and should be retained

1. **Validity.** A feature list copied from a listing is marketplace boilerplate that reviewers or the platform's auto-fill paste; it says nothing about the reviewer's satisfaction. Counting it as positive would let promotional text raise a product's "positive share". Treating it as no opinion matches the purpose of the review checker (what buyers experienced).
2. **A five-star rating is not evidence of sentiment** (approved S4 clarification): on marketplaces a star rating is frequently left without any written experience; whether that holds for these reviews was not measured.
3. **Neutral stays interpretable**: neutral = "no evaluation expressed". Folding such reviews into positive would blur positive with "no information".

## The real defect: S4 is ambiguous at its boundary, not wrong

The disagreement between the two AI-assisted sets (31 of 37; reported descriptively earlier, and used here only to see where the wording is unclear, not to choose a rule to fit any score) arises where a feature statement **contains evaluative words** ("Great value", "Sleek and modern design", "easy to use") that look like praise but may be copied claims. v1 does not say which wins. **Recommended clarification (v1.1, new annotation only):**

1. **Experience test.** Positive only if the reviewer reports their own experience or expresses their own judgment (first person, past tense of use, "I", "ko", "nagamit ko", "sulit para sa akin", "okay naman siya" about use). A bare description of properties, even with evaluative adjectives that read as listing copy ("High-quality charger and cable., Fast charging speed!") is neutral + `no-opinion`.
2. **Template rule.** A comma- or period-separated list of 3 or more short claims with no first-person, no experience, and no contrast is a listing copy: neutral + `no-opinion`. If one clause reports use ("so far okay ang takbo"), label by that clause.
3. **Generic praise with a feature word** ("Ganda ng design!") is a judgment: positive. A bare adjective with no object ("Good") is positive if the reviewer expresses it as a verdict, neutral + `no-opinion` if it is clearly a template tag.
4. Record `tags = no-opinion` in every case of 1 and 2 so models and aggregation can treat them separately.

## Product-level handling (an owner decision, not a labelling rule)

Report sentiment shares **with and without `no-opinion` reviews**; a conclusion card should state how many reviews expressed an opinion. This also resolves the tension for the classifier: a separate "no-opinion" detector (a different, simpler task than sentiment) may serve better than forcing the three-class model to separate feature lists from satisfaction by itself.

## Decision requested

Retain S4 as approved; adopt the clarifications 1 to 4 as **v1.1** for new annotation only; keep the frozen test and its labels under v1. v1.1 requires the adviser's written confirmation before the development pool is labelled with it. (If the adviser prefers v1 unchanged, the development pool is labelled under v1 and the prompt file already follows v1 text.)
