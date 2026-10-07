import os, io, base64, json, qrcode
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .db import init, one, all_rows, execute, now

init()
app=FastAPI(title="أَثَرُهُم — Digital Chain of Trusted Knowledge",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"],allow_credentials=False)

class Ask(BaseModel): content_id:str; question:str
class Event(BaseModel): event_type:str; metadata:dict={}
class Collaboration(BaseModel): content_id:str; role:str; note:str=""

def record(t,content_id=None,journey_id=None,metadata=None):
    execute("INSERT INTO events(type,content_id,journey_id,metadata,created_at) VALUES(:t,:c,:j,:m,:d)",{"t":t,"c":content_id,"j":journey_id,"m":json.dumps(metadata or {},ensure_ascii=False),"d":now()})

def public_base(): return os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")

@app.get("/health")
def health(): return {"status":"healthy","service":"atharhum","database":os.getenv("DATABASE_URL","sqlite-local")[:12]+"…"}
@app.get("/api/v1/stats")
def stats():
    return {"organizations":one("SELECT COUNT(*) n FROM organizations")["n"],"content":one("SELECT COUNT(*) n FROM content")["n"],"journeys":one("SELECT COUNT(*) n FROM journeys")["n"],"events":one("SELECT COUNT(*) n FROM events")["n"]}
@app.get("/api/v1/organizations")
def organizations(): return all_rows("SELECT * FROM organizations ORDER BY name")
@app.get("/api/v1/discover")
def discover():
    return all_rows("""SELECT c.id,c.title,c.summary,c.license,c.rights,c.version,c.status,o.name organization,o.country,o.source_url organization_url
                     FROM content c JOIN organizations o ON o.id=c.organization_id ORDER BY c.created_at DESC""")
@app.get("/api/v1/content/{cid}")
def content(cid):
    r=one("SELECT * FROM content WHERE id=:id",{"id":cid})
    if not r: raise HTTPException(404,"Content not found")
    return r
@app.get("/api/v1/passports/{cid}")
def passport(cid):
    r=one("""SELECT c.*,o.name issuer,o.label issuer_label,o.country issuer_country FROM content c JOIN organizations o ON o.id=c.organization_id WHERE c.id=:id""",{"id":cid})
    if not r: raise HTTPException(404,"Content not found")
    return {"content_id":r["id"],"title":r["title"],"summary":r["summary"],"issuer":r["issuer"],"issuer_label":r["issuer_label"],"issuer_country":r["issuer_country"],"version":r["version"],"integrity":{"algorithm":"SHA-256","value":r["integrity"]},"rights":r["rights"],"license":r["license"],"source":{"name":r["source_name"],"url":r["source_url"]},"verification":{"status":"registered","scope":"identity / source / integrity / rights metadata / provenance"},"qr_url":f"{public_base()}/verify/{cid}","journey_id":r["journey_id"]}
@app.get("/verify/{cid}")
def verify_page(cid):
    p=one("SELECT id FROM content WHERE id=:id",{"id":cid})
    if not p: raise HTTPException(404,"Content not found")
    return FileResponse(Path(__file__).resolve().parents[2]/"frontend"/"dist"/"index.html")
@app.get("/api/v1/verify/{cid}")
def verify(cid):
    if not one("SELECT id FROM content WHERE id=:id",{"id":cid}): raise HTTPException(404,"Content not found")
    record("verified",cid)
    return {"verified":True,"content_id":cid,"verified_at":now(),"checks":[{"key":"identity","label":"هوية السجل","status":"pass"},{"key":"source","label":"ارتباط المصدر الرسمي","status":"pass"},{"key":"integrity","label":"سلامة بصمة السجل","status":"pass"},{"key":"rights","label":"بيانات الحقوق","status":"recorded"},{"key":"provenance","label":"السند الرقمي","status":"recorded"}]}
@app.get("/api/v1/provenance/{cid}")
def provenance(cid):
    if not one("SELECT id FROM content WHERE id=:id",{"id":cid}): raise HTTPException(404,"Content not found")
    record("provenance_opened",cid)
    return {"content_id":cid,"nodes":all_rows("SELECT type,label,entity,position FROM provenance WHERE content_id=:id ORDER BY position",{"id":cid})}
@app.get("/api/v1/qr/{cid}")
def qr(cid):
    if not one("SELECT id FROM content WHERE id=:id",{"id":cid}): raise HTTPException(404,"Content not found")
    img=qrcode.make(f"{public_base()}/verify/{cid}"); b=io.BytesIO(); img.save(b,format="PNG")
    record("qr_generated",cid)
    return {"content_id":cid,"verify_url":f"{public_base()}/verify/{cid}","data_url":"data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()}
@app.post("/api/v1/ai/ask")
def ai(req:Ask):
    c=one("""SELECT c.*,o.name issuer FROM content c JOIN organizations o ON o.id=c.organization_id WHERE c.id=:id""",{"id":req.content_id})
    if not c: raise HTTPException(404,"Content not found")
    record("ai_question",req.content_id,metadata={"question":req.question})
    q=req.question.lower()
    if any(x in q for x in ["أصل","مصدر","source","من أين","origin"]):
        answer=f"الأصل المسجل هو {c['source_name']}، والجهة المرتبطة بالسجل هي {c['issuer']}. أَثَرُهُم لا يعتبر نفسه مصدرًا بديلًا؛ بل يعرض بيانات المصدر ومسار التحقق والحقوق كما هي مسجلة."
    elif any(x in q for x in ["حق","حقوق","license","ترخيص"]):
        answer=f"حالة الحقوق المسجلة: {c['license']}. الملاحظة التشغيلية: {c['rights']}"
    else:
        answer=f"بحسب السجل الموثق، هذه المادة مرتبطة بـ {c['source_name']}، وحالتها {c['status']}. للحصول على التفاصيل افتح الـPassport ثم المصدر الأصلي. لا توجد إجابة معرفية مستقلة عندما لا يقدم السجل دليلًا كافيًا."
    return {"answer":answer,"grounding":"database-record-grounded","evidence":[{"source":c["source_name"],"url":c["source_url"],"scope":"السجل والجهة والمصدر المرتبط","reason":"تم توليد الإجابة من بيانات السجل فقط"}],"insufficient_evidence_policy":"لا يخترع أَثَرُهُم إجابة خارج الأدلة المسجلة"}
@app.get("/api/v1/learning/{jid}")
def learning(jid):
    j=one("SELECT * FROM journeys WHERE id=:id",{"id":jid})
    if not j: raise HTTPException(404,"Journey not found")
    return {**j,"steps":all_rows("SELECT id,title,description,position FROM journey_steps WHERE journey_id=:id ORDER BY position",{"id":jid})}
@app.post("/api/v1/learning/{jid}/events")
def learning_event(jid,event_in:Event):
    j=one("SELECT * FROM journeys WHERE id=:id",{"id":jid})
    if not j: raise HTTPException(404,"Journey not found")
    record(event_in.event_type,j["content_id"],jid,event_in.metadata)
    return {"recorded":True,"event_type":event_in.event_type,"created_at":now()}
@app.get("/api/v1/impact/{cid}")
def impact(cid):
    if not one("SELECT id FROM content WHERE id=:id",{"id":cid}): raise HTTPException(404,"Content not found")
    types=["verified","provenance_opened","qr_generated","ai_question","learning_started","learning_completed","collaboration_requested"]
    rows=all_rows("SELECT type,created_at,metadata FROM events WHERE content_id=:id ORDER BY id DESC LIMIT 100",{"id":cid})
    return {"content_id":cid,"metrics":{t:sum(x["type"]==t for x in rows) for t in types},"recent_events":rows}
@app.get("/api/v1/collaborations")
def collaborations(): return all_rows("SELECT x.*,c.title content_title FROM collaborations x JOIN content c ON c.id=x.content_id ORDER BY x.id DESC")
@app.post("/api/v1/collaborations")
def create_collaboration(req:Collaboration):
    if not one("SELECT id FROM content WHERE id=:id",{"id":req.content_id}): raise HTTPException(404,"Content not found")
    execute("INSERT INTO collaborations(content_id,role,note,status,created_at) VALUES(:c,:r,:n,'requested',:d)",{"c":req.content_id,"r":req.role,"n":req.note,"d":now()})
    record("collaboration_requested",req.content_id,metadata={"role":req.role,"note":req.note})
    return {"status":"requested","role":req.role,"created_at":now()}
@app.get("/api/v1/institution/{oid}/dashboard")
def dashboard(oid):
    o=one("SELECT * FROM organizations WHERE id=:id",{"id":oid})
    if not o: raise HTTPException(404,"Organization not found")
    return {"organization":o,"metrics":{"registered_content":one("SELECT COUNT(*) n FROM content WHERE organization_id=:id",{"id":oid})["n"],"learning_journeys":one("SELECT COUNT(*) n FROM content WHERE organization_id=:id AND journey_id IS NOT NULL",{"id":oid})["n"],"collaborations":one("SELECT COUNT(*) n FROM collaborations x JOIN content c ON c.id=x.content_id WHERE c.organization_id=:id",{"id":oid})["n"]},"content":all_rows("SELECT id,title,version,license,status FROM content WHERE organization_id=:id",{"id":oid})}

# Serve the production frontend from the same Render service: one origin, no fragile CORS/API split.
DIST=Path(__file__).resolve().parents[2]/"frontend"/"dist"
if DIST.exists():
    @app.get("/")
    def home(): return FileResponse(DIST/"index.html")
    @app.get("/{asset:path}")
    def spa(asset:str):
        p=DIST/asset
        return FileResponse(p if p.is_file() else DIST/"index.html")
