# Architecture audit

Status: written from reading the repository at commit `831f22f` plus the research-branch changes. Every statement about behaviour was checked by running the code (tests, the benchmark, the evidence audit), not only by reading it. Where something could not be verified it says so.

## 1. How a review becomes a flag

1. **Product category.** `product_category.py` classifies the listing title with ordered regex rules into one of 49 categories (11 groups) or `other`.
2. **Normalization and segmentation.** `text_norm.py` normalizes Taglish spelling (variants file `taglish_variants_v1.tsv`) and splits the review into sentences. The sentence is the unit everything below works on. Evidence offsets are relative to the original sentence text.
3. **Keyword layer (`hazard_model.py`, `LexiconHazardTagger`).** A lexicon of terms per label, negation handling, phrase exclusions and many numbered rule revisions (`r1`..`r8`, `f1`..`f14`, `s1`..`s5`, `pc3`, `pc4`). Category files add terms (`*.add.tsv`) and set aside phrases (`*.tsv`, with optional `unless` and `when` conditions). A shared `all.add.tsv` / `all.tsv` applies to every product, `other` included.
4. **Learned layer (`hazard_learned.py`).** Two joblib classifiers (defect, safety) over keyword features and sentence embeddings, combined with the keyword layer as an "or, gated" rule: the model may only add a flag, and a chain of gates (praise, denial, battery praise, category exemption, packing damage, feared fake, heat already reported as safety) can stop it.
5. **Extra labels (`extra_labels.py`).** Regex rule groups plus two joblib classifiers for quality and not-as-advertised.
6. **Listing context (`listing_context.py`).** Compares a sentence with the listing title/description for not-as-advertised and counterfeit.
7. **Sentiment (`transformer_sentiment.py`).** XLM-RoBERTa (Cardiff NLP Twitter checkpoint, ONNX int8), three classes. Independent of the flags.
8. **Aggregation (`product_badges.py`, `analyze_reviews.py`, `dashboard_utils.py`).** Reviews are weighted back to the listing's star mix (inverse-probability weights per star level), rates use Wilson lower bounds, a sample-size floor, absolute floors per flag and a count-based safety alert; the buying conclusion is a separate card built from the verdict and the sentiment shares; wording per product group is in `category_copy.py`.

## 2. Component inventory

| Component | Purpose | Dependencies | Known limitations |
|---|---|---|---|
| `product_category.py` + `lexicons/categories/*.tsv` | Category, per-category exceptions and additions, shared `all` files, packing-damage and denial guards | regex, TSV files | Title-only classification; 49 categories but `other` still holds ~6% of rows; exceptions see one sentence at a time (the segmenter splits at "pero") |
| `text_norm.py` | Taglish normalization, sentence segmentation | variants and golden TSV files | Splitting at conjunctions removes cross-clause context |
| `hazard_model.py` | Keyword tagger, rule revisions, learned-model gates, review-level guards | all of the above | 1,900 lines of layered revisions; each fix interacts with older ones; tuned on the team's training labels, so train scores are optimistic |
| `hazard_learned.py` + `models/hazard_classifier_v6` | Learned defect and safety | joblib, sentence embedding from the sentiment ONNX model | Training data and split for v6 are not in the repository (provenance not verifiable here) |
| `extra_labels.py` + `models/extra_labels_v1` | Quality and not-as-advertised | joblib, regex groups | Same provenance gap; quality has the lowest precision |
| `transformer_sentiment.py` + `models/sentiment_onnx` | Sentiment | onnxruntime | Neutral class poorly separated (F1 about 0.2) on the team's labels; see the evaluation report |
| `product_badges.py` | Wilson bounds, tiers, alert, verdict | none | Verdict covers safety, counterfeit and defect only; quality complaints reach the user through the buying conclusion, not the verdict |
| `analyze_reviews.py` | Scan analysis with per-star inverse-probability weights | the above | Weights need the listing's star distribution; without it rates are unweighted and the card says so |
| `dashboard_utils.py`, `category_copy.py` | Conclusion card and per-group wording | the above | Thresholds are fixed constants (not validated against independently labelled conclusions: none exist yet) |
| `research/` (this round) | Audit, baselines, evaluation, benchmarks | scikit-learn, sentence-transformers, cleanlab | Nothing here is imported by the app except the opt-in sentiment calibrator |

## 3. Bottlenecks

* **Latency (VM, 2 CPUs):** median 62 ms per review, 14.4 reviews per second in batches (`deployment_benchmark.md`). Per-component timing was not profiled in this round, so which layer dominates is not established.
* **Memory:** 377 MB peak of 3.8 GB.
* **Maintainability:** rule revisions accumulate; the test suite (206 tests) is the safety net.

## 4. Evaluation leakage audit

Run by `research/data_audit.py` (results in `research/data_audit.json`):

* Training: 3,946 high-confidence rows, 303 products. Historical test: 846 rows, 82 products. **Product overlap between them: 0.**
* **Exact duplicates across the two files: 0. Near-duplicates (character-3 to 5-gram cosine >= 0.90) across them: 0.**
* Inside training there are 343 repeated review texts (generated review templates such as "Leaves hair feeling soft, ..." posted by many buyers). They never carry conflicting labels, but they count several times in training and can sit in the same fold. Product-grouped folds keep a template's product together; templates repeated across products can still land in different folds. This slightly inflates cross-validation scores; it does not touch the historical test.
* **The rules were tuned on the training rows** (this session read their errors), so rule scores on training rows are optimistic. The historical test was not used to write rules after the first scoring, but it was scored and its aggregate numbers were seen many times; it is therefore a *historical benchmark*, not an untouched test (see `evaluation_report.md`).
* The sentiment model was not trained on the team's sentiment labels, so those labels are valid evaluation data in full.
* **Distribution shift:** the test set is concentrated in beauty/health (227), home (200) and food (158) rows and has no `other`; quality positives come from 13 products and safety positives from 11, which is why confidence intervals are wide.
* The provenance of `hazard_classifier_v6` and `extra_labels_v1` training data could not be verified from the repository. If they were trained on any of the reviews in the labelled files, scores for the two labels they feed would be optimistic; this is listed as an open risk in `remaining_limitations.md`.

## 5. Evidence spans

`research/evidence_check.py` ran the deployed checker over all 4,792 labelled reviews:

* 1,912 supporting spans checked, **0 invalid** (all inside their sentence, none empty).
* Flags raised with at least one valid span: counterfeit 182 of 182, safety 138 of 139, not-as-advertised 427 of 449, quality 389 of 410, defect 428 of 539. The flags without a span (defect 111, not-as-advertised 22, quality 21, safety 1) come from the learned layer or the listing-context rules, which do not highlight words; the app should show these as less certain, not quote words for them.
* Offsets are relative to the sentence (the quote the app shows), not to the whole review; the app highlights inside that quote. Added category terms carry the regular expression as their `ngram`, but only the span is used for display.
