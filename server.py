"""Atharhum application server. SQLite for local tests; PostgreSQL for hosted production."""
from __future__ import annotations
import os, json, sqlite3, hashlib, secrets, hmac, re, time, logging, urllib.parse, mimetypes, threading
from datetime import datetime, timezone
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / 'static'
PORT = int(os.getenv('PORT', '8080'))
DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
DB_PATH = Path(os.getenv('ATHARHUM_DB_PATH', str(ROOT / 'data' / 'atharhum.db')))
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', f'http://localhost:{PORT}').rstrip('/')
SECRET = os.getenv('ATHARHUM_SECRET', '')
BOOTSTRAP_TOKEN = os.getenv('ATHARHUM_BOOTSTRAP_TOKEN', '')
IS_PRODUCTION = os.getenv('RENDER', '').lower() == 'true' or os.getenv('APP_ENV', '').lower() == 'production'
if IS_PRODUCTION and len(SECRET) < 32:
    raise RuntimeError('ATHARHUM_SECRET must be set to a random secret of at least 32 characters in production')
if not SECRET:
    SECRET = 'local-only-' + hashlib.sha256(str(ROOT).encode()).hexdigest()
SEED_DEMO = os.getenv('ATHARHUM_SEED_DEMO', 'false' if IS_PRODUCTION else 'true').lower() == 'true'

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'), format='%(asctime)s %(levelname)s %(message)s')
LOG = logging.getLogger('atharhum')

SEED_SOURCES = [
('SRC-QF','Quran Foundation','Quran data provider','https://quran.com/','https://api-docs.quran.com/docs/api-reference/','public_source','Public API documentation; no partnership implied.'),
('SRC-TANZIL','Tanzil Project','Open Quran text project','https://tanzil.net/','https://tanzil.net/docs/Text_License','open_licensed_source','Tanzil states verbatim copies are permitted under CC BY 3.0 with attribution; source text must not be changed.'),
('SRC-YAQEEN','Yaqeen Institute for Islamic Research','Islamic research institute','https://yaqeeninstitute.org/','https://yaqeeninstitute.org/','public_source','Public research and educational resources; no partnership implied.'),
('SRC-IIIT','International Institute of Islamic Thought (IIIT)','Research and publishing institute','https://iiit.org/','https://iiit.org/en/research-tools/resources/','public_source','Public institutional resource metadata; no partnership implied.'),
('SRC-C2PA','C2PA','Content provenance standard','https://c2pa.org/','https://c2pa.org/principles/','technical_reference','Technical provenance reference; not an Islamic authority.')]
SEED_CONTENT = [
('ATH-TANZIL-001','Tanzil Quran Text — License & Provenance Record','Open knowledge source','SRC-TANZIL','https://tanzil.net/docs/Text_License','Tanzil states its Quran text is carefully produced, highly verified and continuously monitored, and licenses verbatim copying/distribution under CC BY 3.0 with attribution.','CC BY 3.0 for verbatim Quran text; attribution required; changing the text is not allowed.','approved','Publisher license metadata checked','No AI transformation on source text',0,'tanzil-license','Tanzil source → rights recorded → Atharhum identity → public verification → permitted reuse'),
('ATH-QURAN-001','Al-Fatihah 1:1 — Basmalah','Quran verse','SRC-QF','https://quran.com/1/1','بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ','Source-linked; verify publisher terms before redistribution','source-linked','Source URL recorded; interpretation requires cited tafsir','No AI transformation on source text',0,'quran-1-1','Quran Foundation source → Atharhum identity → public verification'),
('ATH-YAQ-001','Basics of Islam','Educational resource','SRC-YAQEEN','https://yaqeeninstitute.org/what-islam-says-about/basics-of-islam','A public Yaqeen resource introducing foundational Islamic beliefs and practices.','Publicly readable; reuse subject to publisher terms','source-linked','Publisher metadata; independent review status not asserted','No AI transformation claimed',0,'yaqeen-basics','Yaqeen source → Atharhum identity → public verification → learning journey'),
('ATH-YAQ-002','Keys to Tadabbur: How to Reflect Deeply on the Qur\'an','Research paper','SRC-YAQEEN','https://legacy-api.yaqeeninstitute.org/read/paper/keys-to-tadabbur-how-to-reflect-deeply-on-the-quran','A Yaqeen paper on reflecting deeply on the Qur\'an, authored by Sh. Yousef Wahb and Sh. Mohammad Elshinawy.','Publicly readable; reuse subject to publisher terms','source-linked','Publisher metadata; source page lists authors and dates','AI may summarize only with source citation',0,'yaqeen-tadabbur','Yaqeen source → Atharhum identity → AI evidence layer → learning journey'),
('ATH-IIIT-001','IIIT Scholar — AI Search','Knowledge infrastructure','SRC-IIIT','https://iiit.org/en/research-tools/about/iiit-scholar-ai-search/','IIIT describes an intelligent search experience for Islamic scholarship using a digitized collection of books, journals and manuscripts and source tracing.','Verify individual publication rights before reuse','source-linked','Institutional source metadata','Source describes RAG-based research tooling',0,'iiit-scholar','IIIT resource → Atharhum identity → collaboration candidate → knowledge graph')]

# A small DB facade lets local tests use SQLite while Render can use PostgreSQL via DATABASE_URL.
class Cursor:
    def __init__(self, cur, pg=False): self.cur, self.pg = cur, pg
    def execute(self, sql, params=()): self.cur.execute(sql, params); return self
    def fetchone(self):
        r=self.cur.fetchone()
        if r is None: return None
        return dict(r) if isinstance(r, dict) else dict(r)
    def fetchall(self):
        rows=self.cur.fetchall(); return [dict(r) if isinstance(r, dict) else dict(r) for r in rows]
    @property
    def rowcount(self): return self.cur.rowcount
    @property
    def lastrowid(self): return getattr(self.cur, 'lastrowid', None)

PG_POOL = None

class DB:
    def __init__(self):
        self.pg=bool(DATABASE_URL)
        if self.pg:
            try:
                if PG_POOL is None: raise RuntimeError('PostgreSQL connection pool was not initialized')
                self.conn=PG_POOL.getconn()
            except Exception as e: raise RuntimeError('DATABASE_URL is set but PostgreSQL connection failed; verify psycopg dependency and database credentials') from e
        else:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.conn=sqlite3.connect(DB_PATH, timeout=15)
            self.conn.row_factory=sqlite3.Row
            self.conn.execute('PRAGMA foreign_keys=ON')
            self.conn.execute('PRAGMA busy_timeout=15000')
            self.conn.execute('PRAGMA journal_mode=WAL')
    def execute(self, sql, params=()):
        if self.pg:
            sql=sql.replace('INSERT OR IGNORE INTO', 'INSERT INTO')
            sql=sql.replace('?', '%s')
            return Cursor(self.conn.cursor().execute(sql, params), True)
        return Cursor(self.conn.execute(sql, params), False)
    def executescript(self, sql):
        if self.pg:
            # Schema contains ordinary statements separated by semicolons only.
            for stmt in sql.split(';'):
                if stmt.strip(): self.conn.execute(stmt)
        else: self.conn.executescript(sql)
    def commit(self): self.conn.commit()
    def close(self): self.conn.close()

def db(): return DB()
def now(): return datetime.now(timezone.utc).isoformat()
def hashpw(p): return hashlib.pbkdf2_hmac('sha256', p.encode(), SECRET.encode(), 310000).hex()
def valid_url(url):
    try:
        u=urllib.parse.urlparse(str(url))
        return u.scheme in ('http','https') and bool(u.netloc) and len(str(url)) <= 2048
    except Exception: return False

def init():
    c=db()
    if c.pg:
        schema='''
        CREATE TABLE IF NOT EXISTS organizations(id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE, slug TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users(id BIGSERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL, organization_id BIGINT REFERENCES organizations(id), password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,name TEXT NOT NULL,type TEXT,url TEXT,evidence_url TEXT,status TEXT,note TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS content(id TEXT PRIMARY KEY,title TEXT NOT NULL,kind TEXT,source_id TEXT NOT NULL REFERENCES sources(id),source_url TEXT,excerpt TEXT,rights TEXT,status TEXT,review TEXT,ai TEXT,divergence INTEGER DEFAULT 0,slug TEXT,trace TEXT,version INTEGER DEFAULT 1,content_hash TEXT,visibility TEXT DEFAULT 'public',organization_id BIGINT REFERENCES organizations(id),parent_content_id TEXT REFERENCES content(id),language TEXT DEFAULT 'ar',transformation_type TEXT DEFAULT 'original',approved_by TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS journeys(id TEXT PRIMARY KEY,title TEXT,audience TEXT,description TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS journey_steps(journey_id TEXT REFERENCES journeys(id),position INTEGER,content_id TEXT REFERENCES content(id),PRIMARY KEY(journey_id,position));
        CREATE TABLE IF NOT EXISTS journey_progress(id BIGSERIAL PRIMARY KEY,journey_id TEXT REFERENCES journeys(id),user_id BIGINT REFERENCES users(id),session_key TEXT NOT NULL,step_position INTEGER NOT NULL,status TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(journey_id,session_key,step_position));
        CREATE TABLE IF NOT EXISTS events(id BIGSERIAL PRIMARY KEY,type TEXT NOT NULL,content_id TEXT,user_id BIGINT REFERENCES users(id),meta TEXT,ip TEXT,created_at TEXT NOT NULL,prev_hash TEXT,event_hash TEXT);
        CREATE TABLE IF NOT EXISTS versions(id BIGSERIAL PRIMARY KEY,content_id TEXT REFERENCES content(id),version INTEGER,change_type TEXT,summary TEXT,actor TEXT,created_at TEXT NOT NULL,content_hash TEXT);
        CREATE TABLE IF NOT EXISTS collaborations(id BIGSERIAL PRIMARY KEY,from_org TEXT,to_org TEXT,content_id TEXT,message TEXT,status TEXT DEFAULT 'proposed',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reuse(id BIGSERIAL PRIMARY KEY,content_id TEXT,creator TEXT,channel TEXT,attribution TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id BIGINT REFERENCES users(id),expires_at BIGINT);
        CREATE INDEX IF NOT EXISTS idx_events_type_created ON events(type,created_at);
        CREATE INDEX IF NOT EXISTS idx_events_content ON events(content_id);
        CREATE INDEX IF NOT EXISTS idx_content_source ON content(source_id);
        CREATE INDEX IF NOT EXISTS idx_content_org ON content(organization_id,visibility);
        CREATE INDEX IF NOT EXISTS idx_versions_content ON versions(content_id,version);
        '''
    else:
        schema='''
        CREATE TABLE IF NOT EXISTS organizations(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, slug TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL, organization_id INTEGER REFERENCES organizations(id), password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,name TEXT NOT NULL,type TEXT,url TEXT,evidence_url TEXT,status TEXT,note TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS content(id TEXT PRIMARY KEY,title TEXT NOT NULL,kind TEXT,source_id TEXT NOT NULL REFERENCES sources(id),source_url TEXT,excerpt TEXT,rights TEXT,status TEXT,review TEXT,ai TEXT,divergence INTEGER DEFAULT 0,slug TEXT,trace TEXT,version INTEGER DEFAULT 1,content_hash TEXT,visibility TEXT DEFAULT 'public',organization_id INTEGER REFERENCES organizations(id),parent_content_id TEXT REFERENCES content(id),language TEXT DEFAULT 'ar',transformation_type TEXT DEFAULT 'original',approved_by TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS journeys(id TEXT PRIMARY KEY,title TEXT,audience TEXT,description TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS journey_steps(journey_id TEXT REFERENCES journeys(id),position INTEGER,content_id TEXT REFERENCES content(id),PRIMARY KEY(journey_id,position));
        CREATE TABLE IF NOT EXISTS journey_progress(id INTEGER PRIMARY KEY AUTOINCREMENT,journey_id TEXT REFERENCES journeys(id),user_id INTEGER REFERENCES users(id),session_key TEXT NOT NULL,step_position INTEGER NOT NULL,status TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(journey_id,session_key,step_position));
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,type TEXT NOT NULL,content_id TEXT,user_id INTEGER REFERENCES users(id),meta TEXT,ip TEXT,created_at TEXT NOT NULL,prev_hash TEXT,event_hash TEXT);
        CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY AUTOINCREMENT,content_id TEXT REFERENCES content(id),version INTEGER,change_type TEXT,summary TEXT,actor TEXT,created_at TEXT NOT NULL,content_hash TEXT);
        CREATE TABLE IF NOT EXISTS collaborations(id INTEGER PRIMARY KEY AUTOINCREMENT,from_org TEXT,to_org TEXT,content_id TEXT,message TEXT,status TEXT DEFAULT 'proposed',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reuse(id INTEGER PRIMARY KEY AUTOINCREMENT,content_id TEXT,creator TEXT,channel TEXT,attribution TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),expires_at INTEGER);
        CREATE INDEX IF NOT EXISTS idx_events_type_created ON events(type,created_at);
        CREATE INDEX IF NOT EXISTS idx_events_content ON events(content_id);
        CREATE INDEX IF NOT EXISTS idx_content_source ON content(source_id);
        CREATE INDEX IF NOT EXISTS idx_content_org ON content(organization_id,visibility);
        CREATE INDEX IF NOT EXISTS idx_versions_content ON versions(content_id,version);
        '''
    c.executescript(schema)
    c.execute('INSERT INTO organizations(name,slug,created_at) VALUES(?,?,?) ON CONFLICT(slug) DO NOTHING',('Atharhum Primary Organization','atharhum-primary',now()))
    org=c.execute('SELECT id FROM organizations WHERE slug=?',('atharhum-primary',)).fetchone()['id']
    user=c.execute('SELECT id FROM users WHERE email=?',('demo@atharhum.org',)).fetchone()
    if not user and SEED_DEMO:
        c.execute('INSERT INTO users(email,name,role,organization_id,password_hash,created_at) VALUES(?,?,?,?,?,?)',('demo@atharhum.org','Demo Institution','institution',org,hashpw('Atharhum2026!'),now()))
    # Do not reset passwords on every startup. Seed only if missing.
    for s in SEED_SOURCES:
        c.execute('INSERT INTO sources(id,name,type,url,evidence_url,status,note,created_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',(*s,now()))
    for x in SEED_CONTENT:
        data={'id':x[0],'title':x[1],'kind':x[2],'source_id':x[3],'source_url':x[4],'excerpt':x[5],'rights':x[6],'status':x[7],'review':x[8],'ai':x[9],'divergence':x[10],'slug':x[11],'trace':x[12],'version':1,'visibility':'public'}
        ch=content_digest(data)
        c.execute('INSERT INTO content(id,title,kind,source_id,source_url,excerpt,rights,status,review,ai,divergence,slug,trace,version,content_hash,visibility,organization_id,parent_content_id,language,transformation_type,approved_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',(x[0],x[1],x[2],x[3],x[4],x[5],x[6],x[7],x[8],x[9],x[10],x[11],x[12],1,ch,'public',None,None,'ar','original',None,now(),now()))
    c.execute('INSERT INTO journeys(id,title,audience,description,created_at) VALUES(?,?,?,?,?) ON CONFLICT(id) DO NOTHING',('JRN-001','Start with the Qur\'an: Source → Context → Reflection','Beginner','A measurable learning journey built from public source records.',now()))
    for i,cid in enumerate(['ATH-QURAN-001','ATH-YAQ-001','ATH-YAQ-002'],1): c.execute('INSERT INTO journey_steps(journey_id,position,content_id) VALUES(?,?,?) ON CONFLICT(journey_id,position) DO NOTHING',('JRN-001',i,cid))
    c.commit(); c.close()

def content_digest(d):
    keys=('id','title','source_id','source_url','excerpt','rights','review','ai','version')
    payload={k:d.get(k) for k in keys}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def safe_user(row): return {k:row[k] for k in ('id','email','name','role','organization_id','created_at')}
def user_from(headers):
    t=headers.get('Authorization','').replace('Bearer ','').strip()
    if not t:return None
    c=db(); r=c.execute('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires_at>?',(t,int(time.time()))).fetchone(); c.close(); return dict(r) if r else None

def event(typ,cid=None,uid=None,meta=None,ip=''):
    # Serialize hash-chain writes within the single application instance.
    with EVENT_LOCK:
        c=db(); prev=c.execute('SELECT event_hash FROM events ORDER BY id DESC LIMIT 1').fetchone(); prev_hash=prev['event_hash'] if prev else 'GENESIS'
        payload={'type':typ,'content_id':cid,'user_id':uid,'meta':meta or {},'created_at':now(),'prev_hash':prev_hash}
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        c.execute('INSERT INTO events(type,content_id,user_id,meta,ip,created_at,prev_hash,event_hash) VALUES(?,?,?,?,?,?,?,?)',(typ,cid,uid,json.dumps(meta or {},ensure_ascii=False),ip,payload['created_at'],prev_hash,digest)); c.commit(); c.close()

def content(cid, uid=None):
    c=db(); r=c.execute('SELECT x.*,s.name source_name,s.url source_root,s.evidence_url FROM content x JOIN sources s ON s.id=x.source_id WHERE x.id=?',(cid,)).fetchone(); c.close()
    if not r:return None
    d=dict(r)
    if d.get('visibility')!='public' and (not uid or d.get('organization_id') != uid.get('organization_id')): return None
    d['hash_valid']=bool(d.get('content_hash')) and hmac.compare_digest(str(d.get('content_hash')),content_digest(d))
    d['trace']=(d.get('trace') or '').split(' → ')
    return d

def metrics(org_id=None):
    c=db()
    if org_id is None:
        rows=c.execute("SELECT type,COUNT(*) n FROM events WHERE content_id IN (SELECT id FROM content WHERE visibility='public') OR (content_id IS NULL AND type IN ('journey_start','journey_complete','learning_step')) GROUP BY type").fetchall()
        n=c.execute("SELECT COUNT(*) n FROM content WHERE visibility='public'").fetchone()['n']
        hashrows=c.execute("SELECT source_url,rights,review,ai,version,content_hash FROM content WHERE visibility='public'").fetchall()
    else:
        rows=c.execute("SELECT type,COUNT(*) n FROM events WHERE content_id IN (SELECT id FROM content WHERE visibility='public' OR organization_id=?) OR user_id IN (SELECT id FROM users WHERE organization_id=?) OR (content_id IS NULL AND type IN ('journey_start','journey_complete','learning_step')) GROUP BY type",(org_id,org_id)).fetchall()
        n=c.execute("SELECT COUNT(*) n FROM content WHERE visibility='public' OR organization_id=?",(org_id,)).fetchone()['n']
        hashrows=c.execute("SELECT source_url,rights,review,ai,version,content_hash FROM content WHERE visibility='public' OR organization_id=?",(org_id,)).fetchall()
    m={r['type']:r['n'] for r in rows}; total=sum(m.values()); sources=c.execute('SELECT COUNT(*) n FROM sources').fetchone()['n']
    trace=round(100*sum(bool(r['source_url'] and r['rights'] and r['review'] and r['ai'] and r['version'] and r['content_hash']) for r in hashrows)/max(1,len(hashrows)))
    views=m.get('view',0); starts=m.get('journey_start',0); completions=m.get('journey_complete',0)
    c.close()
    return {'content':n,'sources':sources,'views':views,'verifications':m.get('verify',0),'source_opens':m.get('source_open',0),'ai_questions':m.get('ai_question',0),'reuse':m.get('reuse',0),'collaborations':m.get('collaboration_request',0),'journeys_started':starts,'journeys_completed':completions,'corrections':m.get('correction',0),'divergence_flags':m.get('divergence_flag',0),'events':total,'traceability':trace,'engagement_rate':round(100*(m.get('source_open',0)+m.get('ai_question',0)+m.get('reuse',0)+starts)/max(1,views)) if views else 0}

ALLOWED_EVENTS={'view','qr_scan','verify','engage','source_open','journey_start','journey_complete','reuse','collaboration_request','ai_question','divergence_flag','correction','passport_share','learning_step','content_search','translation_requested','adaptation_requested'}
LOGIN_FAILURES={}
EVENT_LOCK=threading.Lock()

def read_json(h):
    try:
        n=int(h.headers.get('Content-Length','0'))
        if n>1_000_000: return {}
        return json.loads(h.rfile.read(n) or b'{}')
    except Exception:return {}

class Handler(BaseHTTPRequestHandler):
    server_version='Atharhum/2.0'
    def log_message(self,fmt,*args): LOG.info('%s %s',self.address_string(),fmt%args)
    def send_json(self,obj,status=200):
        raw=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'"); self.end_headers(); self.wfile.write(raw)
    def send_html(self,raw,status=200):
        self.send_response(status); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'"); self.end_headers(); self.wfile.write(raw)
    def get_uid(self): return user_from(self.headers)
    def do_GET(self):
        p=urlparse(self.path).path; uid=self.get_uid()
        if p=='/health':
            try:
                c=db(); c.execute('SELECT 1').fetchone(); c.close(); self.send_json({'ok':True,'service':'atharhum','database':'postgresql' if DATABASE_URL else 'sqlite','time':now()})
            except Exception: self.send_json({'ok':False,'service':'atharhum'},503)
            return
        if p=='/' or p.startswith('/verify/'): return self.send_html((STATIC/'index.html').read_bytes())
        if p.startswith('/static/'):
            rel=p[len('/static/'):]; f=(STATIC/rel).resolve()
            if STATIC.resolve() not in f.parents or not f.is_file(): return self.send_json({'error':'not_found'},404)
            raw=f.read_bytes(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(f.name)[0] or 'application/octet-stream'); self.send_header('Content-Length',str(len(raw))); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(raw); return
        if p.startswith('/qr/') and p.endswith('.png'):
            name=p[len('/qr/'):]
            if not re.fullmatch(r'[A-Z0-9-]+\.png',name): return self.send_json({'error':'not_found'},404)
            f=(ROOT/'qr'/name).resolve()
            if (ROOT/'qr').resolve() not in f.parents: return self.send_json({'error':'not_found'},404)
            cid=name[:-4]
            if not content(cid,uid): return self.send_json({'error':'not_found'},404)
            if not f.is_file():
                try:
                    import qrcode
                    f.parent.mkdir(parents=True,exist_ok=True); qrcode.make(PUBLIC_BASE_URL+'/verify/'+urllib.parse.quote(cid,safe='')).save(f)
                except Exception: return self.send_json({'error':'qr_unavailable'},503)
            raw=f.read_bytes(); self.send_response(200); self.send_header('Content-Type','image/png'); self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','public, max-age=300'); self.end_headers(); self.wfile.write(raw); return
        if p=='/api/bootstrap':
            c=db(); rows=c.execute("SELECT x.*,s.name source_name,s.url source_root FROM content x JOIN sources s ON s.id=x.source_id WHERE x.visibility='public' OR x.organization_id=? ORDER BY x.created_at",(uid['organization_id'] if uid else -1,)).fetchall(); sources=c.execute('SELECT * FROM sources ORDER BY name').fetchall(); journeys=c.execute('SELECT * FROM journeys ORDER BY created_at').fetchall(); c.close()
            for r in rows:
                if r.get('trace') is not None:r['trace']=r['trace'].split(' → ')
            self.send_json({'contents':rows,'sources':sources,'journeys':journeys,'metrics':metrics(uid['organization_id'] if uid else None),'user':safe_user(uid) if uid else None,'demo_mode':SEED_DEMO}); return
        if p=='/api/metrics': return self.send_json(metrics(uid['organization_id'] if uid else None))
        if p=='/api/admin/events':
            if not uid or uid['role']!='institution': return self.send_json({'error':'forbidden'},403)
            c=db(); rows=c.execute('SELECT e.* FROM events e WHERE e.user_id IN (SELECT id FROM users WHERE organization_id=?) OR e.content_id IN (SELECT id FROM content WHERE organization_id=? OR visibility=?) ORDER BY e.id DESC LIMIT 100',(uid['organization_id'],uid['organization_id'],'public')).fetchall(); c.close(); return self.send_json({'events':rows})
        if p=='/api/integrity/audit-chain':
            if not uid or uid['role']!='institution': return self.send_json({'error':'forbidden'},403)
            c=db(); rows=c.execute('SELECT id,type,content_id,prev_hash,event_hash,created_at FROM events ORDER BY id').fetchall(); valid=True; prev='GENESIS'
            for row in rows:
                if row['prev_hash']!=prev: valid=False; break
                full=c.execute('SELECT type,content_id,user_id,meta,created_at,prev_hash,event_hash FROM events WHERE id=?',(row['id'],)).fetchone()
                payload={'type':full['type'],'content_id':full['content_id'],'user_id':full['user_id'],'meta':json.loads(full['meta'] or '{}'),'created_at':full['created_at'],'prev_hash':full['prev_hash']}
                expected=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
                if not hmac.compare_digest(expected,full['event_hash'] or ''): valid=False; break
                prev=row['event_hash']
            c.close()
            return self.send_json({'valid_chain':valid,'events_checked':len(rows),'note':'Hash chaining detects accidental or partial tampering; it is not a qualified digital signature.'})
        if p=='/api/journey/progress':
            session_key='u:'+str(uid['id']) if uid else 'anon:'+hashlib.sha256((self.headers.get('X-Session-ID','anonymous')+SECRET).encode()).hexdigest()[:32]
            c=db(); rows=c.execute('SELECT step_position,status FROM journey_progress WHERE journey_id=? AND session_key=? ORDER BY step_position',('JRN-001',session_key)).fetchall(); c.close()
            completed=[r['step_position'] for r in rows if r['status']=='completed']
            return self.send_json({'journey_id':'JRN-001','completed_steps':completed,'next_step':max(completed,default=0)+1 if len(completed)<3 else 4})
        if p.startswith('/api/versions/'):
            cid=p.rsplit('/',1)[-1]; x=content(cid,uid)
            if not x:return self.send_json({'error':'not_found'},404)
            c=db(); rows=c.execute('SELECT version,change_type,summary,actor,created_at,content_hash FROM versions WHERE content_id=? ORDER BY version DESC',(cid,)).fetchall(); c.close(); return self.send_json({'content_id':cid,'versions':rows})
        if p.startswith('/api/content/'):
            cid=p.rsplit('/',1)[-1]; x=content(cid,uid)
            if not x:return self.send_json({'error':'not_found'},404)
            event('view',cid,uid['id'] if uid else None,{},hashlib.sha256((self.client_address[0]+SECRET).encode()).hexdigest()[:16]); return self.send_json({'content':x,'metrics':metrics(uid['organization_id'] if uid else None)})
        if p.startswith('/api/verify/'):
            cid=p.rsplit('/',1)[-1]; x=content(cid,uid)
            if not x:return self.send_json({'error':'not_found'},404)
            event('verify',cid,uid['id'] if uid else None,{},hashlib.sha256((self.client_address[0]+SECRET).encode()).hexdigest()[:16]);
            verified=x.get('status','').lower() not in ('rejected','withdrawn') and bool(x.get('source_url'))
            return self.send_json({'verified':verified,'integrity':{'source_linked':bool(x.get('source_url')),'identity':bool(x.get('content_hash')) and bool(x.get('hash_valid')),'hash_valid':bool(x.get('hash_valid')),'review_recorded':bool(x.get('review')),'ai_disclosed':bool(x.get('ai')),'divergence':x['divergence'],'content_hash':x.get('content_hash')},'content':x,'metrics':metrics(uid['organization_id'] if uid else None)})
        return self.send_json({'error':'not_found'},404)
    def do_POST(self):
        p=urlparse(self.path).path; b=read_json(self); uid=self.get_uid(); ip=self.client_address[0]
        if p=='/api/bootstrap-admin':
            if not BOOTSTRAP_TOKEN or not hmac.compare_digest(str(b.get('bootstrap_token','')),BOOTSTRAP_TOKEN):return self.send_json({'error':'bootstrap_forbidden'},403)
            email=str(b.get('email','')).strip().lower(); name=str(b.get('name','')).strip()[:160]; password=str(b.get('password',''))
            if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email) or len(name)<2 or len(password)<14:return self.send_json({'error':'invalid_admin_fields','message':'Valid email, name, and password of at least 14 characters are required.'},400)
            c=db(); existing=c.execute("SELECT COUNT(*) n FROM users WHERE role='institution'").fetchone()['n']
            if existing:
                c.close(); return self.send_json({'error':'bootstrap_already_completed'},409)
            org=c.execute('SELECT id FROM organizations WHERE slug=?',('atharhum-primary',)).fetchone()
            if not org:c.close(); return self.send_json({'error':'organization_missing'},500)
            try:c.execute('INSERT INTO users(email,name,role,organization_id,password_hash,created_at) VALUES(?,?,?,?,?,?)',(email,name,'institution',org['id'],hashpw(password),now())); c.commit()
            except Exception:
                c.close(); return self.send_json({'error':'account_creation_failed'},409)
            c.close(); event('institution_bootstrapped',None,None,{'email_domain':email.rsplit('@',1)[-1]}); return self.send_json({'ok':True,'message':'Institution account created. Remove ATHARHUM_BOOTSTRAP_TOKEN from hosting environment now.'},201)
        if p=='/api/login':
            attempts=LOGIN_FAILURES.get(ip,[]); attempts=[t for t in attempts if time.time()-t<300]
            if len(attempts)>=10: return self.send_json({'error':'rate_limited','message':'Try again in five minutes.'},429)
            c=db(); r=c.execute('SELECT * FROM users WHERE email=?',(str(b.get('email','')).strip().lower(),)).fetchone(); c.close()
            if not r or not hmac.compare_digest(r['password_hash'],hashpw(str(b.get('password','')))):
                attempts.append(time.time()); LOGIN_FAILURES[ip]=attempts; return self.send_json({'error':'invalid_credentials'},401)
            LOGIN_FAILURES.pop(ip,None); t=secrets.token_urlsafe(40); c=db(); c.execute('INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)',(t,r['id'],int(time.time())+86400)); c.commit(); c.close()
            event('login',None,r['id'],{},ip); return self.send_json({'token':t,'user':safe_user(r)})
        if p=='/api/logout':
            t=self.headers.get('Authorization','').replace('Bearer ','').strip(); c=db(); c.execute('DELETE FROM sessions WHERE token=?',(t,)); c.commit(); c.close(); return self.send_json({'ok':True})
        if p=='/api/events':
            typ=b.get('type','engage')
            if typ not in ALLOWED_EVENTS:return self.send_json({'error':'invalid_event_type'},400)
            cid=b.get('content_id');
            if cid and not content(cid,uid):return self.send_json({'error':'not_found'},404)
            meta=b.get('meta') if isinstance(b.get('meta'),dict) else {}
            # Never store raw IP address in the analytics event log.
            event(typ,cid,uid['id'] if uid else None,meta,hashlib.sha256((ip+SECRET).encode()).hexdigest()[:16]); return self.send_json({'ok':True,'metrics':metrics(uid['organization_id'] if uid else None)})
        if p=='/api/reuse':
            cid=b.get('content_id'); x=content(cid,uid)
            if not x:return self.send_json({'error':'not_found'},404)
            creator=str(b.get('creator','Anonymous'))[:160]; channel=str(b.get('channel','Web'))[:120]
            attribution=f"{x['title']} — {x['source_name']} — {x['source_url']} — Atharhum ID: {cid} — Version: {x['version']}"
            c=db(); c.execute('INSERT INTO reuse(content_id,creator,channel,attribution,created_at) VALUES(?,?,?,?,?)',(cid,creator,channel,attribution,now())); c.commit(); c.close(); event('reuse',cid,uid['id'] if uid else None,{'channel':channel}); return self.send_json({'ok':True,'attribution':attribution})
        if p=='/api/collaboration':
            if not uid:return self.send_json({'error':'login_required'},401)
            cid=b.get('content_id');
            if cid and not content(cid,uid):return self.send_json({'error':'not_found'},404)
            to_org=str(b.get('to_org','')).strip()[:180]; msg=str(b.get('message',''))[:2000]
            if not to_org:return self.send_json({'error':'recipient_required'},400)
            c=db(); c.execute('INSERT INTO collaborations(from_org,to_org,content_id,message,status,created_at) VALUES(?,?,?,?,?,?)',(uid['name'],to_org,cid,msg,'proposed',now())); c.commit(); c.close(); event('collaboration_request',cid,uid['id'],{'to':to_org}); return self.send_json({'ok':True,'status':'proposed'})
        if p=='/api/ai/ask':
            q=str(b.get('question') or '').strip()[:1000]; cid=b.get('content_id')
            if not q:return self.send_json({'error':'question_required'},400)
            x=content(cid,uid) if cid else None; event('ai_question',cid if x else None,uid['id'] if uid else None,{'question_length':len(q)})
            if not x:return self.send_json({'answer':'لا توجد مادة محددة ومتاحة في سياق السؤال. لا يخمّن أَثَرُهُم؛ اختر مادة موثقة أولًا. لا تُقدَّم فتاوى أو أحكام شرعية تلقائية.','grounded':False,'insufficient_sources':True,'citations':[],'guardrail':'grounded-only'})
            terms={'مصدر':'source','المصدر':'source','من أين':'source','ترخيص':'rights','حقوق':'rights','مراجعة':'review','راجع':'review','ذكاء':'ai','ai':'ai','نسخة':'version','إصدار':'version','عنوان':'title','ما هذه':'title'}
            ql=q.lower(); field=next((v for k,v in terms.items() if k in ql),None)
            if field=='source': ans=f"المصدر المسجل: {x['source_name']} — {x['source_url']}"
            elif field=='rights': ans=x.get('rights') or 'لم تُسجل بيانات حقوق كافية؛ تحقق من الناشر قبل إعادة الاستخدام.'
            elif field=='review': ans=x.get('review') or 'لا توجد مراجعة مسجلة في هذا السجل.'
            elif field=='ai': ans=x.get('ai') or 'لا يوجد إفصاح كافٍ عن دور AI.'
            elif field=='version': ans=f"رقم الإصدار المسجل: {x['version']}؛ بصمة السجل: {x.get('content_hash','غير متاحة')}"
            elif field=='title': ans=f"{x['title']} — {x.get('excerpt','')}"
            else: ans='المعلومات المتاحة في هذا السجل محدودة. أستطيع عرض المصدر والحقوق وحالة المراجعة والإفصاح عن AI والإصدار، لكن لا أستنتج أحكامًا أو معلومات خارج الدليل المسجل.'
            return self.send_json({'answer':ans,'grounded':True,'insufficient_sources':False,'citations':[{'title':x['title'],'url':x['source_url'],'source':x['source_name'],'content_id':x['id'],'version':x['version']}],'guardrail':'الإجابة مقيدة ببيانات السجل ومصدره؛ هذا ليس نموذج LLM/RAG ولا فتوى.'})
        if p=='/api/sources/create':
            if not uid:return self.send_json({'error':'login_required'},401)
            if uid['role']!='institution':return self.send_json({'error':'forbidden'},403)
            sid=str(b.get('id','')).strip().upper(); name=str(b.get('name','')).strip()[:240]; url=str(b.get('url','')).strip(); evidence=str(b.get('evidence_url','')).strip()
            if not re.fullmatch(r'SRC-[A-Z0-9-]{2,80}',sid) or not name or not valid_url(url):return self.send_json({'error':'invalid_source'},400)
            if evidence and not valid_url(evidence):return self.send_json({'error':'invalid_evidence_url'},400)
            c=db()
            try:c.execute('INSERT INTO sources(id,name,type,url,evidence_url,status,note,created_at) VALUES(?,?,?,?,?,?,?,?)',(sid,name,str(b.get('type','institutional source'))[:120],url,evidence or url,'institution_submitted',str(b.get('note','Pending verification; not a partnership claim'))[:1000],now())); c.commit()
            except Exception as e:
                c.close()
                if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():return self.send_json({'error':'source_exists'},409)
                return self.send_json({'error':'database_error'},500)
            c.close(); event('source_registered',None,uid['id'],{'source_id':sid}); return self.send_json({'ok':True,'source_id':sid},201)
        if p=='/api/content/adapt':
            if not uid:return self.send_json({'error':'login_required'},401)
            if uid['role']!='institution':return self.send_json({'error':'forbidden'},403)
            parent_id=str(b.get('parent_content_id','')); parent=content(parent_id,uid)
            if not parent:return self.send_json({'error':'parent_not_found'},404)
            cid=str(b.get('id','')).strip().upper(); title=str(b.get('title','')).strip()[:300]; language=str(b.get('language','')).strip()[:12]; transformation=str(b.get('transformation_type','translation')).strip().lower()
            if not re.fullmatch(r'ATH-[A-Z0-9-]{3,80}',cid) or not title or not language:return self.send_json({'error':'invalid_adaptation'},400)
            if transformation not in ('translation','summary','audience_adaptation','transliteration','format_conversion'):return self.send_json({'error':'invalid_transformation_type'},400)
            excerpt=str(b.get('excerpt','')).strip()[:5000]
            # The platform records an adaptation workflow; it does not pretend to generate a translation with an unavailable LLM.
            disclosure='Transformation requested: '+transformation+'. Output requires human review before publication; no automated scholarly approval.'
            trace=' → '.join([parent['source_name']+' source',parent_id,'Adaptation requested ('+language+')','Human review required'])
            data={'id':cid,'title':title,'source_id':parent['source_id'],'source_url':parent['source_url'],'excerpt':excerpt,'rights':parent['rights'],'review':'Pending human review','ai':disclosure,'version':1}; ch=content_digest(data); c=db()
            try:
                c.execute('INSERT INTO content(id,title,kind,source_id,source_url,excerpt,rights,status,review,ai,divergence,slug,trace,version,content_hash,visibility,organization_id,parent_content_id,language,transformation_type,approved_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(cid,title,'Derived adaptation',parent['source_id'],parent['source_url'],excerpt,parent['rights'],'pending','Pending human review',disclosure,0,re.sub(r'[^a-z0-9]+','-',cid.lower()),trace,1,ch,'private',uid['organization_id'],parent_id,language,transformation,None,now(),now())); c.execute('INSERT INTO versions(content_id,version,change_type,summary,actor,created_at,content_hash) VALUES(?,?,?,?,?,?,?)',(cid,1,'adaptation_requested',transformation+' to '+language,uid['name'],now(),ch)); c.commit()
            except Exception as e:
                c.close()
                if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():return self.send_json({'error':'id_exists'},409)
                LOG.exception('adaptation create failed'); return self.send_json({'error':'database_error'},500)
            c.close(); event('adaptation_requested',cid,uid['id'],{'parent_content_id':parent_id,'language':language,'type':transformation}); return self.send_json({'ok':True,'content':content(cid,uid),'message':'Adaptation workflow recorded; human review is required. No AI-generated text was fabricated.'},201)
        if p=='/api/content/create':
            if not uid:return self.send_json({'error':'login_required'},401)
            if uid['role']!='institution':return self.send_json({'error':'forbidden'},403)
            required=['id','title','source_id','source_url']
            if any(not str(b.get(k,'')).strip() for k in required):return self.send_json({'error':'missing_fields'},400)
            cid=str(b['id']).strip().upper(); title=str(b['title']).strip()[:300]; source_url=str(b['source_url']).strip()
            if not re.fullmatch(r'ATH-[A-Z0-9-]{3,80}',cid):return self.send_json({'error':'invalid_content_id'},400)
            if not valid_url(source_url):return self.send_json({'error':'invalid_source_url'},400)
            c=db()
            if not c.execute('SELECT 1 FROM sources WHERE id=?',(b['source_id'],)).fetchone():c.close(); return self.send_json({'error':'source_not_found'},400)
            version=1; data={'id':cid,'title':title,'source_id':b['source_id'],'source_url':source_url,'excerpt':str(b.get('excerpt',''))[:5000],'rights':str(b.get('rights','Verify publisher terms'))[:1000],'review':str(b.get('review','Pending review'))[:1000],'ai':str(b.get('ai','AI role not yet assessed'))[:1000],'version':version}; ch=content_digest(data)
            try:
                c.execute('INSERT INTO content(id,title,kind,source_id,source_url,excerpt,rights,status,review,ai,divergence,slug,trace,version,content_hash,visibility,organization_id,parent_content_id,language,transformation_type,approved_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(cid,title,str(b.get('kind','Knowledge asset'))[:100],b['source_id'],source_url,data['excerpt'],data['rights'],str(b.get('status','pending'))[:100],data['review'],data['ai'],0,re.sub(r'[^a-z0-9]+','-',cid.lower()),'Source → Atharhum identity → Human review → Publication',1,ch,'private',uid['organization_id'],None,str(b.get('language','ar'))[:12],'original',None,now(),now()))
                c.execute('INSERT INTO versions(content_id,version,change_type,summary,actor,created_at,content_hash) VALUES(?,?,?,?,?,?,?)',(cid,1,'created','Initial knowledge asset',uid['name'],now(),ch)); c.commit()
            except Exception as e:
                c.close()
                if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():return self.send_json({'error':'id_exists'},409)
                LOG.exception('create asset failed'); return self.send_json({'error':'database_error'},500)
            c.close(); event('content_created',cid,uid['id'],{'organization_id':uid['organization_id']}); return self.send_json({'content':content(cid,uid)},201)
        if p in ('/api/divergence','/api/correction','/api/review'):
            if not uid:return self.send_json({'error':'login_required'},401)
            if uid['role']!='institution':return self.send_json({'error':'forbidden'},403)
            cid=b.get('content_id'); x=content(cid,uid)
            if not x:return self.send_json({'error':'not_found'},404)
            if p=='/api/review':
                status=str(b.get('status','')).lower()
                if status not in ('pending','reviewed','approved','rejected','withdrawn'):return self.send_json({'error':'invalid_review_status'},400)
                summary=str(b.get('summary','Review status changed'))[:1000]; divergence=x['divergence']; change='review_status'
                if status=='approved' and x['divergence']: return self.send_json({'error':'divergence_must_be_resolved'},409)
                if not summary.strip(): return self.send_json({'error':'review_summary_required'},400)
                c=db(); c.execute('UPDATE content SET status=?,review=?,approved_by=?,visibility=?,version=version+1,updated_at=? WHERE id=?',(status,summary,uid['name'] if status=='approved' else None,'public' if status=='approved' else 'private',now(),cid));
            elif p=='/api/divergence':
                summary=str(b.get('summary','Potential divergence reported'))[:1000]; divergence=1; change='divergence_flag'; c=db(); c.execute('UPDATE content SET divergence=1,version=version+1,updated_at=? WHERE id=?',(now(),cid))
            else:
                summary=str(b.get('summary','Correction recorded'))[:1000]; divergence=0; change='correction'; c=db(); c.execute('UPDATE content SET divergence=0,version=version+1,review=?,updated_at=? WHERE id=?',(summary,now(),cid))
            new_version=x['version']+1; updated=c.execute('SELECT * FROM content WHERE id=?',(cid,)).fetchone(); ch=content_digest(dict(updated)); c.execute('UPDATE content SET content_hash=? WHERE id=?',(ch,cid)); c.execute('INSERT INTO versions(content_id,version,change_type,summary,actor,created_at,content_hash) VALUES(?,?,?,?,?,?,?)',(cid,new_version,change,summary,uid['name'],now(),ch)); c.commit(); c.close(); event(change,cid,uid['id'],{'summary':summary}); return self.send_json({'ok':True,'content':content(cid,uid)})
        if p=='/api/journey/progress':
            journey_id=str(b.get('journey_id','JRN-001')); step=int(b.get('step_position',0)); status=str(b.get('status','completed'))
            if status not in ('started','completed') or step<0 or step>100:return self.send_json({'error':'invalid_progress'},400)
            session_key='u:'+str(uid['id']) if uid else 'anon:'+hashlib.sha256((self.headers.get('X-Session-ID','anonymous')+SECRET).encode()).hexdigest()[:32]
            if status=='completed' and step>1:
                checkdb=db(); prev=checkdb.execute('SELECT status FROM journey_progress WHERE journey_id=? AND session_key=? AND step_position=?', (journey_id,session_key,step-1)).fetchone(); checkdb.close()
                if not prev or prev['status']!='completed': return self.send_json({'error':'previous_step_incomplete'},409)
            c=db(); c.execute('INSERT INTO journey_progress(journey_id,user_id,session_key,step_position,status,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(journey_id,session_key,step_position) DO UPDATE SET status=excluded.status,updated_at=excluded.updated_at',(journey_id,uid['id'] if uid else None,session_key,step,status,now())); c.commit(); c.close()
            event('journey_start' if status=='started' else 'learning_step',None,uid['id'] if uid else None,{'journey_id':journey_id,'step':step}); return self.send_json({'ok':True,'journey_id':journey_id,'step_position':step,'status':status})
        return self.send_json({'error':'not_found'},404)
    def do_OPTIONS(self): self.send_response(204); self.send_header('Allow','GET, POST, OPTIONS'); self.end_headers()

def generate_qr_codes():
    try:
        import qrcode
        folder=ROOT/'qr'; folder.mkdir(parents=True,exist_ok=True)
        for row in SEED_CONTENT:
            cid=row[0]; img=qrcode.make(PUBLIC_BASE_URL+'/verify/'+urllib.parse.quote(cid,safe='')); img.save(folder/(cid+'.png'))
    except Exception as e: LOG.warning('QR generation skipped: %s',e)

init()
generate_qr_codes()
LOG.info('Atharhum started; database=%s', 'postgresql' if DATABASE_URL else 'sqlite')
ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
