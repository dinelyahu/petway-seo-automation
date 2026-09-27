from .content import update_content_tab
from .info import update_info_tab
from .variations import apply_variations
from .pricing import update_pricing_tab
from .assignments import update_assignments_tab


def update_product(driver, product):

    print("🔄 מעדכן מוצר קיים")

    update_content_tab(driver, product)
    update_info_tab(driver, product)

    apply_variations(driver, product.get("variations", []))

    update_pricing_tab(driver, product)
    update_assignments_tab(driver, product)

    print("✅ עדכון הסתיים")