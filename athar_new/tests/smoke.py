import json
from urllib.request import urlopen, Request

BASE='http://127.0.0.1:8000'

def get(path):
    with urlopen(BASE+path, timeout=5) as r:
        assert r.status == 200, (path, r.status)
        return json.loads(r.read())

assert get('/api/health')['status'] == 'ok'
assert get('/api/dashboard')['kpis']['verification_rate'] > 0
assert get('/api/content')['items']
assert get('/api/content/ATH-001')['passport']['content_id'] == 'ATH-001'
assert get('/api/verify/ATH-001')['verified'] is True
assert get('/api/sources')['items']
assert get('/api/ai/answer?q=test')['citations']
assert get('/api/impact')['journey']['applied'] > 0
assert get('/api/journey')['progress'] > 0
with urlopen(Request(BASE+'/api/studio/generate', data=json.dumps({'title':'اختبار','topic':'عام','source_ids':['SRC-001']}).encode(), headers={'Content-Type':'application/json'}), timeout=5) as r:
    assert r.status == 200
    assert json.loads(r.read())['status'].startswith('مسودة')
with urlopen(BASE+'/', timeout=5) as r:
    html=r.read().decode('utf-8')
    assert 'أَثَرُهُم' in html and 'وضع لجنة التحكيم' in html
print('ALL_SMOKE_TESTS_PASSED')
