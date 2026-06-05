"""Browsable categories that map friendly names to Google Places types.

Each ``Category`` (``food``, ``sights``, ``museums`` …) bundles the Google Place
types searched when the user browses by category rather than typing a specific
place type. ``recommend_by_categories`` in ``app/reviews/checker.py`` fans out
one search per category using these type tuples.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    """A browsable category: an id, the Google types it searches, and a keyword."""

    id: str
    google_types: tuple[str, ...]
    keyword: str | None = None


CATEGORIES: dict[str, Category] = {
    "food":      Category(id="food",      google_types=("restaurant", "cafe", "meal_takeaway")),
    "sights":    Category(id="sights",    google_types=("tourist_attraction", "landmark", "place_of_worship")),
    "museums":   Category(id="museums",   google_types=("museum", "art_gallery")),
    "nature":    Category(id="nature",    google_types=("park", "natural_feature", "campground")),
    "shopping":  Category(id="shopping",  google_types=("shopping_mall", "store", "clothing_store")),
    "nightlife": Category(id="nightlife", google_types=("bar", "night_club")),
    "family":    Category(id="family",    google_types=("amusement_park", "aquarium", "zoo", "park")),
    "lodging":   Category(id="lodging",   google_types=("lodging",)),
    "wellness":  Category(id="wellness",  google_types=("spa", "gym")),
}

CATEGORY_ORDER: tuple[str, ...] = (
    "food", "sights", "museums", "nature", "shopping", "nightlife", "family", "lodging", "wellness",
)


def get_category(cat_id: str) -> Category:
    """Look up a ``Category`` by id, raising ``ValueError`` if unknown."""
    if cat_id not in CATEGORIES:
        raise ValueError(f"Unknown category {cat_id!r}. Choices: {sorted(CATEGORIES.keys())}")
    return CATEGORIES[cat_id]
