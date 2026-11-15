# Phase 6B comparison and decisions

**Status:** AI-to-AI development-only error investigation. This does not establish corrected truth or replace existing Claude labels.

## What was done

1. The 54 selected development IDs were precommitted in \`phase6b_blind_ids.csv\` at \`1eb7c680fb9dc803533b6597bce49931502035bf\`.
2. ChatGPT GPT-6 read the full unlabelled source review text and title, using frozen Policy v1 (no model predictions or star ratings), and recorded an AI-only second pass with confidence, tags, aspects for Mixed and concise evidence.
3. The 54-ID GPT-6 file was **separately locked in commit \`3cdf1c0b4d8661eefc9439c0afff2a0ab318ec43\`**, before comparison against Claude's existing labels in the current turn.
4. Existing conversation may have exposed annotations for certain examples, so the second pass is *partly blind*, **not** strictly independent and not independent human annotation.
5. \`compare_phase6b.py\` validates the exact original review source / label SHA-1 locks, then computes descriptive label and tag disagreements and creates a **proposed-only** correction overlay; no training or frozen sets are read.

## Initial results from comparison

- 54/54 second AI rows recorded, 40/54 exact **sentiment** agreement with Claude.
- 14/54 sentiment disagreements (9 Neutral-to-Positive, 2 Positive-to-Mixed, 1 Positive-to-Negative, 2 Neutral-to-Negative).
- Four additional tag-only disagreements; other 36 rows agree in sentiment and tags.
- These are deliberately risk-enriched (not a random population sample).
- Strong review priorities requiring independent human adjudication:
  - \`N2459\`: first praises charger; later states it failed after less than one month, charges only for seconds, and was a bad buy. Earlier Claude Positive; GPT-6 Negative + Mixed.
  - \`N2372\`: power bank drained after charging phone only 8%; earlier Claude Neutral, GPT-6 Negative.
  - \`N1025\`: first-person intercom comfort, microphone and range experience; Claude Neutral, GPT-6 Positive.
  - \`N1682\`: explicitly reports fast device performance; Claude Neutral, GPT-6 Positive.
- **Policy S4 is still unresolved** for bare buyer-selectable tag lists. Those should not be automatically relabeled.

## Acceptance criteria before any corrected training labels

1. Present \`proposed_annotation_overlay.csv\` to an independently briefed adjudicator; the first reviewer's source should not be disclosed to a new blind reviewer. The coordinator may reveal both after the independent decisions are locked.
2. Record each decision, reason/evidence span, exact reviewer identity/role, policy version and date.
3. Maintain the original \`*_ai_v1.csv\` as immutable; apply adjudication only into a NEW versioned development-only reference sheet once approved, and preserve per-row source and conflicts.
4. Confirm that the new policy is approved for S4 if the definition of buyer-selected tag sentiment changes. Do not quietly repurpose v1 or change the already scored confirmation/frozen test.
5. Do not claim any model performance improvement, model-neutral recovery or human agreement solely because GPT-6 differs from Claude.

No production or deployment changes.
