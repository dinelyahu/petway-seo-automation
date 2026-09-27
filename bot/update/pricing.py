from bot.products.base import click_tab, fill_field


def update_pricing_tab(driver, product):

    if not product.get("price"):
        return

    click_tab(driver, "nav-price-tab")

    fill_field(driver, "item[price]", product["price"])

    if product.get("price_discount"):
        fill_field(driver, "item[price_discount]", product["price_discount"])

    print("✏️ מחיר עודכן")