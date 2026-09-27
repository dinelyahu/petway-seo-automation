from .variation_create import create_variation
from .deal_label import update_deal_label


def create_deal_variation(driver, variation):

    title = variation.get("title")
    weight = variation.get("weight")
    price = variation.get("price")
    units = variation.get("units", 2)

    print(f"💥 יוצר דיל: {title}")

    # קביעת הטקסט של הלייבל
    if units == 2:
        label = "💥דיל זוגות"
    else:
        label = f"💥דיל {units} יחידות"

    create_variation(driver, {
        "title": title,
        "price": price,
        "price_discount": variation.get("price_discount", ""),
        "weight": weight
    })

    # מעבר לטאב מידע והכנסת הלייבל
    update_deal_label(driver, label)