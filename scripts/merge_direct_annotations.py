"""Validate and assemble direct AI annotations without treating them as human gold.

The part files are manually authored by AI annotators reading review text only.
This script does not assign labels or invoke a sentiment classifier.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {'positive', 'negative', 'neutral', 'mixed', 'unclear'}
CONFIDENCES = {'high', 'medium', 'low'}
ASPECTS = {'delivery', 'packaging', 'seller_service', 'price', 'quality', 'functionality'}


def parse_aspects(value):
    result = {}
    for pair in value.split(';') if value.strip() else []:
        key, separator, label = pair.strip().partition('=')
        if not separator or key not in ASPECTS or label not in LABELS or key in result:
            raise ValueError(f'Invalid or duplicate aspect: {pair!r}')
        result[key] = label
    return result


def read_parts(folder, expected_ids):
    annotations = {}
    hashes = {}
    for part in range(1, 11):
        path = folder / f'part_{part}.tsv'
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle, delimiter='\t')
            if reader.fieldnames != ['id', 'sentiment', 'confidence', 'aspects']:
                raise ValueError(f'{path.name}: invalid header')
            rows = list(reader)
        ids = {f'R{i:05}' for i in range((part - 1) * 1000 + 1, part * 1000 + 1)}
        if len(rows) != 1000 or {row['id'] for row in rows} != ids:
            raise ValueError(f'{path.name}: expected exactly 1000 assigned IDs')
        for row in rows:
            if row['id'] in annotations or row['id'] not in expected_ids:
                raise ValueError(f"Duplicate/unknown ID: {row['id']}")
            if row['sentiment'] not in LABELS or row['confidence'] not in CONFIDENCES:
                raise ValueError(f"{row['id']}: invalid label/confidence")
            if None in row or row['aspects'] is None:
                raise ValueError(f"{row['id']}: wrong number of TSV fields")
            row['aspects'] = parse_aspects(row['aspects'])
            annotations[row['id']] = row
    if set(annotations) != expected_ids:
        raise ValueError('Incomplete annotation coverage')
    return annotations, hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parts', type=Path, default=ROOT / 'evaluation/annotation_batch_ai_direct')
    parser.add_argument('--output', type=Path, default=ROOT / 'evaluation/annotation_batch_ai_direct/assembled')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; use a new path to preserve previous annotations.')
    source = ROOT / 'evaluation/review_pool_10000.csv'
    original = ROOT / 'evaluation/annotation_batch_10000/annotations.csv'
    with source.open(encoding='utf-8-sig', newline='') as handle:
        reviews = list(csv.DictReader(handle))
    with original.open(encoding='utf-8-sig', newline='') as handle:
        queue = {row['id']: row for row in csv.DictReader(handle)}
    expected = {row['id'] for row in reviews}
    if len(reviews) != 10000 or len(expected) != 10000 or set(queue) != expected:
        parser.error('Expected 10,000 unique matching source IDs.')
    if any(row['review_text'] != queue[row['id']]['review_text'] for row in reviews):
        parser.error('Source text differs from original annotation queue.')
    annotations, hashes = read_parts(args.parts, expected)
    labels, confidence, topics, splits = Counter(), Counter(), Counter(), Counter()
    records = []
    disagreements = 0
    for source_row in reviews:
        identifier = source_row['id']
        annotation, prior = annotations[identifier], queue[identifier]
        label = annotation['sentiment']
        labels[label] += 1
        confidence[annotation['confidence']] += 1
        topics.update(annotation['aspects'].keys())
        splits[prior['split']] += 1
        difference = bool(prior['proposed_sentiment'] and prior['proposed_sentiment'] != label)
        disagreements += difference
        records.append({'id': identifier, 'platform': source_row['platform'],
            'review_text': source_row['review_text'], 'group_id': prior['group_id'],
            'original_split': prior['split'], 'ai_sentiment': label,
            'ai_confidence': annotation['confidence'], 'ai_aspects': annotation['aspects'],
            'annotation_source': 'direct_ai_text_review', 'human_approved': False,
            'needs_adjudication': annotation['confidence'] != 'high' or label == 'unclear' or difference,
            'differs_from_previous_proposal': difference})
    args.output.mkdir(parents=True)
    with (args.output / 'annotations.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        for row in records:
            writer.writerow({**row, 'ai_aspects': json.dumps(row['ai_aspects'], ensure_ascii=False)})
    # Keep every original split separate, with source/provenance on every record.
    for split in splits:
        with (args.output / f'{split}.jsonl').open('w', encoding='utf-8') as handle:
            for row in records:
                if row['original_split'] == split:
                    handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    manifest = {'rows': len(records), 'labels': dict(labels), 'confidence': dict(confidence),
        'aspect_mentions': dict(topics), 'original_splits': dict(splits),
        'needs_adjudication': sum(row['needs_adjudication'] for row in records),
        'disagreements_with_previous_proposals': disagreements,
        'human_approved': 0, 'method': 'Direct parallel AI review of full review text; no ratings or proposed labels shown',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'original_queue_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
        'part_sha256': hashes,
        'limitations': ['AI annotations are fallible silver labels, not human gold.',
            'Confidence is annotator judgment, not a calibrated probability.',
            'Aspect labels do not include independently annotated evidence spans.',
            'This copy labels former blind rows; it is not an untouched evaluation benchmark.',
            'Human adjudication and a fresh independent test are needed before accuracy claims.',
            'No production model weights were changed.']}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({key:value for key,value in manifest.items() if key != 'part_sha256'}, indent=2))


if __name__ == '__main__':
    main()
