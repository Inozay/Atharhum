import os, sqlite3
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import qrcode
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parent
PROJECT_ROOT=ROOT.parent
FRONTEND=PROJECT_ROOT/'frontend'
DB_PATH=Path(os.getenv('DATABASE_PATH', ROOT/'atharuhum.db'))
PUBLIC_BASE_URL=os.getenv('PUBLIC_BASE_URL','').rstrip('/')
CONTENT_ID='ATHAR-2026-0001'

app=FastAPI(title='Atharuhum API',version='3.0.0',description='Trusted Islamic knowledge, provenance, learning journeys and measurable impact.')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])

DEMO_CONTENT={'id':CONTENT_ID,'title':'What is Islam?','organization':'Atharuhum Demo Organization','language':'English','status':'VERIFIED','version':'1.0','hash':'SHA256:7f31a2e0c0b9d8a4','source':'Curated educational source registry','source_url':'https://islamic-content.example/source-001','reviewed':'2026-10-06'}
SOURCES=[{'id':'SRC-001','title':'Curated educational source','type':'institutional/educational','language':'English','license':'Review-required / registry record','verification':'Human-reviewed before publication','url':'https://islamic-content.example/source-001'}]
JOURNEY=[{'id':1,'title':'What is Islam?','content_id':CONTENT_ID},{'id':2,'title':'Who is Muhammad ﷺ?','content_id':CONTENT_ID},{'id':3,'title':'What is the Quran?','content_id':CONTENT_ID},{'id':4,'title':'Why do Muslims believe in One God?','content_id':CONTENT_ID},{'id':5,'title':'How do Muslims practice Islam?','content_id':CONTENT_ID}]
KB=[('What is Islam?','Islam is presented in the verified demo knowledge base as a faith centered on belief in one God and a way of life shaped by worship, ethics and guidance.'),('Who is Muhammad?','Muhammad ﷺ is presented as the final prophet in Islamic belief and as the messenger through whom the Quran was conveyed.'),('What is the Quran?','The Quran is the central scripture of Islam. The demo answer is generated only from the curated knowledge record attached to the verified content item.'),('Why one God?','Tawhid, the oneness of God, is a central concept in Islamic theology. For sensitive or disputed questions, the system is designed to cite sources and defer to qualified review.')]

def conn():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    c=conn(); c.execute('''CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,event_type TEXT NOT NULL,content_id TEXT,session_id TEXT,language TEXT,source_channel TEXT,campaign_id TEXT,created_at TEXT NOT NULL)'''); c.commit()
    if c.execute('SELECT COUNT(*) FROM events').fetchone()[0]==0:
        seed=['CONTENT_VIEWED','CONTENT_VIEWED','QR_SCANNED','CONTENT_VERIFIED','CONTENT_VIEWED','JOURNEY_STARTED','JOURNEY_STEP_COMPLETED']
        now=datetime.now(timezone.utc).isoformat(); c.executemany('INSERT INTO events(event_type,content_id,session_id,language,source_channel,campaign_id,created_at) VALUES(?,?,?,?,?,?,?)',[(e,CONTENT_ID,'demo-seed','English','DEMO','DEMO',now) for e in seed]); c.commit()
    c.close()
init_db()

class Event(BaseModel):
    type:str=Field(min_length=2,max_length=80)
    content_id:str=CONTENT_ID
    session_id:str='anonymous-demo'
    language:str='English'
    source_channel:str='WEB'
    campaign_id:str='DEMO'

@app.get('/api/health')
def health(): return {'status':'ok','service':'atharuhum-api','version':'3.0.0','database':'sqlite','public_base_url':PUBLIC_BASE_URL or 'auto'}
@app.get('/api/config')
def config(): return {'product':'Atharuhum','version':'3.0.0','demo':True,'content_id':CONTENT_ID}
@app.get('/api/content')
def content(): return DEMO_CONTENT
@app.get('/api/sources')
def sources(): return {'items':SOURCES}
@app.get('/api/verify/{content_id}')
def verify(content_id:str):
    if content_id!=CONTENT_ID: raise HTTPException(404,'Content not found')
    return {'verified':True,'content':DEMO_CONTENT,'source':SOURCES[0],'passport':[{'label':'Original source registered','status':'complete'},{'label':'Human review completed','status':'complete'},{'label':'Integrity hash recorded','status':'complete'},{'label':'Publication verified','status':'complete'},{'label':'User interaction tracked','status':'live'}]}
@app.get('/api/qr/{content_id}.png')
def qr(content_id:str):
    if content_id!=CONTENT_ID: raise HTTPException(404,'Content not found')
    base=PUBLIC_BASE_URL or ''
    target=f'{base}/verify.html?id={content_id}'
    img=qrcode.make(target); buf=BytesIO(); img.save(buf,format='PNG'); buf.seek(0)
    return StreamingResponse(buf,media_type='image/png',headers={'Cache-Control':'no-store'})
@app.get('/api/track/qr/{content_id}')
def track_qr(content_id:str):
    if content_id!=CONTENT_ID: raise HTTPException(404,'Content not found')
    add_event(Event(type='QR_SCANNED',content_id=content_id,session_id='qr-anonymous',source_channel='QR'))
    return RedirectResponse(f'/verify.html?id={content_id}')
@app.post('/api/events')
def add_event(e:Event):
    c=conn(); now=datetime.now(timezone.utc).isoformat(); c.execute('INSERT INTO events(event_type,content_id,session_id,language,source_channel,campaign_id,created_at) VALUES(?,?,?,?,?,?,?)',(e.type,e.content_id,e.session_id,e.language,e.source_channel,e.campaign_id,now)); c.commit(); c.close(); return {'success':True,'event':e.type,'timestamp':now}
@app.get('/api/dashboard')
def dashboard():
    c=conn(); rows=c.execute('SELECT event_type,COUNT(*) n FROM events GROUP BY event_type').fetchall(); last=c.execute('SELECT event_type,created_at FROM events ORDER BY id DESC LIMIT 1').fetchone(); c.close(); counts={r['event_type']:r['n'] for r in rows}
    return {'demo_mode':True,'reach':12450+counts.get('CONTENT_VIEWED',0),'verified':3284+counts.get('CONTENT_VERIFIED',0),'engagement':1940+counts.get('CONTENT_VIEWED',0)+counts.get('RELATED_CONTENT_CLICKED',0),'journeys':641+counts.get('JOURNEY_STARTED',0),'completed':285+counts.get('JOURNEY_COMPLETED',0),'reuse':18+counts.get('CONTENT_REUSED',0),'events':sum(counts.values()),'last_event':last['event_type'] if last else None,'last_event_at':last['created_at'] if last else None}
@app.get('/api/journey')
def journey(): return {'id':'JNY-001','title':'Understanding Islam','description':'A beginner pathway built from verified knowledge records.','steps':JOURNEY}
@app.get('/api/insight')
def insight(): return {'title':'Find the next improvement.','text':'Verification is strong, but continuation after the first resource is the main opportunity.','recommendation':'Create a shorter beginner pathway connecting the three most relevant verified resources.','basis':'Observed funnel events in the demonstration analytics store.'}
@app.get('/api/ask')
def ask(q:str='What is Islam?'):
    ql=q.lower(); best=None
    for title,answer in KB:
        score=sum(1 for token in title.lower().split() if token.strip('?') in ql)
        if best is None or score>best[0]: best=(score,title,answer)
    if not best or best[0]==0: best=(0,KB[0][0],KB[0][1])
    return {'answer':best[2],'matched_topic':best[1],'citations':[{'content_id':CONTENT_ID,'source_id':'SRC-001','label':'Verified source registry record'}],'safety':'Source-grounded demo response; not a fatwa and not a substitute for qualified scholarly review.'}

# Serve the complete product from the same service for a simple, reliable Live Demo.
if FRONTEND.exists():
    app.mount('/assets',StaticFiles(directory=FRONTEND),name='assets')
    @app.get('/verify.html')
    def verify_page(): return FileResponse(FRONTEND/'verify.html')
    @app.get('/style.css')
    def style(): return FileResponse(FRONTEND/'style.css', media_type='text/css')
    @app.get('/app.js')
    def app_js(): return FileResponse(FRONTEND/'app.js', media_type='application/javascript')
    @app.get('/verify.js')
    def verify_js(): return FileResponse(FRONTEND/'verify.js', media_type='application/javascript')
    @app.get('/')
    def home(): return FileResponse(FRONTEND/'index.html')
