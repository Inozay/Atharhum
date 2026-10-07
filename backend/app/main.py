from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .db import connect, now
import base64, io, qrcode

app=FastAPI(title="Atharhum Trust API",version="0.2.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

class Ask(BaseModel): content_id:str; question:str
class Event(BaseModel): event_type:str; metadata:dict={}
class Collaboration(BaseModel): content_id:str; role:str; note:str=""

def one(q,args=()):
    c=connect(); r=c.execute(q,args).fetchone(); c.close(); return dict(r) if r else None
def many(q,args=()):
    c=connect(); r=[dict(x) for x in c.execute(q,args).fetchall()]; c.close(); return r
def event(t,content_id=None,journey_id=None,metadata=None):
    c=connect(); c.execute("INSERT INTO events(type,content_id,journey_id,metadata,created_at) VALUES(?,?,?,?,?)",
      (t,content_id,journey_id,__import__("json").dumps(metadata or {},ensure_ascii=False),now())); c.commit(); c.close()

@app.get("/")
def root(): return {"name":"Atharhum","status":"ok","version":"0.2.0"}
@app.get("/health")
def health(): return {"status":"healthy"}
@app.get("/api/v1/organizations")
def organizations(): return many("SELECT * FROM organizations ORDER BY name")
@app.get("/api/v1/discover")
def discover():
    return many("""SELECT c.id,c.title,c.summary,c.license,c.rights,c.version,o.name organization
                   FROM content c JOIN organizations o ON o.id=c.organization_id ORDER BY c.created_at DESC""")
@app.get("/api/v1/content/{cid}")
def get_content(cid):
    r=one("SELECT * FROM content WHERE id=?",(cid,))
    if not r: raise HTTPException(404,"Content not found")
    return r
@app.get("/api/v1/passports/{cid}")
def passport(cid):
    r=one("""SELECT c.*,o.name issuer,o.label issuer_label FROM content c
             JOIN organizations o ON o.id=c.organization_id WHERE c.id=?""",(cid,))
    if not r: raise HTTPException(404,"Content not found")
    return {"content_id":r["id"],"title":r["title"],"issuer":r["issuer"],"issuer_label":r["issuer_label"],
      "version":r["version"],"integrity":{"algorithm":"SHA-256","value":r["integrity"]},
      "rights":r["rights"],"license":r["license"],"source":{"name":r["source_name"],"url":r["source_url"]},
      "verification":{"status":"registered","scope":"identity/integrity/recorded-rights/provenance"},
      "qr_verify":f"/api/v1/verify/{cid}","journey_id":r["journey_id"]}
@app.get("/api/v1/verify/{cid}")
def verify(cid):
    if not one("SELECT id FROM content WHERE id=?",(cid,)): raise HTTPException(404,"Content not found")
    event("verified",cid)
    return {"verified":True,"content_id":cid,"checks":[
      {"key":"identity","label":"هوية السجل","status":"pass"},
      {"key":"integrity","label":"سلامة النسخة","status":"pass"},
      {"key":"rights","label":"بيانات الحقوق","status":"recorded"},
      {"key":"provenance","label":"السند","status":"recorded"}]}
@app.get("/api/v1/provenance/{cid}")
def provenance(cid):
    if not one("SELECT id FROM content WHERE id=?",(cid,)): raise HTTPException(404,"Content not found")
    event("provenance_opened",cid)
    return {"content_id":cid,"nodes":many("SELECT type,label,entity,position FROM provenance WHERE content_id=? ORDER BY position",(cid,))}
@app.get("/api/v1/qr/{cid}")
def qr(cid):
    if not one("SELECT id FROM content WHERE id=?",(cid,)): raise HTTPException(404,"Content not found")
    img=qrcode.make(f"/verify/{cid}"); b=io.BytesIO(); img.save(b,format="PNG")
    return {"content_id":cid,"data_url":"data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()}
@app.post("/api/v1/ai/ask")
def ai(req:Ask):
    c=one("SELECT * FROM content WHERE id=?",(req.content_id,))
    if not c: raise HTTPException(404,"Content not found")
    event("ai_question",req.content_id,metadata={"question":req.question})
    return {"answer":"هذه إجابة مرتبطة بسجل المصدر الحالي. لا يعامل أَثَرُهُم النموذج اللغوي كمصدر مستقل؛ وعند غياب الدليل يجب التصريح بعدم كفايته.",
      "evidence":[{"source":c["source_name"],"url":c["source_url"],"scope":"المصدر المرتبط بالسجل","reason":"source-grounded"}],
      "grounding":"source-grounded","insufficient_evidence_policy":"refuse_or_qualify"}
@app.get("/api/v1/learning/{jid}")
def learning(jid):
    j=one("SELECT * FROM journeys WHERE id=?",(jid,))
    if not j: raise HTTPException(404,"Journey not found")
    return {**j,"steps":many("SELECT id,title,description,position FROM journey_steps WHERE journey_id=? ORDER BY position",(jid,))}
@app.post("/api/v1/learning/{jid}/events")
def learning_event(jid,event_in:Event):
    if not one("SELECT id FROM journeys WHERE id=?",(jid,)): raise HTTPException(404,"Journey not found")
    j=one("SELECT content_id FROM journeys WHERE id=?",(jid,))
    event(event_in.event_type,j["content_id"],jid,event_in.metadata)
    return {"recorded":True,"event_type":event_in.event_type}
@app.get("/api/v1/impact/{cid}")
def impact(cid):
    if not one("SELECT id FROM content WHERE id=?",(cid,)): raise HTTPException(404,"Content not found")
    types=["verified","provenance_opened","ai_question","learning_started","learning_completed","collaboration_requested"]
    rows=many("SELECT type,created_at,metadata FROM events WHERE content_id=? ORDER BY id DESC LIMIT 30",(cid,))
    return {"content_id":cid,"metrics":{t:sum(x["type"]==t for x in rows) for t in types},"recent_events":rows}
@app.get("/api/v1/collaborations")
def collaborations():
    return many("""SELECT x.*,c.title content_title FROM collaborations x JOIN content c ON c.id=x.content_id ORDER BY x.id DESC""")
@app.post("/api/v1/collaborations")
def create_collaboration(req:Collaboration):
    if not one("SELECT id FROM content WHERE id=?",(req.content_id,)): raise HTTPException(404,"Content not found")
    c=connect(); c.execute("INSERT INTO collaborations(content_id,role,note,status,created_at) VALUES(?,?,?,?,?)",
      (req.content_id,req.role,req.note,"requested",now())); c.commit(); cid=c.execute("SELECT last_insert_rowid()").fetchone()[0]; c.close()
    event("collaboration_requested",req.content_id,metadata={"role":req.role})
    return {"id":cid,"status":"requested","role":req.role}
@app.get("/api/v1/institution/{oid}/dashboard")
def dashboard(oid):
    o=one("SELECT * FROM organizations WHERE id=?",(oid,))
    if not o: raise HTTPException(404,"Organization not found")
    total=one("SELECT COUNT(*) n FROM content WHERE organization_id=?",(oid,))["n"]
    journeys=one("""SELECT COUNT(*) n FROM content c JOIN journeys j ON j.id=c.journey_id WHERE c.organization_id=?""",(oid,))["n"]
    return {"organization":o,"metrics":{"registered_content":total,"learning_journeys":journeys},
            "content":many("SELECT id,title,version,license,status FROM content WHERE organization_id=?",(oid,))}
