"""Rich-based rendering of CLI output: panels, recommendation tables, plans.

All user-facing formatting for the interactive menu lives here; strings are
localized through ``app.i18n.strings.t``. Functions print directly to a shared
``rich`` console and return nothing.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from app.reviews.profiles import FACTOR_KEYS

console = Console()


def show_welcome(lang: str = "tr"):
    """Print the welcome banner."""
    title = "🌍 Travel Recommender" if lang == "en" else "🌍 Seyahat Öneri"
    console.print(Panel(title, style="bold cyan", padding=(1, 2)))


def show_translation(text: str, lang: str = "tr"):
    """Render translated text in a titled panel."""
    from app.i18n.strings import t
    from app.llm.client import LANG_NAMES
    lang_name = LANG_NAMES.get(lang, "Turkish")
    header = t("header_translation", lang, lang_name=lang_name)
    console.print()
    console.print(Panel(text, title=header, border_style="green", padding=(1, 2)))


def show_summary(text: str, lang: str = "tr"):
    """Render a Markdown summary in a titled panel."""
    from app.i18n.strings import t
    header = t("header_summary", lang)
    console.print()
    console.print(Panel(Markdown(text), title=header, border_style="yellow", padding=(1, 2)))


def _format_breakdown(breakdown: dict[str, float], lang: str) -> str:
    """Render the score breakdown as percent-of-total contributions, largest first.

    Unlike the CLI helper of the same name, this normalises to percentages and
    drops factors contributing under 1%, for a compact at-a-glance view."""
    from app.i18n.strings import t
    total = sum(breakdown.values())
    if total <= 0:
        return ""
    items = []
    for k in FACTOR_KEYS:
        v = breakdown.get(k, 0.0)
        if v <= 0:
            continue
        pct = round(v / total * 100)
        if pct < 1:
            continue
        items.append((pct, t(f"factor_{k}", lang)))
    items.sort(key=lambda x: x[0], reverse=True)
    return " · ".join(f"{label} {pct}%" for pct, label in items)


def show_recommendations(places: list[dict], lang: str = "tr"):
    """Render ranked places as a table plus per-place breakdown, rationale, pros/cons.

    Falls back to a few raw review excerpts only when no LLM pros/cons exist."""
    from app.i18n.strings import t
    header = t("header_recommendations", lang)

    table = Table(title=header, show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Name" if lang == "en" else "İsim", style="bold")
    table.add_column(t("label_score", lang), justify="center")
    table.add_column("Rating" if lang == "en" else "Puan", justify="center")
    table.add_column(t("label_distance", lang), justify="right")
    table.add_column(t("label_reviews", lang), justify="right")
    table.add_column("Price" if lang == "en" else "Fiyat", justify="center")
    table.add_column("Address" if lang == "en" else "Adres")

    for i, place in enumerate(places, 1):
        score = place.get("score")
        score_str = f"{score:.2f}" if isinstance(score, (int, float)) else "-"
        rating = str(place.get("rating", "N/A"))
        name = place.get("name", "")
        address = place.get("address", "")
        price_level = place.get("price_level")
        if price_level:
            price = "$" * price_level
            if place.get("price_level_source") == "llm":
                price = f"{price} ({t('price_estimated', lang)})"
        else:
            price = "-"
        d = place.get("distance_km")
        distance = f"{d:.1f} km" if isinstance(d, (int, float)) else "-"
        n_reviews = place.get("user_ratings_total")
        n_reviews_str = f"{n_reviews:,}" if n_reviews else "-"
        table.add_row(str(i), name, score_str, rating, distance, n_reviews_str, price, address)

    console.print()
    if places and places[0].get("d_half_km") is not None:
        console.print(f"  [dim]{t('label_distance_scale', lang)}: {places[0]['d_half_km']:.1f} km[/dim]")
    console.print(table)

    for place in places:
        breakdown = place.get("score_breakdown")
        if breakdown:
            label = t("label_breakdown", lang)
            bd = _format_breakdown(breakdown, lang)
            console.print(f"\n  [bold]{place.get('name', '')}[/bold] — [dim]{label}:[/dim] {bd}")
        rationale = place.get("llm_rationale")
        if rationale:
            console.print(f"    [italic]{t('label_llm_rationale', lang)}:[/italic] {rationale}")
        pros = place.get("pros") or []
        cons = place.get("cons") or []
        if pros:
            console.print(f"    [green]{t('label_pros', lang)}:[/green]")
            for p in pros:
                console.print(f"      [green]✓[/green] {p}")
        if cons:
            console.print(f"    [red]{t('label_cons', lang)}:[/red]")
            for c in cons:
                console.print(f"      [red]✗[/red] {c}")
        reviews = place.get("reviews", [])
        if reviews and not pros and not cons:
            console.print(f"  [dim]{t('label_reviews', lang)}:[/dim]")
            for rev in reviews[:3]:
                stars = "⭐" * rev.get("rating", 0)
                text = (rev.get("text") or "")[:140]
                if len(rev.get("text") or "") > 140:
                    text = text[:text.rfind(" ")] + "…" if " " in text else text + "…"
                console.print(f"    {stars} [dim]{rev.get('author', '')}[/dim]: {text}")


def show_categorized_recommendations(results_by_category: dict[str, list[dict]], lang: str = "tr"):
    """Render each category as a labelled section of recommendation tables."""
    from app.i18n.strings import t
    for cat_id, places in results_by_category.items():
        label = t(f"category_{cat_id}", lang)
        console.print()
        console.print(Panel(label, style="bold cyan", padding=(0, 2)))
        if not places:
            console.print(f"  [dim]({'no results' if lang == 'en' else 'sonuç yok'})[/dim]")
            continue
        show_recommendations(places, lang)


def show_plan(plan_text: str, lang: str = "tr"):
    """Render the generated itinerary (Markdown) in a titled panel."""
    from app.i18n.strings import t
    header = t("header_plan", lang)
    console.print()
    console.print(Panel(Markdown(plan_text), title=header, border_style="magenta", padding=(1, 2)))


def show_error(message: str):
    """Print an error message in red."""
    console.print(f"[bold red]✗ {message}[/bold red]")


def show_info(message: str):
    """Print a dimmed informational message."""
    console.print(f"[dim]{message}[/dim]")


def show_success(message: str):
    """Print a success message in green."""
    console.print(f"[bold green]✓ {message}[/bold green]")
