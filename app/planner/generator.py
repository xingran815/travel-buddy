from app.llm.factory import get_provider


def generate_plan(
    destination: str,
    budget: float,
    days: int,
    preferences: str = "",
    youtube_summary: str = "",
    review_results: list[dict] | None = None,
    lang: str = "tr",
    max_reviews_per_place: int = 3,
    max_review_length: int = 300,
) -> str:
    review_text = ""
    if review_results:
        for r in review_results:
            review_text += f"- {r.get('name', 'Unknown')}: Rating {r.get('rating', 'N/A')}, Address: {r.get('address', 'N/A')}\n"
            if r.get("price_level"):
                review_text += f"  Price level: {r['price_level']}\n"
            for rev in r.get("reviews", [])[:max_reviews_per_place]:
                review_text += f"  Review ({rev.get('rating')}/5): {rev.get('text', '')[:max_review_length]}\n"

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

    result = get_provider().chat_text(
        [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
    )
    return result.text.strip()
