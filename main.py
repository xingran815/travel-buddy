import os
import sys
import click
from app.i18n.strings import t
from app.config import APP_LANG
from app.youtube.downloader import download_audio, get_video_title, cleanup
from app.youtube.transcriber import transcribe
from app.llm.client import translate_to_turkish, summarize_in_turkish
from app.reviews.checker import recommend_places
from app.reviews.profiles import PROFILES, DEFAULT_PROFILE
from app.planner.generator import generate_plan


FACTOR_DISPLAY_ORDER = ("quality", "volume", "distance", "cost", "recency", "sentiment", "audience", "cuisine", "aspects")


@click.group(invoke_without_command=True)
@click.option("--lang", default=APP_LANG, type=click.Choice(["en", "tr"]), help="Interface language")
@click.pass_context
def cli(ctx, lang):
    ctx.ensure_object(dict)
    ctx.obj["lang"] = lang
    if ctx.invoked_subcommand is None:
        from app.ui.menu import run_main_menu
        run_main_menu()


def _parse_types(types_str: str | None) -> list[str] | None:
    if not types_str:
        return None
    return [t.strip() for t in types_str.split(",") if t.strip()]


def _parse_location(location_str: str | None) -> tuple[float, float] | None:
    if not location_str:
        return None
    parts = location_str.split(",")
    if len(parts) != 2:
        raise click.BadParameter("Location must be 'lat,lng' format")
    return (float(parts[0].strip()), float(parts[1].strip()))


@cli.command()
@click.argument("url")
@click.pass_context
def summarize(ctx, url):
    lang = ctx.obj["lang"]
    click.echo(t("welcome", lang))

    click.echo(t("downloading", lang))
    audio_path, video_id = download_audio(url)
    click.echo(t("download_done", lang))

    title = get_video_title(url)
    click.echo(f"  {title}")

    click.echo(t("transcribing", lang))
    result = transcribe(audio_path)
    click.echo(t("transcribe_done", lang))
    click.echo(f"  ({result['language']})")

    click.echo(t("translating", lang))
    turkish_text = translate_to_turkish(result["text"], result["language"])
    click.echo(t("translate_done", lang))

    click.echo(t("summarizing", lang))
    summary = summarize_in_turkish(turkish_text)
    click.echo(t("summarize_done", lang))

    cleanup(video_id)

    click.echo()
    click.echo(t("header_translation", lang))
    click.echo(turkish_text)

    click.echo()
    click.echo(t("header_summary", lang))
    click.echo(summary)


def _format_breakdown(breakdown: dict, lang: str) -> str:
    parts = []
    for k in FACTOR_DISPLAY_ORDER:
        label = t(f"factor_{k}", lang)
        parts.append(f"{label} {breakdown.get(k, 0.0):.2f}")
    return " · ".join(parts)


@cli.command()
@click.argument("region")
@click.option("--type", "place_type", default="restaurant", help="Place type (restaurant, museum, etc.)")
@click.option("--types", default=None, help="Comma-separated place types for diverse results (e.g. restaurant,tourist_attraction)")
@click.option("--top", default=5, help="Number of recommendations")
@click.option("--max-pages", default=1, help="Number of Google Places pages to fetch (1-3)")
@click.option("--min-price", default=None, type=int, help="Min price level (1-4)")
@click.option("--max-price", default=None, type=int, help="Max price level (1-4)")
@click.option("--budget", default=None, type=float, help="Budget in USD (auto-derives max price)")
@click.option("--location", default=None, help="Center point as 'lat,lng' for radius search")
@click.option("--radius", default=None, type=int, help="Search radius in meters (requires --location)")
@click.option("--no-details", is_flag=True, help="Skip detail fetching (faster, no reviews)")
@click.option("--profile", default=DEFAULT_PROFILE, type=click.Choice(sorted(PROFILES.keys())), help="Recommendation weight profile")
@click.option("--cuisine", default=None, help="Preferred cuisine (e.g. turkish, italian, seafood)")
@click.option("--audience", default=None, type=click.Choice(["family", "adult"]), help="Audience preference")
@click.option("--people", default=2, type=int, help="Number of people (affects cost fit)")
@click.option("--query", default=None, help="Free-form query for LLM parsing (e.g. 'romantic seafood with view')")
@click.option("--aspects", default=None, help="Comma-separated aspect tags (e.g. romantic,view,quiet)")
@click.option("--llm-parse", is_flag=True, help="Parse --query with LLM into structured prefs")
@click.option("--llm-rerank", is_flag=True, help="Use LLM to re-rank top-K results")
@click.option("--llm-summarize", is_flag=True, help="Use LLM to generate per-place pros/cons")
@click.option("--llm-aspects", is_flag=True, help="Use LLM to tag place aspects for scoring")
@click.option("--no-cache", is_flag=True, help="Bypass the local Google Places HTTP cache")
@click.pass_context
def recommend(ctx, region, place_type, types, top, max_pages, min_price, max_price, budget, location, radius, no_details, profile, cuisine, audience, people, query, aspects, llm_parse, llm_rerank, llm_summarize, llm_aspects, no_cache):
    lang = ctx.obj["lang"]
    if no_cache:
        os.environ["PLACES_CACHE"] = "off"
    click.echo(t("welcome", lang))
    click.echo(t("fetching_reviews", lang, region=region))

    parsed_types = _parse_types(types)
    parsed_location = _parse_location(location)
    parsed_aspects = [a.strip() for a in (aspects or "").split(",") if a.strip()] or None
    results = recommend_places(
        region,
        place_type=place_type,
        place_types=parsed_types,
        top_n=top,
        max_pages=max_pages,
        min_price=min_price,
        max_price=max_price,
        budget=budget,
        location=parsed_location,
        radius=radius,
        include_details=not no_details,
        profile=profile,
        cuisine=cuisine,
        audience=audience,
        people=people,
        query=query,
        aspects=parsed_aspects,
        llm_parse=llm_parse,
        llm_rerank=llm_rerank,
        llm_summarize=llm_summarize,
        llm_aspects=llm_aspects,
        lang=lang,
    )
    click.echo(t("reviews_done", lang, count=len(results)))

    click.echo()
    click.echo(t("header_recommendations", lang))
    if results and results[0].get("d_half_km") is not None:
        click.echo(f"  {t('label_distance_scale', lang)}: {results[0]['d_half_km']:.1f} km")
    for i, r in enumerate(results, 1):
        click.echo(f"\n{i}. {r['name']} — ★ {r.get('score', 0):.2f} / 5")
        click.echo(f"   {'Rating' if lang == 'en' else 'Puan'}: {r.get('rating', 'N/A')}/5")
        click.echo(f"   {'Address' if lang == 'en' else 'Adres'}: {r.get('address', 'N/A')}")
        meta_parts = []
        if r.get("price_level"):
            meta_parts.append(f"{'Price' if lang == 'en' else 'Fiyat'}: {'$' * r['price_level']}")
        if r.get("distance_km") is not None:
            meta_parts.append(f"{t('label_distance', lang)}: {r['distance_km']:.1f} km")
        if r.get("user_ratings_total"):
            meta_parts.append(f"{r['user_ratings_total']} {t('label_reviews', lang).lower()}")
        if meta_parts:
            click.echo("   " + " · ".join(meta_parts))
        if r.get("website"):
            click.echo(f"   {'Website' if lang == 'en' else 'Web sitesi'}: {r['website']}")
        if r.get("score_breakdown"):
            click.echo(f"   {t('label_breakdown', lang)}: {_format_breakdown(r['score_breakdown'], lang)}")
        if r.get("llm_rationale"):
            click.echo(f"   {t('label_llm_rationale', lang)}: {r['llm_rationale']}")
        pros = r.get("pros") or []
        cons = r.get("cons") or []
        if pros:
            click.echo(f"   {t('label_pros', lang)}: {'; '.join(pros)}")
        if cons:
            click.echo(f"   {t('label_cons', lang)}: {'; '.join(cons)}")
        if r.get("reviews") and not pros and not cons:
            click.echo(f"   {'Top reviews' if lang == 'en' else 'Yorumlar'}:")
            for rev in r["reviews"][:3]:
                click.echo(f"     - {rev['author']} ({rev['rating']}/5): {rev['text'][:80]}...")


@cli.command()
@click.argument("region")
@click.option("--budget", default=500, help="Budget in USD")
@click.option("--days", default=3, help="Number of days")
@click.option("--preferences", default="", help="Comma-separated preferences (e.g. history,food)")
@click.option("--url", default=None, help="YouTube video URL for destination info")
@click.option("--place-type", default="restaurant", help="Place type for recommendations")
@click.option("--types", default=None, help="Comma-separated place types for diverse recommendations")
@click.option("--top", default=5, help="Number of place recommendations to include")
@click.option("--max-pages", default=1, help="Number of Google Places pages to fetch")
@click.option("--min-price", default=None, type=int, help="Min price level (1-4)")
@click.option("--max-price", default=None, type=int, help="Max price level (1-4)")
@click.option("--location", default=None, help="Center point as 'lat,lng' for radius search")
@click.option("--radius", default=None, type=int, help="Search radius in meters (requires --location)")
@click.option("--profile", default=DEFAULT_PROFILE, type=click.Choice(sorted(PROFILES.keys())), help="Recommendation weight profile")
@click.option("--cuisine", default=None, help="Preferred cuisine (e.g. turkish, italian, seafood)")
@click.option("--audience", default=None, type=click.Choice(["family", "adult"]), help="Audience preference")
@click.option("--people", default=2, type=int, help="Number of people (affects cost fit)")
@click.option("--query", default=None, help="Free-form query for LLM parsing")
@click.option("--aspects", default=None, help="Comma-separated aspect tags (e.g. romantic,view,quiet)")
@click.option("--llm-parse", is_flag=True, help="Parse --query with LLM into structured prefs")
@click.option("--llm-rerank", is_flag=True, help="Use LLM to re-rank top-K results")
@click.option("--llm-summarize", is_flag=True, help="Use LLM to generate per-place pros/cons")
@click.option("--llm-aspects", is_flag=True, help="Use LLM to tag place aspects for scoring")
@click.option("--no-cache", is_flag=True, help="Bypass the local Google Places HTTP cache")
@click.pass_context
def plan(ctx, region, budget, days, preferences, url, place_type, types, top, max_pages, min_price, max_price, location, radius, profile, cuisine, audience, people, query, aspects, llm_parse, llm_rerank, llm_summarize, llm_aspects, no_cache):
    lang = ctx.obj["lang"]
    if no_cache:
        os.environ["PLACES_CACHE"] = "off"
    click.echo(t("welcome", lang))

    youtube_summary = ""
    if url:
        click.echo(t("downloading", lang))
        audio_path, video_id = download_audio(url)
        click.echo(t("transcribing", lang))
        result = transcribe(audio_path)
        click.echo(t("translating", lang))
        turkish_text = translate_to_turkish(result["text"], result["language"])
        click.echo(t("summarizing", lang))
        youtube_summary = summarize_in_turkish(turkish_text)
        click.echo(t("summarize_done", lang))
        cleanup(video_id)

        click.echo()
        click.echo(t("header_translation", lang))
        click.echo(turkish_text)
        click.echo()
        click.echo(t("header_summary", lang))
        click.echo(youtube_summary)

    click.echo(t("fetching_reviews", lang, region=region))
    parsed_types = _parse_types(types)
    parsed_location = _parse_location(location)
    parsed_aspects_plan = [a.strip() for a in (aspects or "").split(",") if a.strip()] or None

    review_results = recommend_places(
        region,
        place_type=place_type,
        place_types=parsed_types,
        top_n=top,
        max_pages=max_pages,
        min_price=min_price,
        max_price=max_price,
        budget=budget,
        location=parsed_location,
        radius=radius,
        profile=profile,
        cuisine=cuisine,
        audience=audience,
        people=people,
        query=query,
        aspects=parsed_aspects_plan,
        llm_parse=llm_parse,
        llm_rerank=llm_rerank,
        llm_summarize=llm_summarize,
        llm_aspects=llm_aspects,
        lang=lang,
    )
    click.echo(t("reviews_done", lang, count=len(review_results)))

    click.echo(t("generating_plan", lang))
    itinerary = generate_plan(
        destination=region,
        budget=budget,
        days=days,
        preferences=preferences,
        youtube_summary=youtube_summary,
        review_results=review_results,
        lang=lang,
    )
    click.echo(t("plan_done", lang))

    click.echo()
    click.echo(t("header_plan", lang))
    click.echo(itinerary)


if __name__ == "__main__":
    cli()
