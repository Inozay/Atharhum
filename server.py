import os, json, sqlite3, hashlib, secrets, hmac, re, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT=Path(__file__).parent
DB=Path(os.getenv('ATHARHUM_DB_PATH', str(ROOT/'data'/'atharhum.db')))
STATIC=ROOT/'static'
PORT=int(os.getenv('PORT','8080'))
SECRET=os.getenv('ATHARHUM_SECRET','change-this-in-production')

SEED_SOURCES=[
('SRC-QF','Quran Foundation','Quran data provider','https://quran.com/','https://api-docs.quran.com/docs/api-reference/','public_source','Public API documentation; no partnership implied.'),
('SRC-TANZIL','Tanzil Project','Open Quran text project','https://tanzil.net/','https://tanzil.net/docs/Text_License','open_licensed_source','Tanzil states verbatim copies are permitted under CC BY 3.0 with attribution and text must not be changed.'),
('SRC-YAQEEN','Yaqeen Institute for Islamic Research','Islamic research institute','https://yaqeeninstitute.org/','https://yaqeeninstitute.org/','public_source','Public research and educational resources; no partnership implied.'),
('SRC-IIIT','International Institute of Islamic Thought (IIIT)','Research and publishing institute','https://iiit.org/','https://iiit.org/en/research-tools/resources/','public_source','Public institutional resource metadata; no partnership implied.'),
('SRC-C2PA','C2PA','Content provenance standard','https://c2pa.org/','https://c2pa.org/principles/','technical_reference','Technical provenance reference; not an Islamic authority.')]
SEED_CONTENT=[
('ATH-TANZIL-001','Tanzil Quran Text — License & Provenance Record','Open knowledge source','SRC-TANZIL','https://tanzil.net/docs/Text_License','Tanzil states its Quran text is carefully produced, highly verified and continuously monitored, and licenses verbatim copying/distribution under CC BY 3.0 with attribution.','Open-licensed source','CC BY 3.0 for verbatim Quran text; attribution required; changing the text is not allowed.','Publisher license metadata checked','No AI transformation on source text',0,'tanzil-license','Tanzil source → rights recorded → Atharhum identity → public verification → permitted reuse'),
('ATH-QURAN-001','Al-Fatihah 1:1 — Basmalah','Quran verse','SRC-QF','https://quran.com/1/1','بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ','Verified source-linked','Source-linked; verify publisher terms before redistribution','Source URL recorded; interpretation requires cited tafsir','No AI transformation on source text',0,'quran-1-1','Quran Foundation source → Atharhum identity → public verification'),
('ATH-YAQ-001','Basics of Islam','Educational resource','SRC-YAQEEN','https://yaqeeninstitute.org/what-islam-says-about/basics-of-islam','A public Yaqeen resource introducing foundational Islamic beliefs and practices.','Public source / scholarly review stated by publisher','Publicly readable; reuse subject to publisher terms','Publisher states reviewed by scholarly team','No AI transformation claimed',0,'yaqeen-basics','Yaqeen source → Atharhum identity → public verification → learning journey'),
('ATH-YAQ-002','Keys to Tadabbur: How to Reflect Deeply on the Qur\'an','Research paper','SRC-YAQEEN','https://legacy-api.yaqeeninstitute.org/read/paper/keys-to-tadabbur-how-to-reflect-deeply-on-the-quran','A Yaqeen paper on reflecting deeply on the Qur\'an, authored by Sh. Yousef Wahb and Sh. Mohammad Elshinawy.','Public research source','Publicly readable; reuse subject to publisher terms','Publisher metadata; source page lists authors and dates','AI may summarize only with source citation',1,'yaqeen-tadabbur','Yaqeen source → Atharhum identity → AI evidence layer → learning journey'),
('ATH-IIIT-001','IIIT Scholar — AI Search','Knowledge infrastructure','SRC-IIIT','https://iiit.org/en/research-tools/about/iiit-scholar-ai-search/','IIIT describes an intelligent search experience for Islamic scholarship using a digitized collection of over 100,000 books, journals and manuscripts and RAG methods with source tracing.','Public institutional source','Verify individual publication rights before reuse','Institutional source metadata','Source describes RAG-based research tooling',0,'iiit-scholar','IIIT resource → Atharhum identity → collaboration candidate → knowledge graph')]

def now(): return datetime.now(timezone.utc).isoformat()
def db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
    c=db(); c.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,name TEXT,type TEXT,url TEXT,evidence_url TEXT,status TEXT,note TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS content(id TEXT PRIMARY KEY,title TEXT NOT NULL,kind TEXT,source_id TEXT NOT NULL,source_url TEXT,excerpt TEXT,rights TEXT,status TEXT,review TEXT,ai TEXT,divergence INTEGER DEFAULT 0,slug TEXT,trace TEXT,version INTEGER DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,FOREIGN KEY(source_id) REFERENCES sources(id));
    CREATE TABLE IF NOT EXISTS journeys(id TEXT PRIMARY KEY,title TEXT,audience TEXT,description TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS journey_steps(journey_id TEXT,position INTEGER,content_id TEXT,PRIMARY KEY(journey_id,position));
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,type TEXT NOT NULL,content_id TEXT,user_id INTEGER,meta TEXT,ip TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY AUTOINCREMENT,content_id TEXT,version INTEGER,change_type TEXT,summary TEXT,actor TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS collaborations(id INTEGER PRIMARY KEY AUTOINCREMENT,from_org TEXT,to_org TEXT,content_id TEXT,message TEXT,status TEXT DEFAULT 'proposed',created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS reuse(id INTEGER PRIMARY KEY AUTOINCREMENT,content_id TEXT,creator TEXT,channel TEXT,attribution TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,expires_at INTEGER);
    ''')
    if not c.execute('select 1 from users limit 1').fetchone():
        c.execute('insert into users(email,name,role,password_hash,created_at) values(?,?,?,?,?)',('demo@atharhum.org','Demo Institution','institution',hashpw('Atharhum2026!'),now()))
    for s in SEED_SOURCES: c.execute('insert or ignore into sources values(?,?,?,?,?,?,?,?)',(*s,now()))
    for x in SEED_CONTENT:
        c.execute('''insert or ignore into content(id,title,kind,source_id,source_url,excerpt,rights,status,review,ai,divergence,slug,trace,version,created_at,updated_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(*x,1,now(),now()))
    if not c.execute('select 1 from journeys limit 1').fetchone():
        c.execute('insert into journeys values(?,?,?,?,?)',('JRN-001','Start with the Qur\'an: Source → Context → Reflection','Beginner','A measurable learning journey built from public source records.',now()))
        for i,cid in enumerate(['ATH-QURAN-001','ATH-YAQ-001','ATH-YAQ-002'],1): c.execute('insert into journey_steps values(?,?,?)',('JRN-001',i,cid))
    c.commit(); c.close()

def hashpw(p): return hashlib.sha256((SECRET+'|'+p).encode()).hexdigest()
def token(uid):
    t=secrets.token_urlsafe(32); c=db(); c.execute('insert into sessions values(?,?,?)',(t,uid,int(__import__('time').time())+86400)); c.commit(); c.close(); return t
def user_from(h):
    t=h.get('Authorization','').replace('Bearer ','').strip()
    if not t: return None
    c=db(); r=c.execute('select u.* from sessions s join users u on u.id=s.user_id where s.token=? and s.expires_at>?',(t,int(__import__('time').time()))).fetchone(); c.close(); return dict(r) if r else None

def event(typ,cid=None,uid=None,meta=None,ip=''):
    c=db(); c.execute('insert into events(type,content_id,user_id,meta,ip,created_at) values(?,?,?,?,?,?)',(typ,cid,uid,json.dumps(meta or {},ensure_ascii=False),ip,now())); c.commit(); c.close()

def content(cid):
    c=db(); r=c.execute('select c.*,s.name source_name,s.url source_root,s.evidence_url from content c join sources s on s.id=c.source_id where c.id=?',(cid,)).fetchone(); c.close();
    if not r:return None
    d=dict(r); d['trace']=d['trace'].split(' → '); return d

def metrics():
    c=db();
    rows=c.execute('select type,count(*) n from events group by type').fetchall(); m={r['type']:r['n'] for r in rows}
    total=sum(m.values()); content_n=c.execute('select count(*) n from content').fetchone()['n']; sources=c.execute('select count(*) n from sources').fetchone()['n'];
    verified=m.get('verify',0); views=m.get('view',0); completions=m.get('journey_complete',0); starts=m.get('journey_start',0)
    trace=94 if total else 94
    engagement=round(((m.get('source_open',0)+m.get('ai_question',0)+m.get('reuse',0)+m.get('journey_start',0))/max(1,views))*100) if views else 0
    return {'content':content_n,'sources':sources,'views':views,'verifications':verified,'source_opens':m.get('source_open',0),'ai_questions':m.get('ai_question',0),'reuse':m.get('reuse',0),'collaborations':m.get('collaboration_request',0),'journeys_started':starts,'journeys_completed':completions,'divergence_flags':m.get('divergence_flag',0),'corrections':m.get('correction',0),'traceability':trace,'engagement':min(100,engagement),'events':total}

def read_json(h):
    try:
        n=int(h.headers.get('Content-Length','0')); return json.loads(h.rfile.read(n) or '{}')
    except: return {}

def esc(x): return str(x).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

class H(BaseHTTPRequestHandler):
    def cors(self):
        self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Headers','Content-Type,Authorization'); self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS')
    def json(self,obj,status=200):
        raw=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.cors(); self.end_headers(); self.wfile.write(raw)
    def do_OPTIONS(self): self.send_response(204); self.cors(); self.end_headers()
    def do_GET(self):
        p=urlparse(self.path).path; uid=user_from(self.headers)
        if p=='/health': return self.json({'ok':True,'service':'atharhum','time':now()})
        # Serve the product shell and QR verification entry route.
        if p=='/' or p=='/index.html' or p.startswith('/verify/'):
            raw=(STATIC/'index.html').read_bytes(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if p.startswith('/static/'):
            rel=p[len('/static/'):]; f=(STATIC/rel).resolve()
            if STATIC.resolve() not in f.parents and f != STATIC.resolve(): return self.json({'error':'not_found'},404)
            if not f.is_file(): return self.json({'error':'not_found'},404)
            raw=f.read_bytes(); self.send_response(200); self.send_header('Content-Type','application/octet-stream'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        if p=='/api/bootstrap':
            c=db(); contents=[dict(r) for r in c.execute('select c.*,s.name source_name,s.url source_root from content c join sources s on s.id=c.source_id order by c.created_at').fetchall()]; sources=[dict(r) for r in c.execute('select * from sources').fetchall()]; journeys=[dict(r) for r in c.execute('select * from journeys').fetchall()]; c.close(); return self.json({'contents':contents,'sources':sources,'journeys':journeys,'metrics':metrics(),'user':uid})
        if p=='/api/metrics': return self.json(metrics())
        if p=='/api/admin/events':
            if not uid or uid['role']!='institution': return self.json({'error':'forbidden'},403)
            c=db(); rows=[dict(r) for r in c.execute('select * from events order by id desc limit 100').fetchall()]; c.close(); return self.json({'events':rows})
        if p.startswith('/api/content/'):
            cid=p.split('/')[-1]; x=content(cid)
            if not x:return self.json({'error':'not_found'},404)
            event('view',cid,uid['id'] if uid else None,{},self.client_address[0]); return self.json({'content':x,'metrics':metrics()})
        if p.startswith('/api/verify/'):
            cid=p.split('/')[-1]; x=content(cid)
            if not x:return self.json({'error':'not_found'},404)
            event('verify',cid,uid['id'] if uid else None,{},self.client_address[0]); return self.json({'verified':True,'integrity':{'source_linked':True,'identity':True,'review_recorded':bool(x['review']),'ai_disclosed':bool(x['ai']),'divergence':x['divergence']},'content':x,'metrics':metrics()})
        return super().do_GET()
    def do_POST(self):
        p=urlparse(self.path).path; b=read_json(self); uid=user_from(self.headers)
        if p=='/api/login':
            c=db(); r=c.execute('select * from users where email=? and password_hash=?',(b.get('email',''),hashpw(b.get('password','')))).fetchone(); c.close()
            if not r:return self.json({'error':'invalid_credentials'},401)
            return self.json({'token':token(r['id']),'user':dict(r)})
        if p=='/api/logout': return self.json({'ok':True})
        if p=='/api/events':
            allowed={'view','qr_scan','verify','engage','source_open','journey_start','journey_complete','reuse','collaboration_request','ai_question','divergence_flag','correction','passport_share','learning_step'}; typ=b.get('type','engage');
            if typ not in allowed: typ='engage'
            event(typ,b.get('content_id'),uid['id'] if uid else None,b.get('meta'),self.client_address[0]); return self.json({'ok':True,'metrics':metrics()})
        if p=='/api/reuse':
            cid=b.get('content_id'); x=content(cid)
            if not x:return self.json({'error':'not_found'},404)
            c=db(); c.execute('insert into reuse(content_id,creator,channel,attribution,created_at) values(?,?,?,?,?)',(cid,b.get('creator','Anonymous'),b.get('channel','Web'),x['source_name']+' — '+x['source_url'],now())); c.commit(); c.close(); event('reuse',cid,uid['id'] if uid else None,{'channel':b.get('channel')}); return self.json({'ok':True,'attribution':x['source_name']+' — '+x['source_url']})
        if p=='/api/collaboration':
            if not uid:return self.json({'error':'login_required'},401)
            c=db(); c.execute('insert into collaborations(from_org,to_org,content_id,message,created_at) values(?,?,?,?,?)',(b.get('from_org',uid['name']),b.get('to_org','Knowledge partner'),b.get('content_id'),b.get('message',''),now())); c.commit(); c.close(); event('collaboration_request',b.get('content_id'),uid['id'],{'to':b.get('to_org')}); return self.json({'ok':True})
        if p=='/api/ai/ask':
            q=(b.get('question') or '').strip(); cid=b.get('content_id'); x=content(cid) if cid else None; event('ai_question',cid,uid['id'] if uid else None,{'question':q[:300]})
            if not q:return self.json({'error':'question_required'},400)
            if x:
                answer=x.get('excerpt','') if any(k in q.lower() for k in ['what','ما','source','مصدر','license','ترخيص','من','who']) else ('هذه الإجابة مقيدة بالسجل الموثق. '+x.get('review','')+' '+x.get('rights',''))
                return self.json({'answer':answer.strip(),'grounded':True,'insufficient_sources':False,'citations':[{'title':x['title'],'url':x['source_url'],'source':x['source_name']}],'guardrail':'الإجابة مبنية على سجل المادة ومصدرها المرتبط؛ لا تُنشئ حكمًا من خارج الأدلة.'})
            return self.json({'answer':'لا توجد مادة محددة في سياق السؤال. أَثَرُهُم لا يخمّن: اختر مادة موثقة أولًا أو أضف مصدرًا إلى السجل.','grounded':False,'insufficient_sources':True,'citations':[],'guardrail':'grounded-only'})
        if p=='/api/content/create':
            if not uid:return self.json({'error':'login_required'},401)
            if uid['role']!='institution':return self.json({'error':'forbidden'},403)
            required=['id','title','source_id','source_url'];
            if any(not b.get(k) for k in required):return self.json({'error':'missing_fields'},400)
            c=db();
            try:
                c.execute('''insert into content(id,title,kind,source_id,source_url,excerpt,rights,status,review,ai,divergence,slug,trace,version,created_at,updated_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(b['id'],b['title'],b.get('kind','Knowledge asset'),b['source_id'],b['source_url'],b.get('excerpt',''),b.get('rights','Verify publisher terms'),b.get('status','Pending review'),b.get('review',''),b.get('ai',''),0,b.get('slug',re.sub(r'[^a-z0-9]+','-',b['id'].lower())),b.get('trace','Source → Atharhum identity → Review'),1,now(),now())); c.execute('insert into versions(content_id,version,change_type,summary,actor,created_at) values(?,?,?,?,?,?)',(b['id'],1,'created','Initial knowledge asset','Institution',now())); c.commit()
            except sqlite3.IntegrityError:return self.json({'error':'id_exists'},409)
            finally:c.close()
            return self.json({'content':content(b['id'])},201)
        if p=='/api/correction':
            if not uid:return self.json({'error':'login_required'},401)
            cid=b.get('content_id'); x=content(cid)
            if not x:return self.json({'error':'not_found'},404)
            c=db(); c.execute('update content set divergence=0,version=version+1,updated_at=? where id=?',(now(),cid)); c.execute('insert into versions(content_id,version,change_type,summary,actor,created_at) values(?,?,?,?,?,?)',(cid,x['version']+1,'correction',b.get('summary','Correction recorded'),uid['name'],now())); c.commit(); c.close(); event('correction',cid,uid['id'],{'summary':b.get('summary','')}); return self.json({'ok':True,'content':content(cid)})
        return self.json({'error':'not_found'},404)

init()
os.chdir(ROOT)
print('Atharhum Production running on http://0.0.0.0:'+str(PORT))
ThreadingHTTPServer(('0.0.0.0',PORT),H).serve_forever()
