"""System prompts and the aspect vocabulary for the LLM recommendation helpers.

Prompts that vary by language carry a literal ``{lang}`` placeholder, filled at
call time with ``.replace("{lang}", lang)`` — not ``str.format`` — so the JSON
braces in the examples are left untouched."""

ASPECT_KEYS = (
    "atmosphere", "service", "value", "cleanliness",
    "view", "romantic", "noise", "kid_friendly", "quiet",
)

PARSE_QUERY_SYSTEM = (
    "Extract structured travel preferences from a free-form user request. "
    "Output JSON with keys: cuisine (string or null), audience ('family'/'adult'/null), "
    "aspects (list of short tags such as 'romantic','view','quiet','rooftop'), "
    "near (string or null), price_level (1-4 or null). Use null when uncertain."
)

RERANK_SYSTEM = (
    "You re-rank place recommendations. Given a JSON payload with a user query, profile, "
    "preferences, and candidate places, choose the best k_out in preferred order. Each place "
    "carries score_breakdown, up to 3 top-rated review excerpts in good_reviews, and up to 3 "
    "lowest-rated review excerpts in bad_reviews. Read BOTH sides: a high overall rating with "
    "damaging bad_reviews (e.g. 'overpriced', 'dirty', 'rude staff', 'closed early') that "
    "match the user's stated priorities should drop in your ranking. A merely-OK rating whose "
    "bad_reviews are minor or off-topic should not. The rationale must mention the deciding "
    "pro or con in 1 short sentence. Output JSON: "
    "{\"order\": [{\"place_id\": str, \"rationale\": str}, ...]}. "
    "Reply in the user's language ({lang})."
)

RERANK_PROS_CONS_SYSTEM = (
    "You re-rank place recommendations AND summarize each chosen place. Given a JSON payload "
    "with a user query, profile, preferences, and candidate places, choose the best k_out in "
    "preferred order. Each place carries score_breakdown, up to 3 top-rated review excerpts in "
    "good_reviews, and up to 3 lowest-rated review excerpts in bad_reviews. Read BOTH sides: "
    "a high overall rating with damaging bad_reviews (e.g. 'overpriced', 'dirty', 'rude staff', "
    "'closed early') that match the user's stated priorities should drop in your ranking. "
    "A merely-OK rating whose bad_reviews are minor or off-topic should not. "
    "For each chosen place, also produce 2 short pros and 2 short cons (≤ 12 words each), "
    "grounded in good_reviews and bad_reviews. The rationale must mention the deciding pro or "
    "con in 1 short sentence. Output JSON: "
    "{\"order\": [{\"place_id\": str, \"rationale\": str, "
    "\"pros\": [str, str], \"cons\": [str, str]}, ...]}. "
    "Reply in the user's language ({lang})."
)

SUMMARIZE_SYSTEM = (
    "Summarize a place's user reviews into 2 short pros and 2 short cons. Reply in {lang}. "
    "Output JSON: {\"pros\": [str, str], \"cons\": [str, str]}. Each item ≤ 12 words."
)

PRICE_LEVEL_SYSTEM = (
    "Estimate Google Places price_level for a place using its user reviews. "
    "Scale: 1 = cheap, 2 = moderate, 3 = expensive, 4 = very expensive. "
    "Output JSON: {\"level\": int (1-4) or null, \"confidence\": \"low\"|\"med\"|\"high\"}. "
    "Return null level when reviews don't mention price or value."
)

EXTRACT_ASPECTS_SYSTEM = (
    "Tag a place with aspect scores 0..1 based on name, types, and review excerpts. "
    f"Aspects to score: {', '.join(ASPECT_KEYS)}. Output JSON: a flat object mapping aspect "
    "→ float in [0, 1]. Unknown aspects: 0.5."
)
