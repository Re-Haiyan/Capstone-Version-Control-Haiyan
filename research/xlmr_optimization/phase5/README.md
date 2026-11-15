# Phase 5 — source-only generalization audit

This isolated research branch does not train or deploy models. It validates the original text of all 3,400 Phase 4 development rows, measures Neutral and tag-list concentration, flags possible unread post-170-character experience text, and prepares a blinded second-annotator review-ID queue.

Run: python research/xlmr_optimization/phase5/label_quality_audit.py

The queue contains review IDs, not review text, model predictions or existing labels. For independent annotation, a coordinator must join IDs to the original unlabelled sheets; the original-label column must remain hidden until the new labels are locked. Flags only determine review priority; they are NOT asserted label mistakes.

Before further optimization: obtain an adviser decision on buyer-selected tags under S4; independently reannotate a representative sample of full-text English, Filipino and Taglish reviews; compare naturally sampled and tag-list-heavy subsets; use nested product-grouped model selection; collect authorized fresh product-disjoint final evaluation. Do not score the frozen test or the already used confirmation set for tuning. No accuracy improvement is claimed here.