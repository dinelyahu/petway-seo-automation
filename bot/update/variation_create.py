from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time


def create_variation(driver, variation):

    # גלילה למטה כדי לוודא שהכפתור נראה
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")

    # לחיצה על הוספת תכונה
    add_btn = driver.find_element(By.ID, "attAdd")
    add_btn.click()

    time.sleep(1)

    # קבלת כל השורות של התכונות
    rows = driver.find_elements(By.CSS_SELECTOR, "#attItems .attr-item")

    # השורה החדשה היא האחרונה
    row = rows[-1]

    # -------------------
    # כותרת
    # -------------------
    title = row.find_element(By.CSS_SELECTOR, ".attr-title")

    driver.execute_script(
        "arguments[0].value = arguments[1];",
        title,
        variation["title"]
    )

    # -------------------
    # מחיר
    # -------------------
    price = row.find_element(By.CSS_SELECTOR, ".attr-price")
    price.clear()
    price.send_keys(str(variation["price"]))

    # -------------------
    # מחיר הנחה
    # -------------------
    discount = row.find_element(By.CSS_SELECTOR, ".attr-discount")
    discount.clear()
    discount.send_keys(str(variation.get("price_discount", 0)))

    # -------------------
    # בחירת תכונה (משקל)
    # -------------------
    inner = row.find_element(By.CSS_SELECTOR, ".choices__inner")

    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});", inner
    )

    inner.click()

    time.sleep(0.5)

    search = row.find_element(By.CSS_SELECTOR, ".choices__input--cloned")

    search.clear()

    # כתיבה
    search.send_keys(variation["weight"])

    time.sleep(0.5)

    # רווח
    search.send_keys(" ")

    time.sleep(0.2)

    # מחיקת הרווח
    search.send_keys(Keys.BACK_SPACE)

    time.sleep(0.2)

    # אנטר
    search.send_keys(Keys.ENTER)

    time.sleep(0.7)

    print(f"➕ נוצרה תכונה חדשה {variation['weight']}")