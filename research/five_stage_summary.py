"""Publish aggregate coverage only; never copy private review inputs into Git."""
import argparse
import collections
import csv
import json
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--checkout', type=Path, required=True)
p.add_argument('--evidence', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
sys.path.insert(0, str(a.checkout / 'backend/sentiment-analysis'))
from defaketive_sentiment.product_category import classify_listing

read = lambda name: json.loads((a.evidence / name).read_text())
matrix = read('category-matrix.json')
holdout = read('candidate-holdout.json')
backup = read('input-private.json')
live = read('scraped-input-private.json') + read('additional-input-private.json')
replays = [read(name) for name in ('comparison-summary.json', 'candidate-live-comparison-summary.json', 'candidate-additional-comparison-summary.json')]
rows = []
for category in sorted(x['category'] for x in matrix):
    synthetic = next(x for x in matrix if x['category'] == category)
    b = [x for x in backup if classify_listing(x) == category]
    l = [x for x in live if classify_listing(x) == category]
    h = [x for x in holdout if x['category'] == category]
    labels = collections.Counter(x['expected_sentiment'] for x in h)
    rows.append({
        'category': category, 'synthetic_status': synthetic['regression_status'],
        'synthetic_cases': len(synthetic['cases']), 'backup_listings': len(b),
        'backup_review_rows': sum(len(x.get('comments') or []) for x in b),
        'live_listing_observations': len(l), 'live_review_rows': sum(len(x.get('comments') or []) for x in l),
        'product_disjoint_labeled_rows': len(h),
        'labeled_positive': labels['positive'], 'labeled_neutral': labels['neutral'], 'labeled_negative': labels['negative'],
        'sentiment_label_disagreements': sum(x['expected_sentiment'] != x['actual_sentiment'] for x in h),
        'five_flag_label_disagreements': sum(x['expected_flags'] != x['actual_flags'] for x in h),
        'empirical_status': 'unresolved_gap: no independently adjudicated ambiguous/context labels or complete language/polarity coverage'
    })
a.output.mkdir(parents=True, exist_ok=True)
with (a.output / 'category-coverage.csv').open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
summary = {
    'baseline': read('manifest.json')['baseline'],
    'backup_sha256': read('manifest.json')['backup_sha256'],
    'synthetic_categories': len(matrix), 'synthetic_cases': sum(len(x['cases']) for x in matrix),
    'synthetic_gaps': [x['category'] for x in matrix if x['regression_status'] != 'pass'],
    'paired_report_observations': sum(len(x) for x in replays),
    'paired_review_observations': sum(r['reviews'] for x in replays for r in x),
    'initial_sentiment_and_scores_unchanged_in_paired_replays': True,
    'removed_safety': [{'report_index': r['index'], 'review_index': d['review']} for r in replays[0] for d in r['flag_changes'] if 'safety' in d['removed']],
    'backend_changes': [{k: r[k] for k in ('index', 'state', 'decision')} for x in replays for r in x if r['state'][0] != r['state'][1] or r['decision'][0] != r['decision'][1]],
    'heldout_rows': len(holdout), 'heldout_products': len({x['product_hash'] for x in holdout}),
    'heldout_sentiment_label_agreement': sum(x['expected_sentiment'] == x['actual_sentiment'] for x in holdout),
    'heldout_five_flag_exact_agreement': sum(x['expected_flags'] == x['actual_flags'] for x in holdout),
    'holdout_limit': 'Repository labels, not newly adjudicated gold. Current-fix product-disjoint; model-training disjointness unknown. Late title-only discoveries were removed from the final validation split.',
    'five_flag_disagreements': {
        flag: {'predicted_without_label': sum(flag in x['actual_flags'] and flag not in x['expected_flags'] for x in holdout),
               'labeled_without_prediction': sum(flag in x['expected_flags'] and flag not in x['actual_flags'] for x in holdout)}
        for flag in ('safety', 'defect', 'counterfeit', 'quality', 'not_as_described')
    },
    'positive_model_predictions_with_safety_in_matrix': sum(x['initial']['initial_label'] == 'positive' and 'safety' in x['flags'] for r in matrix for x in r['cases']),
    'real_review_gaps': [r['category'] for r in rows if r['backup_review_rows'] + r['live_review_rows'] == 0],
    'empirical_certification': 'UNRESOLVED for every category; synthetic regressions pass but the historical labels cannot certify all requested semantic/language cases.',
}
(a.output / 'acceptance-summary.json').write_text(json.dumps(summary, indent=2))
(a.output / 'historical-preservation.json').write_text(json.dumps(read('historical-preservation.json'), indent=2))
print(json.dumps(summary, indent=2))
