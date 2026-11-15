# Product-Specific Conclusions: how to improve feature extraction F1

**Prepared 2026-11-15. No model candidate, new test set, or numerical improvement is claimed.**

## Current baseline

Phase 3 C3, 104 real non-electronics reviews in 15 products (F), using a single Claude-assisted reference:

| Task | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| T1 product features | 0.852 | 0.371 | 0.517 |
| T2 service experiences | 0.818 | 0.209 | 0.333 |
| T0 all kinds | 0.850 | 0.315 | 0.459 |

This is not an independent human benchmark. The largest bottleneck is recall, not precision. The original Phase 3 D2 was used in candidate selection, and F was already unsealed, so neither can be retuned and then reported as fresh.

The predeclared Phase 4 protocol identifies C6 (distinguish buyer experience such as "works as expected" from hypothetical claims), C7 (conservative implicit praise and complaints, Filipino/Taglish), C8 (scoped negation, contrast, product vs service), and C9 (learned/hybrid classifier, only after adequate per-aspect counts). Avoid increasing false product benefits or muffling hazard warnings simply to increase recall.

## Prerequisite: real, rights-cleared data

The existing Phase 4 intake currently has ZERO accepted D3/V3/F2 rows. The research protocol requires at least 300 D3 reviews, 150 V3 and 200 untouched F2, from disjoint new product listings. The samples also need adequate per-category and per-language coverage; footwear and motorcycle categories are not demonstrated. The team must verify legal rights to reuse customer texts, with source-rights evidence in a private ledger. Having a copy of the database on the VM alone does NOT establish research reuse rights.

## New practical tool

After real source records pass Phase 4 intake and a research coordinator confirms their rights and provenance, on an authorized PRIVATE machine:

    python research/product_specific_conclusions/phase4/prepare_reference.py \
      --intake-dir /restricted/phase4/development \
      --out-dir /restricted/phase4/reviewer_packets

The command checks the actual intake manifest and D3/V3 product IDs, and creates two private, differently shuffled BLIND development annotation packets (reviewer A and reviewer B). Each contains review text, category, group and language, plus BLANK feature-pair, confidence, rationale, reviewer ID/type and policy-version fields. It intentionally withholds stars, prior model predictions, source IDs and product hashes.

The flag --include-v3 explicitly prepares a separately restricted validation packet; model developers must not inspect V3 reviews or disagreements while writing candidates. The flag --dry-run checks aggregate counts without exporting text. Source and output must be outside the public repository. Existing output is never overwritten, reviewer CSVs are owner-only (0600), and the F2 vault is never read.

This tool does NOT label reviews, certify identity/rights, calculate F1, or change the model. Completed human or AI sheets need independent provenance; AI review remains AI-assisted. No review-text copies may be uploaded to public CI or GitHub.

## Prospective candidate and measurement sequence

1. Obtain eligible real, canonical-product-linked reviews and pass existing intake.py. Do not invent examples.
2. Independently annotate D3 and use D3 ONLY to develop predeclared C6/C7/C8 candidates with conservative aspect and evidence rules. Do not inspect F2.
3. Freeze candidate code; use V3 only for the preregistered adoption decision (T1 F1 +0.03 absolute minimum; T1 precision decline no more than 0.03; T2 F1 decline no more than 0.05; strict safety/evidence and latency checks).
4. Freeze final code and reference provenance; unseal F2 ONCE. Compare baseline C3 and the frozen candidate on exactly the same product-disjoint F2 reviews and publish TP/FP/FN, precision, recall, F1, category/language support and confidence intervals.
5. Keep the actual VM and shipped conclusion feature unchanged until separate safety, explanation and staging approval.

**No current metric has changed.** The new tool eliminates one workflow obstacle but the next unavoidable dependency is eligible real data. Do not claim F1 of 0.80 or a production improvement based on code tests alone.
