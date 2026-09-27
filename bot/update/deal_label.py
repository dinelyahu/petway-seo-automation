from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def update_deal_label(driver, label_text):

    wait = WebDriverWait(driver, 10)

    # מעבר לטאב מידע
    tab = wait.until(
        EC.element_to_be_clickable((By.ID, "nav-info-tab"))
    )

    driver.execute_script("arguments[0].click();", tab)

    # חכה שהטאב נטען
    label = wait.until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, 'input[name="item[label]"]')
        )
    )

    # הכנסת טקסט דרך JS (כדי לא להיתקע על emoji)
    driver.execute_script(
        "arguments[0].value = arguments[1];",
        label,
        label_text
    )

    print(f"🏷️ עודכן label: {label_text}")