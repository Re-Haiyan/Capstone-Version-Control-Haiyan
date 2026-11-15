# Evaluation dataset specification: categories without real reviews

**No customer review in this folder was invented, and none may be.** This is the specification for collecting the real data that the
categories below still need before they can be called validated. Until that data exists they stay **experimental**: their aspect tables
are exercised only by constructed sentences in unit tests, which show that a rule does what its author meant and nothing about whether
it is right on real reviews.

## Current status by category (checked against the product titles, not only the classifier)

| Profile | Real reviews in the project | What the titles actually are | Status |
|---|---|---|---|
| footwear | **none** | no shoe listing in any scan | experimental, constructed tests only |
| motorcycle parts | **none** | the 7 listings the classifier calls `automotive` are kids' electric ride-on cars and RC toy cars (e.g. "Electric Car For Kids Ride On Jeep", "RC Car 2.4G Off-Road"); they are **toys, not motorcycle parts**, and are excluded | experimental, constructed tests only |
| hair | shampoo only | shampoos (Palmolive, Ginger shampoo, Hosoku …) | experimental; conditioners, masks, treatments unseen |
| skin | cleanser, lipstick, sunscreen, serum | Cetaphil cleansers, matte lipsticks, sunscreens, whitening serums | experimental; moisturisers, toners, lotions unseen |
| apparel | women's dresses only | maxi dresses | experimental; shirts, pants unseen. The profile also reads bags and bed sheets, which are not clothing |
| food | protein powder, vitamins | whey protein, mass gainers, gummies, ACV capsules | experimental; supplements are not snacks, drinks or groceries |
| appliance | air fryer, rice cooker | air fryers, rice cookers, a hot-pot cooker | experimental; fans, kettles, blenders, irons unseen |

The 15 listings the category classifier put in the wrong type (lipsticks as kitchenware, protein powders as `other`, serums as supplements, a
shampoo as household cleaning) are listed in `aspect_validation_real.json`. **Every sample for evaluation must have its category confirmed from
the listing title and description by a person**, not taken from the classifier.

## What to collect, per category

| Item | Requirement |
|---|---|
| Listings | at least **20 distinct listings** per category, from at least 5 different brands or sellers, public Lazada PH pages |
| Reviews | at least **100 written reviews per listing** (the app's own sampler: up to 300, star-stratified); keep stars, text, date, and the review id; **drop reviewer names** |
| Footwear | sneakers, sandals, school shoes, work boots, slippers (the aspects that matter: comfort, fit and sizing, material, sole, durability) |
| Motorcycle parts | helmets, brake pads, tyres, engine oil, chains, mirrors, phone holders; **confirm each is a motorcycle part by reading the listing** (a toy motorcycle is a toy) |
| Hair | conditioners, hair masks, treatments, hair serums (shampoo is covered) |
| Skin | moisturisers, toners, face masks, lotions, soaps (cleanser, lipstick, sunscreen, serum are covered) |
| Apparel | shirts, pants, shorts, jackets, school uniforms (dresses are covered) |
| Food | snacks, noodles, coffee, drinks, canned goods, sweets (supplements are covered) |
| Appliance | electric fans, kettles, blenders, irons, rice-cooker accessories, hair dryers |
| Language | Filipino and Taglish must be present: record the share of reviews that are not English (the pack's `filipino_or_taglish_share` is the model) |
| Hazard pictures | at least some listings with reported hazards (skin reactions, spoiled food, overheating) and with authenticity complaints, so the safety handling is tested, not only the easy products |

## How the data must be kept and used

1. **Split before looking.** Choose the evaluation listings *first*, by a fixed rule (for example a hash of the link, as `aspect_validation.py` does), and **do not read their reviews while editing the aspect tables**. The developer-used data of this project (the 21 products in `real_examples.md` and the development half) is spent; it cannot be used as test data.
2. **Analyse with the app's own pipeline** (`analyse_real_nongadget.py` is the model) so each product has its real hazard flags and sentiment shares.
3. **Two independent annotators** judge about **100 claims per category** (`claims_sheet`) and the overall card for at least 30 products across categories (`card_sheet`), blind, using `human_eval_pack/INSTRUCTIONS.md`.
4. **Report** per category: the number of claims judged, correct claims, the 95% Wilson interval, Cohen's kappa between the annotators. With 100 claims an observed 90% has an interval of about 83 to 94%; to show "at least 85%" with confidence, more claims are needed. These sample sizes are proposals, not derived requirements.
5. **A category passes only if** its interval's lower end meets a bar the team sets in advance (suggested: 85% precision on claims, no safety-related error in the words sheet), and the annotators agree (kappa of at least 0.6). Write the bar down before the annotation.
6. A category that does not pass ships with reasons off or labelled experimental (the off-switch is global; a per-category list is a small change if wanted).

## Not allowed

Writing reviews, paraphrasing real ones, using an AI to generate "realistic" reviews for evaluation, balancing a sample by editing it, or removing hard cases. Constructed sentences are for unit tests only and are labelled as such wherever they appear.
