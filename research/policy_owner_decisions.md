# Owner decision sheet: annotation policy v2

**Nothing on this sheet is approved.** Each row needs a decision from the project owner, recorded in the last column. The policy in force is v1. No historical label has been or will be changed by approving a row: relabelling is a separate, later step (`annotation_policy_v2.md`, section Adoption). Label statistics are from the training file (team-supplied labels, provenance unverified: `annotation_provenance.md`); the historical test file was not read.

How to answer: write **Approve**, **Approve with change (say what)** or **Reject** next to each row, sign and date at the bottom.

## The two open decisions in detail

### D. Missing freebies

| | |
|---|---|
| **Proposed rule (v2)** | A freebie promised in the listing or the purchase terms and not delivered is `not_as_described`; an unadvertised one is not; a seller-fulfilment complaint may also be `delivery` |
| **Current behaviour** | "Walang freebie na kasama": no flag. "Nakalagay sa listing may free tumbler pero wala": `not_as_described` (the rules read the sentence, not the listing's freebie list) |
| **What the labels show** | Freebie wording, 72 training rows: not_as_described 17%, none 69%. Missing **and** promised (the review says the listing, sale or seller promised it): 11 rows, not_as_described 45%, none 45%. Missing, no promise stated: 12 rows, not_as_described 25%, delivery 33%. Freebie mentioned but not missing: 49 rows, not_as_described 8% |
| **Alternatives** | **D1** a missing freebie is never `not_as_described`. **D2** `not_as_described` only when the review states the promise (implementable as a rule). **D3** only when the listing text confirms the freebie (best precision; needs the listing's description read for "free gift" lines; more work). **D4** D2 or D3 plus `delivery` for the fulfilment complaint |
| **Consequences** | D1 loses the 45% of promised-and-missing reviews that the team did flag, and agrees with the 25% of unpromised ones that it should not. D2 recovers most promised cases from the review alone but trusts the reviewer's claim. D3 is the most defensible and the slowest to build. Every option is based on 11 and 12 rows: **too few to choose by data** |
| **Recommended interpretation** | **D2 as the working rule and D3 as the target**, with D4's `delivery` once a `delivery` rule flag exists. Because the numbers are small, have the annotators label about 60 freebie reviews **with the listing visible** before the rule is built |
| **Required human decision** | Choose D1, D2, D3 or D4; and approve labelling about 60 freebie reviews with the listing shown |

### G. Thin material and "pero okay"

| | |
|---|---|
| **Proposed rule (v2)** | Do not exclude `quality` merely because the reviewer adds "pero okay"; judge the whole statement; a neutral physical description is not a complaint; a genuine complaint stays one with partial praise |
| **Current behaviour** | "Manipis pero okay naman", "Sobrang manipis, parang papel", "Manipis pero pwede na": all `quality`. An opt-in switch (`DEFAKETIVE_CLAUSE_RESOLVE=quality`, off) clears plain descriptions only and never an intensified or judged statement |
| **What the labels show** | 208 training rows mention thinness: quality 69%, none 27%. Without a concession: 86 rows, quality 71%. With one: 122 rows, quality 67%. With a named drawback or intensifier: 78 rows, quality 71%; with a concession and no drawback named: 44 rows, quality 61%. **No cue I tried separates complaint from description by more than about 10 points.** The switch costs 0.031 quality F1 on the labels |
| **Alternatives** | **G1** thin is a (minor) `quality` report whatever follows (today). **G2** a concession clears it (the switch; contradicts the labels, which agree with "a complaint stays one with partial praise"). **G3** annotators judge each review as a whole (complaint if the reviewer names it as a drawback or worries about durability; description if they only describe it); rules unchanged until the judgement is measurable. **G4** keep G1 but count thin separately as "minor" |
| **Consequences** | `quality` is an **informational** badge ("N reviews mention weak build quality"): it never enters a verdict, so a false report costs less than a false `defect` or `safety`. G2 (measured on training rows) removed 34 quality flags: 20 were labelled true and 14 false, so it loses more true reports than false alarms it clears (quality F1 0.691 to 0.660). G3 makes the *labels* consistent, which is what the rules and any model need |
| **Recommended interpretation** | **G3 for the annotation policy, G1 for the rules.** Keep thin as a minor `quality` report; do not resolve it automatically; revisit after two annotators label the thin reviews under G3 and a cue is shown to separate the two kinds |
| **Required human decision** | Choose G1, G2, G3 or G4 |

## All ten decisions at a glance

| # | Decision (v2) | Current behaviour | Gap? | Recommended | Owner decision |
|---|---|---|---|---|---|
| A | Packing damage alone is `delivery`, not `defect`; both if the item is also damaged | Box-only damage: no defect (correct). Item damage in the same sentence as a packing word: **missed** (the core lexicon's shipping rule). No `delivery` flag in the rules | Yes (two gaps) | Approve. Build item-damage-beside-packing and a rule-layer `delivery` flag after approval | |
| B | Differentiate battery complaints; objective failure is `defect`; do not infer a malfunction from "mabilis malowbat" | Bare "mabilis malowbat": none. Abrupt or measurable wording (minutes, "kahit full", "agad", a number, a power bank) and charging failures: defect | No | Approve; two kinds (no longer holds a charge, abnormally rapid) have 2 training rows each and need targeted annotation | |
| C | A fit complaint is not a mismatch; an explicit ordered-versus-received difference is `not_as_described` | Met, including across "pero" and the comma form | No | Approve | |
| D | See above | See above | Partial | D2 now, D3 as the target | |
| E | Separate half-filled packs, less than the stated amount, leakage, broken seals; mark uncertain cases | "Kalahati lang ang laman": none; with a leak: defect; "buy 1 take 1, half in each": none | Yes (stated quantities need the listing) | Approve; build only with the listing's quantity | |
| F | No hypothetical fear; abnormal heating, burning smell, smoke, sparks, shock when reported; fear plus a stated abnormal condition qualifies | "Umusok na at nakakatakot": safety. **"Baka sumabog yung charger": flagged defect** | Yes | Approve; stop a purely hypothetical fear from being flagged. Note the labels disagree with v2 on fear plus an abnormal condition (5 rows, mostly none), so re-adjudicate first | |
| G | See above | See above | Owner decision | G3 for the policy, G1 for the rules | |
| H | `safety` and `defect` together only when both are independently supported | Met | No | Approve | |
| I | `counterfeit` and `defect` together only when both are explicit | Met | No | Approve | |
| J | Effect complaints are not malfunctions; propose an `effectiveness` flag if the data justify it | "Walang epekto, hindi pumuti": **flagged defect**. Data: 11 rows, 8 labelled counterfeit | Yes; **not justified yet** | Approve the principle; do not add the flag (needs about 100 rows in at least three groups with agreement) | |

## Decisions that go with these

| Question | Recommended | Owner decision |
|---|---|---|
| Use v1 or v2 for the next annotation round? | **v1** for the 300 agreement sheets, so agreement is measured against the policy the labels were made under; v2 only after approval, written in each file name | |
| Relabel historical data under v2? | **No**, not before agreement is measured and the adjudication queue is worked; keep every original label in a separate column | |
| May rule changes for the gaps (A, E, F, J) be made? | Yes, on training evidence only, measured on a fresh test, never on the historical test | |

Owner: ____________________  Date: ____________  Policy version approved: ____________
