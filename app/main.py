from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import json

BASE = Path(__file__).resolve().parent
DATA = BASE / "data.json"

app = FastAPI(title="أَثَرُهُم | Atharuhum", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

with open(DATA, "r", encoding="utf-8") as f:
    DB = json.load(f)

class VerifyRequest(BaseModel):
    code: str

class AskRequest(BaseModel):
    question: str

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE / "static" / "index.html")

@app.get("/api/health")
def health():
    return {"ok": True, "service": "atharuhum", "version": "1.0.0"}

@app.get("/api/content/{content_id}")
def content(content_id: str):
    item = next((x for x in DB["content"] if x["id"] == content_id), None)
    if not item:
        raise HTTPException(404, "Content not found")
    return item

@app.get("/api/institutions")
def institutions():
    return DB["institutions"]

@app.get("/api/impact")
def impact():
    return DB["impact"]

@app.post("/api/verify")
def verify(payload: VerifyRequest):
    item = next((x for x in DB["content"] if x["verification_code"] == payload.code), None)
    if not item:
        return {"verified": False, "message": "لم يتم العثور على سجل مطابق."}
    return {
        "verified": True,
        "message": "السجل صالح داخل نموذج أَثَرُهُم التجريبي.",
        "content_id": item["id"],
        "title": item["title"],
        "institution": item["institution"],
        "chain": item["chain"],
        "version": item["version"],
    }

@app.post("/api/assistant")
def assistant(payload: AskRequest):
    q = payload.question.strip()
    if not q:
        return {"answer": "اكتب سؤالًا عن المحتوى أو السند أو المصدر.", "sources": []}
    item = DB["content"][0]
    answer = (
        f"وفق سجل «{item['title']}»، تبدأ سلسلة التوثيق من الأصل ثم تمر بالمراجعة "
        f"والإصدار قبل الإتاحة. المساعد هنا لا يقدّم فتوى ولا يستبدل المختص؛ "
        f"وظيفته ربط الإجابة بالسجل والمصادر المعتمدة."
    )
    return {"answer": answer, "sources": item["sources"]}

@app.get("/api/demo")
def demo():
    return {
        "content": DB["content"],
        "institutions": DB["institutions"],
        "impact": DB["impact"],
    }
