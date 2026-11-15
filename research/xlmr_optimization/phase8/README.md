# Phase 8 — Authorized fresh held-out collection with DeFaketive's scraper

**Current status: no new real reviews have been collected.** GitHub repository is PUBLIC; do not commit customer review text, cookies, product histories or annotation packets.

## Permission and privacy

Lazada's public Terms of Use limit reproduction/storage of marketplace materials without permission and its platform-tool terms prohibit scraping in that context. The MIT license of the repository's existing scraper grants code rights, **not** rights in marketplace reviews. Obtain and document appropriate site/content collection and storage permissions before a real collection. Do not bypass login, bot challenges, captchas or access limits.

This pipeline deliberately has no unattended live GitHub Actions crawler: running a public CI worker would leak data through its logs/artifacts and cannot prove any marketplace permission. Use an approved, privately controlled machine and transfer only summary counts into public GitHub.

## Collector

The existing Lazada scraper is located at backend/lazada-scraper/src/lazada_scraper.py. Its outputs are JSON lists of products with names, URLs and comment records. On an authorized computer, its accepted flags include --product-url, --all-star-types, --star-limit-per-type, --window headless, --never-show-window, --no-verification-pause, --reviews-from feed, and -o.

Example CLI shape with an actual, authorized listing URL substituted in place of the placeholder:

    python backend/lazada-scraper/src/lazada_scraper.py \
      -n 30 --all-star-types --star-limit-per-type 6 \
      --product-url "https://www.lazada.com.ph/products/REPLACE_WITH_AUTHORIZED_PRODUCT-i123456.html" \
      --window headless --never-show-window --no-verification-pause \
      --reviews-from feed -o /private/defaketive/scans/batch_01.json

If a login, verification or access denial occurs, stop; don't attempt workarounds. Collect at least 100 genuinely unseen products spanning categories; make more collection attempts than the 400-review goal, because blocked, duplicate and empty reviews will be excluded.

## Private held-out intake

Phase8's prepare_scraper_heldout.py reads only genuine existing scraper JSON and writes private, unlabelled, blinded annotation sheets. It NEVER visits Lazada. It checks prior product titles/links, exact text, char n-gram cosine near-duplicates, review-ID duplicates and obvious email/phone identifiers. It does not fake labels, reviews or missing quota.

Outside the public repo prepare a JSON permission document containing source=lazada_ph, authorized_by, rights_basis, record_date, allowed_collection=true, allowed_research_storage=true. The study coordinator must independently confirm its authenticity. Maintain an authorized complete private history map (CSV fields product_link,product) covering **all** previous train/dev/final evaluations including local-only scans.

Run:

    python research/xlmr_optimization/phase8/prepare_scraper_heldout.py \
      --scrape-json /private/defaketive/scans/batch_01.json \
      --authorization-record /private/defaketive/permission.json \
      --private-historical-map /private/defaketive/all_prior_products.csv \
      --output-private /private/defaketive/heldout_v2 \
      --target 400 --min-products 100 --max-per-product 6

Pass multiple batch files after --scrape-json as needed. Outputs: blind_reviewer_A.csv, blind_reviewer_B.csv, PRIVATE_source_map.csv, manifest.json. A and B show the same reviews in different order, without star ratings, source IDs or model predictions. All files contain customer data and must be treated as private; only the manifest's aggregate facts may be disclosed.

If private historical product IDs are absent, output is **provisional**, not confirmed independent. A file existing is not proof that its exclusions cover all previously used data. The program refuses output inside the public repository and never overwrites old outputs.

## Verification after collection

Have two genuine independent humans annotate each review blindly, followed by third-person adjudication. Freeze human reference labels, verify original product IDs and language/class support, and lock the deployed and candidate weights before one final head-to-head evaluation. Never use the new final test to choose epochs or retrain. Review product conclusions, neutral Filipino/Taglish sentiment, negative/hazard accuracy and ONNX inference separately.

The Phase 8 GitHub workflow runs ONLY synthetic unit tests and NO live website requests.
