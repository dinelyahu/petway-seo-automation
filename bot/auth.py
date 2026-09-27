import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

BASE_URL = "https://www.petway.co.il"
EMAIL    = os.getenv("PETWAY_EMAIL")
PASSWORD = os.getenv("PETWAY_PASSWORD")


def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def login(driver):
    print("🔄 פותח דפדפן ומנווט לעמוד התחברות...")
    driver.get(f"{BASE_URL}/התחברות")

    wait = WebDriverWait(driver, 10)

    # מסתיר פופאפ עוגיות
    driver.execute_script("""
        var el = document.getElementById('cookie_ok');
        if (el) el.style.display = 'none';
    """)
    print("✅ הסתיר פופאפ עוגיות")

    # מזין אימייל וסיסמא
    email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    email_field.clear()
    email_field.send_keys(EMAIL)
    print("✅ הוזן אימייל")

    password_field = driver.find_element(By.NAME, "password")
    password_field.clear()
    password_field.send_keys(PASSWORD)
    print("✅ הוזנה סיסמא")

    # לוחץ על כפתור התחברות
    login_btn = wait.until(EC.presence_of_element_located((By.ID, "loginBtn")))
    driver.execute_script("arguments[0].click();", login_btn)
    print("🔄 לוחץ על כפתור התחברות...")

    # מחכה שהדף יעבור
    time.sleep(3)
    print(f"✅ התחברות הצליחה! URL נוכחי: {driver.current_url}")
    return True