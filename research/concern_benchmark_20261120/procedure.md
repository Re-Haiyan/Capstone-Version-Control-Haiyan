# Concern development and one-time reserved validation

Baseline: `d3fd020f7185c732ac1fb0c22963306331af8aaf`.
Development reference: ChatGPT annotations, frozen SHA-256
`2a1531cb5208c92ba22ba49abff3a3a714c4d2b8c8d1e7dce35ed0729642754f`.
These are AI labels, not independent human gold. The 300 ordinary and 100
challenge reviews are now development data. Do not claim held-out gains on them.

Snapshot SHA-256: `33bdeb6a0b23e8f83aaaa77ab04b8f4905ae46631737d890fccc71e97101d053`.
Use a read-only SQLite URI. Keep all report writes in isolated output paths.

## Freeze before reserve access

Commit code, regression tests and this procedure. Record the exact commit and
the procedure hash externally before opening the reserved JSON. Create one
blind annotation CSV from its 100 ID/title/review rows, without predictions,
ratings, category estimates or existing labels. Label all five concerns using
the original guide; record AI-assisted provenance, literal target/quotes and
ambiguous cases. Freeze this label CSV and hash before either version predicts.
It is AI-assisted validation with known prior development context, not an
independent human annotation exercise. Preserve the reserved source unchanged.

## Replay and score

Run `scripts/evaluate_concern_benchmark.py` in separate processes for baseline
and the frozen candidate, passing identical sample, labels and label hash.
Use the same Python environment and matching model artifact hashes. The runner
forces shared XLM-R, learned hazard mode, evidence keep and calibrator/adapter
OFF; network connections are disabled. It never auto-discovers reserved data.
Fail on missing/duplicate IDs, changed source text, invalid labels or nonliteral
reference quotes. Exclude ambiguous labels independently for each concern.

Report TP/FP/FN, support, exclusions, precision, recall and F1 per sample/concern;
undefined denominators are NA, never silently zero. Preserve all raw predictions.
Audit every changed safety flag and safety-positive miss, as well as each
changed excerpt's subject, negation and uncertainty. Verify initial labels and
all returned sentiment probabilities remain identical. Do not infer full-product
guidance from sampled reviews. Quality is informational and does not enter backend
verdict rules. Replay complete safety-affected reports and cube/fan controls with
original sampling metadata, and verify report/export evidence and historical
report retention in isolation.

No fixes after observing reserved results. If those results motivate a fix,
mark it as a new candidate and obtain a fresh, independently frozen holdout.
Retire this reserve from future validation. Publish limitations and any NO-GO
result; do not hide annotation disagreements or count development tests as
independent accuracy evidence. Production stays untouched.
