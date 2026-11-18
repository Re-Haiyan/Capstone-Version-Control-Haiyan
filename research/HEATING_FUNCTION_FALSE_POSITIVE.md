# Heating-function false-positive investigation — release blocked pending paired VM audit

**Observed report:** An Instant Water Heater received positive reviews stating "heats up very quickly." The evidence card incorrectly marked those phrases as **Safety problem**.

## Verified root cause

The shipped keyword tagger's `SAFETY_GAPS[1]` pattern matches `heat(s) up` without considering product purpose. The older `small_appliance.tsv` `init` exception doesn't cover this gap: `_safety_guide16` adds it **after** category-term exclusions and initial false-friend processing. PR #49's context v2 is shadow-only and is intentionally unable to change the independent hazard classifier.

## Proposed narrow solution (NOT LIVE)

In `hazard_model.py`, a normal-heating exception skips **only** the s1 `heats up` safety gap when all these hold:

1. The exact listing title contains an explicit *heating appliance* (heater, electric kettle, rice cooker, air fryer, straightener, etc.).
2. The sentence explicitly praises ordinary heating performance ("heats up very quickly", "heats up fast", "heats up evenly", etc.).
3. There are **no** warning cues (overheating, smoke, fire, sparks, shock, burns, dangerous temperature, hot plugs, hot handles, leaks, and similar red flags).

The script never suppresses unrelated existing lexicon matches, changes product category, changes XLM-RoBERTa sentiment, or touches classifier weights. The same phrase in a powerbank, phone or charger is still eligible for a safety flag. Full copy from the screenshot and dangerous counterexamples are in `tests/test_safety_regression.py`.

**The rules stamp changes from `s1` to `s1h`.** That is deliberate: changing safety detection requires saved-report version transparency. It may initially mark all stored reports as older until a compatibility audit is completed. Do not quietly bypass that by reusing the old stamp, bulk rewriting database records, or changing a production version-compatibility rule without evidence.

## Required release gate

- All exact phrase and hazard-preservation tests pass on Python 3.11/3.12.
- Compare paired current VM reviews against the original release `38b551ae60bbe7cf84bc7d1518fbfee88442a38f`: record every lost/gained safety flag, all five issues, all verdict changes and affected report IDs. Independently inspect **every lost safety flag**. No genuine safety concern may be suppressed.
- Check heaters and non-heating listings in **English, Filipino and Taglish**; include an unrelated hazard in the same sentence and in the next sentence.
- Prepare a saved-report compatibility plan respecting **all** historical reports. Do not silently rewrite or mark them current if affected. Back up both databases, confirm integrity and scratch rollback.
- Keep PR #48/#50 separate and automatic category-based sentiment correction OFF.
- **NO GO** on VM deployment until the paired review and stale-report audits pass and the owner authorizes release.

The user's separate image of the **old flow diagram** is not addressed by this hazard PR. It depicts sentiment before category-specific audit, which is still how current backend executes. A category-first architectural change must not be implied by changing diagram wording without implementing it.
