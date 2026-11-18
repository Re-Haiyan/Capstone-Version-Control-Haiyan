# DeFaketive — fresh multicategory evaluation (research only)

**Status: tooling ready; no new reviews or human labels have been supplied.** The production system remains at `147eccbfcf206b37550ce9e8b0a71bba626dacc3` (pc7, context v2); **automatic sentiment correction stays OFF**.

## Why this evaluation comes next

- The currently deployed read-only contextual check covers **49 product categories and 10 subtypes**, but it rarely finds explicit phrases. A historical 800-review diagnostic matched only three positive/negative examples and disagreed with XLM-R once. This is **not** independently measured accuracy.
- The pre-existing proposed "fresh" set is **gadget-only** (89 unseen gadget products; proposed 712 representative reviews). It cannot validate category interpretation on clothing, food, appliances, health products and other non-gadget groups.
- Earlier 846-review and 3,946-row labelled datasets have uncertain annotation provenance and have already been inspected for model tuning. They are **not** a new untouched holdout.

## Phase 1 — independent human pilot (next actual task)

1. Obtain rights-cleared review text from **new marketplace products** with stable product IDs, and verify by a person that the products were not used in model training, annotation, previous evaluations or current VM saved analyses. Use a random selection of reviews per listing; do not use model predictions to select them. Collect from all 11 groups if possible, with extra attention to non-gadgets and English, Filipino and Taglish.
2. Keep an **input CSV local**, not in GitHub. Each row requires these columns:

   | Column | Example/requirements |
   |---|---|
   | `marketplace` | `shopee` or `lazada` |
   | `product_id`, `review_id` | Stable marketplace identifiers |
   | `product` | Product listing title needed to interpret reviews |
   | `category` | One manually verified slug from the shipped 49 categories |
   | `review_text` | Original review text (12–5000 normalized characters); do not include personal data |
   | `stars` | Integer 1–5 (metadata, not a label) |
   | `collected_at` | ISO `YYYY-MM-DD`, actual collection date |
   | `rights_confirmed` | `yes` only when collection/use is authorized |
   | `new_product_verified` | `yes` after manually checking products/listing variants |
   | `category_verified` | `yes` after manual category verification |
   | `selection_method` | `random` (NOT model disagreement or keyword-selected) |

3. Run from an isolated local/VM checkout of this **research** branch. Prefer checking the production saved-products SQLite database in read-only mode, in addition to all `evaluation/**/*.csv` files:

   ```bash
   python research/fresh_multicategory_intake.py prepare \
     --input /private/new_marketplace_reviews.csv \
     --known-extra /private/copy_of_production_saved_products.db \
     --out-dir research/independent_eval_private/pilot1 \
     --target 220 --min-groups 8 --min-products 44 \
     --model-sha 147eccbfcf206b37550ce9e8b0a71bba626dacc3
   ```

   `--known-extra` accepts a read-only `*.db`/`*.sqlite` saved-product database containing `products.raw_json` **or** a CSV of existing product titles. It is optional for exploring data but REQUIRED before calling the corpus product-disjoint from the **live saved catalog**. Confirm historical title variants manually: exact normalized matches cannot catch every relisted product.

4. The script checks rights, manual category verification, historical title/text overlap, duplicate IDs/text, dangerous spreadsheet-formula prefixes, sampling method, group coverage and distinct-product coverage. If there are insufficient eligible reviews or groups, it **stops rather than inventing reviews**.
5. Give `annotator_A.csv` to one researcher and `annotator_B.csv` to another. Sheets contain the same review texts in different orders with blank `sentiment`, `flags` and `confidence` columns. **Do not give either researcher `PRIVATE_manifest.csv`, model outputs or past labels.** No AI annotation in this independent test.
6. Use **the same approved annotation policy** for both. The repository's v2 remains a proposal: v1 is the default unless the owners explicitly approve a newer version. Follow `research/agreement/GUIDE.md` for sentiment and six binary concerns, including delivery.
7. Save completed sheets separately, then validate each against the original:

   ```bash
   python research/agreement.py check \
     research/independent_eval_private/pilot1/annotator_A_done.csv \
     research/independent_eval_private/pilot1/annotator_A.csv \
     --annotator=TeamLabel1 --policy=v1
   python research/agreement.py check \
     research/independent_eval_private/pilot1/annotator_B_done.csv \
     research/independent_eval_private/pilot1/annotator_B.csv \
     --annotator=TeamLabel2 --policy=v1
   python research/agreement.py score \
     research/independent_eval_private/pilot1/annotator_A_done.csv \
     research/independent_eval_private/pilot1/annotator_B_done.csv
   ```

   Record timestamps, annotator IDs and sheet hashes privately. Score human inter-annotator agreement, then use a third person to adjudicate every disagreement **without seeing model predictions**. Freeze the adjudicated reference before scoring model output. A missing annotation is not a neutral or negative label.

## Phase 2 — scale to final holdout

- Expand with new, product-disjoint listings across all **11 groups**; separately track coverage of 49 categories and 10 subtypes. Do not claim performance for a category with no or too few examples.
- Keep a **random representative cohort** separate from a **targeted ambiguity/safety challenge cohort**. Scores on the latter are diagnostic only, not headline accuracy. Group-balanced selection is not automatically representative of marketplace prevalence.
- After the reference is frozen, run inference using the *exact* released ONNX and hazard artifacts (verified SHA), then evaluate the deployed baseline and any frozen proposed candidate on **identical reviews**. Report sentiment macro-F1 and per-class F1, hazard precision/recall by flag, negative/safety misses, per-group support, product-cluster uncertainty intervals, and numbers of changes fixed versus worsened.
- **Do not enable automatic category sentiment label correction** merely because it sounds logical or beats baseline on a few examples. Require the team's predeclared macro-F1 target of at least **0.80**, meaningful improvement over the strongest comparator and no regression in important negative/safety recall, demonstrated on independent adjudicated data. Otherwise keep context audit-only.

## Limits and safeguards

- **No review text, product IDs, human annotations or private manifest belong in GitHub Actions logs, commits or PR descriptions.** The output directory is ignored by Git.
- The intake checks exact known-title and text overlap, but humans still must check relisted/variant products and proper collection rights. No web scraping or database writes are performed.
- The pilot is deliberately small and group-balanced: it estimates labeling ambiguity, product-category confusions and common error types, **not** definitive macro-F1 for all 49 categories.
- Do not modify the deployed production checkout, delete staging clones, alter saved reports, change model-version tags, or activate category corrections as part of this research work.
