from openai import OpenAI
from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def get_client() -> OpenAI:
    return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)


def translate_to_turkish(text: str, source_language: str = "auto") -> str:
    client = get_client()
    source_hint = f"from {source_language}" if source_language != "unknown" else ""
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
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
    return response.choices[0].message.content.strip()


def summarize_in_turkish(text: str) -> str:
    client = get_client()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
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
    return response.choices[0].message.content.strip()
