# Instructions for annotators

You are helping to check whether an automatic summary of customer reviews is correct. **Work alone. Do not discuss your answers with the other annotator
and do not ask the developers what the system "should" say.** There are no right answers to guess: write what the reviews show. If you are unsure, say so in
`confidence` or `unclear`; that is useful information, not a failure.

Files: `reviews.csv` (every review of every product: stars and text; phone numbers, e-mail addresses, links and handles that people typed into reviews were removed and show as
"[number removed]" and so on), then three sheets, **to be done in this order**:
1. `card_sheet_?.csv`: read the reviews and give your own overall assessment. (No system output is on this sheet.)
2. `claims_sheet_?.csv`: judge each claim. (Only the claim and its quotation are shown.)
3. `words_sheet_?.csv`: rate two anonymous texts. (Do this last: it shows the system's assessment label.)
Use the sheet letter you were given (A or B). Do not open `key_private.csv`.

## 1. Card sheet: your own overall assessment

Choose one for `assessment`, from the reviews alone:

| Assessment | Choose it when |
|---|---|
| Well reviewed | reviews are overwhelmingly positive about the product; problems are isolated and minor; nothing a buyer needs warning about |
| Mixed reviews | a real share of positive and of negative reviews; no single serious recurring problem dominates |
| Some concerns | mostly positive or mixed, but a specific problem recurs across several reviews (a defect, doubts that it is genuine, a credible hazard report) that a buyer should weigh |
| Not recommended | mostly negative, or credible repeated reports of a hazard or of a fake product |
| Too few reviews | too few, too repetitive, too unclear, or about the delivery only: not enough to form a view of the product |

`serious_safety_concern`: yes if reviewers credibly report a risk of injury, fire, shock, a skin reaction or sickness; else no. `counterfeit_concern`: yes if several
reviewers say it is fake or not the original; else no. `main_reason`: a few words. `confidence`: high, medium or low.

## 2. Claims sheet: is the claim right?

Each row is "this review says something about <aspect> (<positive or negative>)", with the words quoted. Read the quotation (and the review, `review_no`
in `reviews.csv`, if you need the context) and write one `label`:

| label | meaning | example (invented here for illustration only) |
|---|---|---|
| correct | the quotation says this about the product, in this direction | aspect "softness", positive, "ang lambot ng buhok ko" |
| wrong_aspect | it is about something else | aspect "durability", "long-lasting fragrance" |
| wrong_direction | it says the opposite | aspect "dryness", negative, "hindi nakakadry" |
| not_about_the_product | it is about the shop, the courier, the packaging, or the buyer | aspect "ease of use", "their website was user-friendly" |
| unclear | you cannot tell | |

## 3. Words sheet: rate two texts

Read the reviews again. Text 1 and text 2 are two summaries of the same product, in random order. Rate **each** on seven dimensions, 1 (worst) to 5 (best):

| Dimension | 1 means | 5 means |
|---|---|---|
| factual | a number or plain fact is wrong (how many reviews, what share was positive) | all check out |
| faithful | something is invented or not in the reviews | everything is supported |
| relevant | generic, could be about any product | specific to what reviewers said about this product |
| sentiment | the mood is misdescribed (for example "mostly negative" for a mostly neutral product) | accurate |
| safety | a safety or fake-product report is hidden or overstated, or presented as verified | handled as unverified customer reports |
| clear | confusing | easy for an ordinary shopper on a phone |
| recommendation | the assessment shown is clearly wrong for these reviews | right |

Also: `unsupported_?` yes if the text says anything the reviews do not support; `safety_error_?` yes if it hides, invents, overstates or claims to have verified a safety or authenticity matter;
`preferred` 1, 2 or same.

### What a correct, a partly supported and an unsupported statement look like (invented illustration)
Reviews: of 100, 14 say the shampoo made their hair soft, 3 say it dried their hair, 40 only talk about delivery.
- **Supported**: "Several reviewers said it left their hair soft; a few mentioned dryness." (14 and 3 are real counts.)
- **Partly supported**: "Customers love it for softer, healthier hair." ("love" and "healthier" go beyond "soft"; "customers" suggests all.)
- **Unsupported**: "It promotes hair growth." (no review says so.)
