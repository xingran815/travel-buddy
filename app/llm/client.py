"""High-level text helpers for the YouTube-summary flow: translate and summarize.

Thin wrappers over the configured provider (``app/llm/factory.get_provider``)
that build the system/user prompts for translation and travel-oriented
summarization. Both English and Turkish are supported as output languages.
"""

from app.llm.factory import get_provider

LANG_NAMES = {"en": "English", "tr": "Turkish"}


def translate_text(text: str, target_lang: str = "tr", source_language: str = "auto") -> str:
    """Translate ``text`` into ``target_lang`` (default Turkish), returning only the translation."""
    lang_name = LANG_NAMES.get(target_lang, "Turkish")
    source_hint = f"from {source_language}" if source_language != "unknown" else ""
    result = get_provider().chat_text(
        [
            {
                "role": "system",
                "content": (
                    f"You are a professional translator. Translate the following text to {lang_name}. "
                    f"Output only the {lang_name} translation, nothing else."
                ),
            },
            {
                "role": "user",
                "content": f"Translate the following text {source_hint} to {lang_name}:\n\n{text}",
            },
        ],
        temperature=0.3,
    )
    return result.text.strip()


def summarize_text(text: str, lang: str = "tr") -> str:
    """Summarize ``text`` as a travel writer in ``lang``, emphasizing places and activities."""
    if lang == "en":
        system_content = (
            "You are a professional travel writer. Summarize the given text in English. "
            "In the summary, emphasize important places, restaurants and activities. "
            "Write only the summary, nothing else."
        )
        user_content = f"Summarize the following text in English:\n\n{text}"
    else:
        system_content = (
            "Sen profesyonel bir seyahat yazarısın. Verilen metni Türkçe olarak özetle. "
            "Özette önemli yerler, restoranlar ve aktiviteler vurgulansın. "
            "Sadece özeti yaz, başka bir şey ekleme."
        )
        user_content = f"Aşağıdaki metni Türkçe olarak özetle:\n\n{text}"
    result = get_provider().chat_text(
        [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        temperature=0.5,
    )
    return result.text.strip()
