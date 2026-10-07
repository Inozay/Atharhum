# أَثَرُهُم — Atharuhum

السند الرقمي للعلم والأثر.

## ما الذي تعمل عليه هذه النسخة؟

نسخة نظيفة أحادية الخدمة مصممة للنشر على Render عبر Docker. الواجهة والـAPI داخل حاوية واحدة، لتقليل نقاط الفشل في النشر.

### المسارات التجريبية

- الصفحة الرئيسية وتجربة لجنة التحكيم
- جواز المحتوى
- سلسلة السند
- بطاقة هوية معرفية
- مركز التحقق + محاكاة QR
- شبكة المؤسسات
- مساعد موثق مرتبط بالمصادر
- ذكاء الأثر ومؤشرات مجمعة

> بيانات الأثر في هذه النسخة تجريبية توضيحية وليست نتائج بحثية. المؤسسات المدرجة هي مصادر/وجهات اكتشاف، وليست شركاء أو مؤسسات متعاقدة مع أَثَرُهُم.

## التشغيل المحلي

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

ثم:
http://localhost:8000

## Docker

```bash
docker build -t atharhum .
docker run -p 8000:8000 -e PORT=8000 atharhum
```

## Render

الخدمة:
- Runtime: Docker
- Dockerfile: `./Dockerfile`
- Context: `.`
- Health check: `/api/health`

لا تستخدم `pip install -r requirements.txt` كـ Build Command في خدمة Docker؛ ملف Dockerfile يتولى التثبيت والبناء.
