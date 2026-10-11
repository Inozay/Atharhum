import os,sys,time,json,subprocess,urllib.request,urllib.error,socket,sqlite3,shutil,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data'/'e2e-test.db'
if DB.exists(): DB.unlink()
PORT=18941
ENV=os.environ.copy(); ENV.update({'PORT':str(PORT),'ATHARHUM_DB_PATH':str(DB),'ATHARHUM_SECRET':'e2e-test-secret-strong-enough','PUBLIC_BASE_URL':f'http://127.0.0.1:{PORT}','ATHARHUM_SEED_DEMO':'true'})
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
    st,ver=req('/api/verify/ATH-TANZIL-001'); check('verify known asset and content hash',st==200 and ver['verified'] and ver['content']['source_id']=='SRC-TANZIL' and ver['integrity']['hash_valid'])
    st,miss=req('/api/verify/NO-SUCH-ASSET'); check('unknown asset rejected',st==404)
    st,ai=req('/api/ai/ask','POST',{'question':'ما المصدر؟'}); check('AI refuses without evidence',st==200 and ai['insufficient_sources'] and not ai['grounded'])
    st,ai2=req('/api/ai/ask','POST',{'question':'ما الترخيص؟','content_id':'ATH-TANZIL-001'}); check('AI cites selected source',st==200 and ai2['grounded'] and len(ai2['citations'])==1 and 'Tanzil' in ai2['citations'][0]['source'])
    st,badlogin=req('/api/login','POST',{'email':'demo@atharhum.org','password':'wrong'}); check('bad login rejected',st==401)
    st,login=req('/api/login','POST',{'email':'demo@atharhum.org','password':'Atharhum2026!'}); tok=login.get('token'); check('demo institution login',st==200 and tok and 'password_hash' not in login['user'])
    st,events=req('/api/admin/events'); check('audit endpoint protected',st==403)
    st,events=req('/api/admin/events',token=tok); check('institution can inspect audit events',st==200 and 'events' in events)
    st,noauth=req('/api/content/create','POST',{'id':'ATH-E2E-1','title':'Test','source_id':'SRC-TANZIL','source_url':'https://tanzil.net'},None); check('create requires login',st==401)
    st,badsrc=req('/api/content/create','POST',{'id':'ATH-E2E-BAD','title':'Test','source_id':'MISSING','source_url':'https://example.com'},tok); check('unknown source rejected',st==400 and badsrc.get('error')=='source_not_found')
    st,badurl=req('/api/content/create','POST',{'id':'ATH-E2E-BADURL','title':'Test','source_id':'SRC-TANZIL','source_url':'javascript:alert(1)'},tok); check('unsafe source URL rejected',st==400 and badurl.get('error')=='invalid_source_url')
    payload={'id':'ATH-E2E-001','title':'E2E Test Asset','kind':'Test','source_id':'SRC-TANZIL','source_url':'https://tanzil.net/docs/Text_License','excerpt':'End-to-end test asset','rights':'Attribution required','review':'Reviewed for test','ai':'No AI transformation'}
    st,created=req('/api/content/create','POST',payload,tok); check('create knowledge asset',st==201 and created['content']['version']==1)
    st,dup=req('/api/content/create','POST',payload,tok); check('duplicate ID rejected',st==409)
    st,hidden=req('/api/content/ATH-E2E-001'); check('private asset hidden from anonymous users',st==404)
    st,c=req('/api/content/ATH-E2E-001',token=tok); check('content passport endpoint and valid hash for owning institution',st==200 and c['content']['title']=='E2E Test Asset' and c['content']['hash_valid'])
    # Verify that a different organization cannot read another institution's private asset.
    con=sqlite3.connect(DB); con.execute("INSERT INTO organizations(name,slug,created_at) VALUES(?,?,?)",('Other Organization','other-org','2026-10-09T00:00:00+00:00')); oid=con.execute("SELECT id FROM organizations WHERE slug='other-org'").fetchone()[0]; ph=hashlib.pbkdf2_hmac('sha256',b'OtherOrgStrongPass2026!',ENV['ATHARHUM_SECRET'].encode(),310000).hex(); con.execute("INSERT INTO users(email,name,role,organization_id,password_hash,created_at) VALUES(?,?,?,?,?,?)",('other@example.org','Other Org','institution',oid,ph,'2026-10-09T00:00:00+00:00')); con.commit(); con.close()
    st,otherlogin=req('/api/login','POST',{'email':'other@example.org','password':'OtherOrgStrongPass2026!'}); other_token=otherlogin.get('token'); st,isolated=req('/api/content/ATH-E2E-001',token=other_token); check('cross-organization private asset isolation',st==404)
    st,r=req('/api/reuse','POST',{'content_id':'ATH-E2E-001','creator':'E2E','channel':'Test'},tok); check('reuse attribution generated',st==200 and r['ok'] and 'Tanzil' in r['attribution'] and 'Version: 1' in r['attribution'])
    st,collab0=req('/api/collaboration','POST',{'to_org':'Test Partner','content_id':'ATH-E2E-001'}); check('collaboration requires login',st==401)
    st,collab=req('/api/collaboration','POST',{'to_org':'Test Partner','content_id':'ATH-E2E-001','message':'Test collaboration'},tok); check('collaboration request recorded',st==200 and collab['ok'])
    st,flag=req('/api/divergence','POST',{'content_id':'ATH-E2E-001','summary':'test mismatch'},tok); check('divergence flag works',st==200 and flag['content']['divergence']==1 and flag['content']['version']==2)
    st,correct=req('/api/correction','POST',{'content_id':'ATH-E2E-001','summary':'test correction'},tok); check('correction resolves flag and increments version',st==200 and correct['content']['divergence']==0 and correct['content']['version']==3)
    st,evt=req('/api/events','POST',{'type':'journey_start','content_id':'ATH-QURAN-001','meta':{'step':1}}); check('learning event recorded',st==200 and evt['ok'])
    st,prog=req('/api/journey/progress'); check('journey progress initially readable',st==200 and isinstance(prog['completed_steps'],list))
    st,outoforder=req('/api/journey/progress','POST',{'journey_id':'JRN-001','step_position':3,'status':'completed'}); check('journey cannot skip prerequisite steps',st==409 and outoforder.get('error')=='previous_step_incomplete')
    st,progpost=req('/api/journey/progress','POST',{'journey_id':'JRN-001','step_position':1,'status':'completed'}); st,prog2=req('/api/journey/progress'); check('journey progress persisted in database',st==200 and 1 in prog2['completed_steps'])
    st,met=req('/api/metrics',token=tok); check('impact metrics reflect events',st==200 and met['verifications']>=1 and met['reuse']>=1 and met['collaborations']>=1 and met['corrections']>=1 and met['journeys_started']>=1)
    st,chainanon=req('/api/integrity/audit-chain'); st,chain=req('/api/integrity/audit-chain',token=tok); check('audit chain is protected and valid for institution',st==200 and chainanon=={'error':'forbidden'} and chain['valid_chain'] and chain['events_checked']>=1)
    st,vers=req('/api/versions/ATH-E2E-001',token=tok); check('version history exposed',st==200 and len(vers['versions'])>=3)
    st,source=req('/api/sources/create','POST',{'id':'SRC-E2E','name':'E2E Source','url':'https://example.org','evidence_url':'https://example.org/evidence'},tok); check('institution can register source',st==201 and source['ok'])
    st,adapt=req('/api/content/adapt','POST',{'id':'ATH-E2E-ADAPT','parent_content_id':'ATH-E2E-001','title':'E2E Arabic adaptation','language':'ar','transformation_type':'summary','excerpt':'Human review required'},tok); check('adaptation workflow preserves parent lineage',st==201 and adapt['content']['parent_content_id']=='ATH-E2E-001' and 'human review' in adapt['content']['ai'].lower())
    st,flagadapt=req('/api/divergence','POST',{'content_id':'ATH-E2E-ADAPT','summary':'Need compare derivative against source'},tok); st,blocked=req('/api/review','POST',{'content_id':'ATH-E2E-ADAPT','status':'approved','summary':'Attempt without resolving divergence'},tok); check('cannot approve while divergence remains open',st==409 and blocked.get('error')=='divergence_must_be_resolved')
    st,fixadapt=req('/api/correction','POST',{'content_id':'ATH-E2E-ADAPT','summary':'Compared with source; divergence resolved'},tok); st,approval=req('/api/review','POST',{'content_id':'ATH-E2E-ADAPT','status':'approved','summary':'Human reviewer approved test adaptation'},tok); check('human approval publishes reviewed derived content',st==200 and approval['content']['visibility']=='public' and approval['content']['approved_by']=='Demo Institution' and approval['content']['hash_valid'])
    st,qrprivate=req('/qr/ATH-E2E-001.png'); check('private asset QR is not exposed before approval',st==404)
    st,qrpublic=req('/qr/ATH-E2E-ADAPT.png'); check('QR dynamically generated for approved derived asset',st==200 and isinstance(qrpublic,bytes) and qrpublic.startswith(b'\x89PNG\r\n\x1a\n'))
    st,out=req('/api/logout','POST',{},tok); st2,protected=req('/api/admin/events',token=tok); check('logout invalidates token',st==200 and st2==403)
    # Restart to prove SQLite persistence; stop first process.
    p.terminate(); p.wait(timeout=5)
    p=subprocess.Popen([sys.executable,'server.py'],cwd=ROOT,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    for _ in range(60):
        try:
            st,login2=req('/api/login','POST',{'email':'demo@atharhum.org','password':'Atharhum2026!'})
            if st==200 and login2.get('token'):
                tok2=login2['token']; st,boot2=req('/api/bootstrap',token=tok2)
                if st==200: break
        except Exception: pass
        time.sleep(.2)
    check('SQLite survives restart',st==200 and any(x['id']=='ATH-E2E-001' for x in boot2['contents']) and any(x['id']=='ATH-E2E-ADAPT' for x in boot2['contents']))
    # QR PNG is generated and verify route serves the frontend.
    qrpath=ROOT/'qr'/'ATH-TANZIL-001.png'
    check('QR generated as PNG',qrpath.exists() and qrpath.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
    st,qr=req('/qr/ATH-TANZIL-001.png'); check('QR image served by application',st==200 and isinstance(qr,bytes) and qr.startswith(b'\x89PNG\r\n\x1a\n'))
    st,verifyroute=req('/verify/ATH-TANZIL-001'); check('QR route serves application',st==200 and 'أَثَرُهُم' in verifyroute)
finally:
    if p.poll() is None: p.terminate(); p.wait(timeout=5)
    for cid in ('ATH-E2E-001','ATH-E2E-ADAPT'):
        q=ROOT/'qr'/(cid+'.png')
        if q.exists(): q.unlink()
    for q in (DB,Path(str(DB)+'-wal'),Path(str(DB)+'-shm')):
        if q.exists(): q.unlink()
    print('\nSUMMARY: %d/%d passed' % (sum(x[1] for x in results),len(results)))
    if not all(x[1] for x in results): sys.exit(1)
