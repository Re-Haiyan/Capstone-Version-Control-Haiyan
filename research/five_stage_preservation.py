"""Verify historical GETs against a read-only backup, without inference or writes.

Use a private evidence directory produced by five_stage_audit.py prepare.
Only aggregate preservation results are written to that evidence directory.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--checkout', type=Path, required=True)
parser.add_argument('--evidence', type=Path, required=True)
args = parser.parse_args()
root, evidence = args.checkout.resolve(), args.evidence.resolve()
os.environ['DEFAKETIVE_ORIGINAL'] = str(root / 'backend')
sys.path[:0] = [str(root), str(root / 'tests'), str(root / 'backend'), str(root / 'backend/sentiment-analysis')]
from server_under_test import app, webapp
import server
import dashboard_utils as du
from saved_pool import SavedPool

manifest = json.loads((evidence / 'manifest.json').read_text())
database = Path(manifest['backup'])
before = hashlib.sha256(database.read_bytes()).hexdigest()
assert before == manifest['backup_sha256']
products = json.loads((evidence / 'input-private.json').read_text())
indices = sorted(set(json.loads((evidence / 'selected-indices.json').read_text())) | {67, 85, 87, 130, 251, 416})

def forbidden(*args, **kwargs):
    raise AssertionError('A saved-report GET attempted inference')

results = []
with patch.object(server, 'pool', SavedPool(database)), patch.object(du, 'analyze_products', forbidden), patch.object(webapp, 'analyze_products', forbidden):
    client = app.test_client()
    for index in indices:
        original = products[index]
        response = client.get('/api/saved/detail', query_string={'link': original['link']})
        assert response.status_code == 200, (index, response.status_code)
        actual = response.get_json()['product']
        assert actual['checked_with_current'] is False, index
        for field in ('sentiment_summary', 'product_category'):
            assert actual.get(field) == original.get(field), (index, field)
        assert len(actual['comments']) == len(original['comments']), index
        for current, saved in zip(actual['comments'], original['comments']):
            # The API's existing author anonymization is intentionally preserved.
            for field in ('content', 'sentiment_analysis'):
                assert current.get(field) == saved.get(field), (index, field)
        results.append({'index': index, 'http_status': 200, 'marked_older': True,
                        'original_category_reviews_and_results_preserved': True})
assert hashlib.sha256(database.read_bytes()).hexdigest() == before
(evidence / 'historical-preservation.json').write_text(json.dumps({
    'backup_sha256_unchanged': before, 'inference_forbidden': True, 'reports': results
}, indent=2))
print('HISTORICAL REPORTS PRESERVED', len(results), 'BACKUP UNCHANGED', before)
