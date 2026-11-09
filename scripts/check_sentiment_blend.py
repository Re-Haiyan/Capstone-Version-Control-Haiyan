"""End-to-end check of the default sentiment blend against the shipped model.

Both run through registry.load_model with star ratings, as the app does:
  * shipped = DEFAKETIVE_SENTIMENT_BLEND=0 and DEFAKETIVE_REVIEW_EXTRAS=0
  * blend   = the default
Reports macro F1 with paired bootstrap 95% intervals for the difference, label
changes, and every hazard-flag difference (any difference fails the check).
Writes backend/sentiment-analysis/models/sentiment_blend_v1/app_check.json.
"""
import csv
import json
import os
from pathlib import Path
import sys

import numpy as np
from sklearn.metrics import f1_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/sentiment-analysis'))
from defaketive_sentiment import registry  # noqa: E402

LABELS = ['negative', 'neutral', 'positive']


def macro(t, p):
    return f1_score(t, p, labels=LABELS, average='macro')


def bootstrap(truth, a, b, n=2000, seed=7):
    rng = np.random.default_rng(seed)
    truth, a, b = map(np.array, (truth, a, b))
    diffs = []
    for _ in range(n):
        i = rng.integers(0, len(truth), len(truth))
        diffs.append(macro(truth[i], b[i]) - macro(truth[i], a[i]))
    return [round(float(np.percentile(diffs, 2.5)), 4), round(float(np.percentile(diffs, 97.5)), 4)]


def tags(analysis):
    return sorted(set(analysis.get('review_tags') or []) | set(analysis.get('review_extra_tags') or []))


def load(blend):
    os.environ['DEFAKETIVE_SENTIMENT_BLEND'] = '1' if blend else '0'
    os.environ['DEFAKETIVE_REVIEW_EXTRAS'] = '1' if blend else '0'
    registry.clear_cache()
    return registry.load_model(sentiment=registry.XLMR_SENTIMENT)


def main():
    shipped, blend = load(False), load(True)
    assert 'blend' in blend.model_version, 'blend files missing: default fell back'
    sets = {}
    for name in ('gold_labels_200.csv', 'heldout_labels_100.csv'):
        with (ROOT / 'evaluation' / name).open(encoding='utf-8-sig', newline='') as handle:
            sets[name] = [(r['review_text'], r['stars'], r['sentiment']) for r in csv.DictReader(handle)]
    with (ROOT / 'evaluation/enhanced_dataset_v1/pool_enriched.csv').open(encoding='utf-8', newline='') as h:
        sets['test_pool_ai_labels'] = [(r['review_text'], r['stars'], r['ai_sentiment3']) for r in csv.DictReader(h)
                                       if r['original_split'] == 'test_candidate' and r['ai_sentiment3']]
    report, hazard = {}, []
    team = {'truth': [], 'a': [], 'b': []}
    for name, rows in sets.items():
        truth, a_labels, b_labels, changes = [], [], [], {}
        for text, stars, label in rows:
            a = shipped.analyze(text, rating=int(stars))
            b = blend.analyze(text, rating=int(stars))
            if tags(a) != tags(b):
                hazard.append({'set': name, 'text': text[:160], 'shipped': tags(a), 'blend': tags(b)})
            truth.append(label); a_labels.append(a['label']); b_labels.append(b['label'])
            if a['label'] != b['label']:
                key = f"{a['label']}->{b['label']}"
                changes[key] = changes.get(key, 0) + 1
        if name != 'test_pool_ai_labels':
            team['truth'] += truth; team['a'] += a_labels; team['b'] += b_labels
        report[name] = {'rows': len(rows), 'shipped_macro_f1': round(macro(truth, a_labels), 4),
                        'blend_macro_f1': round(macro(truth, b_labels), 4),
                        'difference_95ci': bootstrap(truth, a_labels, b_labels), 'label_changes': changes}
        print(name, report[name], flush=True)
    with (ROOT / 'evaluation/enhanced_dataset_v1/combined.csv').open(encoding='utf-8', newline='') as h:
        firecs = [(r['text'], r['label3']) for r in csv.DictReader(h) if r['split'] == 'test_firecs']
    truth = [label for _, label in firecs]
    a_labels = [shipped.sentiment.analyze(text)['label'] for text, _ in firecs]
    b_labels = [blend.sentiment.analyze(text)['label'] for text, _ in firecs]
    report['test_firecs_text_only'] = {'rows': len(firecs), 'shipped_macro_f1': round(macro(truth, a_labels), 4),
                                       'blend_macro_f1': round(macro(truth, b_labels), 4),
                                       'difference_95ci': bootstrap(truth, a_labels, b_labels)}
    print('test_firecs', report['test_firecs_text_only'], flush=True)
    report['team_combined'] = {'rows': len(team['truth']),
                               'shipped_macro_f1': round(macro(team['truth'], team['a']), 4),
                               'blend_macro_f1': round(macro(team['truth'], team['b']), 4),
                               'difference_95ci': bootstrap(team['truth'], team['a'], team['b'])}
    result = {'shipped_model_version': shipped.model_version, 'blend_model_version': blend.model_version,
              'sets': report, 'hazard_flag_differences': len(hazard), 'hazard_examples': hazard[:20],
              'hazard_unchanged': not hazard}
    out = ROOT / 'backend/sentiment-analysis/models/sentiment_blend_v1/app_check.json'
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('hazard_flag_differences', 'hazard_unchanged')}),
          json.dumps(report['team_combined']))
    sys.exit(0 if result['hazard_unchanged'] else 1)


if __name__ == '__main__':
    main()
