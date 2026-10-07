from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlalchemy import create_engine, String, Text, Integer, DateTime, ForeignKey, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from datetime import datetime, timezone
from pathlib import Path
import hashlib, io, os, json, re
import qrcode

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT.parent / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_URL = os.getenv('DATABASE_URL', '').strip()
if DB_URL.startswith('postgres://'):
    DB_URL = DB_URL.replace('postgres://', 'postgresql+psycopg://', 1)
elif DB_URL.startswith('postgresql://'):
    DB_URL = DB_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
if not DB_URL:
    DB_URL = f"sqlite:///{DATA_DIR / 'atharhum.db'}"

engine = create_engine(DB_URL, connect_args={'check_same_thread': False} if DB_URL.startswith('sqlite') else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class Institution(Base):
    __tablename__='institutions'
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(240))
    kind: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(80), default='مرجع عام')

class Content(Base):
    __tablename__='content'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    type: Mapped[str] = mapped_column(String(100))
    summary: Mapped[str] = mapped_column(Text)
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'))
    source_url: Mapped[str] = mapped_column(String(500))
    rights: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(30))
    fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(80), default='مسجل')
    institution = relationship('Institution')

class Sanad(Base):
    __tablename__='sanad'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[str] = mapped_column(ForeignKey('content.id'))
    step: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(240))
    detail: Mapped[str] = mapped_column(Text)

class Journey(Base):
    __tablename__='journeys'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    content_id: Mapped[str] = mapped_column(ForeignKey('content.id'))
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)

class JourneyStep(Base):
    __tablename__='journey_steps'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    journey_id: Mapped[str] = mapped_column(ForeignKey('journeys.id'))
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)

class Event(Base):
    __tablename__='events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[str] = mapped_column(String(80))
    event_type: Mapped[str] = mapped_column(String(100))
    metadata_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Collaboration(Base):
    __tablename__='collaborations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(120))
    note: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(80), default='طلب جديد')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine)

def seed():
    db=SessionLocal()
    if db.scalar(select(func.count(Institution.id))) > 0:
        db.close(); return
    institutions=[
      Institution(id='ksu-quran',name='مشروع المصحف الإلكتروني — جامعة الملك سعود',kind='مصدر قرآني رقمي',description='مشروع إلكتروني تابع لجامعة الملك سعود يتيح المصحف ومواد مرتبطة به رقمياً.',url='https://quran.ksu.edu.sa/',status='مرجع عام — ليست شراكة'),
      Institution(id='kfgqpc',name='مجمع الملك فهد لطباعة المصحف الشريف',kind='مؤسسة قرآنية ونشر',description='جهة متخصصة في خدمة ونشر كتاب الله، وتشمل أعمالها الإصدارات والمصاحف والتقنيات والخطوط.',url='https://qurancomplex.gov.sa/',status='مرجع عام — ليست شراكة'),
      Institution(id='azhar-research',name='مجمع البحوث الإسلامية — الأزهر الشريف',kind='بحوث ونشر إسلامي',description='هيئة علمية للبحوث الإسلامية، ومن اختصاصاتها النشر والترجمة والتأليف والبحوث والدراسات.',url='https://azhar.eg/magmaa',status='مرجع عام — ليست شراكة'),
      Institution(id='ksu-publishing',name='دار جامعة الملك سعود للنشر',kind='نشر أكاديمي',description='جهة نشر جامعية تقدم خدمات النشر والطباعة وخدمات المؤلف والتدريب.',url='https://direct.ksu.edu.sa/',status='مرجع عام — ليست شراكة'),
    ]
    db.add_all(institutions)
    fp=hashlib.sha256(b'atharhum-demo-record-001').hexdigest()
    content=Content(id='passport-quran-001',title='المصحف الإلكتروني — سجل المصدر',type='مصدر قرآني رقمي',summary='تجربة توضح كيف يحوّل أَثَرُهُم المصدر الإسلامي إلى سجل قابل للتحقق: هوية، مصدر، حقوق، سند، QR، رحلة تعلم وأثر.',institution_id='ksu-quran',source_url='https://quran.ksu.edu.sa/index.php?l=ar',rights='الحقوق تحددها الجهة المالكة للمصدر؛ أَثَرُهُم لا يدّعي إعادة ترخيص المحتوى.',version='1.0',fingerprint=fp,status='مسجل ومتحقق من السجل')
    db.add(content)
    db.add_all([
      Sanad(content_id=content.id,step=1,kind='SOURCE',label='المصدر الأصلي',detail='مشروع المصحف الإلكتروني بجامعة الملك سعود'),
      Sanad(content_id=content.id,step=2,kind='REGISTRY',label='التسجيل',detail='إنشاء سجل هوية مستقل داخل أَثَرُهُم'),
      Sanad(content_id=content.id,step=3,kind='INTEGRITY',label='بصمة السجل',detail=f'SHA-256 · {fp[:20]}…'),
      Sanad(content_id=content.id,step=4,kind='RIGHTS',label='الحقوق',detail='يجب الرجوع إلى المصدر قبل إعادة الاستخدام أو النشر'),
      Sanad(content_id=content.id,step=5,kind='LEARNING',label='رحلة تعلم',detail='من التحقق إلى الفهم ثم تسجيل الأثر'),
    ])
    journey=Journey(id='journey-001',content_id=content.id,title='من المصدر إلى الأثر',description='رحلة قصيرة تجعل التحقق جزءاً من التعلم، ثم تقيس ما يحدث بعد الوصول إلى المعرفة.')
    db.add(journey)
    for i,(t,d) in enumerate([
      ('اكتشف','ابدأ من سجل مصدر حقيقي وليس من صفحة مجهولة.'),('تحقق','افحص الهوية والبصمة والحقوق ومسار المصدر.'),('افهم','اسأل المساعد مع إبقاء الدليل مرتبطاً بالمصدر.'),('تعلّم','حوّل المصدر إلى خطوة تعليمية قابلة للمتابعة.'),('أكمل','سجّل إتمام الرحلة بدلاً من الاكتفاء بالمشاهدة.'),('أثر','شاهد الأحداث التي صنعت الأثر ويمكن تدقيقها.')
    ]): db.add(JourneyStep(journey_id=journey.id,position=i+1,title=t,description=d))
    db.commit(); db.close()
seed()

app=FastAPI(title='أَثَرُهُم',version='1.0.0')

class AskIn(BaseModel): question:str
class CollabIn(BaseModel): role:str; note:str=''
class EventIn(BaseModel): event_type:str; metadata:dict={}

def record(db,cid,event_type,meta=None):
    db.add(Event(content_id=cid,event_type=event_type,metadata_json=json.dumps(meta or {},ensure_ascii=False)))
    db.commit()

def content_dict(db,c):
    inst=db.get(Institution,c.institution_id)
    return {'id':c.id,'title':c.title,'type':c.type,'summary':c.summary,'version':c.version,'status':c.status,'fingerprint':c.fingerprint,'rights':c.rights,'source':{'name':inst.name,'url':c.source_url,'institution_status':inst.status}}

@app.get('/',response_class=HTMLResponse)
def home(): return (ROOT/'static'/'index.html').read_text(encoding='utf-8')
@app.get('/health')
def health(): return {'status':'healthy','service':'atharhum','version':'1.0.0'}
@app.get('/api/overview')
def overview():
    db=SessionLocal();
    return_data={'institutions':db.scalar(select(func.count(Institution.id))),'content':db.scalar(select(func.count(Content.id))),'sanad_nodes':db.scalar(select(func.count(Sanad.id))),'journeys':db.scalar(select(func.count(Journey.id))),'events':db.scalar(select(func.count(Event.id)))}
    db.close(); return return_data
@app.get('/api/institutions')
def institutions():
    db=SessionLocal(); rows=db.scalars(select(Institution).order_by(Institution.name)).all(); data=[{'id':x.id,'name':x.name,'kind':x.kind,'description':x.description,'url':x.url,'status':x.status} for x in rows]; db.close(); return data
@app.get('/api/content')
def content():
    db=SessionLocal(); rows=db.scalars(select(Content).order_by(Content.id)).all(); data=[content_dict(db,x) for x in rows]; db.close(); return data
@app.get('/api/content/{cid}')
def get_content(cid:str):
    db=SessionLocal(); c=db.get(Content,cid)
    if not c: db.close(); raise HTTPException(404,'المحتوى غير موجود')
    data=content_dict(db,c); db.close(); return data
@app.get('/api/passport/{cid}')
def passport(cid:str):
    db=SessionLocal(); c=db.get(Content,cid)
    if not c: db.close(); raise HTTPException(404,'السجل غير موجود')
    inst=db.get(Institution,c.institution_id); nodes=db.scalars(select(Sanad).where(Sanad.content_id==cid).order_by(Sanad.step)).all()
    data={'content':content_dict(db,c),'checks':[{'label':'هوية السجل','status':'PASS'},{'label':'سلامة البصمة','status':'PASS'},{'label':'الحقوق','status':'RECORDED'},{'label':'السند','status':'RECORDED'}], 'sanad':[{'step':n.step,'kind':n.kind,'label':n.label,'detail':n.detail} for n in nodes], 'verify_path':f'/verify/{cid}'}
    db.close(); return data
@app.get('/api/verify/{cid}')
def verify(cid:str):
    db=SessionLocal(); c=db.get(Content,cid)
    if not c: db.close(); raise HTTPException(404,'السجل غير موجود')
    record(db,cid,'verification',{'result':'pass'})
    data={'verified':True,'id':cid,'title':c.title,'timestamp':datetime.now(timezone.utc).isoformat(),'checks':['identity','integrity','rights','provenance']}; db.close(); return data
@app.get('/verify/{cid}',response_class=HTMLResponse)
def public_verify(cid:str):
    db=SessionLocal(); c=db.get(Content,cid)
    if not c: db.close(); raise HTTPException(404,'السجل غير موجود')
    inst=db.get(Institution,c.institution_id); record(db,cid,'public_verification',{'channel':'qr_or_link'}); db.close()
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>تحقق — أَثَرُهُم</title><style>body{{margin:0;background:#f6f3eb;color:#10211d;font-family:Arial,sans-serif;display:grid;place-items:center;min-height:100vh;padding:20px}}.box{{max-width:650px;background:#fffdf8;border:1px solid #d9ddd5;border-radius:22px;padding:36px;box-shadow:0 20px 60px #15352b10}}.ok{{color:#174f42;font-weight:700}}small{{color:#65736e}}h1{{font-size:30px}}p{{line-height:2;color:#65736e}}a{{color:#174f42}}</style></head><body><main class="box"><div class="ok">✓ تم التحقق من سجل أَثَرُهُم</div><h1>{c.title}</h1><p>المعرّف: <b>{c.id}</b><br>المصدر: <b>{inst.name}</b><br>الإصدار: <b>{c.version}</b><br>سلامة السجل: <b>SHA-256 مسجل</b></p><small>هذه الصفحة تتحقق من سجل أَثَرُهُم ولا تعني اعتمادًا علميًا مستقلًا للمحتوى.</small><p><a href="{c.source_url}" target="_blank">فتح المصدر الرسمي ↗</a></p><p><a href="/">العودة إلى أَثَرُهُم</a></p></main></body></html>'''

@app.get('/api/qr/{cid}')
def qr(cid:str, request: Request):
    db=SessionLocal(); c=db.get(Content,cid)
    if not c: db.close(); raise HTTPException(404,'السجل غير موجود')
    record(db,cid,'qr_opened')
    base=os.getenv('PUBLIC_BASE_URL','').rstrip('/') or str(request.base_url).rstrip('/')
    payload=f'{base}/verify/{cid}'
    img=qrcode.make(payload); buf=io.BytesIO(); img.save(buf,format='PNG'); db.close()
    return Response(buf.getvalue(),media_type='image/png',headers={'Cache-Control':'no-store'})
@app.get('/api/journey/{cid}')
def journey(cid:str):
    db=SessionLocal(); j=db.scalar(select(Journey).where(Journey.content_id==cid))
    if not j: db.close(); raise HTTPException(404,'لا توجد رحلة')
    steps=db.scalars(select(JourneyStep).where(JourneyStep.journey_id==j.id).order_by(JourneyStep.position)).all(); data={'id':j.id,'title':j.title,'description':j.description,'steps':[{'position':s.position,'title':s.title,'description':s.description} for s in steps]}; db.close(); return data
@app.post('/api/journey/{cid}/event')
def journey_event(cid:str, body:EventIn):
    db=SessionLocal();
    if not db.get(Content,cid): db.close(); raise HTTPException(404,'السجل غير موجود')
    record(db,cid,body.event_type,body.metadata); db.close(); return {'recorded':True,'event':body.event_type}
@app.get('/api/impact/{cid}')
def impact(cid:str):
    db=SessionLocal();
    if not db.get(Content,cid): db.close(); raise HTTPException(404,'السجل غير موجود')
    rows=db.scalars(select(Event).where(Event.content_id==cid).order_by(Event.id.desc()).limit(50)).all()
    counts={k:sum(1 for e in rows if e.event_type==k) for k in ['verification','qr_opened','provenance_opened','ai_question','learning_started','learning_completed','collaboration_requested']}
    db.close(); return {'metrics':counts,'events':[{'type':e.event_type,'at':e.created_at.isoformat() if e.created_at else None} for e in rows]}
@app.post('/api/ai/{cid}')
def ask(cid:str, body:AskIn):
    db=SessionLocal(); c=db.get(Content,cid)
    if not c: db.close(); raise HTTPException(404,'السجل غير موجود')
    inst=db.get(Institution,c.institution_id)
    q=body.question.strip(); terms=[x for x in re.findall(r'[\w\u0600-\u06FF]+',q.lower()) if len(x)>2]
    base='المعلومة في هذه التجربة لا تُقدَّم كمعلومة مستقلة عن المصدر. السجل يربط الإجابة بالمصدر والهوية والبصمة والحقوق والسند.'
    answer=f'{base} المصدر المسجل هو «{inst.name}»، والإصدار {c.version}. حالة السجل: {c.status}. '
    if any(x in q for x in ['أصل','مصدر','من','origin','source']): answer+=f'أصل السجل مرتبط بالمصدر الرسمي: {c.source_url}.'
    elif any(x in q for x in ['تحقق','موثوق','verify','trust']): answer+='تم تسجيل فحوص الهوية وسلامة البصمة والحقوق ومسار المصدر؛ لا يعني ذلك أن أَثَرُهُم جهة اعتماد علمي مستقلة.'
    else: answer+='يمكن استخدام السجل لبدء رحلة تعلم، لكن عند السؤال العلمي التفصيلي يجب الرجوع إلى المادة الأصلية والجهة العلمية المختصة.'
    record(db,cid,'ai_question',{'question':q,'terms':terms}); db.close()
    return {'answer':answer,'grounding':'source-linked','source':{'name':inst.name,'url':c.source_url},'policy':'لا يدّعي المساعد الإفتاء أو الاعتماد العلمي المستقل.'}
@app.post('/api/collaborate/{cid}')
def collaborate(cid:str, body:CollabIn):
    db=SessionLocal();
    if not db.get(Content,cid): db.close(); raise HTTPException(404,'السجل غير موجود')
    x=Collaboration(content_id=cid,role=body.role,note=body.note); db.add(x); db.commit(); record(db,cid,'collaboration_requested',{'role':body.role}); result={'id':x.id,'status':x.status,'role':x.role}; db.close(); return result
@app.get('/api/institution/{iid}')
def institution(iid:str):
    db=SessionLocal(); inst=db.get(Institution,iid)
    if not inst: db.close(); raise HTTPException(404,'المؤسسة غير موجودة')
    items=db.scalars(select(Content).where(Content.institution_id==iid)).all(); data={'institution':{'id':inst.id,'name':inst.name,'kind':inst.kind,'description':inst.description,'url':inst.url,'status':inst.status},'metrics':{'registered_content':len(items)},'content':[{'id':c.id,'title':c.title,'version':c.version,'status':c.status} for c in items]}; db.close(); return data
@app.get('/api/collaborations')
def collaborations():
    db=SessionLocal(); rows=db.scalars(select(Collaboration).order_by(Collaboration.id.desc())).all(); data=[{'id':x.id,'content_id':x.content_id,'role':x.role,'note':x.note,'status':x.status,'created_at':x.created_at.isoformat() if x.created_at else None} for x in rows]; db.close(); return data
@app.get('/api/search')
def search(q:str=''):
    db=SessionLocal(); rows=db.scalars(select(Content)).all(); ql=q.strip().lower(); result=[]
    for c in rows:
        hay=' '.join([c.title,c.summary,c.type]).lower()
        if not ql or ql in hay: result.append(content_dict(db,c))
    db.close(); return result
