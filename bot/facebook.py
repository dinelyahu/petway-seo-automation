"""
facebook.py — פרסום פוסטים לפייסבוק דרך Selenium
"""
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

FACEBOOK_LOGIN_URL = "https://www.facebook.com/login"


def _send(q_fn, msg: str):
    if q_fn:
        q_fn(msg)
    print(msg)


def _type_hebrew(driver, element, text: str):
    """
    הקלדת טקסט בעברית לתוך contenteditable של פייסבוק.
    משתמש ב-execCommand כדי לטרוג אירועי React.
    """
    driver.execute_script(
        "arguments[0].focus();"
        "document.execCommand('selectAll', false, null);"
        "document.execCommand('insertText', false, arguments[1]);",
        element, text
    )
    time.sleep(0.5)
    # אם execCommand לא עבד — fallback לעתק-הדבק
    current = element.text or element.get_attribute("innerText") or ""
    if text[:10] not in current:
        try:
            import subprocess
            subprocess.run(
                ["powershell", "-command",
                 f"Set-Clipboard -Value '{text.replace(chr(39), chr(96))}'"],
                capture_output=True, check=False
            )
            element.click()
            ActionChains(driver).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
            ActionChains(driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
            time.sleep(0.5)
        except Exception:
            element.send_keys(text)


def login_facebook(driver, email: str, password: str, send_fn=None):
    _send(send_fn, "🌐 פותח פייסבוק...")
    driver.get(FACEBOOK_LOGIN_URL)
    wait = WebDriverWait(driver, 15)

    # סגור banner עוגיות אם קיים
    try:
        cookie_btn = WebDriverWait(driver, 4).until(
            EC.element_to_be_clickable((By.XPATH,
                "//button[contains(text(),'Allow') or contains(text(),'Accept')"
                " or contains(text(),'אפשר') or contains(text(),'קבל')]"))
        )
        cookie_btn.click()
        time.sleep(1)
    except Exception:
        pass

    _send(send_fn, "🔐 ממלא פרטי כניסה...")
    email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
    email_field.clear()
    email_field.send_keys(email)

    pass_field = driver.find_element(By.ID, "pass")
    pass_field.clear()
    pass_field.send_keys(password)

    driver.find_element(By.NAME, "login").click()
    time.sleep(5)

    current = driver.current_url
    if "login" in current or "checkpoint" in current or "two_step" in current:
        raise Exception(
            "התחברות לפייסבוק נכשלה — בדוק אימייל/סיסמה, "
            "או שפייסבוק מחייב אימות דו-שלבי (אשר בטלפון ואז נסה שוב)"
        )

    _send(send_fn, "✅ מחובר לפייסבוק!")


def post_to_page(driver, page_url: str, text: str, image_path: str = None, send_fn=None):
    _send(send_fn, "📄 פותח עמוד פייסבוק...")
    driver.get(page_url)
    wait = WebDriverWait(driver, 20)
    time.sleep(4)

    # לחץ על תיבת כתיבת פוסט
    _send(send_fn, "✍️ פותח תיבת כתיבה...")
    post_box_opened = False

    # נסה למצוא את כפתור/תיבת יצירת הפוסט
    selectors_open = [
        (By.XPATH, "//div[@role='button'][.//span[contains(text(),'מה') or contains(text(),'What')]]"),
        (By.XPATH, "//span[contains(text(),'מה אתם') or contains(text(),'What')]//ancestor::div[@role='button']"),
        (By.XPATH, "//div[contains(@aria-label,'Create a post') or contains(@aria-label,'צור פוסט')]"),
        (By.XPATH, "//div[@data-pagelet]//div[@role='button'][contains(.,'פוסט') or contains(.,'Post')]"),
    ]

    for by, sel in selectors_open:
        try:
            btn = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((by, sel)))
            driver.execute_script("arguments[0].click();", btn)
            post_box_opened = True
            time.sleep(2)
            break
        except Exception:
            continue

    # מצא את ה-textbox
    _send(send_fn, "📝 מקליד טקסט...")
    try:
        textbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='textbox']"))
        )
        driver.execute_script("arguments[0].click();", textbox)
        time.sleep(1)
        _type_hebrew(driver, textbox, text)
    except Exception as e:
        raise Exception(f"לא נמצאה תיבת כתיבה: {e}")

    time.sleep(1)

    # העלאת תמונה
    if image_path and os.path.isfile(image_path):
        _send(send_fn, "🖼️ מוסיף תמונה...")
        abs_path = os.path.abspath(image_path)
        try:
            # נסה למצוא כפתור תמונה
            photo_btn_selectors = [
                (By.XPATH, "//div[@aria-label='Photo/video' or @aria-label='תמונה/סרטון']"),
                (By.XPATH, "//span[contains(text(),'Photo') or contains(text(),'תמונה')]//ancestor::div[@role='button']"),
                (By.XPATH, "//div[@role='button'][contains(.,'Photo') or contains(.,'תמונה')]"),
            ]
            for by, sel in photo_btn_selectors:
                try:
                    btn = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((by, sel)))
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(2)
                    break
                except Exception:
                    continue

            # מצא input file
            file_input = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            file_input.send_keys(abs_path)
            time.sleep(4)
            _send(send_fn, "✅ תמונה הועלתה!")
        except Exception as e:
            _send(send_fn, f"⚠️ לא הצלחנו להעלות תמונה: {e}")

    time.sleep(1)

    # לחץ פרסם
    _send(send_fn, "🚀 מפרסם פוסט...")
    post_btn_selectors = [
        (By.XPATH, "//div[@aria-label='Post' and @role='button']"),
        (By.XPATH, "//div[@aria-label='פרסם' and @role='button']"),
        (By.XPATH, "//span[text()='Post']/ancestor::div[@role='button']"),
        (By.XPATH, "//span[text()='פרסם']/ancestor::div[@role='button']"),
        (By.XPATH, "//div[@role='button'][contains(@class,'post') or contains(@class,'Post')]"),
    ]

    posted = False
    for by, sel in post_btn_selectors:
        try:
            btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, sel)))
            driver.execute_script("arguments[0].click();", btn)
            posted = True
            break
        except Exception:
            continue

    if not posted:
        raise Exception("לא נמצא כפתור פרסום — ייתכן שממשק פייסבוק השתנה")

    time.sleep(3)
    _send(send_fn, "✅ הפוסט פורסם בהצלחה!")
