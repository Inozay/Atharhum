import urllib.request, urllib.parse, json, sys, subprocess, time, os
p=subprocess.Popen([sys.executable,'-m','uvicorn','backend.main:app','--port','8123'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(1.8)
base='http://127.0.0.1:8123'
def get(path):
    r=urllib.request.urlopen(base+path,timeout=5); assert r.status==200; return json.load(r) if 'application/json' in r.headers.get('content-type','') else r.read()
def post(path,payload):
    req=urllib.request.Request(base+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    r=urllib.request.urlopen(req,timeout=5); assert r.status==200; return json.load(r)
try:
    assert get('/api/health')['ok']
    assert len(get('/api/content'))>=3
    assert get('/api/content/AH-001')['id']=='AH-001'
    assert get('/api/provenance/AH-001')['lineage']
    assert get('/api/graph/AH-001')['edges']
    assert post('/api/verify',{'content_id':'AH-001'})['verified']
    assert not post('/api/verify',{'content_id':'NOPE'})['verified']
    assert post('/api/ask',{'question':'كيف يعمل التحقق؟'})['sources']
    assert post('/api/ask',{'question':'ترجم هذه الفكرة','content_id':'AH-001','mode':'translate'})['answer']
    assert post('/api/learning/progress',{'session_id':'smoke','content_id':'AH-001','step':1})['ok']
    assert get('/api/learning?session_id=smoke&content_id=AH-001')['step']==1
    assert post('/api/event',{'event':'share','content_id':'AH-001','session_id':'smoke'})['accepted']
    assert 'funnel' in get('/api/impact')
    assert len(get('/api/qr/AH-001'))>100
    print('SMOKE TEST PASSED: health/content/provenance/graph/verify/assistant/learning/events/impact/qr')
finally:
    p.terminate(); p.wait(timeout=3)
