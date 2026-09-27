from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

from .variation_utils import find_row_by_id


def clear_existing_weight(row):
    """
    לוחץ על האיקס של התכונה הקיימת
    """
    try:
        buttons = row.find_elements(By.CSS_SELECTOR, ".choices__button")

        for b in buttons:
            b.click()
            time.sleep(0.3)

    except Exception:
        pass


def set_new_weight(row, weight):

    if not weight:
        return

    try:

        inner = row.find_element(By.CSS_SELECTOR, ".choices__inner")
        inner.click()

        time.sleep(0.5)

        search = row.find_element(By.CSS_SELECTOR, ".choices__input--cloned")

        search.clear()
        search.send_keys(weight)

        time.sleep(1)

        # טריק ל Choices.js
        search.send_keys(" ")
        time.sleep(0.2)
        search.send_keys(Keys.BACK_SPACE)
        time.sleep(0.2)
        search.send_keys(Keys.ENTER)

        time.sleep(0.5)

    except Exception as e:
        print(f"⚠️ שגיאה בבחירת תכונה: {e}")


def update_existing_variation(driver, variation):

    row = find_row_by_id(driver, variation.get("id"))

    if not row:
        print(f"⚠️ לא נמצאה תכונה id={variation.get('id')}")
        return

    try:

        # כותרת
        if variation.get("title") != variation.get("_origTitle"):

            inp = row.find_element(By.CSS_SELECTOR, ".attr-title")
            inp.clear()
            inp.send_keys(variation.get("title"))

        # מחיר
        if str(variation.get("price")) != str(variation.get("_origPrice")):

            inp = row.find_element(By.CSS_SELECTOR, ".attr-price")
            inp.clear()
            inp.send_keys(str(variation.get("price")))

        # הנחה
        if str(variation.get("price_discount")) != str(variation.get("_origPriceDiscount")):

            inp = row.find_element(By.CSS_SELECTOR, ".attr-discount")
            inp.clear()
            inp.send_keys(str(variation.get("price_discount")))

        # שינוי תכונה (משקל)
        if variation.get("weight") != variation.get("_origWeight"):

            clear_existing_weight(row)

            set_new_weight(row, variation.get("weight"))

        print(f"✏️ תכונה עודכנה id={variation.get('id')}")

    except Exception as e:
        print(f"⚠️ שגיאה בעדכון תכונה: {e}")