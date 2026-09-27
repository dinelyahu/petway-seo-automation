"""
bot/products/__init__.py – ממשק ציבורי של חבילת products
"""

from .base import go_to_products, fill_field, select_by_name, select_by_value, click_tab
from .creator import create_product
from .assignments import fetch_categories_from_site
from .images import upload_images

__all__ = [
    "go_to_products",
    "create_product",
    "fetch_categories_from_site",
    "upload_images",
    # עזר
    "fill_field",
    "select_by_name",
    "select_by_value",
    "click_tab",
]
