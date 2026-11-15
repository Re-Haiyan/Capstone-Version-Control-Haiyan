# Aspect validation: real reviews versus constructed examples

**Bottom line.** Six of the seven product types that had never met a real review now have some real-review testing; **none is validated
for production**. Footwear and motorcycle parts have **no real reviews at all** in the project, so they stay experimental. All precision
figures below are one developer's informal judgements, taken on data that the same developer then used to fix errors. They are not
independent accuracy scores. Independent annotation is prepared (`aspect_validation_sample.csv`, `human_evaluation.md`) and not done.

## 1. The data

The project's own Lazada scans, `backups/pool-scans/search_*.json` (public reviews, scraped by the team; read here, never altered).
Nothing was invented, and no real marketplace data was written by hand. Search topics: hair shampoo, facial cleanser, lipstick,
sunscreen, whitening serum, women's dresses, bed sheet, school bag, air fryer, rice cooker, vitamins, protein powder, cat food, dog
food, baby bottle, kids' toys, building blocks.

**The saved pool (182 products) is all electronics.** The other categories came only from these scans, which carry reviews but no
verdict; for the examples, **37** scan products (21 read while developing, then 16 more never read before) were analysed by the app's own pipeline (inference only: no
model or checkpoint was changed) so that real hazard flags and sentiment shares exist for them.

## 2. Status per category

| Profile | Real reviews available | Real products read | Status |
|---|---|---|---|
| hair | shampoo only (conditioners, treatments, masks: none) | 9 products, 2,807 reviews | **Experimental.** Tested on real shampoo reviews. |
| skin | cleanser, lipstick, sunscreen, serum (no moisturiser, toner, lotion) | 25 products, 5,185 reviews | **Experimental.** Tested on real reviews; the most errors were found here, and fixed. |
| apparel | women's dresses only (the "apparel" profile also reads bags and bed sheets, which are *adjacent*, not clothing) | 8 products, 1,585 reviews | **Experimental, thin.** Only 2 products in the development half. |
| footwear | none | 0 | **Constructed examples only. Not validated.** Data needed. |
| food | protein powder and vitamins only (snacks, drinks, groceries: none) | 19 products, 4,668 reviews | **Experimental.** Supplements are not the same as food. |
| appliance | air fryer and rice cooker only | 19 products, 4,227 reviews | **Experimental.** |
| motorcycle | none: the 7 products the classifier calls "automotive" are kids' toy cars | 0 | **Constructed examples only. Not validated.** Data needed. |
| general | electronics (computer peripherals, accessories, wearables), pets, baby, toys | ~55 saved products | Used on real electronics; no category-specific claim. |
| phone, earbuds, powerbank | the saved electronics | 4+2, 60, 60 | Tested on real reviews (developer-judged). |

The product count for the profiles above excludes **15 listings the project's category classifier put in the wrong type** (see §6).

## 3. How the measuring was done, and what was read when

Products were split by a hash of their link: even = **development half**, odd = **held-out half**.

| Step | Data read | What was done |
|---|---|---|
| A | development half | Wrote round-1 additions to the tables (wrong item / wrong size / wrong colour, missing freebies, "fake promo", "yung/ung", "tastes great", mixability, white cast, "good for hair", "fregnance"). |
| B | held-out half, 70 random claims (first look) | Judged each claim. **56 of 70 correct (80%).** This is the only measurement taken before looking at the errors. |
| C | the 14 errors from step B | Wrote round-2 fixes (see §5). |
| D | held-out half, a new draw of 70 claims | **62 of 70 correct (89%).** Not independent: same judge, who had just fixed the error classes it contains. |
| E | 21 analysed real products, read as examples | Found more errors (skin irritation across "not X or Y", "acne-prone", "gentle" in a product name, "as shown", "Effectiveness:legit", a website called user-friendly, "build quality" on cheese, "long-lasting fragrance"). Fixed them. **No precision was re-measured after step E.** |
| F | **16 further real products, held-out half, not among the 21, never read before** (3 hair, 5 skin, 2 apparel, 4 appliance, 2 food), analysed by the app's pipeline; their conclusions were read by the developer | **Found a serious error:** on an anti-hair-fall shampoo, at least half of the 17 "hair fall" complaints were praise ("less hairfall", "super effective for hair fall", "helping with hair fall", "anti-hair loss"), so the conclusion said "Many reviewers reported hair fall". Fixed for **every** problem-type aspect (words that say the problem is lessened, stopped, fought or treated now count as relief), after which 9 complaints remained and the sampled ones were genuine. Also found and fixed: "hindu" (a typo for "hindi") read as itching, "for my rashes, I still use steroid cream", "some people **may** experience irritation", "natuyo" about the product drying, "non greasy" counted as greasy, and a headline that listed "defects" and "faults or failure to work" together. **No precision was re-measured after step F**, and these 16 products are now read, so they are spent as test data; the human pack uses them as its main unseen set but its claims from them were not pre-judged by the developer. |

So: **the held-out half is no longer untouched.** The honest accuracy figure for the final code on real non-electronics reviews is
**unknown**; 80% (step B) is the best uncontaminated estimate and applies to the code before the fixes. A fresh set of real
products, labelled independently, is the only way to get a clean number.

Historical, on the saved electronics: three hand-judged rounds of 100 claims gave 88, 86 and 94 correct (`precision_check.md`).
The extractor has changed a lot since (two silent bugs were found and fixed, see `final_report.md`), so those numbers describe an
earlier extractor and should not be quoted for the current one.

## 4. Coverage on real reviews (final code)

"Coverage" is the share of reviews carrying at least one product-aspect claim. It says how often the tables find something to
say, not whether what they say is right.

| Profile | Development half | Held-out half | Menu-tag clauses skipped (held-out) |
|---|---|---|---|
| hair | 18.2% (3 products) | 15.8% (6 products) | 1,131 |
| skin | 15.5% (14) | 17.8% (11) | 865 |
| apparel | 25.0% (2) | 23.4% (6) | 540 |
| food | 14.5% (12) | 12.4% (7) | 935 |
| appliance | 23.4% (9) | 21.7% (10) | 608 |

Coverage did not fall from the development half to the held-out half, so the round-1 additions were not simply fitted to the half
that was read. But coverage is low everywhere: **most of a real review's text is either a menu-tag block (skipped on purpose), a
thank-you, or a generic remark with no product feature.** The conclusion therefore explains the product from a minority of the reviews;
it says "reviewers praised…" and counts distinct reviews, and never claims to summarise all of them.

## 5. Errors found on real reviews, and what was done

| Error class (real example) | Cause | Fix | Re-measured? |
|---|---|---|---|
| "does not irritate **or** cause any breakouts" counted as irritation | negation window ended before the second item | "or"/"nor" carry the negation up to nine words | No |
| "suits sensitive and acne-prone skin" counted as irritation | bare "acne" read as a reaction | complaint forms only; guard for "acne-prone", "for sensitive skin" | No |
| "Cetaphil **Gentle** Skin Cleanser" counted as texture | "gentle" in a product name | new aspect "gentleness"; names excluded | No |
| "as shown in the video they covered the barcode" counted as matching the listing | "as shown" | removed "as shown" | No |
| "Effectiveness:legit" counted as authenticity | the answer belongs to its prompt | authenticity ignored in prompt-labelled clauses | No |
| "their website was user-friendly" counted as ease of use and as seller praise | shop website | `skip_if` for website/app/site; "user-friendly" no longer seller praise | No |
| "build quality" / "durability" on cheese, shampoo | general aspects read for food and beauty | those profiles say "overall quality" and do not read durability | No |
| "long-lasting fragrance" counted as durability | | lookahead | Yes (B→D) |
| "moisturizes and nourishes **dry hair**" counted as dryness | the hair type the product is for | guard (up to 4 words) | Yes |
| "ang laki ng tipid", "laki ng sayang" counted as size | "laki" is not always size | only "ang liit…", "malaki pala" | Yes |
| "hndi malagkit" read as a complaint | misspelt "hindi" | spelling fold | Yes |
| "di pa nagagamit" ("not used yet") read as "does not work" | negation of "nagagamit" | not-yet-used skips product aspects in the clause | Yes |
| "Reduces acne" counted as a complaint | | relief words (reduces, controls, treats…) | Yes |
| "not exactly gamot **pro** nakakatulong" read as "does not help" | "pro" is "pero" | "pro" ends a negation | Yes |
| a damaged **box** counted as the product failing | "sira" next to a box word | guard on functionality | Yes |
| "not as effective as this" counted as a complaint | comparison without "than" | "as X as" is a comparison | Yes |
| "smoothening the frizzy, dry hair" counted as dryness | the problem it fixes | frizz guarded; **dryness not** | **Open** |
| "less hairfall", "effective for hair fall", "anti-hair loss" counted as hair-fall complaints (anti-hair-fall shampoo) | a product whose purpose is the problem names it in praise | relief words (less, fewer, anti, helps, improves, stops, effective for, good for, works for …) before any problem cue; hair fall now needs an occurrence cue or a Filipino complaint form | Spot-checked (9 complaints left, sampled ones genuine); not precision-measured |
| "hindu nangangati" (typo of "hindi") counted as itching | typo | spelling fold | No |
| "for my rashes, I still use steroid cream" counted as a reaction | names the problem the buyer already had | guard | No |
| "some people may experience irritation" counted as experienced | a warning, not an experience | "may / might / could" as hypothetical | No |
| "pag natuyo … white stain" counted as dryness | "natuyo" about the product | counts only beside hair, skin or lips | No |
| "non greasy" counted as greasy | | guard (and a later patch had replaced the guard: guards now join) | No |
| Headline "…defects, doubts about authenticity **and** faults or failure to work **and** items that differ…" | redundant, ungrammatical | an aspect that duplicates "defects" is dropped; at most three reasons | Yes (test) |
| Headline "some reviewers report X" when X has one report | an uncounted quantity word | "the reviews include reports of X" | Yes (test) |
| "hindi umiinit ang taas ng unit" (the top does not get hot: praise) counted as a performance complaint | negated "heats" in appliances | none | **Open** |
| "mas lalo akong gumagana kumain" ("I'm more motivated to eat") counted as "it works" | "gumagana" about a person | none | **Open** |
| "…, low noise" in a lowercase tag list counted as praise | menu list without capitals | none | **Open** |
| "I only ever buy…" statements about the shopper | | habit rule | Yes (electronics) |

## 6. The category classifier disagrees with the scans

For validation, a scan's search topic is taken as what the product *is*. Where the project's listing classifier
(`product_category.py`, not changed) disagrees, the product is left out of that profile's figures and listed in
`aspect_validation_real.json` under `classifier_disagreements`: **15 listings**, e.g. three lipsticks classified as `kitchen_dining`,
five protein powders as `other`, two serums as `health_supplements`, a shampoo as `household_cleaning`, and the seven toy cars as
`automotive` ("motorcycle parts"). **A product put in the wrong type is read with the wrong aspect table**; the general aspects still
apply, so the conclusion is generic but not absurd. Improving the classifier is outside this work (changing it could change hazard
behaviour, which needs its own validation) and is a recommendation in `final_report.md`.

## 7. What each Filipino / Taglish / English challenge is tested with

Every challenge in the brief has a unit test with constructed sentences (`tests/test_product_conclusion.py`: negation in Filipino and
English, Taglish, mixed opinions in one review, comparisons, hypotheticals and recalled fears, sarcasm and emoji contradiction,
contradictory experiences of one aspect, packaging versus product, delivery-only reviews, not-yet-used). In addition,
`test_every_error_found_on_real_reviews_stays_fixed` keeps the real sentences that were once misread as regression inputs.
**Constructed tests show that a rule does what its author meant; they do not show that the rule is right on real reviews.** Only the
sections above do that, and only for the categories that have real data.

## 8. Data needed before any category can be approved for production

| Profile | Needed |
|---|---|
| footwear | any real shoe reviews (a scan of 10 or more listings) |
| motorcycle parts | real motorcycle-part listings (helmets, brake pads, tyres, oil); the project has none |
| food | snacks, drinks and groceries (not supplements) |
| hair, skin | conditioners, treatments, moisturisers, toners, lotions |
| apparel | shirts, pants, shoes-adjacent items; not bags or bed sheets |
| appliance | fans, kettles, blenders, irons and so on, not only air fryers and rice cookers |
| all | **a fresh set not read by the developer**, about 20 listings per category with at least 100 reviews each, then two independent annotators judging about 100 claims per category (`aspect_validation_sample.csv` has the format) |

The sizes in the last row are a proposal, not a derived sample size. With 100 judged claims per category the 95% interval around an
observed 90% is about ±6 points; for a smaller claim of "≥ 85%" more are needed.
