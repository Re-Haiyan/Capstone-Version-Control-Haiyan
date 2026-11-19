"""Generate synthetic mixed-operation browser evidence using the real model.

The private evidence directory must contain fan-input-private.json. No database
is opened or written. Synthetic controls never replace the saved fan reviews.
"""
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = Path(sys.argv[1])
os.environ['OMP_NUM_THREADS'] = '1'
sys.path[:0] = [str(root / 'backend'), str(root / 'backend/sentiment-analysis')]
import dashboard_utils as du

saved = json.loads((out / 'fan-input-private.json').read_text())[0]
texts = [
    'Gumagana nang maayos pero sobrang init at natunaw ang plug.',
    'gumagana nga s powerbank',
    'Malakas yung hangin at hindi maingay.',
    'Works on a power bank, but the airflow is weak.',
    'Works on a power bank but keeps cutting out.',
    'Sobrang init sa kwarto pero malamig ang hangin ng fan.',
]
p = du.analyze_products([{'name': saved['name'], 'link': saved['link'],
    'platform': saved.get('platform'), 'comments': [{'content': t, 'rating': 5} for t in texts]}])[0]
p['badge_view'] = du.badge_view(p, aspects=True)
p['checked_with_current'] = True
flags = lambda c: set(c['sentiment_analysis'].get('review_tags') or []) | set(c['sentiment_analysis'].get('review_extra_tags') or [])
for index, flag in ((0, 'safety'), (3, 'quality'), (4, 'defect')):
    assert flag in flags(p['comments'][index]), (index, flag)
for index in (1, 2, 5):
    assert not flags(p['comments'][index]), index
(out / 'melted-ui-private.json').write_text(json.dumps({'product': p}, ensure_ascii=False))
print('MIXED OPERATION, GENUINE FAULT AND MELTED-PLUG FIXTURE PASSED')
