from bot.products.base import click_tab, fill_field


def update_content_tab(driver, product):

    if not product.get("title"):
        return

    click_tab(driver, "nav-content-tab")

    fill_field(driver, "item[title]", product["title"])

    if product.get("desc"):
        fill_field(driver, "item[desc]", product["desc"])

    print("✏️ תוכן עודכן")