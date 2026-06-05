"""Argument-parsing and pretty-printing helpers for the CLI commands."""

import click
from app.i18n.strings import t
from app.reviews.profiles import FACTOR_KEYS


def _parse_types(types_str: str | None) -> list[str] | None:
    """Split a comma-separated ``--types`` string into a list, or ``None``."""
    if not types_str:
        return None
    return [t.strip() for t in types_str.split(",") if t.strip()]


def _parse_location(location_str: str | None) -> tuple[float, float] | None:
    """Parse a ``"lat,lng"`` string into a float tuple; raise on bad format."""
    if not location_str:
        return None
    parts = location_str.split(",")
    if len(parts) != 2:
        raise click.BadParameter("Location must be 'lat,lng' format")
    return (float(parts[0].strip()), float(parts[1].strip()))


def _format_breakdown(breakdown: dict, lang: str) -> str:
    """Render the per-factor score contributions as a localized ``·``-joined line."""
    parts = []
    for k in FACTOR_KEYS:
        label = t(f"factor_{k}", lang)
        parts.append(f"{label} {breakdown.get(k, 0.0):.2f}")
    return " · ".join(parts)


def _print_place(i: int, r: dict, lang: str) -> None:
    """Print one ranked place: score, rating, address, breakdown, and LLM notes.

    Falls back to showing the top few raw reviews only when no LLM pros/cons are
    present."""
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
