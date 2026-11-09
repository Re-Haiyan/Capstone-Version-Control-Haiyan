"""Train learned heads on the shipped XLM-R encoder and gate them against it.

The served ONNX model already returns its last hidden layer (`hidden_states`).
This script embeds every row of evaluation/enhanced_dataset_v1 once (cached),
then fits small scikit-learn heads on [mean embedding, base-model probabilities]:

  sentiment3  negative / neutral / positive, domain-adapted with marketplace rows
  mixed       does the review both praise and complain (binary, tuned threshold)
  aspects     per topic: is it discussed (binary) and its polarity

Nothing here changes the served model. The output folder gets a manifest whose
`qualified_for_integration` is true only if the preregistered gate passes:

  * FiReCS official test macro F1 >= the current model's
  * marketplace (test_pool) macro F1 >= the current model's + 0.02
  (hazard regressions are checked separately by scripts/check_review_heads.py)

Model selection uses the validation split only; test splits are scored once.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_recall_fscore_support
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/sentiment-analysis'))
from defaketive_sentiment.review_heads import (  # noqa: E402
    ASPECTS, HEADS_VERSION, SENTIMENT_LABELS, encode, feature_vector)
from defaketive_sentiment.transformer_sentiment import TransformerSentimentClassifier  # noqa: E402

DATA = ROOT / 'evaluation/enhanced_dataset_v1'
ANNOTATIONS = ROOT / 'evaluation/annotation_batch_ai_direct/assembled/annotations.csv'
CONFIDENCE_WEIGHT = {'high': 1.0, 'medium': 0.6, 'low': 0.3, '': 1.0}
C_GRID = (0.03, 0.1, 0.3, 1.0)


def load_rows():
    with (DATA / 'combined.csv').open(encoding='utf-8', newline='') as handle:
        rows = [r for r in csv.DictReader(handle) if r['trainable'] == 'True']
    with ANNOTATIONS.open(encoding='utf-8-sig', newline='') as handle:
        aspects = {r['id']: json.loads(r['ai_aspects']) for r in csv.DictReader(handle)}
    for row in rows:
        row['aspects'] = aspects.get(row['pool_id']) if row['pool_id'] else None
    return rows


def embed_all(rows, classifier, cache):
    if cache.exists():
        data = np.load(cache)
        if list(data['hashes']) == [r['text_hash'] for r in rows]:
            return data['embeddings'], data['probabilities']
    embeddings = np.zeros((len(rows), 768), dtype=np.float32)
    probabilities = np.zeros((len(rows), 3), dtype=np.float32)
    for index, row in enumerate(rows):
        embeddings[index], probabilities[index] = encode(classifier, row['text'])
        if index % 1000 == 0:
            print(f'embedded {index}/{len(rows)}', flush=True)
    np.savez_compressed(cache, hashes=np.array([r['text_hash'] for r in rows]),
                        embeddings=embeddings, probabilities=probabilities)
    return embeddings, probabilities


def weight(row):
    value = 1.0 if row['label_quality'] == 'human' else CONFIDENCE_WEIGHT[row['pool_confidence']]
    return value * (0.5 if row['is_template'] == 'True' else 1.0)


def fit(features, target, weights, C):
    model = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000, class_weight='balanced'))
    model.fit(features, target, logisticregression__sample_weight=weights)
    return model


def macro_f1(truth, predicted):
    return round(float(f1_score(truth, predicted, labels=SENTIMENT_LABELS, average='macro')), 4)


def per_class(truth, predicted, labels):
    p, r, f, s = precision_recall_fscore_support(truth, predicted, labels=labels, zero_division=0)
    return {label: {'precision': round(float(a), 4), 'recall': round(float(b), 4),
                    'f1': round(float(c), 4), 'support': int(d)} for label, a, b, c, d in zip(labels, p, r, f, s)}


def best_threshold(truth, scores):
    best = (0.0, 0.5)
    for threshold in np.arange(0.2, 0.81, 0.02):
        best = max(best, (f1_score(truth, scores >= threshold, zero_division=0), round(float(threshold), 2)))
    return best[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'backend/sentiment-analysis/models/review_heads_v1')
    parser.add_argument('--cache', type=Path, default=DATA / 'embeddings_cache.npz')
    parser.add_argument('--embed-only', action='store_true')
    args = parser.parse_args()
    if args.output.exists() and not args.embed_only:
        parser.error('Output exists; choose a new folder so earlier heads are preserved.')

    classifier = TransformerSentimentClassifier()
    rows = load_rows()
    embeddings, base = embed_all(rows, classifier, args.cache)
    if args.embed_only:
        return
    X = np.hstack([embeddings, np.log(np.clip(base, 1e-6, 1))])
    assert X.shape[1] == feature_vector(embeddings[0], base[0]).shape[0]
    split = np.array([r['split'] for r in rows])
    label3 = np.array([r['label3'] for r in rows])
    weights = np.array([weight(r) for r in rows])
    train, valid = split == 'train', split == 'validation'
    base_label = np.array(SENTIMENT_LABELS)[base.argmax(axis=1)]

    # 1. Sentiment head, C chosen on validation macro F1.
    search = {}
    for C in C_GRID:
        model = fit(X[train], label3[train], weights[train], C)
        search[C] = macro_f1(label3[valid], model.predict(X[valid]))
    C = max(search, key=search.get)
    sentiment = fit(X[train], label3[train], weights[train], C)

    # 2. Mixed detector on rows whose labels distinguish mixed (SentiTaglish or pool).
    has4 = np.array([bool(r['label_sentitaglish'] or r['label_pool']) for r in rows])
    is_mixed = np.array([r['label4'] == 'mixed' for r in rows])
    mixed_search = {}
    for mC in C_GRID:
        m = fit(X[train & has4], is_mixed[train & has4], weights[train & has4], mC)
        mixed_search[mC] = f1_score(is_mixed[valid & has4], m.predict(X[valid & has4]), zero_division=0)
    mC = max(mixed_search, key=mixed_search.get)
    mixed = fit(X[train & has4], is_mixed[train & has4], weights[train & has4], mC)
    mixed_threshold = best_threshold(is_mixed[valid & has4], mixed.predict_proba(X[valid & has4])[:, 1])

    # 3. Aspect heads on pool rows (the only source with aspect labels).
    pool = np.array([r['aspects'] is not None for r in rows])
    aspect_models, aspect_report = {}, {}
    for aspect in ASPECTS:
        mention = np.array([bool(r['aspects']) and aspect in r['aspects'] for r in rows])
        mm = fit(X[train & pool], mention[train & pool], weights[train & pool], 0.1)
        threshold = best_threshold(mention[valid & pool], mm.predict_proba(X[valid & pool])[:, 1])
        polarity = np.array([(r['aspects'] or {}).get(aspect, '') for r in rows])
        has_pol = train & pool & mention & np.isin(polarity, ['positive', 'negative', 'mixed'])
        pm = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=3000, class_weight='balanced'))
        pm.fit(X[has_pol], polarity[has_pol], logisticregression__sample_weight=weights[has_pol])
        aspect_models[aspect] = {'mention': mm, 'threshold': threshold, 'polarity': pm}

    # 4. Score the test splits once.
    report = {}
    for name in ('test_firecs', 'test_pool', 'validation'):
        sel = split == name
        truth = label3[sel]
        candidate = sentiment.predict(X[sel])
        report[name] = {
            'rows': int(sel.sum()),
            'current_macro_f1': macro_f1(truth, base_label[sel]),
            'candidate_macro_f1': macro_f1(truth, candidate),
            'current_per_class': per_class(truth, base_label[sel], SENTIMENT_LABELS),
            'candidate_per_class': per_class(truth, candidate, SENTIMENT_LABELS),
        }
        sel4 = sel & has4
        if sel4.any():
            predicted = mixed.predict_proba(X[sel4])[:, 1] >= mixed_threshold
            p, r, f, _ = precision_recall_fscore_support(is_mixed[sel4], predicted, average='binary', zero_division=0)
            report[name]['mixed'] = {'rows': int(sel4.sum()), 'precision': round(float(p), 4),
                                     'recall': round(float(r), 4), 'f1': round(float(f), 4)}
    sel = (split == 'test_pool') & pool
    for aspect, heads in aspect_models.items():
        mention = np.array([bool(r['aspects']) and aspect in r['aspects'] for r in rows])[sel]
        guess = heads['mention'].predict_proba(X[sel])[:, 1] >= heads['threshold']
        p, r, f, _ = precision_recall_fscore_support(mention, guess, average='binary', zero_division=0)
        polarity = np.array([(r2['aspects'] or {}).get(aspect, '') for r2 in rows])[sel]
        both = mention & guess & np.isin(polarity, ['positive', 'negative', 'mixed'])
        accuracy = float((heads['polarity'].predict(X[sel][both]) == polarity[both]).mean()) if both.any() else None
        aspect_report[aspect] = {'mention_precision': round(float(p), 4), 'mention_recall': round(float(r), 4),
                                 'mention_f1': round(float(f), 4),
                                 'polarity_accuracy': round(accuracy, 4) if accuracy is not None else None}

    firecs, market = report['test_firecs'], report['test_pool']
    gate = {
        'rule': 'test_firecs macro F1 >= current AND test_pool macro F1 >= current + 0.02',
        'firecs_ok': firecs['candidate_macro_f1'] >= firecs['current_macro_f1'],
        'marketplace_ok': market['candidate_macro_f1'] >= market['current_macro_f1'] + 0.02,
    }
    gate['passed'] = gate['firecs_ok'] and gate['marketplace_ok']

    args.output.mkdir(parents=True)
    files = {}
    joblib.dump(sentiment, args.output / 'sentiment.joblib')
    joblib.dump({'model': mixed, 'threshold': mixed_threshold}, args.output / 'mixed.joblib')
    joblib.dump(aspect_models, args.output / 'aspects.joblib')
    for name in ('sentiment.joblib', 'mixed.joblib', 'aspects.joblib'):
        files[name] = hashlib.sha256((args.output / name).read_bytes()).hexdigest()
    manifest = {
        'version': HEADS_VERSION, 'built_at': datetime.now(timezone.utc).isoformat(),
        'encoder_model_version': classifier.model_version,
        'training_data': json.loads((DATA / 'manifest.json').read_text(encoding='utf-8'))['input_sha256'],
        'training_rows': {k: int(v) for k, v in Counter(split).items()},
        'features': '768-d mean last hidden layer + log base-model probabilities, standardized',
        'weights': 'human 1.0; AI label high 1.0 / medium 0.6 / low 0.3; template reviews x0.5',
        'sentiment_C_search': {str(k): v for k, v in search.items()}, 'sentiment_C': C,
        'mixed_C': mC, 'mixed_threshold': mixed_threshold,
        'aspect_thresholds': {a: h['threshold'] for a, h in aspect_models.items()},
        'evaluation': report, 'aspects_test_pool': aspect_report, 'gate': gate,
        'qualified_for_integration': gate['passed'], 'files': files,
        'caveats': ['test_pool labels are AI silver labels, not human gold.',
                    'Current-model scores here are text-only (no star-rating adjustment).',
                    'Hazard flags must be re-checked with scripts/check_review_heads.py.'],
    }
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({k: manifest[k] for k in ('evaluation', 'aspects_test_pool', 'gate', 'sentiment_C_search',
                                               'mixed_threshold')}, indent=2))


if __name__ == '__main__':
    main()
