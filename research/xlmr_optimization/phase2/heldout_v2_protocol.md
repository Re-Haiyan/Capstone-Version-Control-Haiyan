# Protocol for a new independently held-out evaluation set (held-out v2)

**Why a new set.** The frozen 400-review test has been scored (shipped model and `sentiment_head_v1`). It cannot be used again to assess a new candidate: another scoring would make it a development set. Its reference is also AI-assisted and about 100 of its reviews had earlier AI or team labels (`final_human_evaluation/leakage_audit.md`).

**Why it cannot be built from existing data.** After excluding the frozen test, the dev pool, every product already labelled elsewhere and every text already in training, the production database has no further unused products (the frozen test and dev pool already used about 150 of about 150 eligible products; 94% electronics). A held-out v2 therefore needs **freshly scanned products** across home, fashion, beauty, food and automotive as well as electronics. Scanning is a collection task outside this phase: it needs your authorisation of the scan and of the marketplace terms of use.

## Steps (all documented, all before any model sees the set)

1. **Scan** at least 150 new products (target 400 reviews across at least 100 products, at most 6 reviews per product, quotas by category group: electronics 30%, home 18%, fashion 15%, beauty 15%, food 10%, automotive 6%, other 6%; star groups 30/20/20/30). Save into a database with the production schema; record collection dates and marketplace.
2. **Build and freeze** with `build_heldout_v2.py <scan database>`: it excludes blocked products (frozen test, dev pool, neutral candidates, every labelled title), blocked texts (exact and cosine 0.9 or more, including the whole training corpus), writes blank sheets with the same columns as policy v1, writes the frozen manifest with hashes and a timestamp. The star rating is hidden; labels are empty.
3. **Annotate** with the same documented process as the development data (ChatGPT-assisted under policy v1 or v1.1 as confirmed by the adviser, process record completed, prompt file hashed) **and** a human check: a named human adjudicates every disagreement between two AI runs (separate sessions, recorded) and a random sample of at least 100 agreed rows; report the AI-versus-human agreement. The reference is then called "AI-assisted, human-checked", never "independent human ground truth" unless two humans labelled blind.
4. **Lock models first**: write the candidate (artifact hash, configuration, calibration) into a lock file before the labels are used; the held-out set is scored once per locked candidate and never selects or tunes.
5. **Leakage audit** before scoring (`phase2_leakage_audit.py` pattern): texts, near-duplicates and products against training, validation, dev pool and the used frozen test.
6. **Report** the number of locked candidates scored; with more than one, report all of them and apply no selection on this set.

Status: **blocked on the scan** (and on the process record and human-check sample size). Nothing in held-out v2 exists yet.
