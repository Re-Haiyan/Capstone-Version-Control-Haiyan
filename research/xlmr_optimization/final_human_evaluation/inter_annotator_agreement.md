# Inter-annotator agreement: NOT REPORTED

**Status: WITHHELD.** Human provenance is not substantiated (`annotation_provenance.md`), so no inter-annotator reliability figure (raw agreement, Cohen's kappa, interval, per-class agreement, tag agreement) is reported as human agreement, and `agreement_confusion_matrix.csv` was not generated. The scoring code (`sentiment_agreement.py score`) is ready and was exercised on synthetic fixtures only (`tests/test_sentiment_agreement.py`); it will run on genuine sheets once provenance exists.

What can be stated without claiming human reliability: the two returned files differ on 37 of 400 reviews in the label (and in the same 37 reviews' tags): 31 positive versus neutral, 4 unclear versus classified, 1 negative versus neutral, 1 mixed versus single-polarity. Low-confidence rows: 27 (sheet A) and 25 (sheet B). These describe the two files; they do not measure how reliable human annotators are. See `disagreement_cases.csv`.

(An earlier chat message quoted a kappa from these files; it was explicitly marked unverified and is not carried into any research document.)

Table A of `chapter4_objective5_results.md` stays NOT YET VERIFIED until two independent, declared human sheets exist.
