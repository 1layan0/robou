"""توليد التوصية والتقرير النصي بالعربي عبر LLM (OpenAI).

مدخلات: سعر المتر، السعر الإجمالي، النمو %، الحي، المساحة، الاستخدام.
مخرجات: recommendation (strong_buy | buy | hold | avoid)، score، report_ar (فقرة عربية).

إذا OPENAI_API_KEY غير موجود أو فشل الاستدعاء: نرجع توصية وتقرير افتراضي (stub).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config.settings import settings


@dataclass
class ReportResult:
    recommendation: str  # strong_buy | buy | hold | avoid
    score: float  # 0–100
    report_ar: str


def _stub_report(
    price_per_sqm: float,
    total_price: float,
    growth_pct: float,
    district: str,
    area_sqm: float,
    land_use: str,
) -> ReportResult:
    """تقرير افتراضي عند غياب LLM."""
    if growth_pct > 5 and price_per_sqm > 0:
        rec, score = "buy", 65.0
    elif growth_pct > 0:
        rec, score = "hold", 50.0
    else:
        rec, score = "avoid", 35.0
    report_ar = (
        f"تقدير القطعة: حي {district}، مساحة {area_sqm:.0f} م²، استخدام {land_use}. "
        f"سعر المتر {price_per_sqm:,.0f} ر.س، السعر الإجمالي {total_price:,.0f} ر.س. "
        f"معدل النمو السنوي المتوقع {growth_pct:.1f}%. "
        "التوصية الحالية من النظام الافتراضي (لتشغيل التقرير الكامل أضيفي OPENAI_API_KEY في .env)."
    )
    return ReportResult(recommendation=rec, score=score, report_ar=report_ar)


def generate_report(
    price_per_sqm: float,
    total_price: float,
    growth_pct: float,
    district: str,
    area_sqm: float,
    land_use: str,
    city: Optional[str] = None,
) -> ReportResult:
    """توليد التوصية + التقرير بالعربي. إن وُجد مفتاح OpenAI يُستدعى الـ LLM، وإلا stub."""
    if not (settings.openai_api_key or getattr(settings, "openai_api_key", "")):
        return _stub_report(
            price_per_sqm, total_price, growth_pct, district, area_sqm, land_use
        )

    try:
        import openai
    except ImportError:
        return _stub_report(
            price_per_sqm, total_price, growth_pct, district, area_sqm, land_use
        )

    client = openai.OpenAI(api_key=settings.openai_api_key)
    prompt = f"""أنت خبير عقاري. بناءً على البيانات التالية قدّم توصية واحدة فقط وتقريراً قصيراً بالعربية.

البيانات:
- المدينة: {city or 'غير محددة'}
- الحي: {district}
- المساحة: {area_sqm:.0f} م²
- الاستخدام: {land_use}
- سعر المتر: {price_per_sqm:,.0f} ر.س
- السعر الإجمالي: {total_price:,.0f} ر.س
- معدل النمو السنوي المتوقع: {growth_pct:.1f}%

المطلوب (بالضبط بصيغة JSON بدون markdown):
{{
  "recommendation": "واحد من: strong_buy أو buy أو hold أو avoid",
  "score": رقم بين 0 و 100,
  "report_ar": "فقرة أو فقرتان بالعربية تشرح التوصية والعوامل الرئيسية ونصيحة مختصرة"
}}
أرجع JSON فقط بدون أي نص إضافي."""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600,
        )
        text = (resp.choices[0].message.content or "").strip()
        # إزالة markdown code block إن وُجد
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(
                l for l in lines if not l.strip().startswith("```")
            )
        import json as _json
        data = _json.loads(text)
        rec = (data.get("recommendation") or "hold").strip().lower()
        if rec not in ("strong_buy", "buy", "hold", "avoid"):
            rec = "hold"
        score = float(data.get("score", 50))
        score = max(0, min(100, score))
        report_ar = (data.get("report_ar") or "").strip() or _stub_report(
            price_per_sqm, total_price, growth_pct, district, area_sqm, land_use
        ).report_ar
        return ReportResult(recommendation=rec, score=score, report_ar=report_ar)
    except Exception:
        return _stub_report(
            price_per_sqm, total_price, growth_pct, district, area_sqm, land_use
        )
