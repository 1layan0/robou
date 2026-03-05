#!/usr/bin/env python3
"""تشغيل ملف loaded_real.sql الجاهز (بدون إعادة توليد)."""
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SQL = PROJECT / "db" / "loaded_real.sql"

if not SQL.exists():
    print("شغّل load_real_data_to_mysql.py أولاً لتوليد الملف.")
    exit(1)

print("جاري تحميل البيانات...")
with open(SQL) as f:
    r = subprocess.run(
        ["docker", "exec", "-i", "raboo3-ml-mysql", "mysql", "-u", "root", "-praboo3_root", "raboo3"],
        stdin=f, capture_output=True, text=True, cwd=PROJECT
    )
if r.returncode != 0:
    print("خطأ:", r.stderr or r.stdout)
    exit(1)
print("تم.")
