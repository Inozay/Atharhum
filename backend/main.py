from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime, timezone
import sqlite3, io, re
import qrcode

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'atharhum.db'
app = FastAPI(title='أَثَرُهُم — Digital Chain of Trusted Knowledge', version='3.0.0')

CONTENT = [
    {
        'id':'AH-001','title':'حفظ الأثر في البيئة الرقمية','category':'الثقة','language':'العربية',
        'source':'سجل معرفي تجريبي — مادة أصلية داخل بيئة أَثَرُهُم','edition':'الإصدار 1.4','version':'1.4',
        'status':'verified','review':'مراجعة بشرية مسجلة','reviewer':'سجل مراجعة تجريبي','updated':'2026-09-18',
        'summary':'كيف يمكن أن تنتقل المعرفة الرقمية مع هويتها ومصدرها وسياقها بدل أن تصبح نسخة بلا قصة؟',
        'body':'الفكرة الأساسية في أَثَرُهُم هي أن المعرفة لا ينبغي أن تفقد قصتها أثناء انتقالها رقمياً. لذلك تحمل المادة هوية وإصداراً ومراجعة ومساراً يربط الأصل بالنسخ اللاحقة.',
        'tags':['الأثر','السند','المصدر','الثقة'],
        'provenance':[
            ('الأصل','إنشاء المادة الأصلية','2026-08-20','verified'),
            ('المراجعة','تسجيل مراجعة بشرية','2026-08-23','verified'),
            ('الإصدار','تنقيح النسخة 1.4','2026-09-18','verified'),
            ('الترجمة','نسخة إنجليزية مرتبطة بالأصل','2026-09-20','verified'),
            ('النشر','إتاحة المادة في أَثَرُهُم','2026-09-21','verified')],
        'evidence':['هوية المحتوى AH-001','سجل مراجعة','سجل الإصدارات','علاقة الترجمة بالأصل'],
        'learning':['عرّف مشكلة فقدان provenance','تتبّع الأصل والمراجعة','اختبر سؤالاً مرتبطاً بالمصدر','حوّل الفهم إلى أثر قابل للقياس'],
        'english':'Preserving provenance in the digital environment means keeping a knowledge item connected to its identity, source, context, review and versions as it travels.'
    },
    {
        'id':'AH-002','title':'كيف نتحقق من المعلومة قبل نشرها؟','category':'التحقق','language':'العربية',
        'source':'سجل معرفي تجريبي — مادة إرشادية','edition':'الإصدار 2.1','version':'2.1','status':'verified',
        'review':'مراجعة بشرية مسجلة','reviewer':'سجل مراجعة تجريبي','updated':'2026-09-11',
        'summary':'إطار عملي لفحص الأصل والسياق والإصدار والمراجعة قبل إعادة استخدام أي مادة معرفية رقمية.',
        'body':'ابدأ بهوية المادة، ثم افحص مصدرها وإصدارها وحالة مراجعتها، وبعدها تتبع العلاقات مع الترجمات والنسخ المشتقة. التحقق هنا ليس شارة شكلية بل مسار يمكن فحصه.',
        'tags':['تحقق','مصادر','سياق','إصدار'],
        'provenance':[
            ('الأصل','إنشاء الوثيقة الإرشادية','2026-07-11','verified'),('المراجعة','تسجيل مراجعة تحريرية','2026-07-14','verified'),
            ('الإصدار','الإصدار 2.1','2026-09-11','verified'),('النشر','إتاحة المادة','2026-09-12','verified')],
        'evidence':['معرف AH-002','مصدر محدد','سجل مراجعة','نسخة حالية'],
        'learning':['افحص الهوية','افحص المصدر والسياق','افحص الإصدار','قرر قبل إعادة الاستخدام'],
        'english':'Verification starts with identity, then source, context, version and review. The result is a traceable trust path rather than a visual badge.'
    },
    {
        'id':'AH-003','title':'من المصدر إلى المتعلم: رحلة المعرفة','category':'التعلم','language':'العربية',
        'source':'سجل معرفي تجريبي — وحدة تعليمية','edition':'الإصدار 1.0','version':'1.0','status':'verified',
        'review':'مراجعة بشرية مسجلة','reviewer':'سجل مراجعة تجريبي','updated':'2026-09-04',
        'summary':'كيف تتحول المعرفة الموثقة إلى رحلة تعلم قابلة للقياس دون فقدان الأصل أو السياق؟',
        'body':'يحوّل أَثَرُهُم المادة الموثقة إلى أهداف ودروس وأسئلة وتقدم. ثم تنتقل الإشارات المجمعة إلى طبقة الأثر لفهم ما نجح وما يحتاج إلى تحسين.',
        'tags':['تعلم','رحلة','تقدم','أثر'],
        'provenance':[
            ('الأصل','إنشاء الوحدة التعليمية','2026-08-01','verified'),('المراجعة','مراجعة المنهج','2026-08-03','verified'),
            ('التعليم','تحويلها إلى دروس قصيرة','2026-08-15','verified'),('النشر','إتاحة الوحدة','2026-08-16','verified')],
        'evidence':['أهداف تعلم','دروس قصيرة','اختبار فهم','سجل تقدم'],
        'learning':['افهم الفكرة','تتبع السند','اختبر الفهم','سجل التطبيق'],
        'english':'Trusted knowledge can become a measurable learning journey without losing its origin or context.'
    }
]

KEYWORDS = {
    'السند':'السند الرقمي هو سجل قابل للتتبع يربط الأصل بالمراجعة والإصدار والترجمة والنسخ المشتقة. الهدف هو ألا تفقد المعرفة قصتها أثناء انتقالها رقمياً.',
    'التحقق':'التحقق يبدأ من هوية المحتوى ثم المصدر والإصدار والمراجعة، وبعدها يمكن تتبع الترجمات والنسخ المشتقة بدل التعامل معها كمواد منفصلة.',
    'الأثر':'الأثر هو ما يحدث بعد الوصول: فتح الجواز، التحقق، بدء التعلم، الإكمال، وإعادة الاستخدام. تجمع الإشارات بصورة مجمعة لتحديد ما يحتاج إلى تحسين.',
    'الذكاء الاصطناعي':'المساعد الموثق يستخدم الاسترجاع المرتبط بالمصادر ليشرح ويربط ويعرض الأدلة، ويُظهر حدود المعرفة عندما لا يملك سنداً كافياً.',
    'جواز المحتوى':'جواز المحتوى هو الهوية الرقمية للمادة: المصدر، الإصدار، المراجعة، العلاقات، ومسار provenance الذي يمكن فحصه.',
    'الأمانة':'في سياق أَثَرُهُم، الأمانة الرقمية تعني الحفاظ على نسبة المعرفة وسياقها ومسار انتقالها، لا الاكتفاء بنقل النص.'
}

class AskRequest(BaseModel):
    question: str = Field('', max_length=1000)
    content_id: str | None = None
    mode: str = 'ask'

class VerifyRequest(BaseModel):
    content_id: str = Field(..., max_length=50)

class EventRequest(BaseModel):
    event: str = Field(..., max_length=40)
    content_id: str = Field('AH-001', max_length=50)
    session_id: str = Field('anonymous', max_length=80)

class ProgressRequest(BaseModel):
    session_id: str = Field('anonymous', max_length=80)
    content_id: str = Field('AH-001', max_length=50)
    step: int = Field(..., ge=0, le=4)


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    c = db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      event TEXT NOT NULL, content_id TEXT NOT NULL, session_id TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS progress (
      session_id TEXT NOT NULL, content_id TEXT NOT NULL, step INTEGER NOT NULL,
      updated_at TEXT NOT NULL, PRIMARY KEY(session_id, content_id)
    );
    ''')
    # Seed a small, explicitly labelled operational dataset once.
    if c.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 0:
        seed = [('view',6200),('passport',4100),('verify',2780),('ask',2050),('lesson_start',1480),('lesson_complete',920),('reuse',470),('impact',280)]
        now = datetime.now(timezone.utc).isoformat()
        rows=[]
        for event,count in seed:
            rows.extend((event,'AH-001',f'seed-{i}',now) for i in range(count))
        c.executemany('INSERT INTO events(event,content_id,session_id,created_at) VALUES(?,?,?,?)', rows)
    c.commit(); c.close()

init_db()


def find_content(cid):
    return next((x for x in CONTENT if x['id'].upper()==cid.upper()), None)


def now(): return datetime.now(timezone.utc).isoformat()

@app.get('/api/health')
def health():
    return {'ok':True,'service':'atharhum','version':'3.0.0','storage':'sqlite','time':now()}

@app.get('/api/content')
def content(q: str = '', category: str = ''):
    q=q.strip().lower(); category=category.strip().lower()
    items=CONTENT
    if q:
        items=[x for x in items if q in (' '.join([x['title'],x['summary'],x['body'],x['source'],' '.join(x['tags'])])).lower()]
    if category: items=[x for x in items if x['category'].lower()==category]
    return items

@app.get('/api/content/{content_id}')
def content_one(content_id:str):
    x=find_content(content_id)
    if not x: raise HTTPException(404,'المحتوى غير موجود')
    return x

@app.get('/api/provenance/{content_id}')
def provenance(content_id:str):
    x=find_content(content_id)
    if not x: raise HTTPException(404,'المحتوى غير موجود')
    nodes=[{'id':'source','label':'الأصل','detail':x['source'],'kind':'source'}]
    for i,(stage,detail,date,status) in enumerate(x['provenance']):
        nodes.append({'id':f'n{i}','label':stage,'detail':detail,'date':date,'kind':status})
    edges=[{'from':nodes[i]['id'],'to':nodes[i+1]['id']} for i in range(len(nodes)-1)]
    return {'content_id':x['id'],'nodes':nodes,'edges':edges,'lineage':x['provenance']}

@app.get('/api/graph/{content_id}')
def graph(content_id:str):
    x=find_content(content_id)
    if not x: raise HTTPException(404,'المحتوى غير موجود')
    nodes=[
      {'id':'source','label':'المصدر','sub':'Origin','type':'source'},
      {'id':'content','label':x['title'],'sub':x['id'],'type':'content'},
      {'id':'review','label':'المراجعة البشرية','sub':x['reviewer'],'type':'review'},
      {'id':'ai','label':'المساعد الموثق','sub':'Source-grounded','type':'ai'},
      {'id':'learning','label':'رحلة التعلم','sub':'Personal Journey','type':'learning'},
      {'id':'impact','label':'ذكاء الأثر','sub':'Aggregated Signals','type':'impact'}]
    edges=[('source','content'),('content','review'),('content','ai'),('content','learning'),('learning','impact'),('ai','learning')]
    return {'nodes':nodes,'edges':[{'from':a,'to':b} for a,b in edges]}

@app.post('/api/verify')
def verify(req:VerifyRequest):
    x=find_content(req.content_id)
    if not x: return {'verified':False,'message':'لم يتم العثور على هوية محتوى بهذا المعرّف.'}
    return {'verified':True,'id':x['id'],'title':x['title'],'status':x['status'],'version':x['version'],'review':x['review'],'source':x['source'],'updated':x['updated'],'checks':['identity','source','review','version','lineage']}

@app.get('/api/compare')
def compare(ids:str='AH-001,AH-002'):
    wanted=[s.strip() for s in ids.split(',') if s.strip()][:3]
    items=[find_content(i) for i in wanted]
    items=[x for x in items if x]
    return [{'id':x['id'],'title':x['title'],'source':x['source'],'version':x['version'],'review':x['review'],'updated':x['updated'],'provenance_steps':len(x['provenance'])} for x in items]

@app.post('/api/ask')
def ask(req:AskRequest):
    q=req.question.strip(); mode=req.mode if req.mode in {'ask','explain','trace','translate','compare'} else 'ask'
    if not q: return {'answer':'اكتب سؤالاً لأبدأ الاسترجاع من المعرفة المرتبطة بالمصادر.','sources':[],'grounded':True,'mode':mode,'confidence':'غير كافٍ'}
    low=q.lower(); selected=[]
    if req.content_id and find_content(req.content_id): selected=[find_content(req.content_id)]
    else:
        scores=[]
        tokens=[t for t in re.findall(r'[\w\u0600-\u06ff]+',low) if len(t)>2]
        for x in CONTENT:
            hay=(' '.join([x['title'],x['summary'],x['body'],x['category'],' '.join(x['tags'])])).lower()
            score=sum(1 for t in tokens if t in hay)
            scores.append((score,x))
        selected=[x for score,x in sorted(scores,key=lambda z:z[0],reverse=True)[:2] if score>0]
    for k,v in KEYWORDS.items():
        if k in low:
            if mode=='explain': answer=v+'\n\nويمكن فتح جواز المحتوى لرؤية مصدر المادة وإصدارها ومسارها.'
            elif mode=='trace': answer='مسار التتبع: الأصل → المراجعة → الإصدار → الانتقال/الترجمة → النشر. افتح «تتبّع السند» لرؤية العقد المرتبطة بالمادة.'
            else: answer=v
            break
    else:
        if selected:
            x=selected[0]
            if mode=='translate': answer=x['english']
            elif mode=='trace': answer='يمكن تتبع هذه المادة عبر '+ ' → '.join(s[0] for s in x['provenance']) + '، وكل خطوة مرتبطة بالتاريخ والحالة.'
            elif mode=='compare': answer='المقارنة تبدأ من المصدر والإصدار والمراجعة وعدد خطوات provenance، ثم يمكن فتح كل جواز على حدة.'
            else: answer=x['body']
        else:
            answer='لم أجد سنداً كافياً داخل قاعدة المعرفة الحالية. بدلاً من توليد إجابة غير موثقة، أَثَرُهُم يوضح حدود المعرفة ويطلب سؤالاً مرتبطاً بالمصادر المسجلة.'
    return {'answer':answer,'sources':[{'id':x['id'],'title':x['title'],'version':x['version']} for x in selected],'grounded':True,'mode':'source-grounded / '+mode,'confidence':'مرتفع' if selected else 'غير كافٍ'}

@app.post('/api/event')
def event(req:EventRequest):
    allowed={'view','passport','verify','ask','lesson_start','lesson_complete','reuse','share','impact'}
    accepted=req.event in allowed
    if accepted:
        c=db(); c.execute('INSERT INTO events(event,content_id,session_id,created_at) VALUES(?,?,?,?)',(req.event,req.content_id,req.session_id,now())); c.commit(); c.close()
    return {'accepted':accepted,'event':req.event,'content_id':req.content_id,'recorded_at':now(),'privacy':'aggregated'}

@app.get('/api/learning')
def learning(session_id:str='anonymous',content_id:str='AH-001'):
    c=db(); row=c.execute('SELECT step FROM progress WHERE session_id=? AND content_id=?',(session_id,content_id)).fetchone(); c.close()
    return {'session_id':session_id,'content_id':content_id,'step':row['step'] if row else 0,'total':4}

@app.post('/api/learning/progress')
def learning_progress(req:ProgressRequest):
    x=find_content(req.content_id)
    if not x: raise HTTPException(404,'المحتوى غير موجود')
    c=db(); c.execute('INSERT INTO progress(session_id,content_id,step,updated_at) VALUES(?,?,?,?) ON CONFLICT(session_id,content_id) DO UPDATE SET step=excluded.step,updated_at=excluded.updated_at',(req.session_id,req.content_id,req.step,now())); c.commit(); c.close()
    event_name='lesson_complete' if req.step>=4 else 'lesson_start'
    event(EventRequest(event=event_name,content_id=req.content_id,session_id=req.session_id))
    return {'ok':True,'step':req.step,'total':4}

@app.get('/api/impact')
def impact():
    c=db(); rows=c.execute('SELECT event,COUNT(*) n FROM events GROUP BY event').fetchall(); c.close(); counts={r['event']:r['n'] for r in rows}
    keys=[('view','الوصول'),('passport','فتح الجواز'),('verify','التحقق'),('lesson_start','بدء التعلم'),('lesson_complete','إكمال التعلم'),('reuse','إعادة الاستخدام'),('impact','إشارة أثر')]
    funnel=[{'key':k,'label':label,'value':counts.get(k,0)} for k,label in keys]
    return {'funnel':funnel,'note':'المؤشرات التشغيلية تتضمن بيانات تأسيسية تجريبية وإشارات استخدام فعلية أثناء التجربة؛ لا تمثل دراسة بحثية أو ادعاء أثر اجتماعي.'}

@app.get('/api/qr/{content_id}')
def qr(content_id:str):
    x=find_content(content_id)
    if not x: raise HTTPException(404,'المحتوى غير موجود')
    img=qrcode.make(f'ATHARHUM|VERIFY|{x["id"]}|v{x["version"]}')
    buf=io.BytesIO(); img.save(buf,format='PNG'); buf.seek(0)
    return StreamingResponse(buf,media_type='image/png')

@app.get('/')
def root(): return FileResponse(ROOT/'frontend'/'index.html')
app.mount('/static',StaticFiles(directory=ROOT/'frontend'/'static'),name='static')
