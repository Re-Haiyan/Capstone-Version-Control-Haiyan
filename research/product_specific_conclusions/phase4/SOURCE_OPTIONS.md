# Phase 4 source audit — candidate rights-cleared review corpora

**Checked:** 2026-11-15. **Research status:** 0 D3, 0 V3, 0 F2 accepted; no new feature model evaluation. The following is a *discovery note*, not a collected dataset or license clearance for any marketplace review re-use.

## Candidate sources

| Source | Published license / available fields | Potential use | **Why it cannot satisfy the prospective D3/V3/F2 protocol as-is** |
| --- | --- | --- | --- |
| [SentiTaglish: Products and Services](https://huggingface.co/datasets/ccosme/SentiTaglishProductsAndServices) | Dataset card states **CC BY 4.0**, 10,510 Tagalog/English review texts and sentiment labels; fields `review`, `sentiment` | Supplemental Filipino/Taglish language inspection, with attribution and rights review | No stable **product/listing identifier**, per-product title, category, marketplace link, or source collection date in the published fields; mixes service and product reviews |
| [FiReCS](https://huggingface.co/datasets/ccosme/FiReCS) | Dataset card states **CC BY 4.0**, 10,487 review-text and sentiment-label rows; fields `review`, `label` | Supplemental sentiment/language diagnostics, with attribution and rights review | Missing listing-level identity and required category/source fields; sentiment labels are **not** the required per-aspect labels |
| [TagaSenti](https://huggingface.co/datasets/jjjardev/tagasenti) | Dataset card states **CC BY-SA 4.0**, combines third-party corpora and translated, AI-assisted and adversarial synthetic items | Possible *separate* robustness examples after per-origin provenance checks | Mixed provenance includes artificial/translated examples, absent original product IDs and no valid prospective product-grouped final test |
| [Rebrowser Shopee Product Listings](https://huggingface.co/datasets/rebrowser/shopee-dataset) | Metadata sample with item IDs, titles, category fields; **CC BY-NC 4.0** according to card | Potential source of public **listing metadata**, subject to terms | The described dataset is **product listings**, not actual customer review texts. Cannot fabricate missing reviews by joining unrelated texts |

Dataset cards can change. Verify the **exact downloaded version/commit, file schema, license, source rights, and attribution** before use. A dataset-card license is not proof the publishing party had every underlying platform/reviewer right. Do not interpret availability on Hugging Face as blanket permission for application model training or redistribution.

## Implications for DeFaketive

**Do not synthesize a product identifier, attach a random review to a listing, infer a category from a review and call the split product-disjoint, or disguise AI-generated review examples as real.** If a corpus has no stable listing ID, its rows cannot be used to satisfy the preregistered D3/V3/F2 product-disjoint test or the real category coverage gate. Use a separate methodological amendment for auxiliary language testing and exclude its texts from prospective validation/final by exact and near-duplicate checks.

### Preferred route for a research-grade data source

Request a **rights-cleared per-product export** from the team, cooperating vendors or legitimate data providers. It must provide real review text, original rating, actual collection date, marketplace, stable canonical listing ID and public URL, title, source batch, intended category/group, and permission/license citation. Collect enough **distinct listings per category and language**, not just 650 reviews from a few products. No reviewer identity is needed.

Track permission and attribution evidence in a restricted source-rights ledger *outside Git*, not in a published review file. Disclose scope and terms; select `team_owned`, `licensed_dataset`, or `authorized_export` only when justified. The owner's past ownership of `defaketive.db` **does not independently establish** rights to reuse customers' Lazada texts for ML research.

### What stays blocked

The local `phase4/supply_audit.py` report estimated ~17,000 potential non-Phase-3 gadget-review texts after historical/exact/near-duplicate filters. It did not certify legal reuse, complete intake eligibility, rights, category diversity, canonical listing IDs, or privacy. Its illustrative split counts are a **URL-based proxy** and cannot be treated as the exact intake split: real Phase 4 assignments require verified canonical `listing_id` for each product. Even if rights are confirmed, a gadget-only dataset cannot validate footwear, motorcycle parts, skincare or other absent categories.

Until eligible reviews actually pass `phase4/intake.py`, the counts remain **D3=0, V3=0, F2=0** and the Phase 3 accuracy target remains unmet. 
