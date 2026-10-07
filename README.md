# أَثَرُهُم — Atharhum

منصة عربية RTL لتجربة **السند الرقمي للعلم والأثر**، مبنية كتطبيق واحد قابل للنشر: Content Passport، Digital Sanad، Verification، QR، Learning Journey، Athar Events، مؤسسات ومصادر مرجعية، ومساعد معرفي مرتبط بالمصدر.

## ما الذي يعمل؟

- **Content Passport:** هوية السجل، المصدر، الإصدار، الحقوق، والبصمة SHA-256.
- **Digital Sanad:** مسار تقني واضح من المصدر إلى التعلم.
- **QR Verification:** رمز QR يقود إلى صفحة تحقق عامة حقيقية.
- **Learning Journey:** بدء وإكمال رحلة التعلم وتسجيل الأحداث في قاعدة البيانات.
- **Grounded Assistant:** إجابة مرتبطة بالمصدر ولا تدّعي الإفتاء أو الاعتماد العلمي المستقل.
- **Athar Engine:** قياس التحقق، QR، provenance، الأسئلة، التعلم، والإشارات المؤسسية.
- **Institution Collaboration:** طلب تعاون يسجل فعليًا في قاعدة البيانات.

## التشغيل المحلي

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 10000
```

ثم افتح `http://localhost:10000`.

قاعدة SQLite تُنشأ تلقائيًا داخل `data/` عند التشغيل الأول.

## Render

المشروع **Single Service**، و`Dockerfile` موجود في جذر المستودع. `render.yaml` يعرّف Web Service + Render Postgres ويربط `DATABASE_URL` تلقائيًا بقاعدة البيانات.

في حالة إنشاء الخدمة من Blueprint، ارفع المستودع الذي يحتوي مباشرة على:

```text
Dockerfile
render.yaml
requirements.txt
app/
```

يمكن تعريف `PUBLIC_BASE_URL` في Render ليستخدمه QR كرابط عام ثابت. إذا لم يُعرّف، يستخدم التطبيق عنوان الطلب الحالي.

## البيانات والمؤسسات

البيانات الأولية تستخدم أسماء مؤسسات ومصادر حقيقية كمراجع عامة فقط، ولا تدّعي وجود شراكة أو اعتماد. أي محتوى محمي يبقى مرتبطًا بمصدره الأصلي بدل نسخه داخل المنصة.

## فلسفة المنتج

**SOURCE → TRUST → LEARNING → IMPACT → NEXT GENERATION**

أَثَرُهُم لا يقدّم نفسه كجهة إفتاء أو اعتماد علمي؛ دوره هو بناء طبقة هوية، provenance، تحقق، تعلم، وقياس أثر حول المعرفة.
