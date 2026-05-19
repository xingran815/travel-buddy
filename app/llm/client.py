from app.llm.factory import get_provider


def translate_to_turkish(text: str, source_language: str = "auto") -> str:
    source_hint = f"from {source_language}" if source_language != "unknown" else ""
    result = get_provider().chat_text(
        [
            {
                "role": "system",
                "content": "You are a professional translator. Translate the following text to Turkish. Output only the Turkish translation, nothing else.",
            },
            {
                "role": "user",
                "content": f"Translate the following text {source_hint} to Turkish:\n\n{text}",
            },
        ],
        temperature=0.3,
    )
    return result.text.strip()


def summarize_in_turkish(text: str) -> str:
    result = get_provider().chat_text(
        [
            {
                "role": "system",
                "content": "Sen profesyonel bir seyahat yazarısın. Verilen metni Türkçe olarak özetle. Özette önemli yerler, restoranlar ve aktiviteler vurgulansın. Sadece özeti yaz, başka bir şey ekleme.",
            },
            {
                "role": "user",
                "content": f"Aşağıdaki metni Türkçe olarak özetle:\n\n{text}",
            },
        ],
        temperature=0.5,
    )
    return result.text.strip()
