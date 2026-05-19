from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
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
    if cat_id not in CATEGORIES:
        raise ValueError(f"Unknown category {cat_id!r}. Choices: {sorted(CATEGORIES.keys())}")
    return CATEGORIES[cat_id]
