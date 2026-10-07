import sqlite3, json
from pathlib import Path
from datetime import datetime, timezone

DB = Path(__file__).resolve().parent.parent / "atharhum.db"

def now(): return datetime.now(timezone.utc).isoformat()

def connect():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c

def init():
    c=connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS organizations(
      id TEXT PRIMARY KEY,name TEXT NOT NULL,kind TEXT,source_url TEXT,label TEXT);
    CREATE TABLE IF NOT EXISTS content(
      id TEXT PRIMARY KEY,title TEXT NOT NULL,summary TEXT,organization_id TEXT,
      source_name TEXT,source_url TEXT,license TEXT,rights TEXT,version TEXT,
      integrity TEXT,status TEXT,journey_id TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS provenance(
      id INTEGER PRIMARY KEY AUTOINCREMENT,content_id TEXT,type TEXT,label TEXT,entity TEXT,position INTEGER);
    CREATE TABLE IF NOT EXISTS journeys(
      id TEXT PRIMARY KEY,title TEXT,content_id TEXT);
    CREATE TABLE IF NOT EXISTS journey_steps(
      id TEXT PRIMARY KEY,journey_id TEXT,title TEXT,description TEXT,position INTEGER);
    CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY AUTOINCREMENT,type TEXT,content_id TEXT,journey_id TEXT,metadata TEXT,created_at TEXT);
    CREATE TABLE IF NOT EXISTS collaborations(
      id INTEGER PRIMARY KEY AUTOINCREMENT,content_id TEXT,role TEXT,note TEXT,status TEXT,created_at TEXT);
    """)
    seed(c); c.commit(); c.close()

def seed(c):
    if c.execute("SELECT 1 FROM organizations LIMIT 1").fetchone(): return
    orgs=[
      ("qnl","Qatar National Library","reference_source","https://qnl.qa/en/terms-of-use","مرجع مصدر — ليست شراكة"),
      ("loc","Library of Congress","reference_source","https://www.loc.gov/free-to-use/","مرجع مصدر — ليست شراكة"),
      ("unesco","UNESCO World Heritage Centre","reference_source","https://whc.unesco.org/en/licenses","مرجع مصدر — ليست شراكة")]
    c.executemany("INSERT INTO organizations VALUES(?,?,?,?,?)",orgs)
    import hashlib
    integrity=hashlib.sha256(b"atharhum-open-reference-v1").hexdigest()
    c.execute("""INSERT INTO content VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
      "knowledge-001","مرجع معرفة مفتوحة",
      "سجل مرجعي يوضح كيف يربط أَثَرُهُم الهوية والحقوق والسند والتعلم بالمصدر.",
      "qnl","Qatar National Library — Terms of Use","https://qnl.qa/en/terms-of-use",
      "Mixed / item-level rights","تحقق من الترخيص على مستوى المادة قبل إعادة الاستخدام",
      "1.0",integrity,"registered","journey-001",now()))
    prov=[
      ("knowledge-001","original","المصدر المرجعي","Qatar National Library",0),
      ("knowledge-001","registered","سُجل في أَثَرُهُم","Atharhum Registry",1),
      ("knowledge-001","learning","مرتبط برحلة تعلم","From Source to Athar",2)]
    c.executemany("INSERT INTO provenance(content_id,type,label,entity,position) VALUES(?,?,?,?,?)",prov)
    c.execute("INSERT INTO journeys VALUES(?,?,?)",("journey-001","من المصدر إلى الأثر","knowledge-001"))
    steps=[
      ("s1","journey-001","اكتشف","تعرف على المادة ومصدرها.",0),
      ("s2","journey-001","تحقق","افتح Passport وتحقق من الهوية والحقوق.",1),
      ("s3","journey-001","افهم","اقرأ المصدر واسأل المساعد المرتبط بالدليل.",2),
      ("s4","journey-001","تعلم","نفذ نشاطاً قصيراً مرتبطاً بالمصدر.",3),
      ("s5","journey-001","أكمل","سجل إتمام الرحلة.",4),
      ("s6","journey-001","أثر","شاهد كيف تحولت المعرفة إلى فعل.",5)]
    c.executemany("INSERT INTO journey_steps VALUES(?,?,?,?,?)",steps)

init()
