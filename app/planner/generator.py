import json
from openai import OpenAI
from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def _get_client() -> OpenAI:
    return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)


def generate_plan(
    destination: str,
    budget: float,
    days: int,
    preferences: str = "",
    youtube_summary: str = "",
    review_results: list[dict] | None = None,
    lang: str = "tr",
) -> str:
    client = _get_client()

    review_text = ""
    if review_results:
        for r in review_results:
            review_text += f"- {r.get('name', 'Unknown')}: Rating {r.get('rating', 'N/A')}, Address: {r.get('address', 'N/A')}\n"
            if r.get("price_level"):
                review_text += f"  Price level: {r['price_level']}\n"
            for rev in r.get("reviews", [])[:2]:
                review_text += f"  Review ({rev.get('rating')}/5): {rev.get('text', '')[:100]}\n"

    lang_name = "Turkish" if lang == "tr" else "English"
    lang_instruction = "Türkçe olarak" if lang == "tr" else "in English"

    user_content = f"""Create a detailed {days}-day travel plan for {destination}.
Budget: ${budget} USD total
Preferences: {preferences or "general tourism"}
"""

    if youtube_summary:
        user_content += f"""
YouTube Video Summary about the destination:
{youtube_summary}
"""
    if review_text:
        user_content += f"""
Recommended Places & Restaurants:
{review_text}
"""

    user_content += f"""
Please provide:
1. Day-by-day itinerary with morning, afternoon, evening activities
2. Estimated costs per activity/meal
3. Total estimated cost (must be within budget)
4. Transportation tips

Write the plan {lang_instruction}."""

    system_content = f"You are an expert travel planner. Create realistic, detailed travel itineraries. Respond {lang_instruction}."

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()
