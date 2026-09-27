"""
variations.py – טאב תכונות: הוספת וריאציות ומשקלות
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from .base import click_tab
import time
import sys


def add_variation(driver, variation):
    """
    מוסיף וריאציה בודדת למוצר בטאב תכונות.

    variation = {
        'title':          'שקית 2 ק"ג',   # חובה
        'price':          '49',            # חובה
        'price_discount': '39',            # אופציונלי
        'weight':         '2 ק"ג',        # אופציונלי — ערך מ-VALID_WEIGHTS
    }
    """
    try:
        add_btn = driver.find_element(By.ID, "attAdd")
        driver.execute_script("arguments[0].click();", add_btn)
        time.sleep(0.7)

        rows = driver.find_elements(By.CSS_SELECTOR, "#attItems .attr-item")
        last_row = rows[-1]

        def fill_in_row(css, val):
            try:
                f = last_row.find_element(By.CSS_SELECTOR, css)
                val_str = str(val)

                # לכותרת — תמיד clipboard (מכיל תווים עבריים ו-")
                if css == ".attr-title":
                    try:
                        import pyperclip
                        pyperclip.copy(val_str)
                        driver.execute_script("arguments[0].value = ''; arguments[0].focus();", f)
                        f.send_keys(Keys.CONTROL + "a")
                        time.sleep(0.1)
                        f.send_keys(Keys.CONTROL + "v")
                        time.sleep(0.2)
                        driver.execute_script(
                            "arguments[0].dispatchEvent(new Event('input', {bubbles:true})); "
                            "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                            f
                        )
                        return
                    except ImportError:
                        pass

                # שאר השדות — JS direct set
                driver.execute_script(
                    "arguments[0].value = arguments[1]; "
                    "arguments[0].dispatchEvent(new Event('input', {bubbles:true})); "
                    "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                    f, val_str
                )

                # בדיקה — אם הערך נחתך, clipboard
                actual = driver.execute_script("return arguments[0].value;", f)
                if actual != val_str:
                    print(f"  ⚠️  ערך נחתך ({len(actual)}/{len(val_str)} תווים) — מנסה clipboard...")
                    try:
                        import pyperclip
                        pyperclip.copy(val_str)
                        f.click()
                        f.send_keys(Keys.CONTROL + "a")
                        time.sleep(0.1)
                        f.send_keys(Keys.CONTROL + "v")
                        time.sleep(0.2)
                        driver.execute_script(
                            "arguments[0].dispatchEvent(new Event('input', {bubbles:true})); "
                            "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                            f
                        )
                    except ImportError:
                        escaped = val_str.encode("unicode_escape").decode("ascii")
                        driver.execute_script(
                            f"arguments[0].value = '{escaped}'; "
                            "arguments[0].dispatchEvent(new Event('input', {bubbles:true})); "
                            "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                            f
                        )
            except Exception as e:
                print(f"⚠️  {css}: {e}")

        fill_in_row(".attr-title", variation.get("title", ""))
        fill_in_row(".attr-price", variation.get("price", ""))

        if variation.get("price_discount"):
            fill_in_row(".attr-discount", variation["price_discount"])

        # בחירת משקל בדרופדאון Choices.js
        weight_text = variation.get("weight")
        if weight_text:
            _select_weight_choices(driver, last_row, weight_text)

        print(f"✅ וריאציה: {variation.get('title')} | {variation.get('price')}₪")
    except Exception as e:
        print(f"⚠️  הוספת וריאציה: {e}")


def _select_weight_choices(driver, row_element, weight_text):
    """בוחר משקל מתוך Choices.js dropdown בשורת וריאציה."""
    try:
        choices_inner = row_element.find_element(By.CSS_SELECTOR, ".choices__inner")
        driver.execute_script("arguments[0].click();", choices_inner)
        time.sleep(0.4)

        search_input = row_element.find_element(By.CSS_SELECTOR, ".choices__input--cloned")
        search_input.clear()
        search_input.send_keys(weight_text)
        time.sleep(1.0)
        search_input.send_keys(" ")
        time.sleep(0.3)
        search_input.send_keys(Keys.BACK_SPACE)
        time.sleep(0.5)

        opts = row_element.find_elements(
            By.CSS_SELECTOR,
            ".choices__list--dropdown .choices__item--choice[data-choice-selectable]"
        )
        for opt in opts:
            if opt.is_displayed():
                try:
                    opt.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", opt)
                time.sleep(0.3)
                print(f"✅ משקל נבחר: {weight_text}")
                return

        # fallback — Enter
        search_input.send_keys(Keys.ENTER)
        time.sleep(0.3)
        print(f"✅ משקל (Enter): {weight_text}")
    except Exception as e:
        print(f"⚠️  בחירת משקל: {e}")


def fill_variations_tab(driver, product):
    """מלא טאב תכונות עם כל הוריאציות שבמוצר."""
    if not product.get("variations"):
        return

    click_tab(driver, "nav-attr-tab")
    for v in product["variations"]:
        add_variation(driver, v)