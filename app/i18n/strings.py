STRINGS = {
    "welcome": {
        "en": "Welcome to Travel Recommender!",
        "tr": "Seyahat Öneri Sistemine Hoş Geldiniz!",
    },
    "summarizing": {
        "en": "Summarizing video...",
        "tr": "Video özetleniyor...",
    },
    "summarize_done": {
        "en": "Summary complete.",
        "tr": "Özetleme tamamlandı.",
    },
    "downloading": {
        "en": "Downloading video...",
        "tr": "Video indiriliyor...",
    },
    "download_done": {
        "en": "Download complete.",
        "tr": "İndirme tamamlandı.",
    },
    "transcribing": {
        "en": "Transcribing audio...",
        "tr": "Ses yazıya dökülüyor...",
    },
    "transcribe_done": {
        "en": "Transcription complete.",
        "tr": "Yazıya dökme tamamlandı.",
    },
    "translating": {
        "en": "Translating to Turkish...",
        "tr": "Türkçeye çevriliyor...",
    },
    "translate_done": {
        "en": "Translation complete.",
        "tr": "Çeviri tamamlandı.",
    },
    "fetching_reviews": {
        "en": "Fetching reviews for: {region}",
        "tr": "Değerlendirmeler getiriliyor: {region}",
    },
    "reviews_done": {
        "en": "Found {count} recommendations.",
        "tr": "{count} öneri bulundu.",
    },
    "generating_plan": {
        "en": "Generating travel plan...",
        "tr": "Seyahat planı oluşturuluyor...",
    },
    "plan_done": {
        "en": "Travel plan ready!",
        "tr": "Seyahat planı hazır!",
    },
    "error_no_url": {
        "en": "Error: Please provide a YouTube URL.",
        "tr": "Hata: Lütfen bir YouTube URL'si girin.",
    },
    "error_no_region": {
        "en": "Error: Please provide a region.",
        "tr": "Hata: Lütfen bir bölge girin.",
    },
    "error_api_key": {
        "en": "Error: Missing API key. Check your .env file.",
        "tr": "Hata: API anahtarı eksik. .env dosyanızı kontrol edin.",
    },
    "header_summary": {
        "en": "=== Video Summary ===",
        "tr": "=== Video Özeti ===",
    },
    "header_translation": {
        "en": "=== Turkish Translation ===",
        "tr": "=== Türkçe Çeviri ===",
    },
    "header_recommendations": {
        "en": "=== Recommendations ===",
        "tr": "=== Öneriler ===",
    },
    "header_plan": {
        "en": "=== Travel Plan ===",
        "tr": "=== Seyahat Planı ===",
    },
    "lang_set": {
        "en": "Language set to English.",
        "tr": "Dil Türkçe olarak ayarlandı.",
    },
}


def t(key: str, lang: str = "tr", **kwargs) -> str:
    entry = STRINGS.get(key, {})
    text = entry.get(lang, entry.get("en", key))
    if kwargs:
        text = text.format(**kwargs)
    return text
