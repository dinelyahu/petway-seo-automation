"""
assignments.py – טאב שיוכים: קטגוריה ראשית וקטגוריות משניות
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from .base import click_tab
import time


def _select_in_choices(driver, container_el, cat_id):
    """מחפש ובוחר קטגוריה לפי ID בתוך אלמנט Choices.js נתון."""
    inner = container_el.find_element(By.CSS_SELECTOR, ".choices__inner")
    driver.execute_script("arguments[0].click();", inner)
    time.sleep(0.4)

    search_input = container_el.find_element(By.CSS_SELECTOR, ".choices__input--cloned")
    search_input.clear()
    search_input.send_keys(str(cat_id))
    time.sleep(0.6)
    search_input.send_keys(" ")
    time.sleep(0.4)
    search_input.send_keys(Keys.BACK_SPACE)
    time.sleep(0.5)

    opts = container_el.find_elements(
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
            return True
    return False


def _assign_primary_category(driver, cat_name):
    """שיוך קטגוריה ראשית (item[catID]) דרך Choices.js לפי שם."""
    try:
        primary_container = driver.find_element(
            By.CSS_SELECTOR, ".choices:has(select[name='item[catID]'])"
        )
        if _select_in_choices(driver, primary_container, cat_name):
            print(f"✅ קטגוריה ראשית '{cat_name}' נבחרה")
        else:
            print(f"⚠️  לא נמצאה קטגוריה ראשית '{cat_name}'")
    except Exception as e:
        print(f"⚠️  קטגוריה ראשית {cat_name}: {e}")


def _assign_secondary_category(driver, cat_id, cat_name):
    """הוספת קטגוריה משנית דרך כפתור catAdd."""
    if not cat_name:
        print(f"⚠️  לא נמצא שם לקטגוריה — מדלג")
        return
    try:
        cat_add_btn = driver.find_element(By.ID, "catAdd")
        driver.execute_script("arguments[0].click();", cat_add_btn)
        time.sleep(0.7)

        cat_rows = driver.find_elements(By.CSS_SELECTOR, "#catItems .choices")
        if not cat_rows:
            print(f"⚠️  לא נמצא אלמנט קטגוריה משנית עבור {cat_name}")
            return
        last_container = cat_rows[-1]

        inner = last_container.find_element(By.CSS_SELECTOR, ".choices__inner")
        driver.execute_script("arguments[0].click();", inner)
        time.sleep(0.4)

        search_input = last_container.find_element(By.CSS_SELECTOR, ".choices__input--cloned")
        search_input.clear()
        search_input.send_keys(cat_name)
        time.sleep(0.8)
        search_input.send_keys(" ")
        time.sleep(0.4)
        search_input.send_keys(Keys.ENTER)
        time.sleep(0.4)
        print(f"✅ קטגוריה משנית '{cat_name}' נבחרה")
    except Exception as e:
        print(f"⚠️  קטגוריה משנית {cat_id}: {e}")


def fill_assignments_tab(driver, product):
    """מלא טאב שיוכים עם קטגוריה ראשית ואופציונלית משניות לפי שם."""
    categories = product.get("category_ids") or (
        [product["category_id"]] if product.get("category_id") else []
    )
    if not categories:
        return

    click_tab(driver, "nav-connect-tab")
    time.sleep(0.5)

    # בניית מיפוי שם→ID מקטגוריות האתר
    try:
        from categories import CATEGORIES as _CATS
    except ImportError:
        try:
            from bot.categories import CATEGORIES as _CATS
        except ImportError:
            _CATS = {}

    # _CATS הוא {id: name} — בונים הפוך {name: str(id)}
    _name_to_id = {name: str(cid) for cid, name in _CATS.items()}

    def _resolve_to_id(val: str) -> str:
        """אם val הוא כבר מספר — מחזיר אותו. אחרת מחפש לפי שם."""
        if val.strip().lstrip("-").isdigit():
            return val.strip()
        return _name_to_id.get(val, val)

    # קטגוריה ראשית — חובה להיות ID
    primary_id = _resolve_to_id(str(categories[0]))
    _assign_primary_category(driver, primary_id)

    # קטגוריות משניות — ממשיכות לפי שם (Choices.js מחפש טקסט)
    for cat in categories[1:]:
        # אם זה ID — ממיר לשם לצורך חיפוש טקסט
        if str(cat).strip().lstrip("-").isdigit():
            cat_name = _CATS.get(int(cat), str(cat))
        else:
            cat_name = cat
        _assign_secondary_category(driver, cat, cat_name)


def fetch_categories_from_site(driver) -> list[dict]:
    """
    טוען את כל הקטגוריות מה-select המקורי בטאב שיוכים באתר.
    משתמש ב-JS ישיר כדי לעקוף בעיות Choices.js.
    """
    from .base import ADD_PRODUCT_URL
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By

    print("🔄 טוען קטגוריות מהאתר...")
    driver.get(ADD_PRODUCT_URL)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(2)

    try:
        tab = driver.find_element(By.ID, "nav-connect-tab")
        driver.execute_script("arguments[0].click();", tab)
        time.sleep(1.5)
    except Exception:
        pass

    categories = driver.execute_script("""
        var selects = document.querySelectorAll('#nav-connect select');
        var results = [];
        selects.forEach(function(sel) {
            for (var i = 0; i < sel.options.length; i++) {
                var val = sel.options[i].value;
                var text = sel.options[i].text.trim();
                if (val && val !== '0' && text) {
                    results.push({id: val, name: text});
                }
            }
        });
        return results;
    """)

    if not categories:
        print("⚠️  לא נמצאו קטגוריות בטאב שיוכים — בודק select כללי...")
        categories = driver.execute_script("""
            var results = [];
            document.querySelectorAll('select option').forEach(function(opt) {
                if (opt.value && opt.value !== '0' && opt.text.trim())
                    results.push({id: opt.value, name: opt.text.trim()});
            });
            return results;
        """)

    print(f"✅ נמצאו {len(categories)} קטגוריות")
    return categories or []