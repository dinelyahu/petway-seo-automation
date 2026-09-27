"""
base.py – פונקציות עזר בסיסיות וניווט
"""

from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

BASE_URL     = "https://www.petway.co.il"
PRODUCTS_URL = f"{BASE_URL}/לוח-בקרה/מוצרים"
ADD_PRODUCT_URL = f"{BASE_URL}/לוח-בקרה/הוסף-מוצר"


def go_to_products(driver):
    print("🔄 מנווט לדף המוצרים...")
    driver.get(PRODUCTS_URL)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print(f"✅ הגענו לדף: {driver.current_url}")
    return True


def fill_field(driver, name, value):
    try:
        field = driver.find_element(By.NAME, name)
        field.clear()
        field.send_keys(str(value))
    except Exception as e:
        print(f"⚠️  שדה {name}: {e}")


def select_by_name(driver, name, value):
    try:
        el = driver.find_element(By.NAME, name)
        Select(el).select_by_visible_text(value)
    except Exception as e:
        print(f"⚠️  dropdown {name}: {e}")


def select_by_value(driver, name, value):
    try:
        el = driver.find_element(By.NAME, name)
        Select(el).select_by_value(str(value))
    except Exception as e:
        print(f"⚠️  dropdown {name}: {e}")


def click_tab(driver, tab_id):
    """לוחץ על לשונית Bootstrap ומחכה שהיא תהיה פעילה."""
    try:
        tab = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, tab_id))
        )
        driver.execute_script("arguments[0].click();", tab)
        # מחכים שהכפתור יקבל class active — סימן שהלשונית נפתחה
        WebDriverWait(driver, 10).until(
            lambda d: "active" in d.find_element(By.ID, tab_id).get_attribute("class")
        )
        time.sleep(0.3)
    except Exception as e:
        print(f"⚠️  טאב {tab_id}: {e}")