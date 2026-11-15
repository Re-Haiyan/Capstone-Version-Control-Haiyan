# Chapter 5: findings (restricted to completed, verified results)

1. The deployed XLM-RoBERTa sentiment classifier (vocabulary-pruned ONNX int8) reproduces its published score on FiReCS: accuracy 0.833 and macro F1 0.833 on 3,147 reviews (published labels).
2. Against team-supplied marketplace labels of unverified provenance the same model scores macro F1 0.836 on 150 older reviews and 0.570 on 846 reviews; the neutral class is the weak point (F1 0.186 on the larger file). These figures describe agreement with those labels, not verified accuracy.
3. Marketplace-fine-tuned candidates raised the 846-row score by about 0.10 to 0.11 and lowered the older-150 score by a similar amount. With unverified, mutually inconsistent labels no candidate is shown to generalise better, and no replacement is recommended.
4. A frozen 400-review final test, an approved annotation policy (v1) and an annotation workflow exist. The returned annotation sheets could not be shown to be independent human work, so inter-annotator agreement, adjudication and the final-test score are **not available**, and the 80% target is neither achieved nor refuted.
5. To complete the objective: independently labelled and adjudicated reference labels with documented provenance, then a single scoring of the pre-selected model.
