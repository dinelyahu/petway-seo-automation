from bot.products.assignments import fill_assignments_tab


def update_assignments_tab(driver, product):

    if not product.get("category_ids"):
        return

    fill_assignments_tab(driver, product)

    print("✏️ קטגוריות עודכנו")