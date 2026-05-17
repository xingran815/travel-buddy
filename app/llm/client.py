from openai import OpenAI
from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

CHUNK_SIZE = 2500


def get_client() -> OpenAI:
    return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)


def _chunk_text(text: str, max_chars: int = CHUNK_SIZE) -> list[str]:
    paragraphs = text.split("\n")
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = para
        else:
            current = current + "\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())
    if not chunks:
        chunks = [text]
    return chunks


def translate_to_turkish(text: str, source_language: str = "auto") -> str:
    client = get_client()
    source_hint = f"from {source_language}" if source_language != "unknown" else ""
    chunks = _chunk_text(text)
    translations = []
    for i, chunk in enumerate(chunks):
        continuation = " Continue the translation from where the previous chunk left off. Maintain consistent terminology." if i > 0 else ""
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a professional translator. Translate the following text to Turkish. Output only the Turkish translation, nothing else.{continuation}",
                },
                {
                    "role": "user",
                    "content": f"Translate the following text {source_hint} to Turkish:\n\n{chunk}",
                },
            ],
            temperature=0.3,
        )
        translations.append(response.choices[0].message.content.strip())
    return "\n\n".join(translations)


def summarize_in_turkish(text: str) -> str:
    client = get_client()
    chunks = _chunk_text(text)
    if len(chunks) == 1:
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

    partial_summaries = []
    for chunk in chunks:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Sen profesyonel bir seyahat yazarısın. Verilen metin parçasını Türkçe olarak kısaca özetle. Özette önemli yerler, restoranlar ve aktiviteler vurgulansın. Sadece özeti yaz.",
                },
                {
                    "role": "user",
                    "content": f"Aşağıdaki metin parçasını Türkçe olarak özetle:\n\n{chunk}",
                },
            ],
            temperature=0.5,
        )
        partial_summaries.append(response.choices[0].message.content.strip())

    combined = "\n\n".join(partial_summaries)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Sen profesyonel bir seyahat yazarısın. Aşağıdaki kısa özetleri tek bir tutarlı Türkçe özette birleştir. Özette önemli yerler, restoranlar ve aktiviteler vurgulansın. Sadece özeti yaz, başka bir şey ekleme.",
            },
            {
                "role": "user",
                "content": f"Aşağıdaki kısa özetleri tek bir özette birleştir:\n\n{combined}",
            },
        ],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()
