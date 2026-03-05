#!/bin/bash
# تشغيل الباك اند (التحليلات + التقدير)
# من مجلد المشروع: cd backend && ./run.sh
# أو: cd backend && pip install -r requirements.txt && uvicorn api.main:app --reload --port 8000

cd "$(dirname "$0")"
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "تثبيت المتطلبات أولاً: pip install -r requirements.txt"
  pip install -r requirements.txt
fi
exec uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
