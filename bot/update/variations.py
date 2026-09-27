from .variation_utils import open_variations_tab, variation_has_changes
from .variation_existing import update_existing_variation
from .variation_create import create_variation
from .variation_deals import create_deal_variation


def apply_variations(driver, variations):

    open_variations_tab(driver)

    if not variations:
        print("ℹ️ אין תכונות לעדכון")
        return

    for v in variations:

        # תכונה קיימת
        if v.get("id"):

            if variation_has_changes(v):
                update_existing_variation(driver, v)
            else:
                print(f"⏭️ אין שינוי בתכונה id={v.get('id')}")

        # דיל יחידות
        elif v.get("isDeal"):

            create_deal_variation(driver, v)

        # תכונה חדשה רגילה
        else:

            create_variation(driver, v)