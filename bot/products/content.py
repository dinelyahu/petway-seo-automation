"""
content.py – מילוי תוכן: כותרת, תיאור, SEO, TinyMCE
"""

from selenium.webdriver.common.by import By
from .base import fill_field, click_tab, ADD_PRODUCT_URL
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def fill_tinymce(driver, editor_id, content):
    try:
        driver.execute_script(f"""
            var editor = tinymce.get('{editor_id}');
            if (editor) editor.setContent(arguments[0]);
        """, content)
    except Exception as e:
        print(f"⚠️  TinyMCE {editor_id}: {e}")


def fill_general(driver, product):
    """מלא שדות טאב מידע כללי: כותרת, SEO, מותג, תיאור."""
    fill_field(driver, "item[title]", product.get("title", ""))
    print("✅ כותרת")

    if product.get("seo_title"):
        fill_field(driver, "item[seo_title]", product["seo_title"])
        print("✅ כותרת SEO")

    if product.get("brand"):
        try:
            brand_value = product.get("brand_value") or product["brand"]
            driver.execute_script("""
                var sel = document.querySelector('select[name="item[brand_id]"]');
                if (sel) {
                    sel.value = arguments[0];
                    sel.dispatchEvent(new Event('change', {bubbles: true}));
                }
            """, brand_value)
            print(f"✅ מותג: {product['brand']}")
        except Exception as e:
            print(f"⚠️  מותג: {e}")

    if product.get("desc"):
        fill_field(driver, "item[desc]", product["desc"])
        print("✅ תקציר")


def fill_content_tab(driver, product):
    """מלא טאב תוכן: תוכן קצר ותוכן מלא ב-TinyMCE."""
    if not (product.get("short_content") or product.get("content")):
        return

    click_tab(driver, "nav-content-tab")

    if product.get("short_content"):
        fill_tinymce(driver, "mce_0", product["short_content"])
        print("✅ תוכן קצר")

    if product.get("content"):
        fill_tinymce(driver, "mce_2", product["content"])
        print("✅ תוכן מלא")
