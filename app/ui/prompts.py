import questionary
from app.i18n.strings import t
from app.reviews.categories import CATEGORY_ORDER
from app.ui.type_prompts import prompts_for_types

PROFILE_ORDER = ("balanced", "foodie", "budget", "aspect-heavy")

_QUIT = object()


def _ask_text(label: str, default: str = "") -> str | None:
    value = questionary.text(label, default=default).ask()
    if value is None:
        return None
    if value.strip().lower() == "q":
        return None
    return value


def _ask_cuisine(lang: str) -> dict | None:
    v = _ask_text(t("prompt_cuisine", lang), default="")
    if v is None:
        return None
    return {"cuisine": v.strip() or None}


def _ask_people(lang: str) -> dict | None:
    v = _ask_text(t("prompt_people", lang), default="2")
    if v is None:
        return None
    return {"people": int(v) if v.strip() else 2}


def _ask_budget(lang: str) -> dict | None:
    v = _ask_text(t("enter_budget_optional", lang), default="")
    if v is None:
        return None
    return {"budget": float(v) if v.strip() else None}


def _ask_topic(lang: str) -> dict | None:
    v = _ask_text(t("prompt_topic", lang), default="")
    if v is None:
        return None
    return {"topic": v.strip() or None}


def _ask_vibe(lang: str) -> dict | None:
    v = _ask_text(t("prompt_vibe", lang), default="")
    if v is None:
        return None
    return {"vibe": v.strip() or None}


def _ask_nights(lang: str) -> dict | None:
    v = _ask_text(t("prompt_nights", lang), default="2")
    if v is None:
        return None
    return {"nights": int(v) if v.strip() else 2}


def _ask_rooms(lang: str) -> dict | None:
    v = _ask_text(t("prompt_rooms", lang), default="1")
    if v is None:
        return None
    return {"rooms": int(v) if v.strip() else 1}


def _ask_amenities(lang: str) -> dict | None:
    v = _ask_text(t("prompt_amenities", lang), default="")
    if v is None:
        return None
    items = [s.strip() for s in (v or "").split(",") if s.strip()]
    return {"amenities": items}


def _ask_time_required(lang: str) -> dict | None:
    v = _ask_text(t("prompt_time_required", lang), default="")
    if v is None:
        return None
    try:
        hours = float(v) if v.strip() else None
    except ValueError:
        hours = None
    return {"time_hours": hours}


def _ask_indoor_outdoor(lang: str) -> dict | None:
    any_label = t("any_choice", lang)
    indoor_label = t("indoor", lang)
    outdoor_label = t("outdoor", lang)
    selected = questionary.select(
        t("prompt_indoor_outdoor", lang),
        choices=[any_label, indoor_label, outdoor_label],
    ).ask()
    if selected is None or selected == any_label:
        return {"indoor_outdoor": None}
    if selected == indoor_label:
        return {"indoor_outdoor": "indoor"}
    if selected == outdoor_label:
        return {"indoor_outdoor": "outdoor"}
    return {"indoor_outdoor": None}


def _ask_audience_prompt(lang: str) -> dict | None:
    return {"audience": _ask_audience(lang)}


def _ask_budget_tier(lang: str) -> dict | None:
    any_label = t("any_choice", lang)
    low_label = t("budget_low", lang)
    mid_label = t("budget_mid", lang)
    high_label = t("budget_high", lang)
    selected = questionary.select(
        t("prompt_budget_tier", lang),
        choices=[any_label, low_label, mid_label, high_label],
    ).ask()
    if selected is None:
        return None
    mapping = {any_label: None, low_label: 1, mid_label: 2, high_label: 3}
    return {"max_price": mapping.get(selected)}


CATEGORIES_WITH_INDOOR_OUTDOOR = frozenset(
    {"sights", "museums", "nature", "family", "nightlife"}
)
CATEGORIES_WITH_VIBE = frozenset({"nightlife", "food"})


def _ask_category_refinement(category_ids: list[str], lang: str) -> dict | None:
    """Ask a short, universal refinement set for the Browse-by-category path.

    Indoor/outdoor and vibe are only asked when at least one selected category
    can benefit; budget tier and audience are always asked.
    """
    prefs: dict = {"people": 2}
    cat_set = set(category_ids)

    audience_patch = _ask_audience_prompt(lang)
    if audience_patch is None:
        return None
    prefs.update(audience_patch)

    if cat_set & CATEGORIES_WITH_INDOOR_OUTDOOR:
        io = _ask_indoor_outdoor(lang)
        if io is None:
            return None
        prefs.update(io)

    tier = _ask_budget_tier(lang)
    if tier is None:
        return None
    prefs.update(tier)

    if cat_set & CATEGORIES_WITH_VIBE:
        vibe = _ask_vibe(lang)
        if vibe is None:
            return None
        prefs.update(vibe)

    return prefs


PROMPT_HANDLERS = {
    "cuisine": _ask_cuisine,
    "people": _ask_people,
    "budget": _ask_budget,
    "topic": _ask_topic,
    "vibe": _ask_vibe,
    "nights": _ask_nights,
    "rooms": _ask_rooms,
    "amenities": _ask_amenities,
    "time_required": _ask_time_required,
    "indoor_outdoor": _ask_indoor_outdoor,
    "audience": _ask_audience_prompt,
}


def _collect_prefs(types: list[str], lang: str) -> dict | None:
    prefs: dict = {}
    for key in prompts_for_types(types):
        handler = PROMPT_HANDLERS.get(key)
        if handler is None:
            continue
        patch = handler(lang)
        if patch is None:
            return None
        prefs.update(patch)
    return prefs


def _ask_profile(lang: str) -> str | None:
    labels = [(t(f"profile_{p}", lang), p) for p in PROFILE_ORDER]
    selected = questionary.select(
        t("select_profile", lang),
        choices=[l for l, _ in labels],
    ).ask()
    if selected is None:
        return None
    return dict(labels).get(selected)


def _ask_audience(lang: str) -> str | None:
    any_label = t("audience_any", lang)
    family_label = t("audience_family", lang)
    adult_label = t("audience_adult", lang)
    selected = questionary.select(
        t("prompt_audience", lang),
        choices=[any_label, family_label, adult_label],
    ).ask()
    if selected is None or selected == any_label:
        return None
    if selected == family_label:
        return "family"
    if selected == adult_label:
        return "adult"
    return None


PLACE_TYPE_CHOICES = [
    ("Restaurant", "restaurant"),
    ("Cafe", "cafe"),
    ("Museum", "museum"),
    ("Hotel", "lodging"),
    ("Tourist Attraction", "tourist_attraction"),
    ("Bar", "bar"),
]


def _localized_type_choices(lang: str):
    labels = {
        "Restaurant": ("Restaurant" if lang == "en" else "Restoran"),
        "Cafe": ("Cafe" if lang == "en" else "Kafe"),
        "Museum": ("Museum" if lang == "en" else "Müze"),
        "Hotel": ("Hotel" if lang == "en" else "Otel"),
        "Tourist Attraction": ("Tourist Attraction" if lang == "en" else "Turistik Yer"),
        "Bar": ("Bar" if lang == "en" else "Bar"),
    }
    result = []
    for display, value in PLACE_TYPE_CHOICES:
        result.append((labels[display], value))
    return result


def _is_quit(answer) -> bool:
    return answer is not None and answer.strip().lower() == "q"


def _prompt_continue(lang: str = "tr"):
    msg = "Press Enter to continue, q to quit..." if lang == "en" else "Devam etmek için Enter, çıkmak için q..."
    answer = questionary.text(msg, default="").ask()
    if _is_quit(answer):
        raise SystemExit(0)


def _ask_categories(lang: str = "tr") -> list[str] | None:
    from app.ui.display import show_info
    labels = [(t(f"category_{c}", lang), c) for c in CATEGORY_ORDER]
    choices = [label for label, _ in labels]
    label_to_id = dict(labels)
    for _ in range(2):
        selected = questionary.checkbox(
            t("select_categories", lang),
            choices=choices,
        ).ask()
        if selected is None:
            return None
        if selected:
            return [label_to_id[s] for s in selected]
        show_info(t("empty_selection_hint", lang))
    return None


def _ask_place_types(lang: str = "tr") -> list[str] | None:
    choices = _localized_type_choices(lang)
    display_names = [c[0] for c in choices]

    single_label = "Single type" if lang == "en" else "Tek tür"
    multi_label = "Multiple types" if lang == "en" else "Birden fazla tür"
    skip_label = "Skip" if lang == "en" else "Atla"

    mode = questionary.select(
        t("select_type_mode", lang),
        choices=[single_label, multi_label, skip_label],
    ).ask()
    if mode is None or mode == skip_label:
        return None

    value_map = {c[0]: c[1] for c in choices}

    if mode == single_label:
        selected = questionary.select(
            t("select_place_type", lang),
            choices=display_names,
        ).ask()
        if selected is None:
            return None
        return [value_map[selected]]

    from app.ui.display import show_info
    for _ in range(2):
        selected = questionary.checkbox(
            t("select_place_types", lang),
            choices=display_names,
        ).ask()
        if selected is None:
            return None
        if selected:
            return [value_map[s] for s in selected]
        show_info(t("empty_selection_hint", lang))
    return None
