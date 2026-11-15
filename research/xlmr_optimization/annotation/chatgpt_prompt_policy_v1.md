# Prompt for the ChatGPT-assisted annotation of sentiment (policy v1)

Use the same prompt, unchanged, for every batch; record the exact ChatGPT model and version, the date, and whether you used a fresh conversation per batch in `annotation/ai_annotation_log.csv` (done by `import_ai_annotations.py`). Paste this text first, then one batch file (`annotation/chatgpt_batches/*.csv`: columns id, product, language_hint, review_text; **no star ratings, no model predictions, no earlier labels are included**).

---

You are annotating marketplace product reviews (English, Filipino, Taglish) for a sentiment study. Judge **the review text only**, in the context of the product title. Label every row. Return ONLY a CSV (UTF-8, header included) with exactly these columns:

`id,sentiment,tags,positive_aspect,negative_aspect,confidence,rationale`

Keep each `id` exactly as given. Do not return the review text. Do not skip rows.

**sentiment**: one of `positive`, `neutral`, `negative`, `mixed`, `unclear`.
- `positive`: the reviewer clearly evaluates the product or purchase favourably and the favourable side dominates, expressed as their own experience or judgment.
- `negative`: clearly unfavourable and dominates; a report that something broke, is fake, is wrong or is unsafe is negative.
- `neutral`: no clear positive or negative evaluation: facts, a description or feature list without the reviewer's own experience or judgment, "not yet used / will update", a question, a standalone lukewarm "okay lang / so-so / pwede na".
- `mixed`: two clear opposite evaluations and neither dominates. If one side clearly dominates, use that polarity in `sentiment` and add the tag `mixed`.
- `unclear`: a person cannot decide from the text.

**tags**: zero or more of `mixed`, `delivery-only`, `no-opinion`, joined with `;`, or empty.
- `delivery-only`: the review is only about delivery, packing, the rider or the seller (label the feeling it states).
- `no-opinion`: facts or a feature list with no expressed opinion, or "not yet used"; the sentiment must be `neutral` or `unclear`.
- `mixed`: required whenever the review contains both a clear positive and a clear negative evaluation; then `positive_aspect` and `negative_aspect` must both be filled (a few words each). `neutral` together with `mixed` is not allowed.

**confidence**: `high` or `low`. **rationale**: a few words.

Rules: the star rating is not given and must not be guessed; a five-star review is not proof of a positive review. Sarcasm: label the intended opinion. Negation by meaning. Emojis count only when they carry an explicit opinion. Do not label a mixed review neutral. A list of product claims copied from a listing, with no experience, is `neutral` with the tag `no-opinion`.

---

(Policy v1 hash: see `annotation/policy_v1.lock.json`. The proposed clarifications of `phase2/policy_s4_recommendation.md` are NOT in this prompt; they would be added only after the adviser confirms v1.1, as a new prompt file with its own hash.)
