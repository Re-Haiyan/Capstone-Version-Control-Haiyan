# Phase 4 — rights-cleared real-review intake

**Status as of 2026-11-15: intake software prepared, zero new real reviews claimed.** The historical Phase 3 extractor remains frozen and its low T1 recall of **0.371** is unchanged. There is no Phase 4 dataset, model candidate, validation result, or production promotion yet.

This intake implements the collection, leakage and privacy constraints in [protocol.md](protocol.md) **before** any new Phase 4 model development. It never scrapes sites or manufactures observations. It accepts only rights-cleared, genuine review records the team is authorized to use.

## Collecting the input

Create a UTF-8 **JSON Lines** file stored in a private folder **outside the Git repository**, with **one actual customer review per line**. Do not send reviewer IDs, usernames, seller contact details, private conversations or session tokens. Each record must have **exactly** these fields:

```json
{
  "marketplace": "lazada",
  "listing_id": "actual-public-listing-id",
  "listing_url": "https://www.lazada.com.ph/products/actual-public-listing-id.html",
  "listing_title": "Exact public product listing title",
  "category": "small_appliance",
  "group": "home_living",
  "language": "taglish",
  "review_text": "The actual reviewer text goes here, unchanged except for privacy-preserving redactions.",
  "stars": 4,
  "collection_date": "2026-11-15",
  "source_kind": "authorized_export",
  "source_id": "authorized-batch-001",
  "rights_confirmed": "yes"
}
```

**The object above is a schema illustration, not a real review or a seed record.** Do not copy the sample text into the research dataset.

- `marketplace` and `listing_id`: canonical, stable identifiers for the **same product across all its reviews**. Do not assign a new ID per variant, review, crawl or scan. `listing_url` must identify the actual public HTTPS product; do not use redirects that hide or vary the canonical listing. Intake rejects mismatched Lazada/Shopee hosts, two identifiers pointing to the same normalized listing URL and one identifier with conflicting URL paths; resolve aliases before input.
- `listing_title`: visible product listing title, needed to detect overlap with 35 locked product titles. Do not fabricate it.
- `category` and `group`: the project's existing classification names; retain what was documented at collection rather than retroactively using the model prediction.
- `language`: `en`, `fil`, `taglish`, `other`, or `unknown`. This is supplied by the source/team and is **not** a new automatic language classifier; independently verify language coverage before analysis.
- `stars`: integer from 1 through 5. Stars never substitute for the review's text meaning.
- `collection_date`: actual collection date (YYYY-MM-DD), not a guessed publication date.
- `source_kind`: `authorized_export`, `licensed_dataset` or `team_owned`. `source_id` identifies the *collection batch*, not a reviewer. Store the permission/license citation separately in the team access-controlled evidence log.
- `rights_confirmed`: exactly `yes`, set only when source use is authorized. The tool cannot verify a legal right by itself.

The validator deliberately fails on unexpected keys—including `reviewer_id`, `reviewer_name` and contact fields—rather than silently copying private data. It also rejects text/title patterns resembling phone numbers, emails, OTPs, secrets and URLs. This is **best-effort screening, not comprehensive PII detection**: review data privacy and rights separately before import. Manually sanitize sensitive content in the original authorized record; never invent, change the sentiment or replace the review with a generated example.

## Run the intake

For example, using folders outside the checkout:

```bash
python research/product_specific_conclusions/phase4/intake.py \
  --input /restricted/phase4/real_reviews.jsonl \
  --dev-output /restricted/phase4/development \
  --final-vault /separate-restricted-storage/phase4-final \
  --confirm-rights \
  --dry-run
```

Omit `--dry-run` only when you want to create the split files. It refuses to overwrite an existing destination. Use **separate directories** for development and final data, preferably with separate access permissions or storage accounts. The tool creates:

| Location | Files | Access |
| --- | --- | --- |
| Development directory | `D3.csv`, `V3.csv`, `manifest.json` | Authorized researchers; D3 for development and V3 for one-shot candidate selection |
| **Separate final vault** | `F2_SEALED_DO_NOT_OPEN.csv` | Restrict until model/code/annotation protocol freeze |

The files are created with owner-only permissions when supported; **that is not encryption or a security boundary on shared accounts**. Provide independent storage access controls. The tool never prints F2 reviews and never writes them into the D3/V3 directory. It *must read input text internally to deduplicate*, so keep the input access-controlled as well. The final F2 **reference labels and model outputs must not be inspected before the freeze**.

**No output review data is committed to GitHub.** The repository contains code, schema, synthetic unit tests and methodology only.

## What is checked

1. **Historical products:** compare listing title to the 35 fixed product titles, plus compare SHA1 of the exact listing URL to all truncated 12-character Phase 3 product hashes. Any missing historical index means fail closed. URL aliasing and changed product titles can still evade this heuristic; confirm canonical listing IDs independently before calling a product new.
2. **Historical review text:** reject normalized exact and token-Jaccard **>=0.80** near-duplicates against the full historical 5,946-review pack and Phase 3 D1/D2/F texts. The inverted-token index is exact for this Jaccard threshold—not a probability sample.
3. **Cross-split and cross-listing duplication:** reject duplicate/near-duplicate review content within the new intake; assign **all reviews of a canonical product** to one split based on frozen SHA256(salt, marketplace, listing_id). Assignment cannot be changed to move difficult products.
4. **Privacy/provenance:** source kind, source batch, collection date, categories, language tags, rights attestation and text checks. No reviewer identities or contact details in output.
5. **Quotas:** D3 minimum **300**, V3 minimum **150**, F2 minimum **200** genuinely new reviews, with disjoint products. A shortfall sets `research_ready=false`, and the tool explicitly reports the deficit. Meeting counts is **only a necessary condition**; category/language coverage and proper AI label provenance are still required.

## Scientific restrictions

- Source ingestion does **not** label reviews, compute model precision/recall/F1, train C6–C9 or certify research reliability. Never call prepared synthetic or historical records *fresh validation*.
- The owner selected an **AI-only exploratory** reference method: record the exact AI model, full prompt/rubric, run date, exposure/blinding, source row hashes and uncertainty for genuine new reviews. Never relabel AI output as a human annotation or claim independent human Cohen's kappa.
- D3 may inform candidate development, V3 is for preregistered selection only, and **F2 is opened once only after freeze**. Do not reuse the Phase 3 F subset or this historical safety triage to tune the new model.
- Existing deployed decisions, hazards, sentiment, saved product verdicts and frozen model/thresholds stay unchanged until the separately reviewed model-adoption protocol can be satisfied. **No Phase 4 model candidate has been created or tested by this intake.**

## Run synthetic-only unit tests

```bash
python -m unittest discover -s tests -p 'test_phase4_intake.py' -q
```

All synthetic text in the test file exists **solely to test the intake gates**. Real Phase 4 research metrics require independently sourced records and cannot be filled from these examples.

## Status audit, 2026-11-15 (Claude Code session; supply estimate only, no data collected)

**Still zero accepted Phase 4 reviews. D3, V3 and F2 were not created, nothing was annotated, no candidate (C6 to C9) was developed or scored, and C3 remains the baseline (T1 precision 0.852, recall 0.371, F1 0.517 against a single AI-assisted reference).**

What was checked: the only locally held source of real marketplace reviews is the project's saved-product database (182 Lazada gadget products, written reviews captured by the app). `supply_audit.py` (read-only, aggregate counts only, no rights attestation) applied the intake's historical gates to it:

| Check | Result |
| --- | --- |
| Products in the database | 182 |
| Excluded as Phase 3 products (link-hash match / title overlap) | 11 / 15 |
| Products not matching any Phase 3 product | 156 (152 with surviving reviews) |
| Reviews in those products | 18,842 |
| Dropped as historical-text duplicates / within-supply duplicates | 955 / 926 |
| Surviving reviews if rights were confirmed (D3 / V3 / F2 by the frozen product hash) | 9,409 / 3,768 / 3,784 (79 / 36 / 37 products) |

Why this does not start Phase 4:

1. **Rights are not established.** A database copy of marketplace reviews is not evidence of permission to use it as research data; `rights_confirmed=yes` is an attestation only the owner can make, and the intake requires `--confirm-rights`. I did not set it and did not run the intake on this data. Decision needed from the owner: is this database, or a specific authorised export, usable under `source_kind=team_owned` or `authorized_export`, with the permission citation recorded in the access-controlled evidence log?
2. **Category coverage is absent.** All 152 products are gadgets (the group field is empty in the saved JSON). The protocol also asks for appliances, clothing and footwear, skincare and haircare, food and supplements, and motorcycle parts. The database cannot satisfy that, so even with rights confirmed, the category gate (RELEASE_GATES gate 4) stays blocked; a gadget-only D3 could support only an explicitly gadget-scoped exploratory study.
3. **Reuse caveat.** Most of these products' reviews were also used by the separate sentiment-neutral research track (candidate pool, impact study) and the 182 products anchor the saved-verdict regression checks; they were not in the Phase 3 product-feature packs, which is the exclusion that this protocol requires, but the owner should accept that overlap knowingly.
4. **No scraping or access bypass was attempted** to obtain other categories; no source outside the project's own files was used.

`tests/test_phase4_supply_audit.py` covers the audit with synthetic rows only.
