# Labelling the non-gadget batch

**Files**
- `label_batch_nongadget.csv` – 289 reviews of non-gadget products (clothes, bags, beauty, food, home, motorcycle parts, sports, stationery). You fill the three empty columns.
- `label_batch_nongadget_key.csv` – category, source and split of each row. **Do not open it while labelling.** It says how each review was picked, and that can steer your judgement.

**Columns you fill**

| column | values |
|---|---|
| `sentiment` | `positive`, `neutral` or `negative` – the reviewer's overall feeling about the product |
| `flags` | one or more of `defect`, `counterfeit`, `safety`, `not_as_described`, `quality`, joined with `;` (for example `defect;not_as_described`), or `none` |
| `confidence` | `high` when you are sure, `low` when the review is unclear. Only `high` rows are scored. |

The product title is in the `product` column. **Read it first**: the same words mean different things on different products.

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

## Keeping the test honest

- Every row is marked `dev` or `test` in the key. **Change rules only because of `dev` rows.** The `test` rows are kept back to say how well the rules work on reviews they were not tuned on.
- If two people label, label **independently**, then compare. Report how often you agree before settling the differences; that agreement is worth a line in the paper.
- Do not edit `review_text`, `product` or `id`.

## Scoring it

```
backend/.venv/Scripts/python.exe evaluation/score_nongadget.py evaluation/label_batch_nongadget.csv --split dev
backend/.venv/Scripts/python.exe evaluation/score_nongadget.py evaluation/label_batch_nongadget.csv --split test
backend/.venv/Scripts/python.exe evaluation/score_nongadget.py evaluation/label_batch_nongadget.csv --no-category   # old behaviour, for comparison
```

A label with fewer than 5 true positives in a group is marked in the output: its score is too noisy to quote.

## What this batch can and cannot tell you

- The reviews come from only **48 products** (food 3, sports 1, stationery 1). Reviews of one product resemble each other, so the scores say how the rules behave on these products, not on every product in a category.
- About a third of the rows were picked because they contain a complaint or hazard word, so that rare labels have positives. The rest are random. The `source` column in the key lets you score the two parts separately.
- Rare hazards (choking, spoiled food, brakes) will still have few positives. For those, scan more products before quoting a number.
