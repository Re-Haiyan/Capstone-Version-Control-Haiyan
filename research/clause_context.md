# Clause-level context

> **Label provenance caveat.** Scores are against *team-supplied labels of unverified provenance* (`annotation_provenance.md`). Development evidence is the training file only; the historical test file was not used for any decision here.

## The problem

The sentence splitter cuts a review at contrast markers such as "pero", so "Akala ko peke | pero original pala" reaches the rules as two separate sentences. A keyword in the first clause cannot see that the second resolves it, and a pattern that spans both ("inorder ko pero small ang dumating") never matches.

## A reusable mechanism, not a phrase list

Three small pieces in `hazard_model.py`, each described by a linguistic pattern, not a memorised sentence:

1. **A feared fake resolved as genuine** (`_feared_not_fake`, **on by default**): a sentence whose only counterfeit evidence is a hedged fear ("akala ko", "I thought it was") and which is resolved in the same or the next clause ("original pala", "pero legit") loses the counterfeit tag. A real fake report ("peke ito"), including one after a hedge ("akala ko original pero peke pala"), is untouched. Changed no score on any labelled file.
2. **A soft statement resolved by a benign clause** (`_resolved_by_contrast`, **off by default**, `DEFAKETIVE_CLAUSE_RESOLVE=safety,quality`): *soft* means mild warmth or a plain thickness description with no alarm word, no intensifier and no negative judgement; *resolved* means the next clause is a positive or normal remark with no tag and no complaint. A genuine complaint is never soft; a complaint in the clause *after* the contrast is never touched. Two safeguards are tested: "Sobrang manipis pero okay naman" and "Manipis, parang papel, pero okay lang" stay complaints; "Mainit pero nakakatakot, baka masunog" stays a safety report.
3. **An order clause and a different arrival clause** (`_joined_mismatch`, **on by default**): an "ordered X" clause followed after a contrast by an arrival clause that names a concrete different size, colour or count ("Large ang inorder ko pero small ang dumating") is `not_as_described`, with the arrival word as the quoted evidence; speed and time ("dumating agad", "kahapon ... ngayon") are excluded by construction. A comma form ("Size 42 ang order ko, 43 ang pinadala") is covered by one shared pattern: a concrete size, colour or count directly before "ang pinadala / dumating".

## The brief's five examples, as they behave now

| Review | Default | With `DEFAKETIVE_CLAUSE_RESOLVE=safety,quality` |
|---|---|---|
| "Manipis pero okay naman." | quality | none |
| "Akala ko fake pero original." | none | none |
| "Mainit pero normal lang." | safety | none |
| "Maganda pero madaling masira." | defect, quality | defect, quality |
| "Okay naman pero kulang ang laman." | not as advertised | not as advertised |

## Why item 2 is off by default: the measured cost

On the training file (3,946 rows), switching it on changed 40 rows: **quality F1 0.691 to 0.660** (20 true quality flags lost, 14 false ones removed) and **safety F1 0.638 to 0.626** (3 lost, 3 removed); defect, counterfeit and not-as-advertised did not change. Reading the removed rows: the team-supplied labels call "manipis lang pero ok" a quality complaint about 59% of the time, because the reviewer is naming a minor drawback ("sana tumagal"); likewise "umiinit ang charger pero goods naman" was labelled safety. That agrees with v2 decision G ("a genuine complaint stays one even with partial praise") and disagrees with the idea that the clause resolves it. So the mechanism is a switch for the owner, who decides under the policy (`annotation_policy_v2.md`, decisions F and G), not a default.

## Effect of items 1 and 3 on the training file

Item 3 and the shared "size / colour before ang pinadala" pattern: not-as-advertised F1 0.764 to 0.772 (7 more true flags for 3 more false ones), defect 0.733 to 0.736. Item 1: no change.

## Tests

`tests/test_clause_context.py` (13 tests): feared fake both ways; defaults unchanged; the switch on and off; intensified and judged statements stay complaints; a complaint after the contrast is untouched; unknown switch values ignored; order and arrival mismatches, speed and time not a mismatch, the quoted evidence is a real word of the review; packing damage is about the packing (a conjunction does not attach a damage word to the box).

## Limits

* The patterns are Filipino and English; other languages are not covered.
* The splitter is unchanged: other contrast markers it does not split on are handled inside one sentence only by item 2's within-sentence test.
* Item 3 needs a concrete difference token; a mismatch described only in prose ("iba talaga ang dumating") is left to the existing single-clause rules.
