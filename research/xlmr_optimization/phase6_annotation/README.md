# Phase 6 — Comprehensive annotation quality (not relabelling)

## Objective and scope

**All 3,400 editable Phase 4 development annotations** (400 dev + 3,000 Neutral candidates) are checked against their untouched original source text under approved policy v1. The previously scored 200-row Phase 3 confirmation set, 400-row frozen final-test sheets, returned final-test annotations, policy lock and the 140 GPT-6 second-pass annotations are protected by Git blob SHA-1 hashes, but their label values are **not** used for tuning, adjudication, scoring or content review. Older private 10,000-review annotations on a local D: drive are not available from GitHub and cannot be audited here.

This change **does not turn all AI labels into verified ground truth**. It finds annotation risks systematically, prepares blind re-review of every development row, and enforces provenance for any submitted correction. It never silently rewrites or "corrects" a sentiment label.

## Exact outputs

Public GitHub Actions produces a metadata-only artifact:

- \`annotation_quality_report.json\`: complete counts and flag coverage, no customer text
- \`all_3400_quality_registry.csv\`: one row per development review ID, original Claude label, risk flags/priority, and \`unverified_ai_label\` status; no review text
- \`priority_ids.csv\`: reproducible prioritized review IDs, no text
- \`priority_coordinator_only.csv\`: Claude and GPT-6 decisions (when present), flags and blank human-adjudication fields; do NOT share it with a blind annotator

All IDs, source labels and rationale fields are validated against their original CSV sources; the script also checks that no source text, product title, language, platform or category was altered. Mixed tags and aspect requirements are checked under v1. Every original row remains individually traceable.

The prioritization marks *possibilities* such as:
1. GPT-6/Claude disagreements in the 140 selected cases
2. Clear negative defect cues hidden under a Neutral/no-opinion label
3. Opinion-bearing language after the first 170 characters, especially in long tag-list reviews Claude may have viewed only partially
4. Low-confidence labels and underrepresented Filipino/Taglish Neutral reviews
5. Template-like feature lists whose authorship as a buyer's endorsement is unresolved by policy S4
6. Ambiguous delivery-only/product-defect combinations and potentially cut-off source texts

These flags are **not automated corrected labels**, and no flag can establish whether a buyer selected or authored a marketplace template.

### Blind full-text reviewer packets — local only

This repository is PUBLIC. To avoid republishing thousands of customer reviews or accidentally revealing existing AI answers to the second reviewer, GitHub Actions intentionally does **not** upload full review text.

In a **private authorized local checkout**, run:

    python research/xlmr_optimization/phase6_annotation/annotation_quality.py --export-blind-text --output /private/defaketive-qa

It produces the metadata files plus:
- \`all_3400_blind_review.csv\`: all 3,400 review texts, titles and blank annotation fields
- \`priority_blind_review.csv\`: up to 480 risk-enriched reviews, blank sentiment/tags/aspects/confidence/rationale and no Claude/GPT-6 labels, star ratings or predictions

The 71 previously documented cross-AI disagreements are guaranteed in the priority packet, plus a reproducible sample of ordinary controls, while varying product titles and languages. The prioritized packet is **not** a random estimate of overall AI-label error. Reviewers must read the entire source review and work blind; coordinator should not reveal risk flags or earlier model outputs until after labels are locked.

A suitably authorized reviewer can fill \`priority_blind_review.csv\` and, without changing any source sheet, validate the submitted work locally:

    python research/xlmr_optimization/phase6_annotation/review_submission.py \
       --blind-original /private/defaketive-qa/priority_blind_review.csv \
       --completed /private/defaketive-qa/priority_blind_review_completed.csv \
       --output /private/defaketive-qa/proposed_reannotation_overlay.csv

Completed rows must have one of the approved policy-v1 labels/tags, aspects for Mixed, rationale, high/low confidence, reviewer ID, self-declared reviewer type (human or AI), and policy version \`v1\` or \`v2-draft\`. They are stored as **proposed_not_adjudicated** in a separate overlay. Claimed reviewer type is self-reported, not automatically verified. A v2-draft decision is not an approved v2 reference.

## Mandatory quality gates before using reviewed labels

- Confirm research adviser/team decision about S4 (buyer-selected vs auto-generated tags); use a separately versioned and approved policy if meaning changes
- Obtain independent blinded human/second-source labels and a documented adjudication for disagreements, not majority vote between GPT-6 and Claude
- Check *natural source distribution* and class/language supports; do not count reviewer-selected tag templates as natural Filipino/Taglish Neutral opinions
- Keep \`annotation_policy.md\` v1, original sheets, final-test refs and previously scored confirmation immutable
- Do not train/tune to the already used 140 disagreement labels or previously scored confirmation; no candidate deployment without independent authorized product-disjoint test
- Do not describe proposed, automatically flagged or AI-reviewed rows as independently human-validated labels

## Research limitations

No scraping was performed. No new human annotations were invented. The source contains 3,400 development rows and a separate 140-case second GPT-6 opinion; the frozen final test and confirm are integrity-guarded only. Complete quality auditing is **not** equivalent to complete human reannotation. The priority-review packet is deliberately biased toward difficult examples. An unauthorized scrape cannot substitute for a genuinely new test set.

The legitimate improvement is reproducible, source-locked **full coverage**, explicit uncertainty, reviewer blinding, provenance validation and a safe pipeline for future corrections—not an invented F1 gain.
