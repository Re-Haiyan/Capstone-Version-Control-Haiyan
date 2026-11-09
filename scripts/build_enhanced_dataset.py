"""Build a combined, de-duplicated sentiment dataset plus an enriched copy of the 10,000-review pool.

Inputs (never modified):
  * FiReCS train/test and SentiTaglish, read from the Version-1.2 branch with `git show`
    (or from --sources DIR containing the same file names);
  * evaluation/review_pool_10000.csv and the assembled direct annotations;
  * optionally, cached predictions of the live model (--live JSONL with id/label/...).

Outputs (a new folder, refused if it exists):
  combined.csv        one row per normalized text, harmonized labels, source, split
  combined_{split}.jsonl
  pool_enriched.csv   the 10,000 annotated reviews with extra columns
  manifest.json       counts, input hashes, rules used

Label rules
  label4: negative / neutral / mixed / positive (unclear kept but marked not trainable)
  label3: label4 with mixed -> neutral, the convention FiReCS itself uses
          (SentiTaglish re-labelled most FiReCS "neutral" rows as mixed).
  Where a text is in both FiReCS and SentiTaglish, label4 comes from SentiTaglish and
  label3 from FiReCS, both originals kept in their own columns.

Split rules
  test_firecs: the official FiReCS test set (benchmark - do not tune on it)
  test_pool:   pool rows that were blind test candidates
  legacy_exposed: pool rows already used in gold/held-out files (evaluation only)
  validation:  pool validation rows + a stable 10% hash slice of the other human rows
  train:       everything else
  A text that occurs in any test or legacy split is dropped from train/validation.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
SRC_FILES = {
    'firecs_train': 'sentiment-analysis/data/firecs/FiReCS_train_set.csv',
    'firecs_test': 'sentiment-analysis/data/firecs/FiReCS_test_set.csv',
    'sentitaglish': 'sentiment-analysis/data/sentitaglish/SentiTaglish_ProductsAndServices.csv',
}
FIRECS = {'0': 'negative', '1': 'neutral', '2': 'positive'}
SENTI = {'1': 'negative', '2': 'neutral', '3': 'positive', '4': 'mixed'}
TL = set('ang ng sa na nang mga yung ung ko mo niya nya siya sya ako ka po naman lang pero kasi kaso hindi di wala may '
         'ba pa din rin talaga sobrang ganda maganda pangit sira gumagana nagana dumating bilis mabilis matagal agad '
         'salamat sana tapos yun iyon kahit lahat isa dalawa binili pinadala tunog mahina malakas lowbat '
         'gamitin gamit ayaw nag mag tagal masyado medyo sakto ganun ganito'.split())
EN = set('the a an is are was were it this that and but for with not no very good bad item product quality fast '
         'slow working works received delivery seller price great nice love easy use i my you so to of in on be '
         'also will can only just really too much well perfect broken defective disappointed recommend sound '
         'battery charging charge thanks thank ordered color size small big long time day buy again worth money '
         'arrived condition expected design comfortable'.split())
TEMPLATE = re.compile(r'^([A-Z][^,]{3,60},\s*){2,}')
EMOJI = re.compile('[\U0001F300-\U0001FAFF☀-➿]')


def norm(text):
    text = unicodedata.normalize('NFKC', text).lower()
    return ' '.join(re.sub(r'[^\w\s]', ' ', text).split())


def text_hash(text):
    return hashlib.sha256(norm(text).encode('utf-8')).hexdigest()


def read_source(name, sources, ref):
    if sources:
        data = (Path(sources) / Path(SRC_FILES[name]).name).read_bytes()
    else:
        data = subprocess.run(['git', 'show', f'{ref}:{SRC_FILES[name]}'], cwd=ROOT,
                              check=True, capture_output=True).stdout
    return data, list(csv.DictReader(data.decode('utf-8-sig').splitlines()))


def language(text):
    words = norm(text).split()
    tl = sum(w in TL for w in words)
    en = sum(w in EN for w in words)
    if tl + en == 0:
        return 'unknown'
    share = tl / (tl + en)
    return 'tagalog' if share >= 0.8 else 'english' if share <= 0.2 else 'taglish'


def features(text):
    stripped = text.strip()
    return {'n_words': len(stripped.split()), 'n_chars': len(stripped),
            'has_emoji': bool(EMOJI.search(stripped)), 'is_template': bool(TEMPLATE.match(stripped)),
            'language': language(stripped)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, default=ROOT / 'evaluation/enhanced_dataset_v1')
    parser.add_argument('--sources', help='folder with the FiReCS/SentiTaglish CSVs instead of git show')
    parser.add_argument('--ref', default='origin/Version-1.2', help='git ref holding the source datasets')
    parser.add_argument('--live', type=Path, help='JSONL of live-model predictions for the pool')
    parser.add_argument('--live-version', help='model_version string of the model that made --live')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; choose a new folder so earlier builds are preserved.')

    hashes = {}
    rows = {}   # normalized hash -> record

    def record(h, text):
        return rows.setdefault(h, {'text_hash': h, 'text': text, 'sources': [], 'label_firecs': '',
                                   'label_sentitaglish': '', 'label_pool': '', 'pool_id': '',
                                   'pool_confidence': '', 'pool_split': '', 'firecs_split': ''})

    for name in ('firecs_train', 'firecs_test', 'sentitaglish'):
        data, table = read_source(name, args.sources, args.ref)
        hashes[name] = hashlib.sha256(data).hexdigest()
        for row in table:
            text = row.get('review', '')
            raw = (row.get('label') or row.get('sentiment') or '').strip().split('.')[0]
            label = (SENTI if name == 'sentitaglish' else FIRECS).get(raw)
            if not text.strip() or not label:
                continue
            rec = record(text_hash(text), text)
            if name not in rec['sources']:
                rec['sources'].append(name)
            if name == 'sentitaglish':
                rec['label_sentitaglish'] = rec['label_sentitaglish'] or label
            else:
                # A text in both FiReCS splits counts as test, so it can never leak into training.
                rec['firecs_split'] = 'test' if name == 'firecs_test' or rec['firecs_split'] == 'test' else 'train'
                rec['label_firecs'] = rec['label_firecs'] or label

    pool_path = ROOT / 'evaluation/review_pool_10000.csv'
    ann_path = ROOT / 'evaluation/annotation_batch_ai_direct/assembled/annotations.csv'
    hashes['review_pool_10000.csv'] = hashlib.sha256(pool_path.read_bytes()).hexdigest()
    hashes['assembled_annotations.csv'] = hashlib.sha256(ann_path.read_bytes()).hexdigest()
    with pool_path.open(encoding='utf-8-sig', newline='') as handle:
        pool = {r['id']: r for r in csv.DictReader(handle)}
    with ann_path.open(encoding='utf-8-sig', newline='') as handle:
        annotations = list(csv.DictReader(handle))
    live = {}
    if args.live:
        hashes['live_predictions'] = hashlib.sha256(args.live.read_bytes()).hexdigest()
        for line in args.live.open(encoding='utf-8'):
            item = json.loads(line)
            live[item['id']] = item

    for ann in annotations:
        rec = record(text_hash(ann['review_text']), ann['review_text'])
        rec['sources'].append('pool_ai_direct')
        if not rec['pool_id']:   # keep the first id of a duplicate group
            rec.update(label_pool=ann['ai_sentiment'], pool_id=ann['id'],
                       pool_confidence=ann['ai_confidence'], pool_split=ann['original_split'])

    def split_of(rec):
        if rec['firecs_split'] == 'test':
            return 'test_firecs'
        if rec['pool_split'] == 'test_candidate':
            return 'test_pool'
        if rec['pool_split'] == 'legacy_exposed':
            return 'legacy_exposed'
        if rec['pool_split'] == 'validation':
            return 'validation'
        if rec['pool_split'] == 'train':
            return 'train'
        return 'validation' if int(rec['text_hash'][:8], 16) % 10 == 0 else 'train'

    combined = []
    for rec in rows.values():
        label4 = rec['label_sentitaglish'] or rec['label_firecs'] or rec['label_pool']
        if rec['label_firecs']:
            label3 = rec['label_firecs']
        else:
            label3 = {'mixed': 'neutral'}.get(label4, label4)
        human = bool(rec['label_firecs'] or rec['label_sentitaglish'])
        disagree = bool(rec['label_pool'] and human and
                        {'mixed': 'neutral'}.get(rec['label_pool'], rec['label_pool']) != label3)
        combined.append({**{k: rec[k] for k in ('text_hash', 'text')},
                         'label4': label4, 'label3': label3 if label3 != 'unclear' else '',
                         'trainable': label4 != 'unclear',
                         'label_quality': 'human' if human else 'ai_silver',
                         'pool_confidence': rec['pool_confidence'],
                         'split': split_of(rec), 'sources': ';'.join(rec['sources']),
                         'label_firecs': rec['label_firecs'], 'label_sentitaglish': rec['label_sentitaglish'],
                         'label_pool': rec['label_pool'], 'pool_id': rec['pool_id'],
                         'sources_disagree': disagree, **features(rec['text'])})

    test_hashes = {r['text_hash'] for r in combined if r['split'] in ('test_firecs', 'test_pool', 'legacy_exposed')}
    assert all(r['text_hash'] not in test_hashes for r in combined if r['split'] in ('train', 'validation'))

    pool_rows = []
    for ann in annotations:
        src = pool[ann['id']]
        lv = live.get(ann['id'], {})
        pool_rows.append({'id': ann['id'], 'platform': ann['platform'], 'stars': src['stars'],
                          'review_text': ann['review_text'], 'group_id': ann['group_id'],
                          'original_split': ann['original_split'], 'ai_sentiment': ann['ai_sentiment'],
                          'ai_sentiment3': {'mixed': 'neutral', 'unclear': ''}.get(ann['ai_sentiment'], ann['ai_sentiment']),
                          'ai_confidence': ann['ai_confidence'], 'ai_aspects': ann['ai_aspects'],
                          'needs_adjudication': ann['needs_adjudication'],
                          'star_sentiment': 'negative' if int(src['stars']) <= 2 else 'neutral' if src['stars'] == '3' else 'positive',
                          'live_model_label': lv.get('label', ''),
                          'live_hazard_tags': ';'.join(lv.get('tags') or []),
                          'live_extra_tags': ';'.join(lv.get('extra') or []),
                          **features(ann['review_text'])})
    for row in pool_rows:
        row['star_text_mismatch'] = bool(row['ai_sentiment3'] and row['ai_sentiment3'] != row['star_sentiment']
                                         and {row['ai_sentiment3'], row['star_sentiment']} == {'negative', 'positive'})
        row['live_agrees'] = (row['live_model_label'] == row['ai_sentiment3']) if row['live_model_label'] and row['ai_sentiment3'] else ''

    args.output.mkdir(parents=True)
    for name, table in (('combined.csv', combined), ('pool_enriched.csv', pool_rows)):
        with (args.output / name).open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
    splits = Counter(r['split'] for r in combined)
    for split in splits:
        with (args.output / f'combined_{split}.jsonl').open('w', encoding='utf-8') as handle:
            for r in combined:
                if r['split'] == split:
                    handle.write(json.dumps(r, ensure_ascii=False) + '\n')

    def counts(key, table, where=lambda r: True):
        return dict(Counter(str(r[key]) for r in table if where(r)).most_common())
    manifest = {
        'built_at': datetime.now(timezone.utc).isoformat(),
        'script': 'scripts/build_enhanced_dataset.py', 'source_ref': args.sources or args.ref,
        'input_sha256': hashes,
        'live_model_version': args.live_version if live else None,
        'combined': {'rows': len(combined), 'splits': dict(splits),
                     'label4': counts('label4', combined), 'label3': counts('label3', combined),
                     'label_quality': counts('label_quality', combined),
                     'label4_by_split': {s: counts('label4', combined, lambda r, s=s: r['split'] == s) for s in splits},
                     'texts_in_more_than_one_source': sum(';' in r['sources'] for r in combined),
                     'sources_disagree': sum(r['sources_disagree'] for r in combined),
                     'language': counts('language', combined)},
        'pool_enriched': {'rows': len(pool_rows), 'language': counts('language', pool_rows),
                          'is_template': counts('is_template', pool_rows),
                          'star_text_mismatch': counts('star_text_mismatch', pool_rows),
                          'live_agrees': counts('live_agrees', pool_rows)},
        'rules': {'label3': 'mixed -> neutral (FiReCS convention); FiReCS label wins when present',
                  'label4': 'SentiTaglish > FiReCS > pool annotation',
                  'dedup': 'NFKC, lowercase, punctuation stripped, whitespace collapsed',
                  'leakage': 'no train/validation text appears in test_firecs, test_pool or legacy_exposed',
                  'language': 'heuristic stopword counts; tagalog >= 80% Tagalog hits, english <= 20%'},
        'limitations': ['Pool labels are AI silver labels, not human gold.',
                        'test_pool rows were labelled in this copy; they are not an untouched benchmark.',
                        'Language and template flags are heuristics.'],
    }
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({k: manifest[k] for k in ('combined', 'pool_enriched')}, indent=2))


if __name__ == '__main__':
    main()
