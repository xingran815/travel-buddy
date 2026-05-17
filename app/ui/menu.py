import questionary
from app.i18n.strings import t
from app.ui.display import (
    show_welcome,
    show_translation,
    show_summary,
    show_recommendations,
    show_plan,
    show_error,
    show_info,
    show_success,
)
from app.youtube.downloader import download_audio, get_video_title, cleanup
from app.youtube.transcriber import transcribe
from app.llm.client import translate_to_turkish, summarize_in_turkish
from app.reviews.checker import recommend_places
from app.planner.generator import generate_plan


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
    else:
        selected = questionary.checkbox(
            t("select_place_types", lang),
            choices=display_names,
        ).ask()
        if not selected:
            return None
        return [value_map[s] for s in selected]


def run_summarize(lang: str = "tr"):
    url = questionary.text(
        "YouTube URL (q to go back):" if lang == "en" else "YouTube URL (geri dönmek için q):",
    ).ask()
    if _is_quit(url) or not url:
        return

    show_info(t("downloading", lang))
    audio_path, video_id = download_audio(url)
    show_success(t("download_done", lang))

    title = get_video_title(url)
    show_info(f"  {title}")

    show_info(t("transcribing", lang))
    result = transcribe(audio_path)
    show_success(t("transcribe_done", lang))
    show_info(f"  ({result['language']})")

    show_info(t("translating", lang))
    turkish_text = translate_to_turkish(result["text"], result["language"])
    show_success(t("translate_done", lang))

    show_info(t("summarizing", lang))
    summary = summarize_in_turkish(turkish_text)
    show_success(t("summarize_done", lang))

    cleanup(video_id)

    show_translation(turkish_text, lang)
    show_summary(summary, lang)


def run_recommend(lang: str = "tr"):
    region = questionary.text(
        "Region (q to go back):" if lang == "en" else "Bölge (geri dönmek için q):",
    ).ask()
    if _is_quit(region) or not region:
        return

    place_types = _ask_place_types(lang)
    if place_types is None:
        return

    count_choices = ["3", "5", "10"]
    top_str = questionary.select(
        "How many?" if lang == "en" else "Kaç tane?",
        choices=count_choices,
    ).ask()
    if top_str is None:
        return
    top_n = int(top_str)

    budget_str = questionary.text(
        "Budget in USD (enter to skip):" if lang == "en" else "Bütçe USD (atlamak için Enter):",
        default="",
    ).ask()
    if _is_quit(budget_str):
        return
    budget = float(budget_str) if budget_str else None

    show_info(t("fetching_reviews", lang, region=region))
    results = recommend_places(
        region,
        place_type=place_types[0] if len(place_types) == 1 else "restaurant",
        place_types=place_types,
        top_n=top_n,
        budget=budget,
    )
    show_success(t("reviews_done", lang, count=len(results)))

    show_recommendations(results, lang)


def run_plan(lang: str = "tr"):
    region = questionary.text(
        "Region (q to go back):" if lang == "en" else "Bölge (geri dönmek için q):",
    ).ask()
    if _is_quit(region) or not region:
        return

    budget_str = questionary.text(
        "Budget (USD):" if lang == "en" else "Bütçe (USD):",
        default="500",
    ).ask()
    if _is_quit(budget_str):
        return
    budget = float(budget_str) if budget_str else 500

    days_str = questionary.text(
        "Days:" if lang == "en" else "Gün sayısı:",
        default="3",
    ).ask()
    if _is_quit(days_str):
        return
    days = int(days_str) if days_str else 3

    preferences = questionary.text(
        "Preferences (comma separated, enter to skip):" if lang == "en" else "Tercihler (virgülle ayırın, atlamak için Enter):",
        default="",
    ).ask()
    if _is_quit(preferences):
        return
    preferences = preferences or ""

    url = questionary.text(
        "YouTube URL (enter to skip):" if lang == "en" else "YouTube URL (atlamak için Enter):",
        default="",
    ).ask()
    if _is_quit(url):
        return

    youtube_summary = ""
    if url and url.strip():
        show_info(t("downloading", lang))
        audio_path, video_id = download_audio(url)
        show_info(t("transcribing", lang))
        result = transcribe(audio_path)
        show_info(t("translating", lang))
        turkish_text = translate_to_turkish(result["text"], result["language"])
        show_info(t("summarizing", lang))
        youtube_summary = summarize_in_turkish(turkish_text)
        show_success(t("summarize_done", lang))
        cleanup(video_id)

        show_translation(turkish_text, lang)
        show_summary(youtube_summary, lang)

    place_types = _ask_place_types(lang)
    review_results = []
    if place_types:
        show_info(t("fetching_reviews", lang, region=region))
        review_results = recommend_places(
            region,
            place_type=place_types[0] if len(place_types) == 1 else "restaurant",
            place_types=place_types,
            top_n=5,
            budget=budget,
        )
        show_success(t("reviews_done", lang, count=len(review_results)))
        show_recommendations(review_results, lang)

    show_info(t("generating_plan", lang))
    itinerary = generate_plan(
        destination=region,
        budget=budget,
        days=days,
        preferences=preferences,
        youtube_summary=youtube_summary,
        review_results=review_results,
        lang=lang,
    )
    show_success(t("plan_done", lang))
    show_plan(itinerary, lang)


def run_settings(lang: str) -> str:
    choices = ["English", "Türkçe"]
    selected = questionary.select(
        "Language / Dil:",
        choices=choices,
    ).ask()
    if selected == "English":
        return "en"
    return "tr"


def run_main_menu():
    lang = "tr"
    while True:
        show_welcome(lang)

        choices = [
            "1. " + ("Summarize YouTube Video" if lang == "en" else "YouTube Videosu Özetle"),
            "2. " + ("Get Place Recommendations" if lang == "en" else "Yer Önerileri Al"),
            "3. " + ("Create Travel Plan" if lang == "en" else "Seyahat Planı Oluştur"),
            "4. " + ("Settings" if lang == "en" else "Ayarlar"),
            "q. " + ("Quit" if lang == "en" else "Çıkış"),
        ]

        answer = questionary.select(
            "",
            choices=choices,
        ).ask()

        if answer is None or answer.startswith("q"):
            break

        try:
            if answer.startswith("1"):
                run_summarize(lang)
            elif answer.startswith("2"):
                run_recommend(lang)
            elif answer.startswith("3"):
                run_plan(lang)
            elif answer.startswith("4"):
                lang = run_settings(lang)
                show_success(t("lang_set", lang))
                continue
        except SystemExit:
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            show_error(str(e))

        try:
            _prompt_continue(lang)
        except (SystemExit, KeyboardInterrupt):
            break

    from rich.console import Console
    Console().print(
        "Goodbye! / Hoşça kalın! 👋"
    )
