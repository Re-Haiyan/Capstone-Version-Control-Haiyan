"""Finish an explicitly machine-annotated corpus, preserving the blind original.

This is silver/pseudo-labeled data, not independent LLM or human adjudication.
Only train-split positive/negative/neutral records passing a confidence heuristic
are exported for optional experiments. Nothing trains or deploys automatically.
"""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/sentiment-analysis'))
from defaketive_sentiment import registry
from defaketive_sentiment.aspects import VERSION, analyze_aspects


def decision(base_label, probabilities, aspects):
    values = sorted(probabilities.values(), reverse=True)
    uncertain = len(values) < 2 or values[0] < .65 or values[0] - values[1] < .15
    if aspects['mixed_evidence']:
        return 'mixed', 'opposing_aspect_cues', True
    polarities = {item['label'] for item in aspects['evidence']}
    disagreement = bool(polarities and base_label not in polarities)
    if uncertain:
        return 'unclear', 'low_score_or_small_margin', True
    return base_label, 'classifier_prediction', disagreement


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'evaluation/annotation_batch_10000/annotations.csv')
    parser.add_argument('--output', type=Path, default=ROOT / 'evaluation/annotation_batch_ai_complete')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; select a new folder to preserve prior work.')
    original_hash = hashlib.sha256(args.input.read_bytes()).hexdigest()
    manifest_path = args.input.parent / 'manifest.json'
    prior = json.loads(manifest_path.read_text(encoding='utf-8'))
    with args.input.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    model = registry.load_model().sentiment
    if prior['sentiment_version'] != model.model_version or prior['aspect_version'] != VERSION:
        parser.error('Cached annotation versions differ; regenerate proposals first.')
    args.output.mkdir(parents=True)
    counts = collections.Counter()
    reasons = collections.Counter()
    flagged = 0
    exported = 0
    fields = ['id', 'platform', 'review_text', 'group_id', 'original_split', 'annotation_status',
              'ai_sentiment', 'base_sentiment', 'probabilities', 'aspect_evidence', 'aspect_coverage',
              'label_reason', 'needs_check', 'sentiment_model_version', 'aspect_version', 'training_eligible']
    with (args.output / 'ai_annotations.csv').open('w', encoding='utf-8-sig', newline='') as handle, \
         (args.output / 'silver_train.jsonl').open('w', encoding='utf-8') as training:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(rows, 1):
            if row['proposed_sentiment']:
                base = row['proposed_sentiment']
                probabilities = json.loads(row['probabilities'])
                aspects = json.loads(row['proposed_aspects'])
            else:
                result = model.analyze(row['review_text'])
                base = result['label']
                probabilities = (result.get('classifier') or {}).get('probabilities') or {}
                aspects = analyze_aspects(row['review_text'])
            for item in aspects['evidence']:
                assert row['review_text'][slice(*item['span'])] == item['text']
            label, reason, check = decision(base, probabilities, aspects)
            eligible = row['split'] == 'train' and not check and label in {'positive','negative','neutral'}
            counts[label] += 1
            reasons[reason] += 1
            flagged += check
            item = {'id': row['id'], 'platform': row['platform'], 'review_text': row['review_text'],
                    'group_id': row['group_id'], 'original_split': row['split'],
                    'annotation_status': 'ai_annotated_unverified', 'ai_sentiment': label,
                    'base_sentiment': base, 'probabilities': json.dumps(probabilities),
                    'aspect_evidence': json.dumps(aspects['evidence'], ensure_ascii=False),
                    'aspect_coverage': 'partial_cue_matches' if aspects['evidence'] else 'abstained',
                    'label_reason': reason, 'needs_check': check,
                    'sentiment_model_version': model.model_version, 'aspect_version': VERSION,
                    'training_eligible': eligible}
            writer.writerow(item)
            if eligible:
                training.write(json.dumps({'id':row['id'], 'text':row['review_text'], 'label':label,
                    'group_id':row['group_id'], 'label_source':'machine_pseudo_label',
                    'teacher_version':model.model_version}, ensure_ascii=False) + '\n')
                exported += 1
            if index % 1000 == 0:
                handle.flush()
                print(f'AI annotated {index}/{len(rows)}', flush=True)
    assert original_hash == hashlib.sha256(args.input.read_bytes()).hexdigest()
    result = {'rows':len(rows), 'label_counts':dict(counts), 'label_reasons':dict(reasons),
              'needs_check':flagged, 'silver_train_rows':exported, 'human_approved':0,
              'source_sha256':original_hash, 'source_preserved':True,
              'annotation_method':'Existing XLM-R predictions plus aspect cue rules, not independent LLM review',
              'limitations':['Pseudo-labels may reproduce existing classifier mistakes.',
                  'Confidence thresholds are heuristics, not calibrated correctness guarantees.',
                  'Blank aspect lists mean abstention, not verified absence of aspects.',
                  'All rows in this copy are exposed to prediction; none is an independent benchmark.',
                  'Original validation, blind and legacy rows are excluded from silver_train.jsonl.',
                  'No model weights changed; no accuracy improvement is claimed.']}
    (args.output / 'manifest.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
