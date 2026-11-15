# Hazard checker improvement study: protocol (written 16 November 2026, before any data was labelled or any rule changed)

Goal set by the owner: raise precision, recall and F1 of the five hazard flags (safety, defect, counterfeit, quality, not_as_described) toward 0.80. This is an optimisation goal, not a promised outcome. Nothing here may be revised after the final evaluation except as a dated amendment at the bottom.

## 1. Baseline, kept as it is
The checker under study is the one on the live site: the backend of commit `09d9946` (rules `pc4`, `hazard-learned-6.0.0`). On the project's historical test (`evaluation/annotated/test_v3.csv`, 846 high-confidence reviews, 82 products) it scores macro F1 0.722: safety 0.533, defect 0.693, counterfeit 0.943, quality 0.726, not_as_described 0.717 (re-measured 16 Nov 2026). That file was inspected during earlier development; it is **not** used to write rules or to choose a candidate here. It is re-scored once at the end, for continuity only.

## 2. Data: new, product-grouped, stratified
- **Source:** the team's own public Lazada scans (`backups/pool-scans`, scraped 13 to 14 Nov 2026) and the saved products in `backend/seed`. Reviewer names are never read.
- **Excluded:** every review whose text appears in any existing labelled file under `evaluation/` (after normalisation), near-duplicates of those and of each other (token Jaccard 0.8 or more), and reviews under 15 characters.
- **Splits by product** (hash of the product link, salt `hazard1`): **HD1** development, inspected; **HD2** development validation, mis-flags not read until a candidate is frozen; **HF** fresh final, labelled only after the freeze, scored once.
- **Why stratified.** Hazard reports are rare (a random sample of 600 reviews would hold a handful of safety reports). Reviews are drawn from four strata defined by the **baseline checker's** output and the star rating: S1 flagged `safety`; S2 flagged another flag; S3 not flagged, 1 to 3 stars (where misses concentrate); S4 not flagged, 4 to 5 stars. Each sampled review carries a weight (stratum size divided by number sampled), and results are reported **weighted** (an estimate for the whole pool) and unweighted (the sample itself). Limitation, stated now: a candidate that adds flags outside S1 and S2 is judged on S3 and S4, which are sampled thinly, so its added false alarms are estimated with wide uncertainty.
- **Labels:** AI-assisted, by Claude (the model and session are recorded in `provenance.json`), following `evaluation/README_nongadget_labelling.md` as written. The sheet shows the product title, stars and review text only, in random order, with no checker output. They are **not** human labels and **not** independent of the developer; this is stated wherever a number appears.

## 3. Candidates
H0 the deployed checker. H1 precision fixes to word lists and context rules found by reading HD1 false flags. H2 recall additions found by reading HD1 misses. H3 H1 and H2 together. H4 a learned filter or threshold change, only if H1 to H3 leave a flag short and the labelled data can support it. The severe-safety rule (what turns a product into a safety warning) is not loosened by any candidate.

## 4. Adoption rule (on HD2, weighted)
A candidate replaces H0 for a flag only if, for that flag: F1 rises by at least 0.03; **recall does not fall by more than 0.02, and for `safety` does not fall at all** (a missed safety report is worse than a false one); and across the saved products no verdict becomes less cautious without that product being listed and read. All existing tests must pass. Flags are judged one by one; a candidate may be adopted for some flags and not others if the code allows it.

## 5. Reporting
Per flag: precision, recall, F1 with counts and 95% intervals (bootstrap over products), weighted and unweighted, for H0 and the adopted candidate on HF; the historical test for continuity; verdict changes on the saved products; runtime. If 0.80 is not reached, that is the result.

## 6. Deployment
Nothing from this study goes to the VM without the owner's explicit approval of a specific commit.
