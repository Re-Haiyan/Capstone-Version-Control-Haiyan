# Architecture

How a product-specific conclusion is made, where each piece lives, and how to change it safely.

## 1. The flow

```
saved report (reviews with text, rating, comment_id, duplicate flags)         unchanged
      |
      +--> hazard checker + sentiment shares --> dashboard_utils._conclusion --> decision, verdict, points, basis, notice   (UNCHANGED)
      |
      +--> aspects.extract(reviews, category) -------------------------------> counts of DISTINCT reviews + quotations
                                                                                        |
dashboard_utils._ground_conclusion  <---------------------------------------------------+
      |   conclusion_text.compose(decision, state, shares, hazard counts, aspect evidence, noun)
      v
conclusion = {decision, headline, text, points, basis, notice         (as before)
              lead, summary, body, warnings, assessment_note,         (the words, new or reworded)
              evidence_status, evidence{why[], counts, rules_version}} (new, product page only)
```

- **The decision is never made here.** `_conclusion` decides; `compose` only chooses words for that decision. Both policies for the
  decision (live and the experimental candidate) are in `backend/recommendation_policy.py`, which is **not wired in**.
- `badge_view(product, aspects=True)` adds the evidence. Only the product-detail endpoint passes `aspects=True`; lists, cards and exports
  call `badge_view(product)` as before and pay nothing.
- A saved report with no review text, or any exception in this path, returns the plain `_conclusion` unchanged: a report is never lost
  over its explanation.

## 2. Modules

| File | Responsibility | Depends on |
|---|---|---|
| `backend/aspect_profiles.py` | **Data**: aspects per product type (cues in English, Filipino, Taglish), shared reading rules, `EVIDENCE_POLICY` | nothing |
| `backend/aspects.py` | **Extractor**: clause-by-clause reading, aggregation of distinct reviews, verbatim quotations with spans, cache | `aspect_profiles`; the standalone `text_norm.py` segmenter |
| `backend/conclusion_text.py` | **Writer**: lead, body, warnings, "Why this conclusion?", word budget, limited-evidence wording | `aspects`, `aspect_profiles` |
| `backend/recommendation_policy.py` | The live decision rules re-stated (tested equal to the live ones) and the experimental candidate | nothing |
| `backend/dashboard_utils.py` | Integration (`_ground_conclusion`, `badge_view(aspects=)`) and the generic wording used when there is no review text | the above, `category_copy` |
| `backend/webapp.py` | The detail endpoint asks for `aspects=True` | |
| `src/lib/components/report/verdict-block.svelte`, `src/lib/types.ts` | The card | |
| `scripts/sync_backend.py` | Copies from the original app without overwriting newer local work; knows the local modules | |

## 3. The extractor in detail

1. **Review gate.** Skipped, and counted: flagged duplicates, empty reviews, promotions (loan or social-media adverts), identical
   normalised text from another reviewer. Reviews are read up to 5,000 characters; longer ones are counted as truncated.
2. **Clauses.** `text_norm.segment_sentences` (the project's segmenter, loaded as one standalone file so no sentiment model is imported
   at first use) cuts at sentence ends and at contrast words (*pero, but*). A clause over 600 characters is cut at word breaks.
3. **Clause gates** (skipped and counted): menu-tag blocks, habit statements, hypotheticals and recalled fears, comparisons, sarcasm
   markers, words that contradict their own emoji. A clause that says the product has not been used yet makes no product claim.
4. **Cues.** Each aspect has praise and complaint regular expressions. Matching runs on a light fold (lower case, stretched letters cut,
   shorthand such as `d`, `hndi` to `hindi`). The project's affix-folding normaliser is deliberately not used for matching.
5. **Negation** within four words, unless used up by the next word ("no defects good packaging"), carried by "or"/"nor", ended by *pero*,
   *pro*, *but*, *kasi*. A negated praise word is a complaint; a negated complaint word is a denial, which is never counted as praise
   (authenticity excepted: "hindi naman fake").
6. **Aggregation.** A review counts once per aspect and side; if it praises and criticises the same aspect it counts for neither. Praise in
   a one- or two-star review and praise from a review that has not used the product are set aside and counted. Each claim keeps the review
   id (`comment_id`, or `review-<position>`), a verbatim slice of the review (whitespace collapsed, cut only with a final "…"), its
   `[start, end)` in the original text, a rough language label, and the star rating. No author or reviewer field is kept.
7. **Kinds.** `product` aspects drive the headline; `trust` (authenticity) is shown but is never a benefit; `service` (delivery, packaging,
   seller, freebies, condition on arrival) only decides whether the reviews talk about the product at all and never makes a product praised.
8. **Cache.** Per product in memory (256 products), keyed on the link, a digest of the reviews and `ASPECT_RULES_VERSION`.

## 4. The writer in detail

- Every headline begins "Based on customer reviews" (or "Although customer feedback is generally positive" when the reviews are mainly about
  delivery). It says "generally well received" only for the decision `recommended`, names a feature only with at least two distinct reviews, uses
  "mainly" only when the named features hold at least 60% of the praise, and never says "most" about reviews unless at least 10 reviews and half
  of those analysed support it.
- The mood is described from the real positive, neutral and negative shares (`mood_sentence`): a majority is named only when it is one, and the
  percentages add up to 100. With too few reviews no percentage is shown.
- Hazard sentences come from the existing hazard checker and are worded as reports: "N reviews describe a possible safety problem (…). These reports
  have not been independently verified; read them first." / "N reviews question whether the product is genuine." They are returned both inside
  `summary` (older readers) and on their own in `warnings` (the card sets them apart and never collapses them). The word budget (100 words) drops
  the lowest-priority sentences first and **never** the hazard or mood sentences.
- `evidence.why` is the expandable list: one line per aspect and side, with its count, quotations, and capped list of ids. Every count is reproducible
  by reading the reviews again (`evidence_verification.py` checks this for every line).

## 5. Compatibility

| Concern | How it is handled |
|---|---|
| API | New fields only (`lead`, `summary`, `body`, `warnings`, `assessment_note`, `evidence_status`, `evidence`), all optional in `src/lib/types.ts`. Existing fields keep their meaning; `summary` still contains the warnings. The decision values are unchanged. |
| Saved reports | Evidence is computed when the product page opens from the saved review text; nothing is stored or migrated; a report without review text shows the plain wording. |
| Hazard behaviour | Not touched: `backend/sentiment-analysis`, the hazard thresholds and the category classifier are unchanged (`git diff` is empty for them). |
| Backend copy / sync | `LOCAL_MODULES` in `scripts/sync_backend.py` lists the new modules; the script never overwrites a file edited locally and fails loudly if a local module is missing. |
| Cold start | No sentiment model is imported to read reviews (a test checks it). |

## 6. Extending it

- **A product type**: add a tuple of `Aspect(...)` to `PROFILES`, map the classifier's category names in `CATEGORY_PROFILE`, add a noun. No code changes. Add a real-review test before trusting it.
- **An aspect**: `Aspect(id, label, pos=..., neg=...)`. `problem` is the complaint phrase; `problem_only=True` for things with no praise side; `neg_guard` / `skip_if` for contexts that do not count; `kind` for product, trust or service. Add it to `EXAMPLES` in the tests: the integrity tests fail if an aspect does not match its own example or a pattern contains a control character.
- **A threshold**: `EVIDENCE_POLICY`. Tests read the values from it.
- **After any table change**: bump `ASPECT_RULES_VERSION`, run the tests, run `evidence_verification.py`.
- **Do not patch the tables with a script that uses `str.replace` or shell-escaped regexes.** Two silent bugs came that way (see `final_report.md`).
