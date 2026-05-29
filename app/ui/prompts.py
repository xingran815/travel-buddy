import questionary
from app.i18n.strings import t
from app.reviews.categories import CATEGORY_ORDER
from app.ui.type_prompts import prompts_for_types

PROFILE_ORDER = ("balanced", "foodie", "budget", "atmosphere")

_QUIT = object()


def _ask_text(label: str, default: str = "") -> str | None:
    value = questionary.text(label, default=default).ask()
    if value is None:
        return None
    if value.strip().lower() == "q":
        return None
    return value


def _parse_hours(v: str) -> float | None:
    try:
        return float(v) if v.strip() else None
    except ValueError:
        return None


# key -> (i18n label, result key, text default, parser applied to the raw answer)
_TEXT_PROMPTS: dict[str, tuple] = {
    "cuisine": ("prompt_cuisine", "cuisine", "", lambda v: v.strip() or None),
    "topic": ("prompt_topic", "topic", "", lambda v: v.strip() or None),
    "vibe": ("prompt_vibe", "vibe", "", lambda v: v.strip() or None),
    "people": ("prompt_people", "people", "2", lambda v: int(v) if v.strip() else 2),
    "nights": ("prompt_nights", "nights", "2", lambda v: int(v) if v.strip() else 2),
    "rooms": ("prompt_rooms", "rooms", "1", lambda v: int(v) if v.strip() else 1),
    "budget": ("enter_budget_optional", "budget", "", lambda v: float(v) if v.strip() else None),
    "amenities": ("prompt_amenities", "amenities", "", lambda v: [s.strip() for s in v.split(",") if s.strip()]),
    "time_required": ("prompt_time_required", "time_hours", "", _parse_hours),
}


def _make_text_handler(label_key: str, result_key: str, default: str, parse):
    """Build a handler that asks for text and returns ``{result_key: parse(value)}``,
    or ``None`` if the user cancels."""
    def handler(lang: str) -> dict | None:
        value = _ask_text(t(label_key, lang), default=default)
        return None if value is None else {result_key: parse(value)}
    return handler


_ask_vibe = _make_text_handler(*_TEXT_PROMPTS["vibe"])


def _ask_choice(prompt_key: str, options: list[tuple[str, object]], lang: str) -> object:
    """Ask a single-select question. ``options`` is (i18n label, value) pairs; the
    first pair is the default value returned when the user picks it or cancels."""
    labels = [(t(label_key, lang), value) for label_key, value in options]
    selected = questionary.select(t(prompt_key, lang), choices=[label for label, _ in labels]).ask()
    if selected is None:
        return options[0][1]
    return dict(labels).get(selected, options[0][1])


def _ask_indoor_outdoor(lang: str) -> dict | None:
    value = _ask_choice(
        "prompt_indoor_outdoor",
        [("any_choice", None), ("indoor", "indoor"), ("outdoor", "outdoor")],
        lang,
    )
    return {"indoor_outdoor": value}


def _ask_audience(lang: str) -> str | None:
    return _ask_choice(
        "prompt_audience",
        [("audience_any", None), ("audience_family", "family"), ("audience_adult", "adult")],
        lang,
    )


def _ask_audience_prompt(lang: str) -> dict | None:
    return {"audience": _ask_audience(lang)}


CATEGORIES_WITH_INDOOR_OUTDOOR = frozenset(
    {"sights", "museums", "nature", "family", "nightlife"}
)
CATEGORIES_WITH_VIBE = frozenset({"nightlife", "food"})


def _build_filter_choices(
    category_ids: list[str], profile: str, lang: str
) -> tuple[list, dict[str, tuple[str, object]]]:
    """Build checkbox choices and a mapping from label → (pref_key, value)."""
    choices: list = []
    mapping: dict[str, tuple[str, object]] = {}
    cat_set = set(category_ids)

    if "family" not in cat_set:
        choices.append(questionary.Separator(f"── {t('filter_group_audience', lang)} ──"))
        for key_suffix, pref_val in (("family", "family"), ("adult", "adult")):
            label = t(f"audience_{key_suffix}", lang)
            choices.append(label)
            mapping[label] = ("audience", pref_val)

    if cat_set & CATEGORIES_WITH_INDOOR_OUTDOOR:
        choices.append(questionary.Separator(f"── {t('filter_group_setting', lang)} ──"))
        for key_suffix, pref_val in (("indoor", "indoor"), ("outdoor", "outdoor")):
            label = t(key_suffix, lang)
            choices.append(label)
            mapping[label] = ("indoor_outdoor", pref_val)

    if profile != "budget":
        choices.append(questionary.Separator(f"── {t('filter_group_budget', lang)} ──"))
        for key_suffix, price in (("low", 1), ("mid", 2), ("high", 3)):
            label = t(f"budget_{key_suffix}", lang)
            choices.append(label)
            mapping[label] = ("max_price", price)

    return choices, mapping


def _has_conflicts(selected: list[str], mapping: dict[str, tuple[str, object]]) -> bool:
    seen_keys: dict[str, int] = {}
    for label in selected:
        key, _ = mapping[label]
        seen_keys[key] = seen_keys.get(key, 0) + 1
    return any(v > 1 for v in seen_keys.values())


def _ask_category_refinement(
    category_ids: list[str], profile: str, lang: str
) -> dict | None:
    """Collect shared filters for a category browse, returning a prefs dict (or None
    if cancelled). The checkbox is re-asked once if the picks conflict (e.g. two
    budget tiers); a second conflict aborts."""
    prefs: dict = {"people": 2}
    cat_set = set(category_ids)

    if "family" in cat_set:
        prefs["audience"] = "family"

    choices, mapping = _build_filter_choices(category_ids, profile, lang)

    if choices:
        from app.ui.display import show_info
        for _ in range(2):
            selected = questionary.checkbox(
                t("prompt_filters", lang),
                choices=choices,
            ).ask()
            if selected is None:
                return None
            if not _has_conflicts(selected, mapping):
                break
            show_info(t("filter_conflict_hint", lang))
        else:
            return None
        for label in selected:
            key, value = mapping[label]
            prefs[key] = value

    if cat_set & CATEGORIES_WITH_VIBE:
        vibe = _ask_vibe(lang)
        if vibe is None:
            return None
        prefs.update(vibe)

    return prefs


PROMPT_HANDLERS = {key: _make_text_handler(*spec) for key, spec in _TEXT_PROMPTS.items()}
PROMPT_HANDLERS["indoor_outdoor"] = _ask_indoor_outdoor
PROMPT_HANDLERS["audience"] = _ask_audience_prompt


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
    return [(labels[display], value) for display, value in PLACE_TYPE_CHOICES]


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
