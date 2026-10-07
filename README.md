# أَثَرُهُم — Atharhum Pro Foundation

**البنية التي تحفظ هوية المعرفة أثناء انتقالها.**

هذه نسخة بناء جديدة ونظيفة، أوسع من الـFoundation السابقة، وتضم نواة تشغيلية لـ:
- Open Knowledge
- Institutional Workspaces
- Content Passport
- Rights
- Provenance / Sanad
- QR / Smart Verification
- Institutional Collaboration
- Source-grounded AI
- Learning Journeys
- Athar / Impact
- Audit-ready events

> المؤسسات الموجودة في البيانات التجريبية **مراجع مصدر وليست شركاء**. لا يوجد ادعاء شراكة.

## تشغيل Backend
```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## تشغيل Frontend
```bash
cd frontend
npm install
npm run dev
```

إذا شُغّل الـfrontend بدون Backend، سيعرض حالة الاتصال بوضوح بدلاً من اختراع بيانات.

## Acceptance Journey
Discover → Passport → QR/Verify → Sanad → AI Evidence → Learning → Completion → Athar → Collaboration → Institution

## Production target
PostgreSQL + pgvector + object storage + Redis workers + RBAC/SSO + signed IDs + observability.
SQLite هنا قاعدة تشغيل محلية حقيقية لتسهيل التجربة، وليست قرار البنية الإنتاجية النهائي.
