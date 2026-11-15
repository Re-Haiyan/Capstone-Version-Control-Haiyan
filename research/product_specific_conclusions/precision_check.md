# Claim-level precision check (developer, informal) — HISTORICAL

> **Historical.** These three rounds describe the extractor as it was on the saved ELECTRONICS before the later work. Since then two silent
> bugs were found and fixed (patterns that never matched, a letter-collapse that never worked), the tables grew, and more rules were added, so
> **the figures below must not be quoted for the current extractor.** The current record, including real non-electronics reviews, is
> `aspect_validation.md`; the all-claims mechanical check is `evidence_verification.md`.

**What this is.** A check of whether the aspect claims on the card (for example "battery life: 3 reviews concerning")
point at review text that really says that. It is **not** an independent evaluation and **not** a score for the
sentiment model or the hazard checker.

**Who judged.** One person, the developer who wrote and tuned the rules. The first two rounds shaped the fixes, so the
numbers can only be read as optimistic; the third round is fresh claims, but the same judge and the same pool.
An independent judgement is what `human_evaluation.md` asks for. Nothing below should be quoted as a validated accuracy.

**How.** Every claim carries a real quotation from a real review (`before_after.py` confirms that all 3,509 quotations
on the 182 saved products appear verbatim in their reviews, at the stated position). For each round, 100 claims were
drawn at random from all quotations shown on the saved products and each was judged "does this quotation support this
aspect and this direction?".

| Round | Code state | Draw | Correct | Wrong |
|---|---|---|---|---|
| 1 | first working version, before any fix | seed 23 (and an earlier read of 70) | 88 | 12 |
| 2 | after menu-tag, "legit", hedge, habit and promotion rules | seed 31 | 86 | 14 |
| 3 | after tag-block, "legit", hedge and negation-scope rules | seed 47 | 94 | 6 |

Round 2 did not improve on round 1 because the first fix attempt silently failed to apply three of its patterns (found
and corrected before round 3: a Python `replace` that matches nothing does not raise). The lesson is recorded in the
tests: the patterns that matter are now asserted by name (`test_filipino_and_taglish_negation`,
`test_menu_tag_blocks_are_not_endorsements`).

## Error classes that remain (round 3, 6 wrong of 100)

| Class | Example (real quotation) | Why it is wrong |
|---|---|---|
| A word with a second meaning | "…but the original color is dark gray" read as *authenticity* | "original" can describe a colour or a version (the pattern now excludes colour, size, version, model; a new instance can still occur) |
| "legit" as praise of a shop | "…order again in this shop napaka legit.." read as *authenticity* of the product | the seller is not the product; some forms are excluded, not all |
| Marketing words | "…anyone prioritizing premium audio and silence" read as *build quality* | "premium" is a build cue in the table but is often advertising language |
| Negation across clauses without punctuation | a seller complaint where a negative word several words back flips a positive cue | negation is read within four words; a longer run of words is not understood |
| Expectation, not experience | "wag rin mag expect ng maganda sound" read as praise | now caught by the hedge list (`expect…`); other phrasings of an expectation exist |
| A neighbouring feature | "ket alam nila sira ipapadala nila yan" read as *durability* | a complaint about the seller shipping a broken item, not about how long it lasts |

Earlier rounds also found, and the rules now handle: tag blocks pasted from the marketplace menu (with and without full
stops), prompt labels such as "Value for money:" read as a claim, "long lasting battery" read as durability, "I only ever
buy affordable smartwatches" read as praise of value, a loan advertisement left as a review, "Anker delivers good quality"
read as delivery, "legit na fast delivery" read as authenticity, and negation leaking across "no defects good packaging".

## What this check cannot say

- It says nothing about **recall**: claims the rules never made (a reviewer who praised battery life in words no table
  contains) are invisible here. The conclusion therefore under-reports; it should never over-report a count, but it may
  leave a real complaint out of the list. The safety and counterfeit sentences come from the existing hazard checker, not
  from these tables, so a missing aspect does not hide a hazard.
- It covers **electronics only**. The saved pool holds earbuds, chargers, power banks, mice and similar. The hair, skin,
  apparel, footwear, food, appliance and motorcycle profiles have been exercised only by unit tests and the constructed
  review sets in `examples.md`. Their precision on real reviews is unknown.
- It is one judge. Use `text_rating.py` and two independent annotators before quoting any accuracy figure in the thesis.
