# ربوع Robou

منصة تقدير أسعار الأراضي في المنطقة الشرقية (الدمام، الخبر، الظهران).

- **Frontend:** Next.js (عربي/إنجليزي، تقدير الأسعار، صفقات الأراضي، لوحة التحليلات، حساب المستخدم)
- **Backend:** FastAPI (تقدير، توصية أحياء، تحليلات)

## التشغيل

```bash
# الواجهة
cd frontend && npm install && npm run dev

# الباك اند (اختياري للتحليلات والتقدير)
cd backend && pip install -r requirements.txt && uvicorn api.main:app --reload --port 8000
```

انظر `frontend/README.md` و `backend/README.md` للتفاصيل.
