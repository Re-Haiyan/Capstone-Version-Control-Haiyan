"""Can the shipped sentiment label be improved without a GPU? Three ideas, one rule.

Candidates (all reuse the shipped XLM-R encoder; nothing is served from here):
  heads_all    logistic head on [embedding, log base probs], all training labels
  heads_human  the same head trained on human-labelled rows only (FiReCS/SentiTaglish)
  gate_*       keep the shipped label unless a head disagrees with prob >= t
  blend_*      average shipped and head probabilities with weight w
  *+tmpl       template reviews ("Battery Life:matagal Performance:good") rewritten
               before encoding, so field names stop reading as neutral fragments

Tuning (C, t, w, template style) uses ONLY the human-labelled validation rows.

Adoption rule, fixed before any result was seen: a candidate replaces the shipped
label only if, versus the shipped model,
  1. FiReCS test macro F1 (human, 3,147) is not lower, AND
  2. team-labelled marketplace macro F1 (gold 200 + held-out 100, all rows, with
     the app's star rule) is not lower, AND
  3. at least one of those two is higher by >= 0.01.
The AI-labelled pool test is reported but cannot qualify a candidate. Note: the
team-labelled sets were looked at once before (scripts/check_review_heads.py), so
they act as a final check here and are never used for tuning.
"""
import csv
import json
from pathlib import Path
import re
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/sentiment-analysis'))
from defaketive_sentiment.model import DefaketiveSentimentModel  # noqa: E402
from defaketive_sentiment.review_heads import SENTIMENT_LABELS, encode  # noqa: E402
from defaketive_sentiment.transformer_sentiment import TransformerSentimentClassifier  # noqa: E402

DATA = ROOT / 'evaluation/enhanced_dataset_v1'
OUT = ROOT / 'evaluation/sentiment_boost_v1'
CONFIDENCE_WEIGHT = {'high': 1.0, 'medium': 0.6, 'low': 0.3, '': 1.0}
LABELS = np.array(SENTIMENT_LABELS)
FIELD = re.compile(r'(?:^|(?<=[\s.,;!]))[^\w\s]?\s*([A-Z][A-Za-z]+(?: [A-Za-z]+){0,3}) ?:\s*')


def template_strip(text):
    """Drop field names, keep the buyer's words: 'Battery Life:matagal' -> 'matagal.'"""
    names = set(FIELD.findall(text))
    if not names:
        return text
    parts = [p.strip(' .,;') for p in FIELD.split(text)]
    kept = [p for p in parts if p and p not in names]
    return '. '.join(kept) + '.' if kept else text


def template_sentences(text):
    """Keep field names as plain sentences: 'Battery Life: matagal.'"""
    return FIELD.sub(lambda m: '. ' + m.group(1) + ': ', text).lstrip('. ').strip()


TEMPLATES = {'raw': lambda t: t, 'strip': template_strip, 'sentences': template_sentences}


def macro(truth, predicted):
    return round(float(f1_score(truth, predicted, labels=SENTIMENT_LABELS, average='macro')), 4)


def weight(row):
    value = 1.0 if row['label_quality'] == 'human' else CONFIDENCE_WEIGHT[row['pool_confidence']]
    return value * (0.5 if row['is_template'] == 'True' else 1.0)


def fit(X, y, w, C):
    model = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=3000, class_weight='balanced'))
    model.fit(X, y, logisticregression__sample_weight=w)
    return model


def features(emb, probs):
    return np.hstack([emb, np.log(np.clip(probs, 1e-6, 1))])


class Fixed:
    """Feeds a chosen label through DefaketiveSentimentModel so the app's star rule applies."""
    wants_raw_text = True
    label_source = 'experiment'
    model_version = 'experiment'

    def __init__(self):
        self.answer = None

    def predict(self, text):
        return self.answer


def main():
    if OUT.exists():
        sys.exit(f'{OUT} exists; choose a new folder so earlier results are preserved.')
    classifier = TransformerSentimentClassifier()
    with (DATA / 'combined.csv').open(encoding='utf-8', newline='') as handle:
        rows = [r for r in csv.DictReader(handle) if r['trainable'] == 'True']
    cache = np.load(DATA / 'embeddings_cache.npz')
    assert list(cache['hashes']) == [r['text_hash'] for r in rows], 'embedding cache is stale'
    team = []
    for name in ('gold_labels_200.csv', 'heldout_labels_100.csv'):
        with (ROOT / 'evaluation' / name).open(encoding='utf-8-sig', newline='') as handle:
            team += [{'text': r['review_text'], 'label3': r['sentiment'], 'stars': r['stars'],
                      'high': r['confidence'] == 'high'} for r in csv.DictReader(handle)]

    # Embeddings per template style (raw from cache; other styles re-encode only changed texts).
    def embed_rows(texts, style, cached=None):
        emb = np.zeros((len(texts), 768), dtype=np.float32)
        probs = np.zeros((len(texts), 3), dtype=np.float32)
        changed = 0
        for i, text in enumerate(texts):
            new = TEMPLATES[style](text)
            if cached is not None and new == text:
                emb[i], probs[i] = cached[0][i], cached[1][i]
            else:
                emb[i], probs[i] = encode(classifier, new)
                changed += new != text
        return emb, probs, changed

    texts = [r['text'] for r in rows]
    team_texts = [r['text'] for r in team]
    E, T = {}, {}
    E['raw'] = (cache['embeddings'], cache['probabilities'])
    T['raw'] = embed_rows(team_texts, 'raw')[:2]
    rewritten = {}
    for style in ('strip', 'sentences'):
        emb, probs, n = embed_rows(texts, style, E['raw'])
        E[style] = (emb, probs)
        temb, tprobs, tn = embed_rows(team_texts, style)
        T[style] = (temb, tprobs)
        rewritten[style] = {'combined_rows': n, 'team_rows': tn}
        print(f'{style}: re-encoded {n} dataset rows, {tn} team rows', flush=True)

    split = np.array([r['split'] for r in rows])
    y = np.array([r['label3'] for r in rows])
    w = np.array([weight(r) for r in rows])
    human = np.array([r['label_quality'] == 'human' for r in rows])
    train, valid = split == 'train', split == 'validation'
    hvalid = valid & human
    team_y = np.array([r['label3'] for r in team])
    team_high = np.array([r['high'] for r in team])

    sentiment = DefaketiveSentimentModel(classifier=Fixed())

    def with_stars(labels, probs):
        out = []
        for i, row in enumerate(team):
            sentiment.trained_classifier.answer = {
                'label': labels[i], 'confidence': float(probs[i].max()),
                'probabilities': dict(zip(SENTIMENT_LABELS, map(float, probs[i]))), 'evidence': []}
            out.append(sentiment.analyze(row['text'], int(row['stars']))['label'])
        return np.array(out)

    results, choices = {}, {}

    def score(name, predict):
        """predict(style_embeddings) -> (labels, probs) for an (emb, probs) pair."""
        r = {}
        for style_key, label in (('firecs', 'test_firecs'), ('pool', 'test_pool')):
            sel = split == label
            labels, _ = predict(E[current_style][0][sel], E[current_style][1][sel])
            r[style_key] = macro(y[sel], labels)
        labels, probs = predict(*T[current_style])
        starred = with_stars(labels, probs)
        r['team_all'] = macro(team_y, starred)
        r['team_high'] = macro(team_y[team_high], starred[team_high])
        r['team_text_only'] = macro(team_y, labels)
        hv_labels, _ = predict(E[current_style][0][hvalid], E[current_style][1][hvalid])
        r['human_validation'] = macro(y[hvalid], hv_labels)
        results[name] = r
        print(name, r, flush=True)

    def base_predict(emb, probs):
        return LABELS[probs.argmax(axis=1)], probs

    for current_style in ('raw', 'strip', 'sentences'):
        suffix = '' if current_style == 'raw' else f'+tmpl_{current_style}'
        emb_all, probs_all = E[current_style]
        X = features(emb_all, probs_all)
        score('shipped' + suffix, base_predict)

        heads = {}
        for kind, mask in (('all', train), ('human', train & human)):
            search = {C: macro(y[hvalid], fit(X[mask], y[mask], w[mask], C).predict(X[hvalid]))
                      for C in (0.03, 0.1, 0.3, 1.0)}
            C = max(search, key=search.get)
            heads[kind] = fit(X[mask], y[mask], w[mask], C)
            choices[f'heads_{kind}{suffix}'] = {'C': C, 'human_validation_search': search}

        for kind, model in heads.items():
            def head_predict(emb, probs, model=model):
                p = model.predict_proba(features(emb, probs))
                p = p[:, [list(model.classes_).index(c) for c in SENTIMENT_LABELS]]
                return LABELS[p.argmax(axis=1)], p
            score(f'heads_{kind}{suffix}', head_predict)

            hp = head_predict(emb_all[hvalid], probs_all[hvalid])[1]
            bp = probs_all[hvalid]
            gates = {t: macro(y[hvalid], np.where((hp.max(1) >= t) & (hp.argmax(1) != bp.argmax(1)),
                                                  LABELS[hp.argmax(1)], LABELS[bp.argmax(1)]))
                     for t in np.round(np.arange(0.5, 0.99, 0.05), 2)}
            t = max(gates, key=gates.get)
            blends = {b: macro(y[hvalid], LABELS[((1 - b) * bp + b * hp).argmax(1)])
                      for b in np.round(np.arange(0.0, 1.01, 0.1), 1)}
            b = max(blends, key=blends.get)
            choices[f'gate_{kind}{suffix}'] = {'t': float(t), 'search': {str(k): v for k, v in gates.items()}}
            choices[f'blend_{kind}{suffix}'] = {'w': float(b), 'search': {str(k): v for k, v in blends.items()}}

            def gate_predict(emb, probs, t=t, head=head_predict):
                hl, hp2 = head(emb, probs)
                take = (hp2.max(1) >= t) & (hp2.argmax(1) != probs.argmax(1))
                return np.where(take, hl, LABELS[probs.argmax(1)]), np.where(take[:, None], hp2, probs)

            def blend_predict(emb, probs, b=b, head=head_predict):
                p = (1 - b) * probs + b * head(emb, probs)[1]
                return LABELS[p.argmax(1)], p

            score(f'gate_{kind}{suffix}', gate_predict)
            score(f'blend_{kind}{suffix}', blend_predict)

    base = results['shipped']
    verdicts = {}
    for name, r in results.items():
        not_lower = r['firecs'] >= base['firecs'] and r['team_all'] >= base['team_all']
        gain = max(r['firecs'] - base['firecs'], r['team_all'] - base['team_all']) >= 0.01
        verdicts[name] = bool(not_lower and gain)
    qualified = [n for n, ok in verdicts.items() if ok]
    best = max(qualified, key=lambda n: results[n]['firecs'] + results[n]['team_all']) if qualified else None

    OUT.mkdir(parents=True)
    report = {'rule': __doc__.split('Adoption rule')[1].split('The AI-labelled')[0].strip(),
              'results': results, 'qualified': verdicts, 'best_qualified': best,
              'choices': choices, 'template_rows_rewritten': rewritten,
              'notes': ['firecs and team_* are human labels; pool is AI labels.',
                        'team_all applies the app star rule; team_text_only does not.']}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('qualified:', qualified, '\nbest:', best)


if __name__ == '__main__':
    main()
