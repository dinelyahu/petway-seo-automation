"""
pricing.py – טאב מחירים: מחיר בסיס, מחיר מבצע, מלאי
"""

from .base import click_tab, fill_field


def fill_pricing_tab(driver, product):
    """מלא טאב מחירים: מחיר, מחיר מבצע, מלאי."""
    if not any(product.get(k) for k in ["price", "price_discount", "stock"]):
        return

    click_tab(driver, "nav-price-tab")

    if product.get("price"):
        fill_field(driver, "item[price]", product["price"])
        print("✅ מחיר")

    if product.get("price_discount"):
        fill_field(driver, "item[price_discount]", product["price_discount"])
        print("✅ מחיר מבצע")

    if product.get("stock"):
        fill_field(driver, "item[stock]", product["stock"])
        print("✅ מלאי")
