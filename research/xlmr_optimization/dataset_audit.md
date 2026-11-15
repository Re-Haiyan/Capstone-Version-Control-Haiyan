# Dataset audit

Source: `results/inventory.json` (script `inventory.py`, which also restores FiReCS from git commit `5ea027e` and checks its published hashes). Counts are rows of each file; "scored" rows are the high-confidence rows. **Marketplace labels are team-supplied and of unverified provenance** (`research/annotation_provenance.md`): they are not human gold.

## 1. Inventory

| Set | File SHA-256 (first 12) | Rows | Label shares (neg / neu / pos), high-confidence rows | Duplicate texts inside | Products | Mean words | Evidence class |
|---|---|---:|---|---:|---:|---:|---|
| FiReCS train | `9ca5ef80b8f9` | 7,340 | 0.324 / 0.347 / 0.328 | 2 | n/a | 26.3 | published, authors' labels |
| FiReCS test | `6c172b8a52ad` | 3,147 | 0.326 / 0.345 / 0.328 | 0 | n/a | 26.3 | published, authors' labels |
| market `train_v3` | `eb17e1abf09b` | 4,268 (3,946 high) | 0.305 / **0.183** / 0.511 | **352** | 305 | 25.1 | team labels, development |
| market `test_v3` | `723f68c21ade` | 886 (846 high) | 0.284 / 0.226 / 0.491 | 56 | 82 | 23.6 | team labels, **historical benchmark** (inspected) |
| market `fresh` | `4cc90bcef2ab` | 310 (293 high) | 0.150 / 0.085 / 0.765 | 36 | 69 | 23.5 | team labels, **not independent (see 3)** |
| market `fresh2` | `04c490d88654` | 270 (253 high) | 0.245 / 0.063 / 0.692 | 21 | 75 | 21.9 | team labels, **not independent** |
| `gold_labels_200` | `756d22255eec` | 200 (150 high) | 0.420 / 0.240 / 0.340 | 0 | no product field | 21.3 | team labels (older), name says "gold" but provenance unverified |
| `heldout_labels_100` | `49e243ab0f33` | 100 (76 high) | 0.474 / 0.132 / 0.395 | 0 | no product field | 20.1 | team labels (older) |

## 2. Class distribution and imbalance

* FiReCS is **balanced** (a third each). Marketplace data is **neutral-poor** (6% to 23% neutral) and positive-heavy, and the files differ from one another by a factor of three in neutral share. A model tuned to FiReCS learns a neutral prior of one third; marketplace reviews are far less often neutral under the team's labelling, so FiReCS-trained neutral predictions are a likely source of the neutral-class failure (`error_analysis.md`).
* The manifest of the `sentiment-blend` branch states that its combined dataset maps `mixed` to `neutral` "(FiReCS convention)". If that is right, FiReCS "neutral" mixes neutral and mixed opinions. I did not verify this against the FiReCS paper; it is a hypothesis to check, and it matters for any neutral comparison.

## 3. Leakage, duplicates and overlap

* **Exact duplicates.** FiReCS: 4 texts are in both train and test, 2 duplicates inside train. Marketplace: `train_v3` has 352 duplicated texts (8.3%) and `test_v3` 56 (6.3%), mostly listing boilerplate (for instance the same baby-bottle feature lines repeated); these inflate any score by counting one text several times.
* **Near duplicates** (character TF-IDF cosine 0.9 or more): FiReCS test against FiReCS train 10 of 3,147 (7 at 0.95); `test_v3` against `train_v3` 1 of 886; `test_v3` against FiReCS train 0.
* **The "fresh" sets are not fresh.** 201 of `fresh`'s texts and 208 of `fresh2`'s are also in `train_v3`; 226 of `fresh`'s 310 rows have a near duplicate (cosine at least 0.95) in `train_v3`; they share 51 and 62 products with it. They were used as clean tests, then folded into training after their misses were read. They must not be reported as independent evidence.
* **Products across splits.** `train_v3` and `test_v3` share **no product** (checked by exact title). `test_v3` shares 18 products with `fresh` and 13 with `fresh2`; because `fresh` rows are in `train_v3`, parts of those products were seen in training.
* **Prior inspection.** The 846-row `test_v3` was inspected during development (rules were tuned after reading related errors; the sentiment recalibrator was evaluated on it). It is a **historical benchmark**: any score on it is optimistic about generalisation and no fresh claim can rest on it. FiReCS test was used for the original model gate ("FiReCS test macro F1 >= incumbent"), so it was also used for selection of the shipped model.
* **Possible inflation of the reported FiReCS score:** a small effect (4 shared texts, 10 near duplicates of 3,147 is 0.3%) but the selection on the test file is a larger caveat.

## 4. Representativeness of what exists

* The production database (396 products, 71,690 reviews, 2026-11-14 backup) is **85% electronics** (Lazada electronics 265 of 325 products; Shopee 45 of 64). Category coverage in the labelled files is wider (beauty, home, fashion, food, baby, pets, automotive), but their labels are unverified.
* After excluding every product whose title appears in a team-labelled file, only **150 products, about 860 reviews** of the production database remain, and 94% of them are electronics. Home and living: 38 products, fashion 6 (none in one half), beauty, food and automotive: **none**.

## 5. The fresh product-disjoint sampling plan (built, frozen, unlabelled)

`build_annotation_sheets.py` wrote `annotation/` from a copy of the production database (read only): a **frozen final test** of 400 reviews (73 products: electronics 375, home and living 19, fashion 6; Lazada 297, Shopee 85, Temu 18; star groups 1 to 2: 52, 3: 24, 4: 26, 5: 298), a **dev pool** of 400 reviews of 76 different products, and a private id map with sampling weights. A product is on exactly one side (hash of its link), a text appears once, at most 6 reviews per product. The frozen list's SHA-256 and the sheets' hashes are in `annotation/frozen_final_test.json` (frozen 2026-11-14T22:56:49Z, **before any model of this study was chosen**).

**Limits, stated plainly:** the quotas for home, fashion, beauty, food and automotive could not be met (241 of 400 test reviews were filled outside the quota, all from electronics); the category labels are the app's own heuristic classifier's (it files a CPU under "home_living"); the language hint is a word-list heuristic; collection dates were not stored in the database rows used. A representative test needs a **new scan** of non-electronics products, which this study did not perform.

## 6. Language

`metrics_x.lang_of` is a stop-word heuristic (Filipino, English, Taglish, unknown). In `test_v3` it gives English 424, Filipino 161, Taglish 167, unknown 89 reviews; subgroup results are reported but are heuristic subgroups.
