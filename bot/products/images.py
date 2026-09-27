"""
images.py – העלאת תמונות מוצר דרך חלון המדיה של Petway
"""

import os
import re
import time
import tempfile
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _pad_image_to_square(src_path: str, padding_pct: float = 0.08) -> str:
    """
    מכניס את התמונה לתוך קנבס לבן ריבועי עם ריפוד.
    padding_pct = אחוז ריפוד מכל צד (ברירת מחדל 8%).
    מחזיר נתיב לקובץ חדש בתיקייה זמנית.
    """
    try:
        from PIL import Image

        img = Image.open(src_path).convert("RGBA")
        w, h = img.size

        # גודל הצלע של הריבוע + ריפוד
        side = max(w, h)
        pad = int(side * padding_pct)
        canvas_size = side + pad * 2

        # קנבס לבן
        canvas = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 255))

        # מרכז את התמונה
        x = (canvas_size - w) // 2
        y = (canvas_size - h) // 2
        canvas.paste(img, (x, y), img if img.mode == "RGBA" else None)

        # שמור כ-JPEG לבן
        result = canvas.convert("RGB")
        ext = os.path.splitext(src_path)[1].lower() or ".jpg"
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False,
                                          dir=tempfile.gettempdir(),
                                          prefix="petway_padded_")
        result.save(tmp.name, quality=92)
        print(f"  ✅ תמונה רופדה: {canvas_size}×{canvas_size}px (ריפוד {int(padding_pct*100)}%)")
        return tmp.name

    except ImportError:
        print("  ⚠️  Pillow לא מותקן — מדלג על ריפוד (pip install Pillow)")
        return src_path
    except Exception as e:
        print(f"  ⚠️  ריפוד תמונה נכשל: {e}")
        return src_path


def upload_images(driver, image_paths: list[str], product_title: str = "") -> bool:
    """
    מעלה תמונות מוצר דרך חלון המדיה של Petway.

    זרימה:
    1. ריפוד כל תמונה לריבוע לבן (zoom-out אפקט)
    2. לחיצה על #prdCover → חלון #mediaModal נפתח
    3. העלאת קבצים דרך #fileUpload input[type=file]
    4. בחירת "הכל" ב-#mediaType
    5. לכל תמונה: בחירה → עדכון שם → שמירה
    6. לחיצה על התמונה הראשונה + #chooseImg לאישור cover
    """
    if not image_paths:
        return False

    valid_paths = _validate_paths(image_paths)
    if not valid_paths:
        return False

    # ── ריפוד לבן לפני העלאה ──
    print("🖼️  מרפד תמונות לריבוע לבן...")
    padded_paths = [_pad_image_to_square(p) for p in valid_paths]

    base_name = _build_base_name(product_title)
    print(f"\n🖼️  מעלה {len(padded_paths)} תמונה/ות...")

    try:
        _open_media_modal(driver)
        existing_count = _get_existing_count(driver)
        print(f"  📊 תמונות קיימות בגלריה: {existing_count}")
        _upload_files(driver, padded_paths)
        _wait_for_uploads(driver, len(padded_paths), existing_count)
        _rename_uploaded_images(driver, len(padded_paths), base_name, existing_count)
        _confirm_cover_image(driver, existing_count)

        names = ", ".join(os.path.basename(p) for p in valid_paths)
        print(f"🖼️  הועלו בהצלחה: {names}")
        return True

    except Exception as e:
        print(f"⚠️  העלאת תמונות נכשלה: {e}")
        return False


# ─── פונקציות פנימיות ────────────────────────────────────────

def _validate_paths(image_paths: list[str]) -> list[str]:
    valid = []
    for p in image_paths:
        abs_p = os.path.abspath(p)
        if os.path.isfile(abs_p):
            valid.append(abs_p)
        else:
            print(f"⚠️  קובץ לא נמצא, מדלג: {abs_p}")
    if not valid:
        print("⚠️  אין קבצים תקינים להעלאה")
    return valid


def _build_base_name(product_title: str) -> str:
    base = re.sub(
        r'\d+[\s.]*(ק["\']ג|גרם|kg|g)\b', '', product_title, flags=re.IGNORECASE
    ).strip()
    return base or "מוצר"


def _get_existing_count(driver) -> int:
    """סופר כמה תמונות יש בגלריה לפני ההעלאה."""
    try:
        items = driver.find_elements(By.CSS_SELECTOR, "#mediaContent .item.img")
        return len(items)
    except Exception:
        return 0


def _open_media_modal(driver):
    cover_div = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "prdCover"))
    )
    driver.execute_script("arguments[0].click();", cover_div)
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "mediaModal"))
    )
    time.sleep(0.3)
    print("✅ חלון מדיה נפתח")


def _upload_files(driver, valid_paths: list[str]):
    file_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#fileUpload input[type='file']"))
    )
    driver.execute_script("""
        arguments[0].style.display  = 'block';
        arguments[0].style.opacity  = '1';
        arguments[0].style.position = 'fixed';
        arguments[0].style.width    = '1px';
        arguments[0].style.height   = '1px';
    """, file_input)
    file_input.send_keys("\n".join(valid_paths))
    print(f"✅ {len(valid_paths)} קבצים נשלחו להעלאה")


def _refresh_gallery_to_show_newest(driver):
    """
    מרענן את הגלריה דרך הדרופדאון של mediaType:
    הכל (0) → מוצר קאבר (3) → הכל (0)
    רצף זה מסדר את התמונות החדשות כך שיופיעו ראשונות.
    """
    try:
        from selenium.webdriver.support.ui import Select

        def _select_value(value: str, label: str):
            sel_el = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.ID, "mediaType"))
            )
            if sel_el.tag_name == "select":
                Select(sel_el).select_by_value(value)
            else:
                driver.execute_script("""
                    var el = document.getElementById('mediaType');
                    if (el) {
                        el.value = arguments[0];
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                """, value)
            print(f"  🔄 דרופדאון → {label}")
            time.sleep(0.4)

        _select_value("0", "הכל")
        _select_value("3", "מוצר קאבר")
        _select_value("0", "הכל")
        print("✅ גלריה רועננה — תמונות חדשות ראשונות")

    except Exception as e:
        print(f"⚠️  רענון גלריה: {e}")


def _wait_for_uploads(driver, count: int, existing_count: int = 0):
    """ממתין שההעלאה תסתיים ומרענן גלריה."""
    expected = existing_count + count
    try:
        WebDriverWait(driver, 30).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#mediaContent .item.img")) >= expected
        )
    except Exception:
        print("⚠️  timeout בהמתנה לתמונות — ממשיך בכל זאת")

    time.sleep(0.2)
    _refresh_gallery_to_show_newest(driver)
    print("✅ תמונות הועלו לגלריה")


def _rename_uploaded_images(driver, count: int, base_name: str, existing_count: int = 0):
    """מעדכן שמות לתמונות החדשות — אחרי הרענון הן ראשונות."""
    items = driver.find_elements(By.CSS_SELECTOR, "#mediaContent .item.img")
    new_items = items[:count]  # אחרי רענון — החדשות ראשונות

    for idx, item in enumerate(new_items):
        img_name = f"{base_name} {idx + 1}" if count > 1 else base_name
        try:
            driver.execute_script("arguments[0].click();", item)
            time.sleep(0.2)

            info_btn = driver.find_element(By.ID, "mediaInfoBtn")
            driver.execute_script("arguments[0].click();", info_btn)
            time.sleep(0.2)

            name_input = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.ID, "mediaInfoName"))
            )
            driver.execute_script("arguments[0].value = '';", name_input)
            name_input.clear()
            name_input.send_keys(img_name)
            time.sleep(0.1)

            save_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "mediaInfoSaveBtn"))
            )
            driver.execute_script("arguments[0].click();", save_btn)
            time.sleep(0.3)
            print(f"  ✅ תמונה {idx+1}: שם עודכן ל-'{img_name}'")

            # סגירת פאנל מידע
            driver.execute_script("arguments[0].click();", info_btn)
            time.sleep(0.2)

        except Exception as e:
            print(f"  ⚠️  עדכון שם תמונה {idx+1}: {e}")


def _confirm_cover_image(driver, existing_count: int = 0):
    """בוחרת את התמונה הראשונה — אחרי רענון זו תמיד החדשה."""
    try:
        items = driver.find_elements(By.CSS_SELECTOR, "#mediaContent .item.img")
        target = items[0]  # אחרי רענון — החדשה ראשונה
        driver.execute_script("arguments[0].click();", target)
        time.sleep(0.2)

        choose_btn = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.ID, "chooseImg"))
        )
        driver.execute_script("arguments[0].click();", choose_btn)
        time.sleep(0.3)
        print("✅ תמונה ראשית אושרה (#chooseImg)")
    except Exception as e:
        print(f"⚠️  אישור תמונה ראשית: {e}")