from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.text import Text

console = Console()


def show_welcome(lang: str = "tr"):
    from app.i18n.strings import t
    title = "🌍 Travel Recommender" if lang == "en" else "🌍 Seyahat Öneri"
    console.print(Panel(title, style="bold cyan", padding=(1, 2)))


def show_translation(text: str, lang: str = "tr"):
    from app.i18n.strings import t
    header = t("header_translation", lang)
    console.print()
    console.print(Panel(text, title=header, border_style="green", padding=(1, 2)))


def show_summary(text: str, lang: str = "tr"):
    from app.i18n.strings import t
    header = t("header_summary", lang)
    console.print()
    console.print(Panel(Markdown(text), title=header, border_style="yellow", padding=(1, 2)))


def show_recommendations(places: list[dict], lang: str = "tr"):
    from app.i18n.strings import t
    header = t("header_recommendations", lang)

    table = Table(title=header, show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Name" if lang == "en" else "İsim", style="bold")
    table.add_column("Rating" if lang == "en" else "Puan", justify="center")
    table.add_column("Address" if lang == "en" else "Adres")
    table.add_column("Price" if lang == "en" else "Fiyat", justify="center")

    for i, place in enumerate(places, 1):
        rating = str(place.get("rating", "N/A"))
        name = place.get("name", "")
        address = place.get("address", "")
        price_level = place.get("price_level")
        price = "$" * price_level if price_level else "-"
        table.add_row(str(i), name, rating, address, price)

    console.print()
    console.print(table)

    for place in places:
        reviews = place.get("reviews", [])
        if reviews:
            console.print(f"\n  [bold]{place['name']}[/bold] — {'Reviews' if lang == 'en' else 'Yorumlar'}:")
            for rev in reviews[:3]:
                stars = "⭐" * rev.get("rating", 0)
                console.print(f"    {stars} [dim]{rev.get('author', '')}[/dim]: {rev.get('text', '')[:120]}")


def show_plan(plan_text: str, lang: str = "tr"):
    from app.i18n.strings import t
    header = t("header_plan", lang)
    console.print()
    console.print(Panel(Markdown(plan_text), title=header, border_style="magenta", padding=(1, 2)))


def show_error(message: str):
    console.print(f"[bold red]✗ {message}[/bold red]")


def show_info(message: str):
    console.print(f"[dim]{message}[/dim]")


def show_success(message: str):
    console.print(f"[bold green]✓ {message}[/bold green]")
