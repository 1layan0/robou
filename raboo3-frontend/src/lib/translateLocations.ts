/**
 * ترجمة أسماء المدن والأحياء ونصوص التوصيات للعرض في الواجهة الإنجليزية.
 */

const CITIES_EN: Record<string, string> = {
  'الدمام': 'Dammam',
  'الخبر': 'Khobar',
  'الظهران': 'Dhahran',
}

const DISTRICTS_EN: Record<string, string> = {
  'ابن خلدون': 'Ibn Khaldun',
  'الأثير': 'Al Athir',
  'البادية': 'Al Badiyah',
  'البديع': 'Al Badi',
  'الجلوية': 'Al Jalowiyah',
  'الجوهرة': 'Al Jawharah',
  'الحمراء': 'Al Hamra',
  'الخليج': 'Al Khalij',
  'الدواسر': 'Al Dawasir',
  'الربيع': 'Al Rabie',
  'السلام': 'Al Salam',
  'السوق': 'Al Suq',
  'الشاطئ الشرقي': 'East Corniche',
  'الشاطئ الغربي': 'West Corniche',
  'الطبيشي': 'Al Tubayshi',
  'العدامة': 'Al Adhamah',
  'العنود': 'Al Anud',
  'الغدير': 'Al Ghadir',
  'القادسية': 'Al Qadisiyah',
  'القزاز': 'Al Qazzaz',
  'المنار': 'Al Manar',
  'النخيل': 'Al Nakhil',
  'النهضة': 'Al Nahdah',
  'مدينة العمال': 'Workers City',
  'الاتصالات': 'Al Ittisalat',
  'الإسكان الجنوبي': 'South Housing',
  'البساتين': 'Al Basatin',
  'الجامعيين': 'Al Jamiyin',
  'الحسام': 'Al Hisam',
  'الخالدية': 'Al Khalidiyah',
  'الروضة': 'Al Rawdah',
  'الريان': 'Al Rayan',
  'السيف': 'Al Sayf',
  'الشفاء': 'Al Shifa',
  'الصدفة': 'Al Sidfah',
  'الصفا': 'Al Safa',
  'الفردوس': 'Al Firdaus',
  'الفنار': 'Al Fanar',
  'الفناتير': 'Al Fanateer',
  'المريكبات': 'Al Marikabat',
  'المزروعية': 'Al Mazruiyah',
  'المنتزه': 'Al Muntazah',
  'الناصرية': 'Al Nasiriyah',
  'النسيم': 'Al Naseem',
  'النورس': 'Al Nawras',
  'الواحة': 'Al Wahah',
  'الراكة': 'Al Rakah',
  'أحد': 'Uhud',
  'الأمانة': 'Al Amanah',
  'الأمل': 'Al Amal',
  'الضاحية': 'Al Dahiyah',
  'الضباب': 'Al Dhabab',
  'العروبة': 'Al Urubah',
  'الفرسان': 'Al Fursan',
  'الفيحاء': 'Al Fayha',
  'الفيصلية': 'Al Faisaliyah',
  'النور': 'Al Noor',
  'بدر': 'Badr',
  'طيبة': 'Taibah',
  'البحيرة': 'Al Buhayrah',
  'الخضرية': 'Al Khudariyah',
  'الصناعية': 'Industrial',
  'المحمدية': 'Al Muhammadiyah',
  'الرابية': 'Al Rabiyah',
  'الأنوار': 'Al Anwar',
  'الحاكمية': 'Al Hakimiyah',
  'الرحاب': 'Al Rihab',
  'الفاخرية': 'Al Fakhriyah',
  'الندى': 'Al Nada',
  'النزهة': 'Al Nuzhah',
  'ضاحية الملك فهد': 'King Fahd District',
  'عبدالله فؤاد': 'Abdullah Fouad',
  'غرناطة': 'Granada',
  'القرية الشعبية': 'Popular Village',
  'العمامرة': 'Al Ammarah',
  'الشعلة': 'Al Sholah',
  'المطار': 'Airport',
  'إشبيلية': 'Seville',
  'ابن سينا': 'Ibn Sina',
  'الإسكان': 'Al Iskan',
  'الأمواج': 'Al Amwaj',
  'الأندلس': 'Andalus',
  'البحر': 'Al Bahr',
  'البستان': 'Al Bustan',
  'البندرية': 'Al Bandariyah',
  'التحلية': 'Al Tahliah',
  'التعاون': 'Al Taawun',
  'الثقبة': 'Al Thuqbah',
  'الجسر': 'Al Jisr',
  'الحزام الأخضر': 'Green Belt',
  'الحزام الذهبي': 'Golden Belt',
  'الخبر الجنوبية': 'South Khobar',
  'الخبر الشمالية': 'North Khobar',
  'الخزامى': 'Al Khuzama',
  'الخور': 'Al Khor',
  'الراكة الجنوبية': 'South Rakah',
  'الراكة الشمالية': 'North Rakah',
  'الرجاء': 'Al Raja',
  'الروابي': 'Al Rawabi',
  'السفن': 'Al Sufun',
  'السليمانية': 'Al Sulimaniyah',
  'الشراع': 'Al Shira',
  'الصواري': 'Al Sawari',
  'العزيزية': 'Al Aziziyah',
  'العقربية': 'Al Aqrabiyah',
  'العقيق': 'Al Aqiq',
  'العليا': 'Al Olaya',
  'الكوثر': 'Al Kawthar',
  'الكورنيش': 'Corniche',
  'اللؤلؤ': 'Al Lu lu',
  'المرجان': 'Al Marjan',
  'المها': 'Al Maha',
  'الهدا': 'Al Hada',
  'اليرموك': 'Al Yarmuk',
  'صناعية الثقبة': 'Thuqbah Industrial',
  'صناعية الفوازية': 'Al Fawaziyah Industrial',
  'قرطبة': 'Cordoba',
  'أجيال': 'Ajyal',
  'التهامة': 'Al Tihamah',
  'الجامعة': 'University',
  'الحرس الوطني': 'National Guard',
  'الدانة الجنوبية': 'South Al Danah',
  'الدانة الشمالية': 'North Al Danah',
  'الدوحة الجنوبية': 'South Al Dohah',
  'الدوحة الشمالية': 'North Al Dohah',
  'السلمانية': 'Al Salmaniyah',
  'القشلة': 'Al Qishlah',
  'القصور': 'Al Qusur',
  'الوسام': 'Al Wisam',
  'تلال الظهران': 'Dhahran Hills',
  'هجر': 'Hajar',
}

// Variants seen in source data (spacing/hamza/spelling/prefixes)
const DISTRICT_ALIASES_EN: Record<string, string> = {
  'اشبيليا': 'Seville',
  'الاسكان': 'Al Iskan',
  'الامواج': 'Al Amwaj',
  'الدانه': 'Al Danah',
  'الأمراء': 'Al Umara',
  'الامراء': 'Al Umara',
  'الأمير محمد بن سعود': 'Prince Mohammed Bin Saud',
  'البيضاء': 'Al Bayda',
  'الخالدية الجنوبية': 'South Al Khalidiyah',
  'الخالدية الشمالية': 'North Al Khalidiyah',
  'الخبر الغربية': 'West Khobar',
}

function normalizeArabicKey(value: string): string {
  return (value || '')
    .trim()
    .replace(/[أإآ]/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ة/g, 'ه')
    .replace(/\s+/g, ' ')
}

function stripCityPrefix(value: string): string {
  const raw = (value || '').trim()
  if (!raw.includes('/')) return raw
  const parts = raw.split('/').map((p) => p.trim()).filter(Boolean)
  return parts.length > 1 ? parts[parts.length - 1] : raw
}

function hasArabicChars(value: string): boolean {
  return /[\u0600-\u06FF]/.test(value)
}

function transliterateArabic(value: string): string {
  const map: Record<string, string> = {
    ا: 'a', أ: 'a', إ: 'i', آ: 'aa',
    ب: 'b', ت: 't', ث: 'th', ج: 'j', ح: 'h', خ: 'kh',
    د: 'd', ذ: 'dh', ر: 'r', ز: 'z', س: 's', ش: 'sh',
    ص: 's', ض: 'd', ط: 't', ظ: 'z', ع: 'a', غ: 'gh',
    ف: 'f', ق: 'q', ك: 'k', ل: 'l', م: 'm', ن: 'n',
    ه: 'h', و: 'w', ي: 'y', ى: 'a', ة: 'h', ء: '',
    ' ': ' ', '/': ' / ', '-': '-',
  }
  return value
    .split('')
    .map((ch) => map[ch] ?? ch)
    .join('')
    .replace(/\s+/g, ' ')
    .trim()
}

const DISTRICTS_EN_NORMALIZED: Record<string, string> = (() => {
  const merged: Record<string, string> = { ...DISTRICTS_EN, ...DISTRICT_ALIASES_EN }
  const out: Record<string, string> = {}
  Object.entries(merged).forEach(([ar, en]) => {
    out[normalizeArabicKey(ar)] = en
  })
  return out
})()

/** أسباب التوصية من الباكند (عربي) → إنجليزي */
const REASONS_EN: Record<string, string> = {
  'مناسب حسب المعايير المختارة': 'Suitable by selected criteria',
  'مناسب حسب المعايير': 'Suitable by criteria',
  'أفضل سعر بين الأحياء الثلاثة': 'Best price among the three districts',
  'أعلى خدمات في المقارنة': 'Highest services in comparison',
  'سعر مناسب ضمن النطاق': 'Price within range',
  'خدمات أعلى من المتوسط': 'Above-average services',
  'اتجاه نمو أفضل': 'Better growth trend',
}

function translateReasonPattern(ar: string, isEn: boolean): string {
  if (!isEn) return ar
  const exact = REASONS_EN[ar]
  if (exact) return exact
  const match = ar.match(/^أعلى نمو متوقع \((.+)\)$/)
  if (match) return `Highest expected growth (${match[1]})`
  const match2 = ar.match(/^نمو متوقع \((.+)\)$/)
  if (match2) return `Expected growth (${match2[1]})`
  const match3 = ar.match(/^اتجاه نمو أفضل \((.+)\)$/)
  if (match3) return `Better growth trend (${match3[1]})`
  return ar
}

export function translateCity(cityAr: string, locale: string): string {
  if (locale !== 'en' || !cityAr) return cityAr
  const raw = cityAr.trim()
  return CITIES_EN[raw] ?? CITIES_EN[normalizeArabicKey(raw)] ?? raw
}

export function translateDistrict(districtAr: string, locale: string): string {
  if (locale !== 'en' || !districtAr) return districtAr
  const raw = districtAr.trim()
  const stripped = stripCityPrefix(raw)
  const normalized = normalizeArabicKey(stripped)
  const translated =
    DISTRICTS_EN[stripped] ??
    DISTRICTS_EN_NORMALIZED[normalized] ??
    translateCity(stripped, locale)
  if (translated !== stripped) return translated
  return hasArabicChars(stripped) ? transliterateArabic(stripped) : stripped
}

export function translateLocation(cityAr: string, districtAr: string, locale: string): { city: string; district: string } {
  return {
    city: translateCity(cityAr, locale),
    district: translateDistrict(districtAr, locale),
  }
}

export function translateReason(reasonAr: string, locale: string): string {
  return translateReasonPattern(reasonAr || '', locale === 'en')
}
