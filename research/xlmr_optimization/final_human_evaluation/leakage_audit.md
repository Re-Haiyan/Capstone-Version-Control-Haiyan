# Leakage audit of the frozen 400-review final test

Data: `leakage_audit.json` (`leakage_audit.py`; texts and products only; no model run, no returned label read). Frozen list: 400 reviews of 73 products (`annotation/frozen_final_test.json`, hash `5d4384bb68b379fa...`).

| Corpus (what it fed) | Rows | Frozen reviews with an exact text match | Near duplicates (cosine at least 0.9) |
|---|---:|---:|---:|
| FiReCS train (fine-tuning and validation of every candidate; the shipped model's own training is undocumented) | 7,340 | 0 | 1 |
| FiReCS test (gate of the shipped model) | 3,147 | 0 | 0 |
| Marketplace rows used to fine-tune the candidates (`market_train`) | 3,135 | 0 | 1 |
| Marketplace validation split (selection, calibration, bias rule) | 495 | 0 | 0 |
| `market_test_v3` historical benchmark | 886 | 0 | 0 |
| `fresh` + `fresh2` | 580 | 0 | 0 |
| Older team-labelled 300 | 300 | 1 | 1 |
| `review_pool_10000` (AI "direct" annotations exist; active-learning pool) | 10,000 | **69** | 75 |
| `conclusion_eval/product_reviews.csv` (product-conclusion study) | 3,392 | **70** | 73 |
| `fresh_eval_sheet.csv` (earlier fresh evaluation, **with team sentiment labels**) | 980 | **31** | 31 |
| `al_pool.csv` (active-learning candidates) | 8,000 | **30** | 31 |
| Annotation dev pool sheet (different products) | 400 | 0 | 0 |
| `manual_marketplace_reviews.csv` (an unrelated file in Downloads) | 498 | 13 | 13 |

Products: no frozen product title appears in any labelled file. 34 of the 73 frozen products exist in the local database copy that `conclusion_impact.py` analysed. The whole production database copy, which contains all 400 frozen reviews, was read (text only, no labels) by `prune_vocab.py` to choose which tokenizer pieces to keep for the pruned artifacts.

## Findings

1. **No overlap with any text that trained, validated, calibrated or selected a candidate**, apart from 1 near duplicate in FiReCS train and 1 in `market_train` (0.25% each).
2. **The frozen test is not untouched by earlier work.** About a sixth of it (69 reviews) is in the 10,000-review pool that received AI-generated sentiment annotations and served as the active-learning pool; 31 reviews were in an earlier team-labelled "fresh evaluation" sheet; 70 are in the product-conclusion study. None of these entered the fine-tuning or validation of the candidates of this study, so they cannot inflate the comparison between candidates. But **prior AI or team labels exist for up to about 100 of the 400**, and the shipped model's own training data are undocumented, so contamination of the shipped model can be neither excluded nor measured.
3. **Pruning saw the frozen texts without labels** (vocabulary selection only): a minor effect on the pruned artifacts, none on the shipped model.

## Assessment

The test remains **usable for one scoring** of the shipped model, with safeguards fixed now, before any scoring: report every score on all 400 reviews and, as a sensitivity analysis, on the reviews that appear in none of `review_pool_10000`, `fresh_eval_sheet` and `al_pool` (about 300); never delete a row after seeing predictions. It is **not** a pristine independent test: its independence from earlier AI and team labelling is incomplete. If a clean test is wanted, draw a new product-disjoint sample from a fresh scan, excluding every text in the corpora above, and freeze it the same way.
