"""
X-Store 应用商店
"""

from .catalog import (
    BUILTIN_APPS,
    load_ratings, save_ratings, rate_app, get_rating,
    load_custom, save_custom, add_custom, remove_custom,
    get_all_apps, get_categories, get_apps_by_category,
    get_top_apps, search_apps, get_app_detail,
    ensure_dirs,
    STORE_DIR, CATALOG_FILE, RATINGS_FILE, CUSTOM_FILE,
)

__all__ = [
    "BUILTIN_APPS",
    "load_ratings", "save_ratings", "rate_app", "get_rating",
    "load_custom", "save_custom", "add_custom", "remove_custom",
    "get_all_apps", "get_categories", "get_apps_by_category",
    "get_top_apps", "search_apps", "get_app_detail",
    "ensure_dirs",
    "STORE_DIR", "CATALOG_FILE", "RATINGS_FILE", "CUSTOM_FILE",
]
