"""
update_product.py – חיפוש, שליפה ועדכון מוצרים קיימים ב-Petway
"""

import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# alias כדי למנוע shadowing
from bot.update.updater import update_product as run_update_product

PRODUCTS_URL = "https://www.petway.co.il/לוח-בקרה/מוצרים"
BASE_URL = "https://www.petway.co.il"


# ════════════════════════════════════════════
# STEP 1 — חיפוש מוצרים בטבלה
# ════════════════════════════════════════════

def search_products(driver, query: str) -> list[dict]:

    driver.get(PRODUCTS_URL)

    wait = WebDriverWait(driver, 15)

    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
    )

    time.sleep(1.5)

    search_input = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'input[data-filter="title"]')
        )
    )

    search_input.clear()
    search_input.send_keys(query)

    time.sleep(0.5)

    search_input.send_keys(Keys.ENTER)

    time.sleep(2.5)

    products = _extract_product_rows(driver)

    print(f"✅ נמצאו {len(products)} מוצרים עבור '{query}'")

    return products


def _extract_product_rows(driver):

    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

    products = []

    for row in rows:

        try:

            p = _parse_row(driver, row)

            if p:
                products.append(p)

        except Exception as e:

            print(f"⚠️ שגיאה בשורה: {e}")

    return products


def _parse_row(driver, row):

    cells = row.find_elements(By.TAG_NAME, "td")

    if len(cells) < 2:
        return None

    product_id = None
    edit_url = None

    try:

        for link in row.find_elements(By.TAG_NAME, "a"):

            href = link.get_attribute("href") or ""

            m = re.search(r'/מוצרים/(\d+)', href)

            if m:
                product_id = m.group(1)
                edit_url = href
                break

    except Exception:
        pass

    if not product_id:

        for cell in cells[:3]:

            t = cell.text.strip().replace("#", "")

            if t.isdigit():
                product_id = t
                break

    if not product_id:
        return None

    name = ""

    for cell in cells:

        txt = cell.text.strip()

        if txt and not txt.isdigit() and "₪" not in txt:
            name = txt
            break

    if not name:
        return None

    price = ""

    for cell in cells:

        txt = cell.text.strip()

        if re.search(r'\d', txt):

            nums = re.findall(r'[\d,]+', txt)

            if nums:
                price = nums[0].replace(",", "")
                break

    status = 1

    try:

        badge = row.find_element(By.CSS_SELECTOR, ".badge")

        if "מוסתר" in badge.text:
            status = 2

    except Exception:
        pass

    image_url = ""

    try:

        img = row.find_element(By.CSS_SELECTOR, "img")
        image_url = img.get_attribute("src") or ""

    except Exception:
        pass

    return {

        "id": product_id,
        "name": name,
        "price": price,
        "price_discount": "",
        "status": status,
        "image": image_url,
        "url": edit_url or f"{BASE_URL}/לוח-בקרה/מוצרים/{product_id}",
        "variations": [],
        "categories": [],
        "images": [{"url": image_url}] if image_url else [],
    }


# ════════════════════════════════════════════
# STEP 2 — שליפת פרטים מלאים
# ════════════════════════════════════════════

def fetch_product_details(driver, product):

    edit_url = product.get("url")

    driver.get(edit_url)

    wait = WebDriverWait(driver, 15)

    wait.until(
        EC.presence_of_element_located((By.NAME, "item[title]"))
    )

    time.sleep(2)

    details = dict(product)

    details["name"] = _js_val(driver, 'input[name="item[title]"]')

    details["desc"] = _js_val(driver, 'textarea[name="item[desc]"]')

    details["price"] = _js_val(driver, 'input[name="item[price]"]')

    details["price_discount"] = _js_val(
        driver,
        'input[name="item[price_discount]"]'
    )

    # ═══ מותג ═══

    brand_id = driver.execute_script("""
    var el = document.querySelector('select[name="item[brand_id]"] option:checked');
    return el ? el.value : "";
    """)

    brand_name = driver.execute_script("""
    var el = document.querySelector('select[name="item[brand_id]"] option:checked');
    return el ? el.textContent.trim() : "";
    """)

    details["brand_id"] = brand_id
    details["brand_name"] = brand_name
    details["brand_value"] = brand_id   # חשוב ל-frontend

    # ═══ וריאציות ═══

    details["variations"] = _fetch_variations(driver)

    print(f"🔎 נמצאו {len(details['variations'])} וריאציות")

    return details


def _js_val(driver, selector):

    try:

        return driver.execute_script(
            f"var e=document.querySelector('{selector}'); return e?e.value:'';"
        ) or ""

    except Exception:

        return ""


# ════════════════════════════════════════════
# שליפת וריאציות (תכונות)
# ════════════════════════════════════════════

def _fetch_variations(driver):

    wait = WebDriverWait(driver, 10)

    # מעבר לטאב תכונות
    try:
        tab = driver.find_element(By.ID, "nav-attr-tab")
        driver.execute_script("arguments[0].click();", tab)
        time.sleep(1)
    except Exception:
        pass

    # מחכים לטעינת התכונות
    try:
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#attItems .attr-item"))
        )
    except Exception:
        print("⚠️ לא נמצאו תכונות")
        return []

    variations = []

    rows = driver.find_elements(By.CSS_SELECTOR, "#attItems .attr-item")

    for i, row in enumerate(rows):

        try:

            title = row.find_element(
                By.CSS_SELECTOR,
                'input[name*="[title]"]'
            ).get_attribute("value")

            price = row.find_element(
                By.CSS_SELECTOR,
                'input[name*="[price]"]'
            ).get_attribute("value")

            price_discount = row.find_element(
                By.CSS_SELECTOR,
                'input[name*="[price_discount]"]'
            ).get_attribute("value")

            var_id = row.find_element(
                By.CSS_SELECTOR,
                'input[name*="[id]"]'
            ).get_attribute("value")

            stock = row.find_element(
                By.CSS_SELECTOR,
                'input[name*="[stock]"]'
            ).get_attribute("value")

            barcode = row.find_element(
                By.CSS_SELECTOR,
                'input[name*="[barcode]"]'
            ).get_attribute("value")

            # שליפת הטקסט מתוך choices.js
            attr_text = driver.execute_script("""
            var el = arguments[0].querySelector('.choices__item--selectable');
            if(!el) return "";
            return el.textContent.trim();
            """, row)

            weight = ""

            if attr_text:
                parts = attr_text.split("/")
                weight = parts[-1]

                # ניקוי Remove item
                weight = weight.replace("Remove item", "")

                weight = weight.replace("-", " ")
                weight = weight.replace("קג", "ק\"ג")

                weight = weight.strip()

            variations.append({
                "idx": i,
                "id": var_id,
                "title": title,
                "price": price,
                "price_discount": price_discount,
                "weight": weight,
                "stock": stock,
                "barcode": barcode,
                "isDeal": False
            })

        except Exception as e:
            print("⚠️ שגיאה בשליפת תכונה:", e)

    print(f"🔎 נמצאו {len(variations)} תכונות")

    return variations


# ════════════════════════════════════════════
# STEP 3 — עדכון מוצר
# ════════════════════════════════════════════

def update_product(driver, product, send):

    name = product.get("name", f"#{product['id']}")

    send(f"📄 פותח עמוד עריכה: {name}", "progress")

    driver.get(product["url"])

    wait = WebDriverWait(driver, 15)

    try:

        wait.until(
            EC.presence_of_element_located((By.NAME, "item[title]"))
        )

    except Exception:

        send(f"⚠️ לא הצליח לטעון דף עריכה של {name}", "progress")

        return False

    time.sleep(1.5)

    # עדכון
    run_update_product(driver, product)

    send(f"✅ {name} עודכן", "progress")

    return True