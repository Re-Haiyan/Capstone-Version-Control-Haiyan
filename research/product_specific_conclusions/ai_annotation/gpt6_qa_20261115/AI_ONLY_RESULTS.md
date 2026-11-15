# DeFaketive AI-only annotation audit — descriptive findings

**As of 2026-11-15** · GPT-6-assisted, non-blind review · **No human annotators** · Research/QA use only

## Study decision and evidence scope

At the project owner's direction, this study uses the existing AI-generated annotations **without recruiting or simulating human annotators**. It is an **AI-assisted exploratory quality audit**, *not* an independently validated model-performance study. The reviewer saw the system's card assessment and both generated summary versions. The 5,946 review texts were programmatically grouped/scanned and selected positive, negative, safety and authenticity excerpts directly inspected, **not** exhaustively adjudicated one-by-one.

Inputs: immutable `human_eval_pack/reviews.csv` (5,946 reviews, 35 products); `human_eval_pack/words_sheet_A.csv` (the system's 35 displayed assessments and 70 text variants); `card_preannotations_ai.csv` (35 GPT-6 provisional card judgments); `summary_triage_ai.csv` (70 GPT-6 issue-triage rows). Full model/version, method and source blob hashes appear in `provenance.json`.

## Descriptive comparison against the system

| Quantity | Result | Interpretation |
| --- | ---: | --- |
| Products in comparison | **35** | One GPT-6 provisional judgment per product |
| System and GPT-6 card labels identical | **24 / 35 (68.6%)** | **Agreement only, NOT accuracy**: GPT-6 saw system outputs |
| Different card labels | **11 / 35 (31.4%)** | Specific cases for follow-up, not adjudicated mistakes |
| System text variants triaged | **70** | Two randomized summary variants per product |
| AI card confidence high / medium / low | **7 / 22 / 6** | GPT-6 self-assessment, **not** calibrated certainty |
| AI card possible safety concerns | **11 products** | Reviewer reports, not independently confirmed injuries |
| AI card counterfeit concerns | **6 products** | Customer allegations; no genuine-item verification |
| Suspected unsupported safety context | **13 products** | Textual QA flags, not proven false positives |

This is the comparison of *two non-independent judgments* (the system assessment and a GPT-6 judgment exposed to it). It is **not** precision, recall, F1, agreement between independent humans, or an unbiased independent test. Do not treat 68.6% as the system's accuracy.

### The 11 assessment disagreements

| Product | System's displayed assessment | GPT-6 provisional judgment |
| --- | --- | --- |
| F001 | Well reviewed | Some concerns |
| F002 | Some concerns | Well reviewed |
| F006 | Some concerns | Not recommended |
| F008 | Some concerns | Not recommended |
| F009 | Too few reviews | Not recommended |
| F011 | Not recommended | Some concerns |
| F014 | Well reviewed | Some concerns |
| F018 | Well reviewed | Some concerns |
| F020 | Too few reviews | Not recommended |
| F026 | Well reviewed | Some concerns |
| F029 | Well reviewed | Not recommended |

Disagreement **does not prove the system was wrong**. The underlying reviews can be mixed, duplicated, star-mismatched or unrepresentative; the GPT-6 reviewer was non-blind and directly inspected only selected excerpts. In particular, a limited-review card can still contain serious allegations; neither a general warning nor a categorical rejection is automatically correct.

## Summary risk-triage queue (unique products)

| Priority | Products | Summary texts (two per product) |
| --- | ---: | ---: |
| Critical | 6 | 12 |
| High | 9 | 18 |
| Medium | 15 | 30 |
| Low | 5 | 10 |
| **Total** | **35** | **70** |

*Both summary wordings inherit the same product-level flag and priority in this preliminary queue.* The counts do **not** mean 12 confirmed critical errors in 12 distinct independent summaries. They indicate where a focused evidence audit should begin.

Examples requiring verification against full review context:

- **F002, review 73:** The reviewer says *no* smoke or overheating, but summaries include an unverified possible-safety claim. This may reflect a negation/attribution failure.
- **F014, review 190:** Irrelevant song lyrics appear in a supplement review; an alleged safety event needs its own genuine review evidence.
- **F020, review 6:** A reviewer alleges an earbud case caught fire while charging; a bare *too few reviews* conclusion might underemphasize it.
- **F011:** The generally favorable Betadine cleanser reports coexist with a *not recommended* system label and proposed rash/safety warnings; meaning and direction must be checked.
- **F029:** Multiple suspected-counterfeit whey supplement and quantity discrepancies coexist with relatively favorable top-line language.
- **F030:** Only 16 microphone reviews and many marketing-like feature descriptions; no direct fire/overheat event was found in the targeted inspection.

The above are **possible evidence mismatches**, never externally verified physical events, fake-item determinations or confirmed errors.

## What has NOT been evaluated

- No independent human A/B annotation, no human-agreement kappa and no adjudicated reference set.
- No complete 1–5 ratings on the seven summary dimensions; no mean, preferred-summary score or formal text-quality significance test.
- No new claim-level precision, feature-level recall/F1 or calibrated error rate derived from these 35 card judgments.
- No fresh independent-category or true staging performance test.
- The historical Phase 3 T1 precision **0.852**, recall **0.371**, F1 **0.517** are from a **separate single Claude-assisted reference**, not from this audit; the 0.80 goal was **not** met there.

The old `human_eval_pack/` remains untouched and blank, as its historical protocol requires. For the owner's selected **AI-only exploratory study**, two human annotators are **not** a task or a claimed source of evidence. If a future paper or release claims *independent* empirical correctness, that claim requires separately collected, genuinely independent evidence and truthful provenance.

## Reproduce

Run:

```bash
python research/product_specific_conclusions/ai_annotation/gpt6_qa_20261115/ai_only_audit.py
python research/product_specific_conclusions/ai_annotation/gpt6_qa_20261115/ai_only_audit.py --json
python -m unittest tests.test_ai_only_audit
```

These scripts recompute descriptive counts from version-controlled inputs. CI tests enforce distinct product IDs, exactly 70 summary variants and the **not accuracy** marker. They cannot certify annotation truth.

**Release decision:** AI-only exploratory report may be used with these caveats; **production remains blocked** by independent safety/accuracy evidence, real category coverage, genuine staging and sync-dry-run results and release approval. No production changes were made.
