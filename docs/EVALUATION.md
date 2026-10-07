# Evaluation Checklist — Atharhum v3

## 1. وضوح المشكلة
- [x] يشرح المنتج مشكلة فقدان المصدر والسياق والإصدار والمراجعة بعد إعادة نشر المحتوى.
- [x] يوضح أن المشكلة ليست نقص المحتوى بل فقدان قصة المعرفة.

## 2. وضوح الحل
- [x] Digital Identity
- [x] Content Passport
- [x] Provenance
- [x] Verification
- [x] Source-grounded AI
- [x] Learning Journey
- [x] Impact Intelligence

## 3. تجربة قابلة للاختبار
- [x] البحث يعمل.
- [x] اختيار المادة يعمل.
- [x] جواز المحتوى يعرض بياناتها.
- [x] QR يتولد من الخادم.
- [x] التحقق يستعلم من API.
- [x] تتبع السند يعمل.
- [x] Knowledge Graph يعمل.
- [x] المساعد يجيب من السجل ويعرض مصادره.
- [x] أوضاع Ask / Explain / Trace / Translate / Compare تعمل.
- [x] مقارنة المواد تعمل.
- [x] رحلة التعلم تحفظ التقدم.
- [x] الأحداث تسجل.
- [x] Impact Intelligence يتغير مع الأحداث.

## 4. الصدق العلمي والمنتجي
- [x] لا يتم تقديم المحتوى التجريبي كفتاوى أو مصادر علمية حقيقية.
- [x] لا يتم تقديم بيانات الأثر التجريبية كبحث أو أثر اجتماعي مثبت.
- [x] عند عدم وجود سند كافٍ، المساعد يعلن حدود المعرفة.

## 5. التقنية والنشر
- [x] FastAPI
- [x] SQLite للنواة
- [x] Docker
- [x] Render health check
- [x] Smoke tests
- [x] لا يعتمد على Node/npm.

## 6. ما بعد النواة
- [ ] PostgreSQL production migration
- [ ] Vector database
- [ ] Knowledge Graph database
- [ ] LLM provider with citation/evaluation harness
- [ ] Authentication + RBAC
- [ ] Institutional workspace
- [ ] Immutable audit log / signed provenance
- [ ] Automated AI evaluation dataset

هذه العناصر الأخيرة هي **توسعة إنتاجية** وليست أزراراً وهمية داخل النسخة الحالية.
