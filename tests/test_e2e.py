import os,sys,time,json,subprocess,urllib.request,urllib.error,socket,sqlite3,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data'/'e2e-test.db'
if DB.exists(): DB.unlink()
PORT=18941
ENV=os.environ.copy(); ENV.update({'PORT':str(PORT),'ATHARHUM_DB_PATH':str(DB),'ATHARHUM_SECRET':'e2e-test-secret-strong-enough','PUBLIC_BASE_URL':f'http://127.0.0.1:{PORT}'})
p=subprocess.Popen([sys.executable,'server.py'],cwd=ROOT,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
base=f'http://127.0.0.1:{PORT}'
results=[]
def req(path,method='GET',body=None,token=None):
    data=None if body is None else json.dumps(body).encode()
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    r=urllib.request.Request(base+path,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(r,timeout=4) as x:
            raw=x.read()
            if 'json' in x.headers.get('Content-Type',''): val=json.loads(raw)
            elif 'image/' in x.headers.get('Content-Type',''): val=raw
            else: val=raw.decode()
            return x.status,val
    except urllib.error.HTTPError as e:
        raw=e.read();
        try: val=json.loads(raw)
        except: val=raw.decode(errors='replace')
        return e.code,val

def check(name,cond,detail=''):
    results.append((name,bool(cond),detail)); print(('PASS' if cond else 'FAIL')+' | '+name+((' | '+str(detail)) if detail else ''))
try:
    for _ in range(60):
        if p.poll() is not None: raise RuntimeError('server exited: '+str(p.stdout.read()))
        try:
            st,j=req('/health');
            if st==200: break
        except Exception: pass
        time.sleep(.25)
    check('health endpoint',st==200 and j.get('ok'))
    st,html=req('/'); check('home page served',st==200 and 'أَثَرُهُم' in html and 'static' not in html[:100])
    st,boot=req('/api/bootstrap'); check('bootstrap seeded data',st==200 and len(boot['contents'])==5 and len(boot['sources'])==5 and len(boot['journeys'])==1)
    st,ver=req('/api/verify/ATH-TANZIL-001'); check('verify known asset',st==200 and ver['verified'] and ver['content']['source_id']=='SRC-TANZIL')
    st,miss=req('/api/verify/NO-SUCH-ASSET'); check('unknown asset rejected',st==404)
    st,ai=req('/api/ai/ask','POST',{'question':'ما المصدر؟'}); check('AI refuses without evidence',st==200 and ai['insufficient_sources'] and not ai['grounded'])
    st,ai2=req('/api/ai/ask','POST',{'question':'ما الترخيص؟','content_id':'ATH-TANZIL-001'}); check('AI cites selected source',st==200 and ai2['grounded'] and len(ai2['citations'])==1 and 'Tanzil' in ai2['citations'][0]['source'])
    st,badlogin=req('/api/login','POST',{'email':'demo@atharhum.org','password':'wrong'}); check('bad login rejected',st==401)
    st,login=req('/api/login','POST',{'email':'demo@atharhum.org','password':'Atharhum2026!'}); tok=login.get('token'); check('demo institution login',st==200 and tok and 'password_hash' not in login['user'])
    st,events=req('/api/admin/events'); check('audit endpoint protected',st==403)
    st,events=req('/api/admin/events',token=tok); check('institution can inspect audit events',st==200 and 'events' in events)
    st,noauth=req('/api/content/create','POST',{'id':'ATH-E2E-1','title':'Test','source_id':'SRC-TANZIL','source_url':'https://tanzil.net'},None); check('create requires login',st==401)
    st,badsrc=req('/api/content/create','POST',{'id':'ATH-E2E-BAD','title':'Test','source_id':'MISSING','source_url':'https://example.com'},tok); check('unknown source rejected',st==400 and badsrc.get('error')=='source_not_found')
    payload={'id':'ATH-E2E-001','title':'E2E Test Asset','kind':'Test','source_id':'SRC-TANZIL','source_url':'https://tanzil.net/docs/Text_License','excerpt':'End-to-end test asset','rights':'Attribution required','review':'Reviewed for test','ai':'No AI transformation'}
    st,created=req('/api/content/create','POST',payload,tok); check('create knowledge asset',st==201 and created['content']['version']==1)
    st,dup=req('/api/content/create','POST',payload,tok); check('duplicate ID rejected',st==409)
    st,c=req('/api/content/ATH-E2E-001'); check('content passport endpoint',st==200 and c['content']['title']=='E2E Test Asset')
    st,r=req('/api/reuse','POST',{'content_id':'ATH-E2E-001','creator':'E2E','channel':'Test'}); check('reuse attribution generated',st==200 and r['ok'] and 'Tanzil' in r['attribution'])
    st,collab0=req('/api/collaboration','POST',{'to_org':'Test Partner','content_id':'ATH-E2E-001'}); check('collaboration requires login',st==401)
    st,collab=req('/api/collaboration','POST',{'to_org':'Test Partner','content_id':'ATH-E2E-001','message':'Test collaboration'},tok); check('collaboration request recorded',st==200 and collab['ok'])
    st,flag=req('/api/divergence','POST',{'content_id':'ATH-E2E-001','summary':'test mismatch'},tok); check('divergence flag works',st==200 and flag['content']['divergence']==1 and flag['content']['version']==2)
    st,correct=req('/api/correction','POST',{'content_id':'ATH-E2E-001','summary':'test correction'},tok); check('correction resolves flag and increments version',st==200 and correct['content']['divergence']==0 and correct['content']['version']==3)
    st,evt=req('/api/events','POST',{'type':'journey_start','content_id':'ATH-QURAN-001','meta':{'step':1}}); check('learning event recorded',st==200 and evt['ok'])
    st,met=req('/api/metrics'); check('impact metrics reflect events',st==200 and met['verifications']>=1 and met['reuse']>=1 and met['collaborations']>=1 and met['corrections']>=1 and met['journeys_started']>=1)
    st,out=req('/api/logout','POST',{},tok); st2,protected=req('/api/admin/events',token=tok); check('logout invalidates token',st==200 and st2==403)
    # Restart to prove SQLite persistence; stop first process.
    p.terminate(); p.wait(timeout=5)
    p=subprocess.Popen([sys.executable,'server.py'],cwd=ROOT,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    for _ in range(60):
        try:
            st,boot2=req('/api/bootstrap')
            if st==200: break
        except Exception: pass
        time.sleep(.2)
    check('SQLite survives restart',st==200 and any(x['id']=='ATH-E2E-001' for x in boot2['contents']))
    # QR PNG generated and decodes to verify route.
    qrpath=ROOT/'qr'/'ATH-TANZIL-001.png'
    check('QR generated as PNG',qrpath.exists() and qrpath.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
    st,qr=req('/qr/ATH-TANZIL-001.png'); check('QR image served by application',st==200 and isinstance(qr,bytes) and qr.startswith(b'\x89PNG\r\n\x1a\n'))
    st,verifyroute=req('/verify/ATH-TANZIL-001'); check('QR route serves application',st==200 and 'أَثَرُهُم' in verifyroute)
finally:
    if p.poll() is None: p.terminate(); p.wait(timeout=5)
    print('\nSUMMARY: %d/%d passed' % (sum(x[1] for x in results),len(results)))
    if not all(x[1] for x in results): sys.exit(1)
