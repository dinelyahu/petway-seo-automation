"""
faqs.py – טאב שאלות ותשובות
"""

from selenium.webdriver.common.by import By
from .base import click_tab
import time


def add_faq(driver, question, answer):
    """מוסיף שאלה ותשובה בודדת בטאב שאלות ותשובות."""
    try:
        faq_btn = driver.find_element(By.ID, "faqAdd")
        driver.execute_script("arguments[0].click();", faq_btn)
        time.sleep(0.7)

        faq_rows = driver.find_elements(By.CSS_SELECTOR, "#faqItems .faq-item")
        last_row = faq_rows[-1]

        q_input = last_row.find_element(By.CSS_SELECTOR, ".faq-q")
        q_input.click()
        q_input.clear()
        q_input.send_keys(question)

        a_input = last_row.find_element(By.CSS_SELECTOR, ".faq-a")
        a_input.click()
        a_input.clear()
        a_input.send_keys(answer)

        print(f"✅ שאלה נוספה: {question[:40]}...")
    except Exception as e:
        print(f"⚠️  הוספת שאלה: {e}")


def fill_faqs_tab(driver, product):
    """מלא טאב שאלות ותשובות עם כל הרשומות שבמוצר."""
    if not product.get("faqs"):
        return

    click_tab(driver, "nav-faq-tab")
    time.sleep(0.5)

    for faq in product["faqs"]:
        add_faq(driver, faq["question"], faq["answer"])
