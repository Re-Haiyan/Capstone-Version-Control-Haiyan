"""Human-review tooling for the sentiment data (the parts only people can do).

  export      write a ranked adjudication sheet and a blind 10% double-label sample
  agreement   score filled sheets: accuracy and Cohen's kappa vs the AI labels
  fresh-test  write a blank template for a new, human-labelled test set
  next-round  rank new unlabelled reviews by model uncertainty (active learning)

Outputs go to a new folder (refused if it exists). Sheets have empty human_*
columns; nothing here writes a human label.
"""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / 'evaluation/enhanced_dataset_v1/pool_enriched.csv'
SENTIMENTS = ('positive', 'negative', 'neutral', 'mixed', 'unclear')
INSTRUCTIONS = """# Human review round

Follow evaluation/ANNOTATION_GUIDE.md. Read the whole review; ignore the stars.

* adjudication.csv - AI labels shown. Fill human_sentiment (positive, negative,
  neutral, mixed or unclear) and, if any differ, human_aspects as
  `aspect=label;aspect=label` (delivery, packaging, seller_service, price,
  quality, functionality). Work top to bottom: rows are ranked by how likely
  the AI label is wrong.
* double_label.csv - AI labels hidden on purpose. Two different people should
  each fill a copy (rename to double_label_<initials>.csv) without talking.

Then run:  python scripts/review_queue.py agreement <this folder>
"""


def read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def write(path, rows, fields):
    with Path(path).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def priority(row):
    score = 3.0 * (row['ai_sentiment'] == 'unclear')
    score += 2.0 * (row['live_agrees'] == 'False')
    score += {'medium': 1.0, 'low': 2.0}.get(row['ai_confidence'], 0.0)
    score += 0.5 * (row['ai_sentiment'] == 'mixed') + 1.0 * (row['star_text_mismatch'] == 'True')
    return score


def export(args):
    rows = read(POOL)
    args.output.mkdir(parents=True)
    flagged = sorted((r for r in rows if r['needs_adjudication'] == 'True'), key=priority, reverse=True)
    for rank, row in enumerate(flagged, 1):
        row['rank'], row['priority'] = rank, priority(row)
    write(args.output / 'adjudication.csv', flagged,
          ['rank', 'priority', 'id', 'review_text', 'ai_sentiment', 'ai_confidence', 'ai_aspects',
           'live_model_label', 'human_sentiment', 'human_aspects', 'reviewer', 'notes'])
    random.seed(args.seed)
    by_label = {}
    for row in rows:
        by_label.setdefault(row['ai_sentiment'], []).append(row)
    sample = []
    for label, group in by_label.items():   # stratified so rare labels are represented
        sample += random.sample(group, max(1, round(len(group) * args.fraction)))
    random.shuffle(sample)
    write(args.output / 'double_label.csv', sample,
          ['id', 'review_text', 'human_sentiment', 'human_aspects', 'annotator', 'notes'])
    (args.output / 'README.md').write_text(INSTRUCTIONS, encoding='utf-8')
    print(f'adjudication.csv: {len(flagged)} rows; double_label.csv: {len(sample)} rows -> {args.output}')


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    observed = sum(a == b for a, b in pairs) / n
    left, right = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(left[k] * right[k] for k in left) / (n * n)
    return round((observed - expected) / (1 - expected), 4) if expected < 1 else 1.0


def three(label):
    return {'mixed': 'neutral', 'unclear': 'neutral'}.get(label, label)


def agreement(args):
    ai = {r['id']: r['ai_sentiment'] for r in read(POOL)}
    report = {}
    sheets = sorted(Path(args.folder).glob('double_label_*.csv')) + [Path(args.folder) / 'adjudication.csv']
    filled = {}
    for sheet in sheets:
        if not sheet.exists():
            continue
        done = [r for r in read(sheet) if r.get('human_sentiment', '').strip() in SENTIMENTS]
        filled[sheet.name] = {r['id']: r['human_sentiment'].strip() for r in done}
        pairs = [(ai[r['id']], r['human_sentiment'].strip()) for r in done]
        report[sheet.name] = {
            'filled': len(pairs),
            'agreement_with_ai': round(sum(a == h for a, h in pairs) / len(pairs), 4) if pairs else None,
            'kappa_5class': kappa(pairs), 'kappa_3class': kappa([(three(a), three(h)) for a, h in pairs]),
            'ai_to_human': dict(Counter(f'{a}->{h}' for a, h in pairs if a != h).most_common(10)),
        }
    doubles = [name for name in filled if name.startswith('double_label_')]
    if len(doubles) >= 2:
        a, b = filled[doubles[0]], filled[doubles[1]]
        shared = [(a[i], b[i]) for i in a if i in b]
        report['between_humans'] = {'sheets': doubles[:2], 'shared': len(shared),
                                    'agreement': round(sum(x == y for x, y in shared) / len(shared), 4) if shared else None,
                                    'kappa_5class': kappa(shared),
                                    'kappa_3class': kappa([(three(x), three(y)) for x, y in shared])}
    (Path(args.folder) / 'agreement.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


def fresh_test(args):
    args.output.mkdir(parents=True)
    write(args.output / 'fresh_test_template.csv', [],
          ['id', 'platform', 'product_url', 'product_category', 'review_date', 'stars', 'review_text',
           'human_sentiment', 'human_aspects', 'annotator_1', 'annotator_2', 'notes'])
    (args.output / 'README.md').write_text(
        '# Fresh human-labelled test set\n\n'
        'Purpose: an independent benchmark the models have never seen.\n\n'
        '* Collect reviews of products NOT in review_pool_10000.csv, posted after the pool was scraped.\n'
        '* Aim for 600+ reviews; keep roughly the marketplace star mix (no cherry-picking).\n'
        '* Two people label every row independently (annotator_1 / annotator_2); settle disagreements\n'
        '  together and write the agreed label in human_sentiment.\n'
        '* Report results per language (English / Tagalog / Taglish) and per platform.\n'
        '* Freeze the file before scoring any model, and never tune on it.\n', encoding='utf-8')
    print(f'Template written to {args.output}')


def next_round(args):
    sys.path.insert(0, str(ROOT / 'backend/sentiment-analysis'))
    from defaketive_sentiment.review_heads import HeadedTransformerSentimentClassifier

    classifier = HeadedTransformerSentimentClassifier()
    rows = read(args.input)
    for row in rows:
        result = classifier.predict(row['review_text'])
        probs = list(result['probabilities'].values())
        entropy = -sum(p * math.log(p) for p in probs if p > 0) / math.log(3)
        base = max(result['base_probabilities'], key=result['base_probabilities'].get)
        near_mixed = 1 - abs(result['mixed']['probability'] - result['mixed']['threshold']) * 2
        row.update(model_label=result['label'], model_confidence=result['confidence'],
                   mixed_probability=result['mixed']['probability'],
                   uncertainty=round(entropy + (base != result['label']) + max(near_mixed, 0) * 0.5, 4))
    rows.sort(key=lambda r: r['uncertainty'], reverse=True)
    args.output.mkdir(parents=True)
    write(args.output / 'to_label.csv', rows[:args.top],
          list(rows[0].keys()) + ['human_sentiment', 'human_aspects', 'reviewer', 'notes'])
    print(f'{min(args.top, len(rows))} most uncertain of {len(rows)} reviews -> {args.output / "to_label.csv"}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    e = sub.add_parser('export')
    e.add_argument('--output', type=Path, default=ROOT / 'evaluation/human_review_round1')
    e.add_argument('--fraction', type=float, default=0.10)
    e.add_argument('--seed', type=int, default=20261109)
    a = sub.add_parser('agreement')
    a.add_argument('folder', type=Path)
    f = sub.add_parser('fresh-test')
    f.add_argument('--output', type=Path, default=ROOT / 'evaluation/fresh_test_v1')
    n = sub.add_parser('next-round')
    n.add_argument('input', type=Path, help='CSV with at least id and review_text')
    n.add_argument('--output', type=Path, required=True)
    n.add_argument('--top', type=int, default=500)
    args = parser.parse_args()
    command = {'export': export, 'agreement': agreement, 'fresh-test': fresh_test, 'next-round': next_round}
    if getattr(args, 'output', None) and args.output.exists():
        parser.error('Output exists; choose a new folder so earlier rounds are preserved.')
    command[args.command](args)


if __name__ == '__main__':
    main()
