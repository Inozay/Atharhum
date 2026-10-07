# أَثَرُهُم — Atharhum v3

## السند الرقمي للعلم والأثر

أَثَرُهُم هو **طبقة ثقة وذكاء وأثر للمعرفة الموثوقة**. الفكرة ليست بناء مكتبة محتوى جديدة، بل إعطاء كل مادة معرفية هوية ومساراً قابلاً للفحص، ثم استخدام هذا السند كأساس للذكاء والتعلم وقياس ما يحدث بعد وصول المعرفة.

### التجربة الأساسية

**اكتشاف → جواز المحتوى → تحقق → تتبع السند → سؤال موثق → رحلة تعلم → أثر**

لا توجد في المنتج عبارات من نوع Demo أو For Judges؛ الواجهة تتعامل مع المنتج كمنصة حقيقية، بينما مواد العرض والتحكيم تبقى خارج المنتج.

## ما يعمل فعلياً

- بحث وتصفية في سجل المعرفة.
- Content Passport لكل مادة.
- QR ديناميكي لكل هوية.
- Verification Engine عبر API حقيقي.
- Provenance Timeline.
- Knowledge Graph بصري مرتبط بالمادة.
- مساعد source-grounded محلي مع أوضاع: Ask / Explain / Trace / Translate / Compare.
- عرض الأدلة والمصادر في كل إجابة موثقة.
- مقارنة بين مواد من حيث المصدر والإصدار والمراجعة ومسار السند.
- Learning Journey مع حفظ التقدم في SQLite.
- Event/Impact layer مع funnel محسوب من سجل الأحداث.
- إشارات استخدام فعلية أثناء التجربة تضاف إلى بيانات التشغيل التأسيسية التجريبية.
- SQLite محلي بلا خدمة قاعدة بيانات خارجية، مناسب للنواة المجانية وقابل للاستبدال لاحقاً بـPostgreSQL.
- FastAPI + Docker + Render.

## ملاحظة مهمة عن AI

المساعد الحالي هو **source-grounded local retrieval** حتى يعمل المنتج بلا API key وبلا اعتماد على مزود خارجي. هذا مقصود للنواة القابلة للنشر. طبقة الاسترجاع والواجهة التعاقدية مصممتان بحيث يمكن لاحقاً ربط Vector DB + Knowledge Graph + LLM إنتاجي دون تغيير تجربة المستخدم أو نموذج provenance.

## ملاحظة عن البيانات والأثر

المحتوى المعروض داخل المستودع **بيانات منتج تجريبية** وليست ادعاءات عن مصادر علمية حقيقية. كذلك أرقام Impact Intelligence تبدأ ببيانات تشغيلية تأسيسية تجريبية، ثم تستقبل أحداث الاستخدام أثناء التجربة. لا تُقدّم كدراسة بحثية أو كدليل على أثر اجتماعي حقيقي.

## التشغيل المحلي

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

ثم افتح:

`http://localhost:8000`

## الاختبار

```bash
python tests/smoke.py
```

الاختبار يغطي:

- Health
- Content
- Provenance
- Knowledge Graph
- Verification
- Source-grounded Assistant
- Learning Progress
- Events
- Impact
- QR generation

## النشر على Render

المشروع مهيأ لخدمة Docker واحدة:

- Runtime: Docker
- Health check: `/api/health`
- Port: متغير البيئة `PORT`
- لا يحتاج Node أو npm.

## البنية

```text
atharhum_v3/
├── backend/
│   └── main.py
├── frontend/
│   ├── index.html
│   └── static/
│       ├── app.js
│       ├── style.css
│       ├── logo.svg
│       └── hero.svg
├── docs/
├── tests/
├── Dockerfile
├── render.yaml
└── requirements.txt
```

## Product DNA

**SOURCE → PROVENANCE → TRUST → INTELLIGENCE → LEARNING → IMPACT → NEXT GENERATION**

الميزة التنافسية ليست AI وحده؛ بل النظام المتراكم حول المعرفة الموثوقة: كل مصدر ومراجعة ومسار تعلم وإشارة أثر يضيف سياقاً إلى الشبكة ويقوي الحلقة التالية.
