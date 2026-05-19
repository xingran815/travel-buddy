import questionary
from app.i18n.strings import t
from app.ui.display import (
    show_welcome,
    show_translation,
    show_summary,
    show_recommendations,
    show_categorized_recommendations,
    show_plan,
    show_error,
    show_info,
    show_success,
)
from app.youtube.downloader import download_audio, get_video_title, cleanup
from app.youtube.transcriber import transcribe
from app.llm.client import translate_to_turkish, summarize_in_turkish
from app.reviews.checker import recommend_places, recommend_by_categories
from app.reviews.profiles import DEFAULT_PROFILE
from app.planner.generator import generate_plan
from app.profile.store import load_profile
from app.ui.prompts import (
    _ask_categories, _ask_place_types, _ask_profile,
    _collect_prefs, _is_quit, _prompt_continue,
)


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

    by_types_label = "Browse by place type" if lang == "en" else "Yer türüne göre"
    by_cats_label = "Browse by category" if lang == "en" else "Kategoriye göre"
    mode = questionary.select(
        "How to browse?" if lang == "en" else "Nasıl gezineyim?",
        choices=[by_types_label, by_cats_label],
    ).ask()
    if mode is None:
        return

    count_choices = ["3", "5", "10"]

    if mode == by_cats_label:
        category_ids = _ask_categories(lang)
        if not category_ids:
            return
        top_str = questionary.select(
            "How many per category?" if lang == "en" else "Kategori başına kaç tane?",
            choices=count_choices,
        ).ask()
        if top_str is None:
            return
        top_n_per = int(top_str)
        profile = _ask_profile(lang) or DEFAULT_PROFILE
        # Use neutral prompts (audience + people + budget) when not single-type.
        prefs = _collect_prefs([], lang)
        if prefs is None:
            return
        show_info(t("fetching_reviews", lang, region=region))
        results_by_cat = recommend_by_categories(
            region,
            category_ids,
            top_n_per=top_n_per,
            budget=prefs.get("budget"),
            profile=profile,
            cuisine=prefs.get("cuisine"),
            audience=prefs.get("audience"),
            people=prefs.get("people", 2),
            user_profile=load_profile(),
        )
        total = sum(len(v) for v in results_by_cat.values())
        show_success(t("reviews_done", lang, count=total))
        show_categorized_recommendations(results_by_cat, lang)
        return

    place_types = _ask_place_types(lang)
    if place_types is None:
        return

    top_str = questionary.select(
        "How many?" if lang == "en" else "Kaç tane?",
        choices=count_choices,
    ).ask()
    if top_str is None:
        return
    top_n = int(top_str)

    profile = _ask_profile(lang) or DEFAULT_PROFILE

    prefs = _collect_prefs(place_types, lang)
    if prefs is None:
        return

    show_info(t("fetching_reviews", lang, region=region))
    results = recommend_places(
        region,
        place_type=place_types[0] if len(place_types) == 1 else "restaurant",
        place_types=place_types,
        top_n=top_n,
        budget=prefs.get("budget"),
        profile=profile,
        cuisine=prefs.get("cuisine"),
        audience=prefs.get("audience"),
        people=prefs.get("people", 2),
        user_profile=load_profile(),
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
        ("Preferences (comma separated, enter to skip):" if lang == "en"
         else "Tercihler (virgülle ayırın, atlamak için Enter):"),
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
        profile = _ask_profile(lang) or DEFAULT_PROFILE
        prefs = _collect_prefs(place_types, lang)
        if prefs is None:
            return
        show_info(t("fetching_reviews", lang, region=region))
        review_results = recommend_places(
            region,
            place_type=place_types[0] if len(place_types) == 1 else "restaurant",
            place_types=place_types,
            top_n=5,
            budget=prefs.get("budget", budget),
            profile=profile,
            cuisine=prefs.get("cuisine"),
            audience=prefs.get("audience"),
            people=prefs.get("people", 2),
            user_profile=load_profile(),
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


def run_settings(_lang: str) -> str:
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
