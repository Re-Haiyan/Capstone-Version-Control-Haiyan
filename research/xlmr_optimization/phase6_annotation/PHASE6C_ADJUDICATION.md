# Phase 6C: Independent reviewer adjudication gate

**Status: research tooling implemented, human annotation NOT performed.**

This phase addresses the missing process for turning completed, genuinely independent reviewer sheets into documented adjudication proposals. It does not obtain or simulate human labels. Phase 6B's 18 GPT-6/Claude differences remain AI-only suggestions, not verified truth.

## Obtain reviewer submissions privately

The repository is PUBLIC. Keep all full-text review packets, reviewer completions and adjudication sheets in a PRIVATE authorized local checkout. Never upload those source-text copies to GitHub or GitHub Actions.

Generate the existing blank source sheets:

    python research/xlmr_optimization/phase6_annotation/annotation_quality.py --export-blind-text --output /private/defaketive-qa

The export offers a 480-review risk-focused packet, a separate 200-review random within-development-pool packet, and all 3,400 rows. Prioritize the **200-review random packet** to estimate annotation quality in the existing selected development corpus; concurrently work through the flagged 18 Phase 6B cases under the separate priority packet. Do not pool their different sampling strategies when reporting error rates.

Give TWO different, independently briefed human reviewers exactly the same blind, full-text packet. They must not see each other's results, Claude/GPT-6 annotations, model predictions or star ratings. Both use approved frozen Policy v1, without changing the meaning of S4 marketplace tags.

Each reviewer fills in sentiment, tags, confidence, rationale, mixed aspects when applicable, reviewer_id, reviewer_type=human, policy_version=v1. These role fields are **self-declared**, not verifiable by software; the research coordinator must separately authenticate each participant and their independence.

## Prepare the independent comparison

    python research/xlmr_optimization/phase6_annotation/adjudication_gate.py prepare \
      --blind /private/defaketive-qa/random_blind_review.csv \
      --reviewer-a /private/defaketive-qa/random_reviewer_A.csv \
      --reviewer-b /private/defaketive-qa/random_reviewer_B.csv \
      --out-dir /private/defaketive-qa/random_adjudication

The script checks identical source rows and review-text fields, distinct reviewer IDs, human self-declared roles, policy v1, valid individual labels and required rationale and confidence. It requires all assigned reviews to be complete by default. If --allow-partial is explicitly supplied, missing reviews are counted and reported instead of silently excluded.

It reports exact five-class agreement, Cohen's kappa and the confusion matrix for paired rows. It generates a third-reviewer adjudication sheet for any sentiment or tag difference, relevant mixed-aspect disagreement, or low-confidence label. Per frozen policy v1, the THIRD reviewer can see both prior decisions and reasons after the first two are locked.

Do not publish adjudication_sheet.csv: it contains source review text and reviewer rationales.

## Third-person adjudication

A different adjudicator fills, on every row: final_sentiment, final_tags, final_positive_aspect, final_negative_aspect, final_confidence, adjudication_rationale, evidence_quote (exact substring of source review), adjudicator_id, adjudicator_type=human, policy_version=v1 and adjudication_date (YYYY-MM-DD).

    python research/xlmr_optimization/phase6_annotation/adjudication_gate.py finalize \
      --blind /private/defaketive-qa/random_blind_review.csv \
      --reviewer-a /private/defaketive-qa/random_reviewer_A.csv \
      --reviewer-b /private/defaketive-qa/random_reviewer_B.csv \
      --completed /private/defaketive-qa/random_adjudication/adjudication_sheet_completed.csv \
      --out-dir /private/defaketive-qa/random_adjudication_final

The tool re-derives the adjudication tasks, rejects any source or prior-reviewer decision that was changed, checks complete decisions, requires evidence quotes from actual source text, and ensures the claimed adjudicator identity differs from Reviewer A and Reviewer B.

**All outputs are still PROPOSED, not approved for model training.** The output status is self_reported_adjudication_pending_identity_and_protocol_verification and approved_for_training=false. Software checks cannot prove someone is a human, truly independent, or adhering to study protocol.

The tool does NOT produce a replacement model-training CSV, alter previous AI-labelled files, certify humans' identity, or touch the frozen test or used Phase 3 confirmation.

## Quality gates after actual independent annotations

1. Verify reviewer identities, independence and training, confirm source hashes, completion dates, and the study's approvals.
2. Have the adviser/team decide whether Policy v1 S4 is sufficient. If its interpretation changes, create and explicitly approve a versioned Policy v2; never silently overwrite v1.
3. Preserve all A/B/third-person original submissions in private research storage. Count missing/ambiguous rows and report raw agreement, kappa with confidence intervals, class/language breakdown, and sampling design.
4. Only after written study-team approval create a NEW versioned development reference and keep old Claude-v1 and original locked evaluations unchanged.
5. Train with real product-ID groups, nested development validation, and fresh authorized product-disjoint final evaluation. Do not use already scored confirmation or frozen test for model selection. Check safety complaints and user-facing product conclusions.

GitHub Actions tests the safeguard logic on **invented synthetic examples only** under Python 3.11 and 3.12. No real reviewer submissions are stored in this public repository.

**Scientific claim supported by this work:** A reproducible independent-review and adjudication mechanism has been implemented and tested. **Not supported:** any count of human-validated labels, an improved model, or independently achieved 0.80 F1.
