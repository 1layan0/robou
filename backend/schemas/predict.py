"""Request/response schemas for the predict API."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# معامل تعديل السعر حسب القرب من المرافق (قريب=بدون تخفيض، بعيد=تخفيض)
PROXIMITY_PRICE_FACTOR = {"قريب": 1.0, "متوسط": 0.97, "بعيد": 0.92}


class PredictRequest(BaseModel):
    """Input for land valuation prediction. Align with frontend predict form."""

    city: str = Field(..., description="City name")
    district: str = Field(..., description="District name")
    area_sqm: float = Field(..., gt=0, description="Land area in square meters")
    land_use: str = Field(..., description="Land use type")
    proximity: Optional[str] = Field(
        None,
        description="القرب من المرافق: قريب | متوسط | بعيد — يعدّل السعر التقديري",
    )
    street_width_m: Optional[float] = Field(None, ge=0, description="Street width in meters")
    street_count: Optional[int] = Field(None, ge=0, description="Number of streets")
    is_corner: bool = Field(False, description="Whether the parcel is on a corner")
    lat: Optional[float] = Field(None, description="Latitude")
    lng: Optional[float] = Field(None, description="Longitude")


class PredictResponse(BaseModel):
    """Response for land valuation (price model)."""

    price_per_sqm: float = Field(..., description="Predicted price per sqm")
    total_price: float = Field(..., description="Predicted total price")
    currency: str = Field("SAR", description="Currency code")


class RentResponse(BaseModel):
    """Response for rent model: monthly rent in SAR."""

    monthly_rent_sar: float = Field(..., description="Predicted monthly rent (SAR)")
    price_per_sqm_used: float = Field(..., description="Price per sqm used for rent prediction")
    currency: str = Field("SAR", description="Currency code")


class GrowthResponse(BaseModel):
    """Response for growth model: expected annual price growth."""

    growth_rate: float = Field(..., description="Annual growth rate (fraction, e.g. 0.05 = 5%)")
    growth_rate_pct: float = Field(..., description="Annual growth rate as percentage")


class InvestmentResponse(BaseModel):
    """Response for investment score: combines price, rent, growth into recommendation."""

    price_per_sqm: float = Field(..., description="Predicted price per sqm")
    total_price: float = Field(..., description="Predicted total price (SAR)")
    monthly_rent_sar: float = Field(..., description="Predicted monthly rent (SAR)")
    annual_growth_rate: float = Field(..., description="Expected annual price growth (fraction)")
    rent_yield: float = Field(..., description="Gross rent yield (fraction, annual)")
    liquidity: float = Field(..., description="Liquidity score 0..1")
    score: float = Field(..., description="Investment score 0..100")
    recommendation: str = Field(..., description="strong_buy | buy | hold | avoid")
    currency: str = Field("SAR", description="Currency code")


class ReportResponse(BaseModel):
    """Response for LLM report: recommendation + Arabic text."""

    price_per_sqm: float = Field(..., description="Price per sqm used")
    total_price: float = Field(..., description="Total price (SAR)")
    growth_rate_pct: float = Field(..., description="Annual growth %")
    recommendation: str = Field(..., description="strong_buy | buy | hold | avoid")
    score: float = Field(..., description="Score 0..100")
    report_ar: str = Field(..., description="Arabic explanation and advice")
    currency: str = Field("SAR", description="Currency code")


class BestAreasRequest(BaseModel):
    """طلب أفضل أحياء داخل نطاق (bbox)."""

    bbox: List[float] = Field(..., min_length=4, max_length=4, description="[minLng, minLat, maxLng, maxLat]")
    land_use: str = Field(..., description="سكني | تجاري")
    proximity: Optional[str] = Field("قريب", description="قريب | متوسط | بعيد")
    area_sqm: float = Field(400.0, gt=0, description="مساحة مرجعية للتقدير")
    top_n: int = Field(3, ge=1, le=5, description="أقصى عدد أحياء (1–5، افتراضي 3)")


class BestAreaItem(BaseModel):
    """حي واحد ضمن أفضل الأحياء في النطاق."""

    city: str = Field(..., description="المدينة")
    district: str = Field(..., description="الحي")
    latitude: float = Field(..., description="خط العرض")
    longitude: float = Field(..., description="خط الطول")
    price_per_sqm: float = Field(..., description="سعر المتر التقديري")
    growth_rate_pct: float = Field(..., description="معدل النمو السنوي %")
    reasons: List[str] = Field(default_factory=list, description="أسباب اقتراح هذا الحي")


class BestAreasResponse(BaseModel):
    """استجابة أفضل أحياء في النطاق (1–3 حسب ما يضمّه المستطيل)."""

    best_areas: List[BestAreaItem] = Field(..., description="أفضل 1–3 أحياء في النطاق")
    primary: BestAreaItem = Field(..., description="الحي الأول (الأفضل في النطاق)")


# --- Recommend districts (center + radius, aggregated price model) ---


class RecommendDistrictsWeights(BaseModel):
    """أوزان مكوّنات أفضلية الحي (اختياري)."""

    price: float = Field(0.5, ge=0, le=1, description="وزن السعر (أرخص = أفضل)")
    growth: float = Field(0.3, ge=0, le=1, description="وزن النمو")
    services: float = Field(0.2, ge=0, le=1, description="وزن الخدمات")


class RecommendDistrictsRequest(BaseModel):
    """طلب اقتراح أفضل أحياء داخل نطاق (دائرة)."""

    center_lat: float = Field(..., description="خط عرض مركز النطاق")
    center_lon: float = Field(..., description="خط طول مركز النطاق")
    radius_km: float = Field(..., gt=0, le=100, description="نصف قطر النطاق بالكم")
    city_ar: Optional[str] = Field(
        None,
        description="فلتر المدينة: الدمام | الخبر | الظهران | null = الكل",
    )
    property_type_ar: str = Field(
        ...,
        description="نوع العقار، مثال: قطعة أرض-سكنى أو قطعة أرض-تجارى",
    )
    top_k: int = Field(3, ge=1, le=10, description="أقصى عدد أحياء في النتيجة")
    mode: Optional[Literal["value", "premium", "growth"]] = Field(
        "value",
        description="وضع ترتيب النتائج (اختياري؛ القيمة الافتراضية 'value').",
    )
    min_price_per_sqm: Optional[float] = Field(None, ge=0, description="الحد الأدنى لسعر المتر (فلتر الميزانية)")
    max_price_per_sqm: Optional[float] = Field(None, ge=0, description="الحد الأعلى لسعر المتر (فلتر الميزانية)")
    proximity: Literal["قريب", "متوسط", "بعيد"] = Field(
        "قريب",
        description="القرب من المرافق: يغيّر أوزان الترتيب (خدمات أعلى وزنًا عند قريب)",
    )
    weights: Optional[RecommendDistrictsWeights] = Field(
        None,
        description="أوزان price/growth/services (اختياري). إن وُجدت تُستخدم بدل mode/proximity.",
    )


class GrowthComponent(BaseModel):
    """مكوّن النمو في نتيجة الحي: نسبة + مصدر + ثقة."""

    growth_pct: float = Field(..., description="نسبة النمو YoY المستخدمة")
    source: str = Field(..., description="district | city | default")
    confidence: str = Field(..., description="high | medium | low")


class ConfidenceReason(BaseModel):
    """سبب تصنيف الثقة: عدد الصفقات وتقلب السعر."""

    deals_count: int = Field(..., description="عدد الصفقات المستخدم")
    volatility: float = Field(..., description="تقلب السعر std أو iqr")


class RecommendDistrictItem(BaseModel):
    """حي واحد في نتيجة الاقتراح."""

    city_ar: str
    district_ar: str
    lat: float
    lon: float
    predicted_median_price_per_sqm: float
    score: int
    confidence: Literal["high", "medium", "low"] = Field(..., description="ثقة التقدير")
    confidence_reason: Optional[Dict[str, Any]] = Field(None, description="deals_count, volatility")
    services_level: Literal["high", "medium", "low"] = Field(..., description="مستوى الخدمات")
    growth_trend: Literal["up", "flat", "down"] = Field(..., description="اتجاه النمو")
    reasons_ar: List[str] = Field(default_factory=list, description="سببين فقط (أعلى مكوّنين)")
    components: Dict[str, float] = Field(default_factory=dict)
    growth_component: Optional[GrowthComponent] = Field(None, description="النمو: نسبة ومصدر وثقة")
    price_source: Optional[str] = Field(None, description="model_district_q | model_city_q | baseline_only")
    deals_count_used: Optional[int] = Field(None, description="عدد الصفقات المستخدم في الميزات")
    baseline_used: Optional[float] = Field(None, description="قيمة الـ baseline المستخدمة للتنبؤ")


class RecommendDistrictsResponse(BaseModel):
    """استجابة اقتراح أفضل أحياء داخل النطاق."""

    query: Dict[str, Any] = Field(default_factory=dict, description="نسخة من الطلب")
    count_in_radius: int = Field(..., description="عدد الأحياء داخل النطاق")
    top_k: int = Field(..., description="عدد النتائج المُرجع")
    tie: bool = Field(False, description="هل أفضل حيين متقاربان (فرق score < 5)")
    note: Optional[str] = Field(None, description="ملاحظة عند التعادل")
    results: List[RecommendDistrictItem] = Field(default_factory=list)
    mode_used: str = Field(..., description="value | premium | growth")
    latest_year: int = Field(..., description="أحدث سنة مستخدمة في التقدير")
    latest_quarter: int = Field(..., description="أحدث ربع مستخدم (1–4)")
    used_weights: Dict[str, float] = Field(default_factory=dict, description="الأوزان المستخدمة")
    proximity_applied: Optional[str] = Field(None, description="قريب | متوسط | بعيد")
    services_mult: Optional[float] = Field(None, description="معامل تضخيم مكوّن الخدمات")
