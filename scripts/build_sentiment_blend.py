"""Build the sentiment blend chosen by scripts/sentiment_boost_experiments.py.

Winner under the pre-written rule: template fields rewritten as sentences, a
logistic head trained on human-labelled rows only (C=0.03), blended 0.6 shipped
/ 0.4 head. Settings come from evaluation/sentiment_boost_v1/report.json (tuned
on human validation rows). Writes backend/sentiment-analysis/models/
sentiment_blend_v1/ (refuses to overwrite).
"""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/sentiment-analysis'))
from defaketive_sentiment.review_heads import encode, feature_vector, template_sentences  # noqa: E402
from defaketive_sentiment.transformer_sentiment import TransformerSentimentClassifier  # noqa: E402

DATA = ROOT / 'evaluation/enhanced_dataset_v1'
REPORT = ROOT / 'evaluation/sentiment_boost_v1/report.json'
OUT = ROOT / 'backend/sentiment-analysis/models/sentiment_blend_v1'
WINNER = 'blend_human+tmpl_sentences'


def main():
    if OUT.exists():
        sys.exit(f'{OUT} exists; choose a new folder.')
    report = json.loads(REPORT.read_text(encoding='utf-8'))
    assert report['best_qualified'] == WINNER and report['qualified'][WINNER]
    C = report['choices']['heads_human+tmpl_sentences']['C']
    weight = report['choices'][WINNER]['w']

    with (DATA / 'combined.csv').open(encoding='utf-8', newline='') as handle:
        rows = [r for r in csv.DictReader(handle) if r['trainable'] == 'True']
    with np.load(DATA / 'embeddings_cache.npz') as data:  # read once: npz members decompress per access
        cache = {key: data[key] for key in ('hashes', 'embeddings', 'probabilities')}
    assert list(cache['hashes']) == [r['text_hash'] for r in rows]
    pick = [i for i, r in enumerate(rows) if r['split'] == 'train' and r['label_quality'] == 'human']
    classifier = TransformerSentimentClassifier()
    X, rewritten = [], 0
    for i in pick:
        text = rows[i]['text']
        if template_sentences(text) != text:
            emb, probs = encode(classifier, template_sentences(text))
            rewritten += 1
        else:
            emb, probs = cache['embeddings'][i], cache['probabilities'][i]
        X.append(feature_vector(emb, probs))
    y = np.array([rows[i]['label3'] for i in pick])
    head = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000, class_weight='balanced'))
    head.fit(np.array(X), y)

    OUT.mkdir(parents=True)
    joblib.dump(head, OUT / 'head.joblib')
    manifest = {
        'version': 'sentiment-blend-1.0.0',
        'built_at': datetime.now(timezone.utc).isoformat(),
        'encoder_model_version': classifier.model_version,
        'recipe': 'label = argmax((1-w)*shipped + w*head) on text with form fields rewritten as sentences',
        'weight': weight, 'C': C, 'template_style': 'sentences',
        'training_rows': len(pick), 'training_rows_rewritten': rewritten,
        'training_labels': 'human only (FiReCS train / SentiTaglish), label3',
        'selection': {'report': 'evaluation/sentiment_boost_v1/report.json', 'candidate': WINNER,
                      'results': report['results'][WINNER], 'shipped': report['results']['shipped'],
                      'rule': report['rule']},
        'files': {'head.joblib': hashlib.sha256((OUT / 'head.joblib').read_bytes()).hexdigest()},
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({k: manifest[k] for k in ('weight', 'C', 'training_rows', 'training_rows_rewritten')}))


if __name__ == '__main__':
    main()
