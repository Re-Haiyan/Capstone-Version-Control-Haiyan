# Source-linked safety evidence review queue (AI-only, **not** independent validation)

**Started 2026-11-15** · Research-only · No new human annotators · No model / rule / verdict changes · No production deployment

The owner selected an AI-only exploratory methodology. The previous GPT-6 triage highlighted customer reports of unsafe chargers and possible unsupported generated warnings. The next step is to make those reports **auditable and reproducible** without recoding the existing frozen evaluation set as training data.

## Run it

```bash
python research/product_specific_conclusions/ai_annotation/safety_source_audit.py \
  --out-json safety_source_audit.json --out-csv safety_source_audit.csv
python -m unittest discover -s tests -p "test_safety_source_audit.py" -q
```

The GitHub Actions workflow **Source-linked hazard QA (non-deployment)** executes those commands on every feature-branch PR and merge and publishes the two generated files as downloadable GitHub Actions artifacts. The files contain product IDs, internal review numbers, short standardized issue codes and counts, **not raw review text**. These are reviewer-friendly queues; review the full, restricted-access original text only when needed.

## What it checks

The script uses a small, conservative set of direct-event expressions for fire/explosion, burning smell/smoke, electrical sparks/shock, overheating, and negative skin reactions. Negated/absence phrasings (including Tagalog) are tracked in a separate list. Suspected counterfeit item wording is tracked as a **customer allegation**, not a factual determination. Both system summary variants are scanned for the numbers of reported safety and authenticity concerns, if they state a count.

The file flags:
- Different reported numbers between summary variants.
- Summaries referring to a safety concern when no direct event candidate was found by this *narrow* checker.
- A direct hazard event in reviews but no explicit hazard wording in either summary.
- A direct hazard event paired with a **Too few reviews** headline, which merits prioritizing the report rather than ignoring it.
- A safety claim on a product with denied/absence language somewhere in the source, requiring a contextual scope check.

**Warning:** the last item is only a request to inspect context, not proof that the claim came from a negated review. The conservative matcher can miss spelling, slang, implicit harm and statements extending across sentences; it can also mistake a hypothetical event for a real event. The system may have matched other review evidence. Therefore **zero matches does not mean the safety warning is false** and **one match does not prove harm**.

## Source-linked review examples to inspect

| Product / review | Source observation | Appropriate disposition |
| --- | --- | --- |
| F002 / 73 | Explicitly says *no* smoke or overheating | Negation/absence candidate. Verify that any model safety count refers to other actual reviews before labelling it a false positive |
| F014 / 190 | Contains irrelevant music-lyric wording about burning, no reported bodily/product injury | Benign word collision. A warning could come from elsewhere; inspect all other evidence before editing rules |
| F020 / 6 | Alleges that an earbud charging case was on fire | Strong direct-event candidate for urgent caution. The report is **not independently verified** |
| F017 / 44, F024 / 15 & 18, F027 / 5 | Direct allegations of popping/exploding or burning-smell devices | Confirm attribution and review language; no physical product verification |
| F011 / 36 & 251 | Mentions rashes in context of a skin cleanser and prior health problems | Distinguish existing conditions and relief claims from product-caused injury |
| F030 / 1 & 2 | Promotional-like descriptions of a microphone rather than firsthand fire events | Example of why generic benefit/feature lists are insufficient evidence of harm |

The F IDs are from the already-frozen **historical** evaluation pack. Their inspection is permitted as an error analysis; they must **never** be used as fresh model-selection data. A future change to the hazard model must be preregistered, developed on new D3 data, selected on V3 and tested once on new F2, with truthful AI-only reference provenance.

## What is NOT claimed

- No independent human labels or independent safety verification.
- No confirmed false-positive/false-negative counts or new precision, recall, F1 or accuracy score.
- No direct recommendation-policy change.
- No modification of the historical human sheets, raw reviews, Phase 3 split, previously selected model or production system.

**Release state:** still *staging candidate, production blocked*. A future staging pass still needs real machine metrics, browser behavior and app synchronization dry run. The policy for safety-sensitive automated claims remains an explicit release decision.
