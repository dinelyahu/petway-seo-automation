"""
info.py – טאב מידע: סטטוס, משקל, תווית
"""

from .base import click_tab, fill_field, select_by_value
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def fill_info_tab(driver, product):
    """מלא טאב מידע: סטטוס, משקל, תווית דיל."""
    if not any(product.get(k) for k in ["status", "weight", "label"]):
        return

    click_tab(driver, "nav-info-tab")
    time.sleep(1)  # המתנה לטאב להיטען במלואו

    if product.get("status"):
        select_by_value(driver, "item[status]", product["status"])
        print(f"✅ סטטוס: {product['status']}")

    if product.get("weight"):
        fill_field(driver, "item[weight]", product["weight"])
        print("✅ משקל")

    if product.get("label"):
        label_val = str(product["label"])
        try:
            f = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.NAME, "item[label]"))
            )
            f.click()
            f.clear()
            time.sleep(0.3)
            # send_keys לא תומך באימוג'י מחוץ ל-BMP — משתמשים ב-JS
            driver.execute_script(
                "arguments[0].value = arguments[1];"
                "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                f, label_val
            )
            print(f"✅ תווית: {label_val}")
        except Exception as e:
            print(f"⚠️  תווית: {e}")