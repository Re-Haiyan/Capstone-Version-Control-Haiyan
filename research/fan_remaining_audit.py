"""Export the adjudicated, complete fan concern ledger from private replays.

No database is opened. Inputs must be the same verified 503-review snapshot.
The ledger contains public review IDs/text but never account/reviewer identity.
"""
import argparse
import collections
import csv
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--evidence', type=Path, required=True)
a = p.parse_args()
out = a.evidence
load = lambda name: json.loads((out / name).read_text())
flagset = lambda analysis: set(analysis.get('review_tags') or []) | set(analysis.get('review_extra_tags') or [])

# Human reading of the complete original review, independent of detector output.
UNSUPPORTED = {
    (36, 'not_as_described'): 'Only 5 W explains modest output; no advertised/actual rating discrepancy.',
    (122, 'not_as_described'): 'Minimal 5-watt consumption is described as energy efficient, not a false specification.',
    (238, 'not_as_described'): '5 watts lang describes low consumption and power-bank use, not a mismatch.',
    (289, 'not_as_described'): '5 watts lang explains modest output; no promised different wattage.',
    (317, 'not_as_described'): 'Since 5w lang explains expectations; no seller specification is disputed.',
    (355, 'not_as_described'): 'The reviewer compares its price with other similar products, not received-item identity.',
    (359, 'defect'): 'The location frequently loses power; the fan is explicitly working well.',
    (427, 'defect'): 'The Quiet field praises almost no sound, not missing intended audio.',
    (408, 'quality'): 'Mahina kumain ng charge means low battery consumption, not low airflow.',
    (435, 'quality'): 'Mahina consume ng kuryente means low electricity consumption; airflow is just right.',
    (441, 'quality'): 'The initial expectation of weak airflow is retracted: malakas Pala.',
}
AMBIGUOUS = {
    (13, 'defect'): 'Not sure if it defective is speculative. Actual weak/no airflow supports quality, not a confirmed fault.',
    (24, 'not_as_described'): 'Kahapon kulang na order received na agad is ambiguous order-timing wording, not an unambiguous shortage claim.',
}
SUPPORTED = {
    0: 'Explicit broken item received: Sira Yong pinadala.',
    1: 'Very weak output, weaker than the reviewer blowing air; wasted-money complaint.',
    3: 'Ordered Vone, received another brand; explicit not as described.',
    4: 'Different received item/quality compared with the previous order and wire length.',
    5: 'Explicit not as described and not Vone. The weak-output complaint also remains in the full review.',
    6: 'Repeated received-brand denial and misleading-listing complaint.',
    7: 'Received item explicitly differs from the displayed listing.',
    9: 'Airflow explicitly napakahina.',
    10: 'Mahina sayang: weak output and regret.',
    11: 'Walang hangin explicitly reports no airflow; previously missed by both keyword and learned paths.',
    12: 'Walang hangin explicitly reports no airflow; retain comparison and full review.',
    13: 'Actual weak fan air and no air blowing out; quality concern, without asserting the speculative defect.',
    15: 'Listing shows Vone but another brand was delivered.',
    16: 'Mahina reports weak output in this fan review.',
    21: 'Fan is weak even on mains power; actual output complaint.',
    23: 'Reviewer explicitly reports receiving a fake instead of the described Vone brand.',
    25: 'Works on USB/power bank, but airflow weak; short wire also described.',
    28: 'Actual 1.5-metre wire explicitly shorter than the description, plus wrong-brand complaint.',
    29: 'Another brand was sent instead of Vone, with short wire.',
    31: 'Weak airflow, qualified by acceptance rather than denied.',
    34: 'Reviewer tested it and found output weak; future camping usefulness remains uncertain.',
    40: 'Weak reach through mosquito net; comparison/acceptance does not retract limitation.',
    42: 'Weak airflow requiring aim at one person.',
    44: 'Weak output requiring closer placement.',
    46: 'Weak airflow despite useful operation; cord also too short to hang.',
    47: 'Moderately weak airflow despite acceptance; possible adaptor explanation is retained.',
    53: 'Performance explicitly mahina despite good quality.',
    84: 'Weak daytime airflow on hot days. This is quality feedback, not device overheating.',
    244: 'Not very strong airflow, but accepted for outages; limitation remains.',
    258: 'Not very strong, not very weak: qualified output limitation, not a mechanical failure.',
    276: 'Not very strong but sufficient: qualified output limitation, not a mechanical failure.',
    327: 'Weak airflow requiring closer installation despite recommendation.',
    356: 'Not strong airflow but sufficient for sleep; expectation and price qualifications retained.',
    367: 'Only one of two ordered units has arrived; the other remains in delivery tracking. Delivery concern, not proven product defect.',
    374: 'Weak but usable during outages; qualified output complaint remains.',
    376: 'Not strong airflow despite usefulness and quiet operation.',
    398: 'Airflow explicitly hindi kalakasan.',
    411: 'Airflow weaker than a clip fan, accepted for outages.',
    415: 'Very weak airflow and wasted-money complaint.',
    457: 'Airflow slightly weaker than clip fan, qualified as good value; comparison retained.',
}

rows = []
versions = {name: load(name + '-reports-private.json')[0] for name in ('production', 'prior', 'candidate')}
source = load('fan-input-private.json')[0]
assert len(source['comments']) == 503
for name, record in versions.items():
    assert record['input_sha256'] == versions['candidate']['input_sha256']
    assert len(record['fresh']['comments']) == 503
    for i, comment in enumerate(record['fresh']['comments']):
        original = source['comments'][i]
        assert comment['content'] == original['content']
        analysis = comment['sentiment_analysis']
        base = versions['production']['fresh']['comments'][i]['sentiment_analysis']
        for key in ('label', 'sampling_weight'):
            assert analysis.get(key) == base.get(key), (name, i, key)
        assert analysis['sentiment']['probabilities'] == base['sentiment']['probabilities']
        assert not analysis['sentiment']['category_context']['sentiment_overridden']
        if name == 'production':
            continue
        for flag in sorted(flagset(analysis)):
            key = (i, flag)
            status = 'unsupported' if key in UNSUPPORTED else 'ambiguous' if key in AMBIGUOUS else 'supported'
            reason = UNSUPPORTED.get(key) or AMBIGUOUS.get(key) or SUPPORTED.get(i)
            if i == 41:
                reason = ('Reported failure on one cheap low-capacity power bank; works on two branded ones. '
                          'Supports a source-dependent operation limitation, not a diagnosis of a broken motor.' if flag == 'defect' else
                          'Lower output than a usual fan is stated and accepted. Mumurahin describes the external power bank, not fan quality.')
            assert reason, (name, i, flag, 'unadjudicated')
            evidence = analysis['review_evidence'][flag]
            for s in evidence.get('spans', []):
                assert original['content'][s['review_start']:s['review_end']] == s['text'], (name, i, flag, 'ungrounded offsets')
            sentences = [s['text_raw'] for s in analysis['sentences'] if s['index'] in evidence.get('sentences', [])]
            learned = [{'sentence': s['index'], 'score': (s.get('extra_learned') or s.get('learned') or {}).get(flag)}
                       for s in analysis['sentences'] if s['index'] in evidence.get('sentences', [])]
            span_audit = [{**s, 'status': ('unsupported' if name == 'prior' and i == 41 and s['text'] == 'mumurahin' else status),
                           'judgment': ('Cheap describes the power bank, not the fan.' if i == 41 and s['text'] == 'mumurahin' else reason)}
                          for s in evidence.get('spans', [])]
            rows.append({'version': name, 'review_index': i, 'review_id': original.get('comment_id'),
                         'product_category': record['fresh']['product_category'], 'flag': flag,
                         'status': status, 'judgment': reason, 'review_excerpt': original['content'],
                         'detector_source': sorted({s.get('source', 'unknown') for s in evidence.get('spans', [])}) or ['learned_classifier'],
                         'detector_name': ('learned extra-label classifier' if flag in ('quality', 'not_as_described') else 'learned hazard classifier') if evidence.get('state') == 'model_only' else 'category/general keyword rules',
                         'sentence_detector_scores': learned,
                         'evidence_state': evidence.get('state'), 'evidence_sentences': sentences,
                         'spans': evidence.get('spans', []), 'span_audit': span_audit, 'model_score': evidence.get('model_score')})
assert len([r for r in rows if r['version'] == 'prior']) == 53
assert all(r['status'] == 'supported' for r in rows if r['version'] == 'candidate'), 'Unresolved shopper concern: NO-GO'
assert all(s['status'] == 'supported' for r in rows if r['version'] == 'candidate' for s in r['span_audit'])
for badge in versions['candidate']['view'].get('badges', []):
    for quote in badge.get('evidence', []):
        text = quote['text'].removesuffix('…')
        assert any(text in c['content'] and badge['category'] in flagset(c['sentiment_analysis'])
                   for c in versions['candidate']['fresh']['comments']), (badge['category'], 'ungrounded shopper quote')
(out / 'remaining-flag-audit.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2))
with (out / 'remaining-flag-audit.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader()
    for row in rows:
        writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})
changes = []
for name in ('production', 'prior'):
    delta = []
    for i, (x, y) in enumerate(zip(versions[name]['fresh']['comments'], versions['candidate']['fresh']['comments'])):
        before, after = x['sentiment_analysis'], y['sentiment_analysis']
        oldflags, newflags = flagset(before), flagset(after)
        oldev, newev = before.get('review_evidence'), after.get('review_evidence')
        if oldflags != newflags or oldev != newev:
            delta.append({'review_index': i, 'review_id': source['comments'][i].get('comment_id'),
                          'removed': sorted(oldflags - newflags), 'added': sorted(newflags - oldflags),
                          'before_evidence': oldev, 'after_evidence': newev, 'review_excerpt': x['content']})
    changes.append({'baseline': name, 'changes': delta, 'before_counts': versions[name]['view']['counts'],
                    'after_counts': versions['candidate']['view']['counts'],
                    'before_state': versions[name]['view']['state'], 'after_state': versions['candidate']['view']['state'],
                    'before_conclusion': versions[name]['view']['conclusion'], 'after_conclusion': versions['candidate']['view']['conclusion']})
(out / 'changed-evidence-audit.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2))
print('ADJUDICATED', dict(collections.Counter((r['version'], r['status']) for r in rows)))
for c in changes:
    print('DELTA', c['baseline'], [(d['review_index'], d['removed'], d['added']) for d in c['changes']])
    print('COUNTS', c['before_counts'], '->', c['after_counts'])
