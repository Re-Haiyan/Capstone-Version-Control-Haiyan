# Reconciling 400, 383, 351 and 37 (frozen test, Team Label 1 against Team Label 2)

Counts are of review IDs, matched by ID; computed from the untouched sheets (descriptive; nothing was relabelled and the frozen test was not used for any tuning).

| Group | Reviews | Note |
|---|---:|---|
| All reviews on the frozen test | **400** | each labelled by both sets |
| Excluded from three-class statistics (at least one set says mixed or unclear) | **17** | |
| Eligible: both sets give positive, neutral or negative | **383** | 400 - 17 |
| of which agree | **351** | the "agreed reference"; 351 / 383 = 0.916 raw agreement |
| of which disagree (three-class) | **32** | 383 - 351 |
| Disagreements outside the three-class set | **5** | in the 17 excluded |
| **All label disagreements** | **37** | 32 + 5 |

The 17 excluded reviews: 6 both mixed, 6 both unclear (the sets agree, but there is no three-class label), and 5 where they differ (mixed versus positive 1, negative versus unclear 1, neutral versus unclear 1, positive versus unclear 2). Mixed and unclear are never counted as neutral (policy S1).

So the three numbers describe different things: **37** = every review where the two label columns differ (the adjudication sheet), **383** = the denominator of the agreement statistics, **351** = the agreed subset used as one of the three reference variants. 37 = 32 + 5; 383 = 351 + 32; 400 = 383 + 17.

Model scoring used three references: sheet A (387 three-class rows), sheet B (384) and the agreed 351. A and B each have more than 383 rows because a review that the *other* set calls mixed or unclear is still three-class under this set.
