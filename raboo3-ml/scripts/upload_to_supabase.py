#!/usr/bin/env python3
"""
رفع جداول وبيانات raboo3 إلى Supabase (PostgreSQL).
يُفضّل ملف db/loaded_aggregate_pg.sql (مُولَّد: python scripts/build_supabase_aggregate_sql.py).
وإلا يُستخدم loaded_aggregate.sql (MySQL) مع قيود أعمدة قديمة.

المطلوب:
  - متغير بيئة: SUPABASE_DB_URL
    من Supabase: Project Settings → Database → Connection string (URI)
    مثال: postgresql://postgres.[ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres

تشغيل:
  cd raboo3-ml
  pip install psycopg2-binary
  export SUPABASE_DB_URL='postgresql://...'
  python scripts/upload_to_supabase.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("تثبيت: pip install psycopg2-binary")
    sys.exit(1)

# مسارات من مجلد raboo3-ml
ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "db" / "schema_supabase.sql"


def _load_supabase_url_from_env_file() -> None:
    """يقرأ SUPABASE_DB_URL من raboo3-ml/.env إن لم تكن مضبوطة في البيئة."""
    if os.environ.get("SUPABASE_DB_URL"):
        return
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("SUPABASE_DB_URL="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    os.environ["SUPABASE_DB_URL"] = val
                return
    except OSError:
        pass
_DATA_PG = ROOT / "db" / "loaded_aggregate_pg.sql"
_DATA_MYSQL = ROOT / "db" / "loaded_aggregate.sql"
# يُفضّل ملف PostgreSQL المُولَّد: python scripts/build_supabase_aggregate_sql.py
DATA_PATH = _DATA_PG if _DATA_PG.exists() else _DATA_MYSQL
BATCH_SIZE = 2000  # عدد صفوف RealSale و DistrictQuarterAggregate في كل دفعة


def get_conn():
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("اضبط SUPABASE_DB_URL (اتصال Supabase PostgreSQL)")
        sys.exit(1)
    conn = psycopg2.connect(url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SET search_path TO public")
    conn.autocommit = False
    return conn


def _split_sql_statements(content: str):
    """تقسيم SQL باحترام النص داخل $$ ... $$ (مثل دوال plpgsql)."""
    statements = []
    i = 0
    n = len(content)
    start = 0
    in_dollar = False
    while i < n:
        if not in_dollar and content[i : i + 2] == "$$":
            in_dollar = True
            i += 2
            continue
        if in_dollar and content[i : i + 2] == "$$":
            in_dollar = False
            i += 2
            continue
        if not in_dollar and content[i] == ";":
            stmt = content[start:i].strip()
            if stmt and not stmt.startswith("--"):
                statements.append(stmt)
            start = i + 1
            i += 1
            continue
        i += 1
    if start < n:
        stmt = content[start:n].strip()
        if stmt and not stmt.startswith("--"):
            statements.append(stmt)
    return statements


def run_schema(conn):
    print("تشغيل السكيمة (schema_supabase.sql)...")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    statements = _split_sql_statements(content)
    old_autocommit = conn.autocommit
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for s in statements:
                s = s.strip()
                if not s:
                    continue
                try:
                    cur.execute(s + ";")
                except Exception as e:
                    conn.rollback()
                    err = str(e).lower()
                    if "already exists" in err or "does not exist" in err:
                        pass
                    else:
                        raise
    finally:
        conn.autocommit = old_autocommit
    print("تم تطبيق السكيمة.")


def extract_section(content: str, start_marker: str, end_marker: str) -> str | None:
    start = content.find(start_marker)
    if start == -1:
        return None
    end = content.find(end_marker, start)
    if end == -1:
        return content[start:]
    return content[start:end]


def run_district(conn, content: str):
    section = extract_section(content, "-- District\n", "\n\n-- RealSale")
    if not section:
        return
    sql_text = section.strip()
    # إزالة سطر التعليق إن وُجد ثم تحويل INSERT IGNORE إلى PostgreSQL
    if sql_text.startswith("--"):
        sql_text = sql_text.split("\n", 1)[-1].strip()
    sql_text = sql_text.replace("INSERT IGNORE INTO District", "INSERT INTO District", 1)
    if sql_text.endswith(";"):
        sql_text = sql_text[:-1].strip()
    if "ON CONFLICT" not in sql_text.upper():
        sql_text += " ON CONFLICT (city_ar, district_ar) DO NOTHING"
    with conn.cursor() as cur:
        cur.execute(sql_text)
    conn.commit()
    print("District: تم.")


def run_realsale(conn, content: str):
    section = extract_section(content, "-- RealSale\nINSERT INTO RealSale", "\n\n-- DistrictQuarterAggregate")
    if not section:
        return
    full_insert = section.strip()
    if full_insert.startswith("--"):
        full_insert = full_insert.split("\n", 1)[1].strip()
    if full_insert.endswith(";"):
        full_insert = full_insert[:-1]
    match = re.match(r"(INSERT INTO RealSale\s*\([^)]+\)\s*VALUES)\s*", full_insert, re.DOTALL)
    if not match:
        print("RealSale: لم يُعثر على نمط INSERT")
        return
    prefix = match.group(1)
    rest = full_insert[match.end() :].strip()
    # تقسيم حسب عمق الأقواس (قيم قد تحتوي فواصل داخل النصوص)
    parts = []
    depth = 0
    start = 0
    for i, c in enumerate(rest):
        if c == "(":
            if depth == 0:
                start = i
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                parts.append(rest[start : i + 1])
    total = len(parts)
    print(f"RealSale: {total} صف، تحميل على دفعات...")
    for offset in range(0, total, BATCH_SIZE):
        batch = parts[offset : offset + BATCH_SIZE]
        values_str = ",\n  ".join(batch)
        q = prefix + " " + values_str
        with conn.cursor() as cur:
            cur.execute(q)
        conn.commit()
        print(f"  {min(offset + BATCH_SIZE, total)} / {total}")
    print("RealSale: تم.")


def run_district_quarter_aggregate(conn, content: str):
    section = extract_section(
        content,
        "-- DistrictQuarterAggregate\nINSERT INTO DistrictQuarterAggregate",
        "\n\n-- DistrictGrowthYoy",
    )
    if not section:
        return
    full_insert = section.strip()
    if full_insert.startswith("--"):
        full_insert = full_insert.split("\n", 1)[1].strip()
    # قصِّ ON CONFLICT / ; الزائدة للدفعات
    if "ON CONFLICT" in full_insert:
        full_insert = full_insert.split("ON CONFLICT")[0].strip()
    if full_insert.endswith(";"):
        full_insert = full_insert[:-1]
    match = re.match(
        r"(INSERT INTO DistrictQuarterAggregate\s*\([^)]+\)\s*VALUES)\s*",
        full_insert,
        re.DOTALL,
    )
    if not match:
        print("DistrictQuarterAggregate: لم يُعثر على نمط INSERT")
        return
    prefix = match.group(1)
    rest = full_insert[match.end() :].strip()
    depth = 0
    start = 0
    parts = []
    for i, c in enumerate(rest):
        if c == "(":
            if depth == 0:
                start = i
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                parts.append(rest[start : i + 1])
    total = len(parts)
    print(f"DistrictQuarterAggregate: {total} صف...")
    for offset in range(0, total, BATCH_SIZE):
        batch = parts[offset : offset + BATCH_SIZE]
        values_str = ",\n  ".join(batch)
        if "district_id" in prefix:
            conflict = "ON CONFLICT (district_id, property_type_ar, year, quarter) DO NOTHING"
        else:
            conflict = "ON CONFLICT (city_ar, district_ar, property_type_ar, year, quarter) DO NOTHING"
        q = prefix + " " + values_str + " " + conflict
        with conn.cursor() as cur:
            cur.execute(q)
        conn.commit()
        print(f"  {min(offset + BATCH_SIZE, total)} / {total}")
    print("DistrictQuarterAggregate: تم.")


def run_district_growth_yoy(conn, content: str):
    section = extract_section(
        content,
        "-- DistrictGrowthYoy\nINSERT INTO DistrictGrowthYoy",
        "\n-- AggregatedPriceModelVersion",
    )
    if not section:
        section = extract_section(
            content,
            "-- DistrictGrowthYoy\nINSERT INTO DistrictGrowthYoy",
            "\nON DUPLICATE KEY UPDATE",
        )
    if not section:
        return
    sql_text = section.strip()
    if sql_text.startswith("--"):
        sql_text = sql_text.split("\n", 1)[1].strip()
    if "ON CONFLICT" in sql_text:
        # ملف PG جاهز يتضمن ON CONFLICT
        if not sql_text.endswith(";"):
            sql_text = sql_text + ";"
    else:
        if sql_text.endswith(";"):
            sql_text = sql_text[:-1]
        if "district_id" in sql_text.split("VALUES", 1)[0]:
            conflict_cols = "(district_id, property_type_ar)"
        else:
            conflict_cols = "(city_ar, district_ar, property_type_ar)"
        growth_col = "yoy_growth_pct" if "district_id" in sql_text.split("VALUES", 1)[0] else "growth_pct"
        sql_text += f"""
 ON CONFLICT {conflict_cols}
 DO UPDATE SET
   {growth_col} = EXCLUDED.{growth_col},
   growth_source = EXCLUDED.growth_source,
   growth_confidence = EXCLUDED.growth_confidence,
   updated_at = CURRENT_TIMESTAMP
"""
    with conn.cursor() as cur:
        cur.execute(sql_text)
    conn.commit()
    print("DistrictGrowthYoy: تم.")


def run_aggregated_price_model_version(conn, content: str):
    with conn.cursor() as cur:
        cur.execute("UPDATE AggregatedPriceModelVersion SET is_active = 0")
    conn.commit()

    section = extract_section(
        content,
        "-- AggregatedPriceModelVersion",
        "\nCOMMIT;",
    )
    if not section:
        section = extract_section(
            content,
            "-- AggregatedPriceModelVersion\nUPDATE",
            "SET FOREIGN_KEY_CHECKS",
        )
    if not section:
        u_pos = content.find("UPDATE AggregatedPriceModelVersion SET is_active = 0")
        if u_pos == -1:
            print("AggregatedPriceModelVersion: لم يُعثر على قسم في الملف")
            return
        c_pos = content.find("\nCOMMIT;", u_pos)
        section = content[u_pos:c_pos] if c_pos != -1 else content[u_pos:]

    idx = section.find("INSERT INTO AggregatedPriceModelVersion")
    if idx == -1:
        print("AggregatedPriceModelVersion: لم يُعثر على INSERT")
        return
    rest = section[idx:]
    semi = rest.find(";")
    if semi == -1:
        print("AggregatedPriceModelVersion: جملة INSERT غير مكتملة")
        return
    sql_text = rest[: semi + 1].strip()
    with conn.cursor() as cur:
        cur.execute(sql_text)
    conn.commit()
    print("AggregatedPriceModelVersion: تم.")


def main():
    _load_supabase_url_from_env_file()
    if not DATA_PATH.exists():
        print(
            f"ملف البيانات غير موجود: {DATA_PATH}\n"
            "للنسخة المطبّعة: python scripts/build_supabase_aggregate_sql.py"
        )
        sys.exit(1)
    if DATA_PATH.name == "loaded_aggregate.sql":
        print("تحذير: تستخدمين loaded_aggregate.sql (MySQL). يُفضّل build_supabase_aggregate_sql.py → loaded_aggregate_pg.sql")
    if not SCHEMA_PATH.exists():
        print(f"ملف السكيمة غير موجود: {SCHEMA_PATH}")
        sys.exit(1)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    conn = get_conn()
    try:
        # السكيمة لا تُشغّل من السكربت مع Pooler (كل أمر يذهب لخادم مختلف).
        # شغّلي schema_supabase.sql مرة واحدة من Supabase: SQL Editor → New query → Paste → Run
        if os.environ.get("RUN_SCHEMA") == "1":
            run_schema(conn)
        else:
            print("تخطي السكيمة (شغّلي db/schema_supabase.sql من Supabase SQL Editor إن لم تكوني فعلت).")
        with conn.cursor() as cur:
            cur.execute("SET search_path TO public")
        conn.commit()
        run_district(conn, content)
        run_realsale(conn, content)
        run_district_quarter_aggregate(conn, content)
        run_district_growth_yoy(conn, content)
        run_aggregated_price_model_version(conn, content)
        print("انتهى رفع الجداول والبيانات إلى Supabase.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
