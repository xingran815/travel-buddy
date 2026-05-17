import os
import click
from app.i18n.strings import t
from app.config import APP_LANG
from app.youtube.downloader import download_audio, get_video_title
from app.youtube.transcriber import transcribe
from app.llm.client import translate_to_turkish, summarize_in_turkish
from app.reviews.checker import recommend_places
from app.planner.generator import generate_plan


@click.group()
@click.option("--lang", default=APP_LANG, type=click.Choice(["en", "tr"]), help="Interface language")
@click.pass_context
def cli(ctx, lang):
    ctx.ensure_object(dict)
    ctx.obj["lang"] = lang


@cli.command()
@click.argument("url")
@click.pass_context
def summarize(ctx, url):
    lang = ctx.obj["lang"]
    click.echo(t("welcome", lang))

    click.echo(t("downloading", lang))
    audio_path = download_audio(url)
    click.echo(t("download_done", lang))

    title = get_video_title(url)
    click.echo(f"  {title}" if lang == "en" else f"  {title}")

    click.echo(t("transcribing", lang))
    result = transcribe(audio_path)
    click.echo(t("transcribe_done", lang))
    click.echo(f"  ({result['language']})" if lang == "en" else f"  ({result['language']})")

    click.echo(t("translating", lang))
    turkish_text = translate_to_turkish(result["text"], result["language"])
    click.echo(t("translate_done", lang))

    click.echo(t("summarizing", lang))
    summary = summarize_in_turkish(turkish_text)
    click.echo(t("summarize_done", lang))

    click.echo()
    click.echo(t("header_summary", lang))
    click.echo(summary)

    if os.path.exists(audio_path):
        os.remove(audio_path)


@cli.command()
@click.argument("region")
@click.option("--type", "place_type", default="restaurant", help="Place type (restaurant, museum, etc.)")
@click.option("--top", default=5, help="Number of recommendations")
@click.pass_context
def recommend(ctx, region, place_type, top):
    lang = ctx.obj["lang"]
    click.echo(t("welcome", lang))
    click.echo(t("fetching_reviews", lang, region=region))

    results = recommend_places(region, place_type=place_type, top_n=top)
    click.echo(t("reviews_done", lang, count=len(results)))

    click.echo()
    click.echo(t("header_recommendations", lang))
    for i, r in enumerate(results, 1):
        click.echo(f"\n{i}. {r['name']}")
        click.echo(f"   {'Rating' if lang == 'en' else 'Puan'}: {r.get('rating', 'N/A')}/5")
        click.echo(f"   {'Address' if lang == 'en' else 'Adres'}: {r.get('address', 'N/A')}")
        if r.get("price_level"):
            click.echo(f"   {'Price level' if lang == 'en' else 'Fiyat seviyesi'}: {'$' * r['price_level']}")
        if r.get("website"):
            click.echo(f"   {'Website' if lang == 'en' else 'Web sitesi'}: {r['website']}")
        if r.get("reviews"):
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
@click.option("--top", default=5, help="Number of place recommendations to include")
@click.pass_context
def plan(ctx, region, budget, days, preferences, url, place_type, top):
    lang = ctx.obj["lang"]
    click.echo(t("welcome", lang))

    youtube_summary = ""
    if url:
        click.echo(t("downloading", lang))
        audio_path = download_audio(url)
        click.echo(t("transcribing", lang))
        result = transcribe(audio_path)
        click.echo(t("translating", lang))
        turkish_text = translate_to_turkish(result["text"], result["language"])
        click.echo(t("summarizing", lang))
        youtube_summary = summarize_in_turkish(turkish_text)
        click.echo(t("summarize_done", lang))
        if os.path.exists(audio_path):
            os.remove(audio_path)

    click.echo(t("fetching_reviews", lang, region=region))
    review_results = recommend_places(region, place_type=place_type, top_n=top)
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
