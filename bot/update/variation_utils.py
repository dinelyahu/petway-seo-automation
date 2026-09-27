import time
from selenium.webdriver.common.by import By


def open_variations_tab(driver):
    try:
        tab = driver.find_element(By.ID, "nav-attr-tab")
        driver.execute_script("arguments[0].click();", tab)
        time.sleep(1)
    except Exception:
        pass


def find_row_by_id(driver, var_id):

    rows = driver.find_elements(By.CSS_SELECTOR, "#attItems .attr-item")

    for r in rows:
        try:
            hidden = r.find_element(By.CSS_SELECTOR, 'input[name*="[id]"]')
            if hidden.get_attribute("value") == str(var_id):
                return r
        except Exception:
            pass

    return None


def variation_has_changes(v):

    return any([
        str(v.get("title", "")) != str(v.get("_origTitle", "")),
        str(v.get("price", "")) != str(v.get("_origPrice", "")),
        str(v.get("price_discount", "")) != str(v.get("_origPriceDiscount", "")),
        str(v.get("weight", "")) != str(v.get("_origWeight", "")),
    ])