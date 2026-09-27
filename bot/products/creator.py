"""
creator.py – אורקסטרטור: create_product מאחד את כל מודולי המוצר
"""

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

from .base import ADD_PRODUCT_URL
from .content import fill_general, fill_content_tab
from .info import fill_info_tab
from .variations import fill_variations_tab
from .faqs import fill_faqs_tab
from .pricing import fill_pricing_tab
from .assignments import fill_assignments_tab
from .images import upload_images


def create_product(driver, product: dict) -> bool:
    """
    יוצר מוצר חדש באתר Petway.

    product = {
        # ── מידע כללי ──
        'title':          'שם המוצר',        # חובה
        'seo_title':      'כותרת SEO',        # אופציונלי
        'brand':          'רויאל קנין',       # שם מותג
        'brand_value':    '2',               # ערך מותג (ID באתר)
        'desc':           'תקציר',            # אופציונלי

        # ── תוכן ──
        'short_content':  'תוכן קצר',         # אופציונלי
        'content':        '<p>תוכן מלא</p>',  # אופציונלי

        # ── מידע ──
        'status':         '1',               # 1=פעיל, 2=מוסתר
        'weight':         '500',             # בגרמים
        'label':          '💥דיל זוגות',     # אופציונלי — תווית דיל

        # ── וריאציות ──
        'variations': [
            {'title': 'שקית 2 ק"ג', 'price': '49', 'weight': '2 ק"ג'},
            {'title': 'שקית 4 ק"ג', 'price': '89', 'price_discount': '79'},
        ],

        # ── שאלות ותשובות ──
        'faqs': [
            {'question': '...', 'answer': '...'},
        ],

        # ── מחירים ──
        'price':          '99',
        'price_discount': '79',
        'stock':          '10',

        # ── שיוכים ──
        'category_ids':   ['104', '78'],     # [ראשית, ...משניות]

        # ── תמונות ──
        'image_paths':    ['/path/img.jpg'],
    }
    """
    print(f"\n🔄 יוצר מוצר: {product.get('title')}")

    driver.get(ADD_PRODUCT_URL)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "item[title]"))
    )
    time.sleep(2)

    fill_general(driver, product)
    fill_content_tab(driver, product)
    fill_info_tab(driver, product)
    fill_variations_tab(driver, product)
    fill_faqs_tab(driver, product)
    fill_pricing_tab(driver, product)
    fill_assignments_tab(driver, product)

    if product.get("image_paths"):
        upload_images(driver, product["image_paths"], product_title=product.get("title", ""))

    print("\n✅ הטופס מולא בהצלחה.")
    return True