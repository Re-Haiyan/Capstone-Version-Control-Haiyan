# DeFaketive: project history of the review-classification work

A chronological record of the work done in the development sessions of 2026-11-13 and 2026-11-14, with the commit that holds each step. Numbers are the ones recorded at the time in the documents named next to them. For the research round (audits, baselines, evaluation), start at `research/README.md`.

## 1. System, in one paragraph

DeFaketive reads Lazada and Shopee reviews and says whether a listing shows signs of counterfeit, defective, unsafe or mis-described goods, with a product conclusion card (Well reviewed, Mixed reviews, Some concerns, Not recommended, Too few reviews). Front end SvelteKit + Tailwind; back end Flask behind Caddy on an Azure VM (2 vCPUs, 3.8 GB, CPU only, ONNX Runtime). Every review gets a sentiment (XLM-RoBERTa ONNX) and five flags (defect, counterfeit, safety, not_as_described, quality) from a keyword layer with rule revisions, learned classifiers and per-category files. Details: `research/architecture_audit.md`.

## 2. Timeline

| Step | What was done | Where |
|---|---|---|
| Product conclusion | One "Product Conclusion" card: the verdict plus a counted paragraph and an overall assessment badge | `79c2806`, `b1c8449` |
| Categories | Product categories grew from 39 in 10 groups to **49 in 11 groups** (digital goods, eyewear, motorcycle parts, battery and solar, collectibles, crafts, party and gifts, office equipment, plumbing, electrical; phones read from spec sheets) with per-category exceptions and additions | `b18898c`, `cc61b25` |
| Polish | Each category behaves differently: labels follow the product kind (heat is not always a hazard), and the report wording follows the product group (`category_copy.py`): "Well reviewed / Mixed reviews / Some concerns / Not recommended / Too few reviews", "No red flags found" instead of "caution / no hazard found" | `2f8aca6`, `6296738` |
| Tuning on context | Exceptions can require context (a `when` column); praise and product names stop being flagged | `b3fd62c` |
| Merge | The teammate's r8 labelling rules, F14 and API reliability merged in | `1383377` (from `164ef9b`) |
| Non-gadget labelling, round 1 | 289 + 281 reviews of non-gadget products chosen without the model's flags, a scorer (`evaluation/score_nongadget.py`) and a labelling guide; the team labelled 570 rows | `5274a10`, `66cbfb6`; results `evaluation/nongadget/RESULTS.md` |
| Tuning on the dev half | Rules tuned on half of the labelled non-gadget rows; the other half kept for testing (test half: not-as-advertised F1 0.40 to 0.55, quality 0.54 to 0.67, counterfeit 0.94 to 1.00, safety 3 of 6 found) | `5a9077b`, `c9044a1` |
| Fresh batches | A second scan of 69 and then 75 new products; two fresh labelled batches (310 and 270 reviews) used as clean tests, each followed by the fix its misses showed (denied damage, praise and far expiry dates; negation of category terms; wrong, different and missing items for every group) | `e2d827f`, `8907a7f`, `c66af6a`, `d74589a`, `1f06658`, `9e7a79f`, `11a5033`; results in `evaluation/nongadget/RESULTS.md` |
| Deployment | Deployed to the Azure VM at `c66af6a`, then `d74589a` (bundle, pull, `deploy/setup-server.sh`, HTTP 200 checked). The VM is still at `d74589a` | `deploy/` |
| Training data | Annotation pools of 2,510 + 1,353 rows, a delivery check and 397 more hazard rows, labelled by the team: 3,946 high-confidence training rows and 846 test rows from products never seen in training | `bdfbe40`, `0819e06`, `ebcde8b`; guides in `docs/annotation_guides/` |
| Fine-tuned XLM-R | Three runs (CPU, 50 to 85 min each; embedding table frozen and length-grouped batches cut a run from 83 to 49 min). The model alone never beat the rules; combined it helped in one run and not in another; the delivery output reached F1 0.47 | `e968d1c`, `ebcde8b`, `e2e0943`; `training/RESULTS_v1.md` |
| Rule tuning on the training rows | Shared files for every product, packing damage is delivery, battery-drain policy, learned-model gates, heat reported as safety is not also a defect. Historical test F1: not-as-advertised 0.59 to 0.72, defect 0.67 to 0.69, counterfeit 0.94, quality 0.73, safety 0.53 | `d9d221b`, `831f22f` |
| Research round | Audits, baselines, evaluation with intervals, weak supervision, active learning, sentiment recalibration, deployment benchmark, 12 deliverables | branch `research-improvements`, `research/` |

## 3. What the numbers say (and do not)

* Counterfeit is at 0.94 F1; not-as-advertised, quality, defect and safety are at 0.53 to 0.73 on the historical test, with wide intervals (`research/evaluation_report.md`).
* The 846-row test file was inspected during development: it is a historical benchmark, not an untouched test. A fresh final test and two-annotator agreement are the next evidence needed.
* Rule tuning on training errors raises fit scores faster than test scores: overfitting is real and documented.
* Labels are inconsistent on ten policy questions (`research/annotation_policy_proposal.md`).

## 4. How to reproduce

* Tests: `backend\.venv\Scripts\python.exe -m unittest discover -s tests` (206 tests).
* Score the rules: `evaluation/score_nongadget.py`, `training/rules_eval.py`, `research/evaluate_all.py`.
* Training environment: `D:\defaketive-train` (CPU PyTorch, transformers, scikit-learn, sentence-transformers, cleanlab); runs are not committed (`training/runs/` is ignored).
* Everything that touches labels uses product-grouped folds (`research/common.py`).

## 5. Guides

`docs/annotation_guides/` holds the three annotation READMEs given to the team (round 1, the 3,863-row pool, round 3). The original unlabelled and team-labelled data are in `evaluation/`.
