# Annotation pool: 3,863 reviews for training the model

**Files**
- `label_train_part1.csv` ... `part4.csv` – 1,971 reviews for TRAINING (about 490 each). One person labels each part. Split them across the team.
- `label_test_set.csv` – 539 reviews for the final TEST. Each of these must be labelled by **two people, independently** (two separate copies). Never let a test row be seen by whoever tunes the model.
- `keep-separate-key/` – category, group, how each review was picked and which split it belongs to. **Do not open it while labelling.**

**Added in round 2 (expansion)**
- `label_train_part5.csv`, `part6`, `part7` – 1,095 more TRAINING rows (about 365 each): reviews of gadgets with fire, burn, overheating or fake words, more non-gadget hazard and fake words, and wrong / missing / size / material mismatches. These fill the labels that had too few examples (safety, counterfeit, not as advertised).
- `label_test_set_part2.csv` – 258 more TEST rows, same rule as the first test file: two people, independently.
- In total: 3,863 rows (3,066 train + 797 test). Gadget reviews are included now: for them, `safety` also covers overheating beside the battery or charger, a burning smell and swelling.

**Priority if time is short:** label the test files first (two people), then `part5` to `part7` (they hold the rare labels), then `part1` to `part4`.

**Same columns and rules as before:** fill `sentiment` (positive, neutral, negative), `flags` (defect, counterfeit, safety, not_as_described, quality joined with `;`, or `none`) and `confidence` (high, or low when unsure). Do not edit `id`, `product` or `review_text`. Save each file under a new name (for example `annotated_train_part1.csv`).

**What is in the pool**
- About a fifth was picked because it has a fake, hazard or health word (rash, expired, burn, sharp, fake...), about a third because it has a complaint word, and the rest at random. So expect many positives, especially in the first two groups. That is on purpose: it is how the rare labels get enough examples.
- Products: 226 products across home, beauty, fashion, pets, baby and toys, food, car and tools, sports. Test-set products never appear in the training files.

**The labelling rules (the guide below is unchanged)**

---

## What each flag means

Label what the reviewer reports **about the product itself**. Do not flag the courier, the packaging, the seller's replies or a refund dispute.

- **defect** – it does not work, stopped working, arrived broken, leaks, is torn, the seal is broken, a code does not work.
- **quality** – it works, but is weak, flimsy, thin, rough, fades, wobbles, or looks cheap. A complaint about how well it is made.
- **counterfeit** – the reviewer says it is a fake, a copy or not the original brand. "I thought it was fake at first" is **not** a report. A product that is simply named "Replica" is not a report either.
- **not_as_described** – size, colour, material, amount, flavour, features or the number of items differ from the listing ("not cotton", "buy 1 take 1 but only one came", "too small for the size stated").
- **safety** – a hazard to a person, pet or home. It depends on the product:
  - gadgets and appliances: fire, smoke, burns, shocks, a burning smell, overheating beside the motor or plug
  - skin and hair products: rash, itching, burning, an allergic reaction
  - food and supplements: spoiled or expired, insects, an upset stomach, illness
  - baby, toys, home, sports: choking, a sharp edge, collapse, injury
  - motorcycle parts and tools: brakes failing, a part breaking loose, a cracked helmet

  Heat that is the **weather** ("ang init ngayon") or the **job of the product** (a hair straightener or a pan heating up) is **not** safety.

## Rules that decide most doubtful cases

1. **Praise and denials are not reports.** "Doesn't feel flimsy", "no rash", "hindi mukhang mumurahin", "not noisy" mean the opposite of the flag.
2. **Report what happened, not a worry.** "Baka masira" (it might break) is not a defect. "Umiinit habang nagchacharge, nakakatakot" (it heats while charging, scary) **is** a safety report.
3. **One review can have several flags**, and a 5-star review can still carry one ("love it, but the zipper broke" is `defect`).
4. **Thin is only a complaint when the reviewer treats it as one.** "Sakto lang ang nipis" (just right) is not `quality`; "sobrang nipis ng tela" is.
5. When you cannot decide, mark `confidence` as `low`. A skipped row costs nothing; a wrong label costs a wrong score.

