"""Compare the default app model with the opt-in review heads, end to end.

Runs both through registry.load_model (stars included, as the app does) on:
  * evaluation/gold_labels_200.csv and heldout_labels_100.csv (score.py's metric)
  * the test_pool rows of evaluation/enhanced_dataset_v1 (AI silver labels)

Hazard flags (review_tags / review_extra_tags) must be identical; any difference
is listed and makes the check fail. Writes a JSON report next to the heads.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/sentiment-analysis'))
from defaketive_sentiment import registry  # noqa: E402

FLAGS = ('defect', 'counterfeit', 'safety', 'not_as_described')
LABELS = ('negative', 'neutral', 'positive')


def macro_f1(pairs):
    scores = []
    for label in LABELS:
        tp = sum(t == label and p == label for t, p in pairs)
        fp = sum(t != label and p == label for t, p in pairs)
        fn = sum(t == label and p != label for t, p in pairs)
        scores.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return round(sum(scores) / 3, 4)


def tags(analysis):
    return sorted(set(analysis.get('review_tags') or []) | set(analysis.get('review_extra_tags') or []))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=0, help='score only the first N test_pool rows')
    args = parser.parse_args()
    base = registry.load_model(sentiment=registry.XLMR_SENTIMENT)
    heads = registry.load_model(sentiment=registry.XLMR_HEADS_SENTIMENT)
    sets = {}
    for name in ('gold_labels_200.csv', 'heldout_labels_100.csv'):
        with (ROOT / 'evaluation' / name).open(encoding='utf-8-sig', newline='') as handle:
            sets[name] = [(r['review_text'], r['stars'], r['sentiment'], r['confidence'] == 'high')
                          for r in csv.DictReader(handle)]
    with (ROOT / 'evaluation/enhanced_dataset_v1/pool_enriched.csv').open(encoding='utf-8', newline='') as handle:
        pool = [(r['review_text'], r['stars'], r['ai_sentiment3'], r['ai_confidence'] == 'high')
                for r in csv.DictReader(handle) if r['original_split'] == 'test_candidate' and r['ai_sentiment3']]
    sets['test_pool'] = pool[:args.limit] if args.limit else pool

    report, hazard_differences = {}, []
    for name, rows in sets.items():
        pairs = {'base': [], 'heads': []}
        changes = Counter()
        mixed = 0
        for text, stars, truth, high in rows:
            a = base.analyze(text, rating=int(stars))
            b = heads.analyze(text, rating=int(stars))
            if tags(a) != tags(b):
                hazard_differences.append({'set': name, 'text': text[:160], 'base': tags(a), 'heads': tags(b)})
            if high:
                pairs['base'].append((truth, a['label']))
                pairs['heads'].append((truth, b['label']))
            changes[(a['label'], b['label'])] += a['label'] != b['label']
            mixed += bool((b.get('sentiment_extra') or {}).get('mixed', {}).get('detected'))
        report[name] = {
            'rows': len(rows), 'scored_high_confidence': len(pairs['base']),
            'base_accuracy': round(sum(t == p for t, p in pairs['base']) / len(pairs['base']), 4),
            'heads_accuracy': round(sum(t == p for t, p in pairs['heads']) / len(pairs['heads']), 4),
            'base_macro_f1': macro_f1(pairs['base']), 'heads_macro_f1': macro_f1(pairs['heads']),
            'label_changes': {f'{a}->{b}': n for (a, b), n in changes.items() if n},
            'mixed_detected': mixed,
        }
    result = {'base_model_version': base.model_version, 'heads_model_version': heads.model_version,
              'sets': report, 'hazard_flag_differences': len(hazard_differences),
              'hazard_examples': hazard_differences[:20], 'hazard_unchanged': not hazard_differences}
    out = ROOT / 'backend/sentiment-analysis/models/review_heads_v1/app_check.json'
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result['hazard_unchanged'] else 1)


if __name__ == '__main__':
    main()
