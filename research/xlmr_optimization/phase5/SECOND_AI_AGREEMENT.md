# Phase 5 follow-up — independent second AI opinion, not independent human truth

The 140 review decisions in `gpt6_second_ai_labels_v1.csv` were completed by ChatGPT GPT-6 from **original full review texts** and committed in `80b2ac33e5f14e16318cf8b4ebf671e3d17fdc40` *before opening the previous Claude per-review labels*. The method, exact interpretation instructions, limitations and provenance are in `gpt6_annotation_provenance.md`.

Run `python research/xlmr_optimization/phase5/compare_second_ai.py --out-dir /tmp/phase5-comparison`. This scorer validates that exactly the 140 independently reviewed development IDs match the preselected review queue and computes 5-class and conditional 3-class descriptive agreement, Cohen's kappa, confidence and language/bucket breakdowns. It writes a disagreement queue with no review text.

Do **not** treat either annotator as a gold label; the intentionally difficult sample does not estimate overall label error. In particular, disagreement between Neutral and Positive on potentially marketplace-supplied positive-sounding tags cannot be resolved without an explicit evidence-based S4 policy choice, and cannot be settled simply by a majority vote between two AI annotators.

Best-practice next steps:

1. Resolve whether the target is **expressed textual sentiment** or **personal post-use experience**; buyer-selected tags have express evaluative words but uncertain authorship. Write a new policy version, not an edit to frozen v1.
2. Keep both original label files and the second-pass data immutable; preserve disagreement reasons.
3. Obtain a human or independently briefed third reviewer for the S4 boundary, or explicitly state the limitations of an all-AI research reference.
4. In future experiments, compare a separate `review_origin`/template detector or abstention flag; do not equate template descriptions with evidence of product use.
5. On new product-grouped development examples, compare **S4-uncertain-excluded** and **S4-uncertain-downweighted** against the unchanged baseline. Never tune to the already-used Phase 3 confirmation or frozen final test.
6. Do not deploy any sentiment candidate until product-level conclusions remain stable and an authorized independent test exists.
