"""
info.py – עדכון טאב מידע (מותג, סטטוס וכו')
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bot.products.base import click_tab


def update_info_tab(driver, product):

    click_tab(driver, "nav-info-tab")

    wait = WebDriverWait(driver, 10)

    try:
        wait.until(
            EC.presence_of_element_located((By.NAME, "item[brand_id]"))
        )
    except:
        print("⚠️ לא נמצא שדה מותג")
        return

    brand_id = product.get("brand_value") or product.get("brand_id")

    if not brand_id:
        return

    try:

        # עדכון דרך JS (יותר יציב)
        driver.execute_script("""
        const select = document.querySelector('select[name="item[brand_id]"]');
        if (!select) return;

        select.value = arguments[0];

        select.dispatchEvent(new Event('change', { bubbles:true }));
        """, str(brand_id))

        print(f"🏷️ מותג עודכן → {brand_id}")

        time.sleep(0.8)

    except Exception as e:

        print("⚠️ שגיאה בעדכון מותג:", e)