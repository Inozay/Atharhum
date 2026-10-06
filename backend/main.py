from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import hashlib, uuid

app = FastAPI(title='Atharuhum — Digital Sanad', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / 'frontend'

sources = [
 {'id':'SRC-001','title':'صحيح البخاري','type':'حديث','authority':'الإمام البخاري','status':'موثق','year':'256هـ'},
 {'id':'SRC-002','title':'القرآن الكريم','type':'قرآن','authority':'المصحف الشريف','status':'موثق','year':'متواتر'},
 {'id':'SRC-003','title':'رياض الصالحين','type':'شرح/حديث','authority':'الإمام النووي','status':'موثق','year':'676هـ'},
]
contents = [
 {'id':'ATH-001','title':'فضل الصدق في بناء المجتمع','topic':'الأخلاق','status':'موثق','confidence':98,'source_count':3,'version':'2.1','updated':'2026-10-07','impact':1842},
 {'id':'ATH-002','title':'آداب طلب العلم','topic':'التعلم','status':'قيد المراجعة','confidence':91,'source_count':4,'version':'1.4','updated':'2026-10-05','impact':936},
 {'id':'ATH-003','title':'الرحمة في التعامل','topic':'القيم','status':'موثق','confidence':97,'source_count':2,'version':'3.0','updated':'2026-10-01','impact':2417},
]

class Draft(BaseModel):
 title: str = Field(min_length=3)
 topic: str = 'عام'
 source_ids: list[str] = []

@app.get('/api/health')
def health(): return {'status':'ok','service':'atharuhum','version':'1.0.0'}

@app.get('/api/dashboard')
def dashboard():
 return {'kpis':{'verified_content':1284,'trusted_sources':96,'learning_journeys':347,'measured_impact':74291,'verification_rate':98.4},'pipeline':[{'label':'وصول','value':9820},{'label':'ثقة','value':9140},{'label':'تفاعل','value':7630},{'label':'تعلم','value':6240},{'label':'أثر','value':4810}], 'last_sync':'منذ 4 دقائق'}

@app.get('/api/content')
def content(q: str = ''):
 items=contents if not q else [x for x in contents if q in x['title'] or q in x['topic']]
 return {'items':items}

@app.get('/api/content/{content_id}')
def content_detail(content_id: str):
 c=next((x for x in contents if x['id']==content_id), contents[0])
 return {**c,'passport':{'content_id':c['id'],'integrity_hash':hashlib.sha256(c['title'].encode()).hexdigest()[:24],'created':'2026-08-14','reviewed_by':'لجنة مراجعة المحتوى','license':'CC BY-NC 4.0'},'sanad':[{'stage':'المصدر الأصلي','date':'2026-08-14','actor':'مصدر موثوق','status':'verified'},{'stage':'المراجعة العلمية','date':'2026-08-16','actor':'مراجع بشري','status':'verified'},{'stage':'الترجمة والتكييف','date':'2026-08-20','actor':'فريق المحتوى','status':'verified'},{'stage':'النشر','date':'2026-08-21','actor':'Atharuhum','status':'verified'}], 'sources':sources}

@app.get('/api/verify/{content_id}')
def verify(content_id: str):
 c=next((x for x in contents if x['id']==content_id), contents[0])
 h=hashlib.sha256((c['id']+c['title']+c['version']).encode()).hexdigest()
 return {'verified':True,'content_id':c['id'],'integrity_hash':h,'message':'المحتوى سليم وسجل السند متسق.','checked_at':datetime.now(timezone.utc).isoformat()}

@app.get('/api/sources')
def get_sources(): return {'items':sources}

@app.get('/api/ai/answer')
def ai_answer(q: str = Query(..., min_length=2)):
 return {'question':q,'answer':'المعرفة لا تكتمل بحفظ النص فقط؛ بل بفهم أصله وسياقه ومسار انتقاله ثم قياس أثره بعد الوصول إلى المتعلم.','citations':[{'id':'SRC-001','title':'صحيح البخاري','relevance':0.96},{'id':'SRC-003','title':'رياض الصالحين','relevance':0.91}], 'confidence':95, 'guardrail':'إجابة مساعدة مرتبطة بمصادر؛ لا تستبدل المراجعة العلمية.'}

@app.post('/api/studio/generate')
def generate(d: Draft):
 ids=d.source_ids or ['SRC-001']
 return {'draft_id':'DRF-'+uuid.uuid4().hex[:8].upper(),'title':d.title,'topic':d.topic,'status':'مسودة — تحتاج مراجعة بشرية','sources':ids,'content':'صياغة أولية مرتبطة بالمصادر المحددة، مع إبقاء التحقق البشري شرطًا قبل النشر.','checks':[{'label':'مصادر مرتبطة','ok':True},{'label':'سياق واضح','ok':True},{'label':'مراجعة بشرية','ok':False}]}

@app.get('/api/impact')
def impact():
 return {'journey':{'reach':9820,'trusted':9140,'engaged':7630,'learned':6240,'applied':4810,'reuse':1260},'privacy':'مؤشرات مجمعة دون عرض هوية المتعلم','insights':['المحتوى المختصر يرفع إكمال الرحلة 18%','وجود بطاقة المصدر يرفع الثقة 24%','الرحلات المتسلسلة تحقق عودة أعلى من المحتوى المنفرد']}

@app.get('/api/journey')
def journey():
 return {'title':'رحلة بناء المعرفة الموثوقة','steps':[('01','اكتشف','تعرف على الفكرة وسؤالها'),('02','تحقق','افتح المصدر وسجل السند'),('03','افهم','اقرأ الشرح والسياق'),('04','تعلم','أكمل مسارًا قصيرًا'),('05','أثر','حوّل المعرفة إلى تطبيق')], 'progress':72}

@app.get('/api/activity')
def activity():
 return {'items':[{'time':'منذ 4 دقائق','event':'تم التحقق من ATH-001','type':'verification'},{'time':'منذ 19 دقيقة','event':'أكملت مؤسسة الرحلة التعليمية #347','type':'learning'},{'time':'منذ ساعة','event':'تم اعتماد الإصدار 3.0 من ATH-003','type':'approval'}]}

if FRONTEND_DIR.exists():
    app.mount('/app', StaticFiles(directory=str(FRONTEND_DIR), html=True), name='frontend')

@app.get('/')
def root():
    if FRONTEND_DIR.exists():
        return FileResponse(str(FRONTEND_DIR / 'index.html'))
    return {'service':'atharuhum','message':'frontend not mounted'}
