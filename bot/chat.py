"""
chat.py – מודול AI לייצור תוכן מוצר אוטומטי באמצעות Claude
"""

import json
import os
import re
import ssl
import tempfile
import urllib.request
import urllib.parse
from anthropic import Anthropic

# Windows לעתים קרובות חסר תעודות SSL מעודכנות — מתעלם מ-verification
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

client = Anthropic()

# ─────────────────────────────────────────────────────────────
# מיפוי קטגוריות — מייובא מ-categories.py (236 קטגוריות אמיתיות)
# ─────────────────────────────────────────────────────────────
try:
    from categories import CATEGORIES
except ImportError:
    try:
        from bot.categories import CATEGORIES
    except ImportError:
        CATEGORIES = {}

# CATEGORIES_LIST: ממיר {id: name} → "  - name (ID: id)"
CATEGORIES_LIST = "\n".join(
    f"  - {name} (ID: {cid})" for cid, name in CATEGORIES.items()
)

# ─────────────────────────────────────────────────────────────
# ערכי תכונות קיימים באתר
# ─────────────────────────────────────────────────────────────
VALID_WEIGHTS = [
    '100 גרם', '200 גרם', '300 גרם', '400 גרם', '500 גרם',
    '800 גרם', '1 ק"ג', '1.5 ק"ג', '2 ק"ג', '3 ק"ג',
    '4 ק"ג', '5 ק"ג', '6 ק"ג', '7 ק"ג', '8 ק"ג',
    '10 ק"ג', '12 ק"ג', '15 ק"ג', '18 ק"ג', '20 ק"ג',
]
WEIGHTS_LIST = ", ".join(VALID_WEIGHTS)

# ─────────────────────────────────────────────────────────────
# רשימת מותגים סגורה
# ─────────────────────────────────────────────────────────────
BRANDS = {
    "ללא הורה": "0",
    "מונג'": "1", "רויאל קנין": "2", "אקאנה": "3",
    "טייסט אוף דה ווילד": "4", "איסגרים": "5", "אלפא ספיריט": "6",
    "ארדן גרנג'": "7", "אריון": "8", "אתנה": "9",
    "ביהפר": "10", "בלקווד": "11", "בלקנדו": "12",
    "בנבו": "13", "דוג פרפורמנס": "14", "בריט": "15",
    "ג'נסיס": "16", "ג'וסרה": "17", "גאטו": "18",
    "הורייזן": "19", "הילס סיינס פלאן": "20", "סולאנו": "21",
    "הפי דוג": "22", "הפי קט": "23", "אברקלין": "24",
    "וט לייף": "25", "וינסנט": "26", "ויסקאס": "27",
    "וירבק": "28", "טומי": "29", "טרווט": "30",
    "יוקונובה": "31", "יורו קיטי": "32", "לאונרדו": "33",
    "לה קט": "34", "מטיס": "35", "מיטו": "36",
    "שזיר": "37", "ראפואר": "38", "אם-פטס": "39",
    "אם-די וואן": "40", "אולטרה קט / אולטרה דוג / אולטרה פט": "41",
    "וט אי קיו": "42", "אבוריג'ינל": "43", "אדוונס": "44",
    "אוונטיס": "45", "אוריגן": "46", "איזי ווק": "47",
    "אינבה": "48", "אלפא דוג": "49", "אנג'וי": "50",
    "בונאסיבו": "51", "ג'וסיקט": "52", "גו": "53",
    "גופלקס": "54", "גרייט פאן": "55", "דיימונד נטוראלס": "56",
    "ויבוקס": "57", "נאו": "58", "נוטרה גולד": "59",
    "נוטריווט": "60", "נטורל באלנס": "61", "נטורל דלישס": "62",
    "סיבאו": "63", "סימבה": "64", "סמרטסיף": "65",
    "סניקט": "66", "ספי קט": "67", "סרה": "68",
    "פדרו": "69", "פורינה": "70", "פטס פרוג'קט": "71",
    "פידוג": "72", "פלטזור": "73", "פלטינום": "74",
    "פנסי פיסט": "75", "פרו נטיב": "76", "פרו פלאן": "77",
    "פרימייר קלאב": "78", "פריסקיז": "79", "פרמיו": "80",
    "צ'יקופי": "81", "קאניס נייצ'ר": "82", "קונג": "83",
    "קט בסט": "84", "קיט קט": "85", "קמון": "86",
    "קנין קוויאר": "87", "קנל סלקט": "88", "קרוסטי": "89",
    "קרוקטייל": "90", "פטיבה": "91", "Rio": "92",
}
BRANDS_LIST = "\n".join(f"  - {name}" for name in BRANDS)


# ─────────────────────────────────────────────────────────────
# חילוץ תמונות מוצר מ-URL באמצעות Claude
# ─────────────────────────────────────────────────────────────

_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "he,en;q=0.9",
}


def _fetch_html(url: str) -> str:
    """מוריד HTML של הדף עם User-Agent של דפדפן."""
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
        raw = resp.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


def _extract_img_urls(html: str, base_url: str) -> list[str]:
    """
    שולף את כל כתובות התמונות מ-HTML.
    תומך ב-src רגיל וגם ב-data-src / data-lazy-src (lazy loading).
    מחזיר רשימת URLs מוחלטים עם סיומת תמונה בלבד.
    """
    # src רגיל + data-src variants
    patterns = [
        r'<img[^>]+\bsrc=["\']([^"\']+)["\']',
        r'<img[^>]+\bdata-src=["\']([^"\']+)["\']',
        r'<img[^>]+\bdata-lazy-src=["\']([^"\']+)["\']',
        r'<img[^>]+\bdata-original=["\']([^"\']+)["\']',
    ]
    srcs = []
    for pat in patterns:
        srcs += re.findall(pat, html, re.IGNORECASE)

    parsed_base = urllib.parse.urlparse(base_url)
    absolute = []
    seen = set()

    for src in srcs:
        src = src.strip()
        if not src or src.startswith("data:"):
            continue
        # המרה ל-URL מוחלט
        if src.startswith("//"):
            src = parsed_base.scheme + ":" + src
        elif src.startswith("/"):
            src = f"{parsed_base.scheme}://{parsed_base.netloc}{src}"
        elif not src.startswith("http"):
            src = urllib.parse.urljoin(base_url, src)
        # סינון לפי סיומת תמונה
        path = urllib.parse.urlparse(src).path.lower().split("?")[0]
        if os.path.splitext(path)[1] not in _IMG_EXTS:
            continue
        if src not in seen:
            seen.add(src)
            absolute.append(src)

    return absolute


def _ask_claude_which_images(product_url: str, img_urls: list[str]) -> list[str]:
    """
    שולח ל-Claude רשימת URLs.
    Claude מסנן ומחזיר רק תמונות של המוצר עצמו
    (ללא לוגו, אייקונים, באנרים, תמונות ניווט).
    """
    urls_text = "\n".join(f"{i+1}. {u}" for i, u in enumerate(img_urls))

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=(
            "אתה מומחה לזיהוי תמונות מוצרים באתרי מסחר. "
            "קבל רשימת URLs של תמונות מדף מוצר. "
            "זהה אילו מהן הן תמונות המוצר עצמו — אריזה, תצלום מוצר, גלריית מוצר. "
            "סנן החוצה: לוגו חברה, אייקוני ניווט, באנרים, תמונות רקע, תמונות קישוטיות. "
            'החזר JSON בלבד: {"product_images": ["url1", "url2", ...]}'
        ),
        messages=[{
            "role": "user",
            "content": (
                f"דף מוצר: {product_url}\n\n"
                f"כל התמונות שנמצאו:\n{urls_text}\n\n"
                "החזר רשימה של תמונות המוצר בלבד, "
                "ממוינות מהחשובה (תמונה ראשית) ועד פחות חשובה. "
                "מקסימום 8 תמונות."
            )
        }]
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(raw).get("product_images", [])
    except Exception:
        # fallback — מחזיר את 8 הראשונות אם Claude נכשל
        return img_urls[:8]


def _download_images(img_urls: list[str], dest_dir: str) -> list[str]:
    """
    מוריד תמונות לתיקייה.
    מחזיר נתיבים מקומיים של קבצים שהורדו בהצלחה.
    """
    paths = []
    for i, url in enumerate(img_urls):
        try:
            path_part = urllib.parse.urlparse(url).path
            ext = os.path.splitext(path_part)[1].lower() or ".jpg"
            if ext not in _IMG_EXTS:
                ext = ".jpg"
            filename = f"product_{i+1:02d}{ext}"
            dest_path = os.path.join(dest_dir, filename)

            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                data = resp.read()

            # בדיקת גודל מינימלי — מסנן תמונות טעינה של 1x1px
            if len(data) < 2048:
                print(f"  ⏭️  מדלג (קטן מדי): {filename}")
                continue

            with open(dest_path, "wb") as f:
                f.write(data)
            paths.append(dest_path)
            print(f"  ✅ הורד: {filename}  ({len(data)//1024} KB)")

        except Exception as e:
            print(f"  ⚠️  נכשל: {url[:60]}... — {e}")

    return paths


def scrape_product_images(product_url: str, max_images: int = 6) -> list[str]:
    """
    מחלץ ומוריד תמונות מוצר מ-URL נתון.

    שלבים:
      1. מוריד HTML של הדף
      2. שולף את כל כתובות <img> (כולל data-src / lazy)
      3. Claude מסנן רק תמונות מוצר ומדרג אותן
      4. מוריד את התמונות לתיקייה זמנית

    Args:
        product_url:  URL של דף המוצר (לדוג׳: https://www.royalcanin.com/...)
        max_images:   מספר מקסימלי של תמונות (ברירת מחדל 6)

    Returns:
        list[str] — נתיבים מוחלטים לקבצים שהורדו.
                    הרשימה ריקה אם נכשל.
                    התמונה הראשונה ברשימה = תמונה ראשית.
    """
    print(f"\n🔍 סורק תמונות מוצר מ: {product_url}")

    try:
        # ── שלב 1: HTML ──
        html = _fetch_html(product_url)
        print(f"  ✅ HTML הורד ({len(html)//1024} KB)")

        # ── שלב 2: חילוץ URLs ──
        all_imgs = _extract_img_urls(html, product_url)
        print(f"  📷 {len(all_imgs)} תמונות נמצאו בדף")
        if not all_imgs:
            print("  ⚠️  לא נמצאו תמונות — נסה להזין נתיב ידנית")
            return []

        # ── שלב 3: סינון ע"י Claude ──
        print("  🤖 Claude מזהה תמונות מוצר...")
        filtered = _ask_claude_which_images(product_url, all_imgs)
        filtered = [u for u in filtered if u][:max_images]
        print(f"  ✅ {len(filtered)} תמונות מוצר זוהו")
        if not filtered:
            return []

        # ── שלב 4: הורדה ──
        tmp_dir = tempfile.mkdtemp(prefix="petway_imgs_")
        print(f"  📁 מוריד לתיקייה זמנית...")
        local_paths = _download_images(filtered, tmp_dir)
        print(f"\n✅ {len(local_paths)} תמונות מוכנות להעלאה")
        return local_paths

    except Exception as e:
        print(f"  ❌ שגיאה בסריקת תמונות: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# פרומפט ייצור תוכן
# ─────────────────────────────────────────────────────────────
def _build_system_prompt() -> str:
    return f"""אתה כותב תוכן SEO מקצועי לחנות חיות מחמד ישראלית בשם Petway.
תפקידך: לקבל פרטי מוצר ולהחזיר JSON מלא מוכן להעלאה.

━━━ כללי תוכן ━━━
• desc: משפט אחד שיווקי, עד 20 מילים.
• content: HTML עשיר ומובנה לפי המבנה הבא בדיוק —
    <h2>[שם המוצר] [משקל — רק אם יש וריאציה אחת, אחרת השמט]</h2>
    <p>פסקת פתיחה שיווקית (3-4 משפטים)</p>
    <h3>יתרונות מרכזיים</h3>
    <ul>
      <li><strong>יתרון 1</strong> — הסבר קצר</li>
      <li>...</li>
    </ul>
    <h3>הרכב ומרכיבים</h3>
    <p>תיאור המרכיבים העיקריים</p>
    <h3>הוראות שימוש</h3>
    <p>כיצד להשתמש / להגיש</p>
• seo_title: עד 60 תווים, מילת מפתח ראשית בהתחלה.
• faqs: בדיוק 4 שאלות ותשובות ספציפיות למוצר.
• brand: בחר את המותג המדויק מהרשימה הסגורה הבאה בלבד —
{BRANDS_LIST}
  אם המותג שנשלח לא מופיע ברשימה — השתמש ב"ללא הורה".

━━━ חוקים חשובים ━━━
• אל תמציא מחירים, מלאי, וריאציות — שמור אותם בדיוק כפי שנשלחו.
• החזר JSON בלבד, ללא markdown, ללא הסברים.

מבנה JSON נדרש:
{{
  "title": "...",
  "seo_title": "...",
  "brand": "...",
  "desc": "...",
  "content": "...",
  "status": "1",
  "price": "...",
  "price_discount": "...",
  "stock": "...",
  "variations": [...],
  "faqs": [{{"question": "...", "answer": "..."}}]
}}
"""


def _call_claude(messages: list, system: str = None) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=system or _build_system_prompt(),
        messages=messages,
    )
    return response.content[0].text.strip()


def _parse_json(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def generate_product_content(partial_product: dict) -> dict:
    """מקבל פרטים חלקיים, מחזיר מוצר מלא עם תוכן SEO."""
    print(f"🤖 מייצר תוכן AI עבור: {partial_product.get('title', '???')}")

    user_message = (
        "צור תוכן מלא ואיכותי למוצר הבא:\n"
        + json.dumps(partial_product, ensure_ascii=False, indent=2)
    )

    raw = _call_claude([{"role": "user", "content": user_message}])

    try:
        product = _parse_json(raw)
    except json.JSONDecodeError as e:
        print(f"⚠️  שגיאת JSON: {e}\n{raw[:400]}")
        raise

    # שמירת שדות שסופקו — לא לדרוס
    PROTECTED = {"title", "brand", "brand_value", "price", "price_discount",
                 "stock", "category_ids", "category_id", "variations", "status",
                 "image_paths", "label"}
    for key in PROTECTED:
        if partial_product.get(key):
            product[key] = partial_product[key]

    print("✅ תוכן AI נוצר בהצלחה")
    product.pop("short_content", None)
    return product


def refine_product_content(product: dict, instructions: str) -> dict:
    """מעדכן תוכן קיים לפי הוראות בשפה חופשית."""
    print(f"🤖 מעדכן: {instructions[:60]}...")

    raw = _call_claude([{
        "role": "user",
        "content": (
            "מוצר קיים:\n"
            + json.dumps(product, ensure_ascii=False, indent=2)
            + f"\n\nעדכן לפי ההוראות הבאות והחזר JSON מלא:\n{instructions}"
        )
    }])

    try:
        updated = _parse_json(raw)
        print("✅ עודכן בהצלחה")
        return updated
    except json.JSONDecodeError as e:
        print(f"⚠️  שגיאת JSON בעדכון: {e}")
        raise


def match_category(description: str) -> tuple[str, str]:
    """מחזיר (category_name, category_id) המתאים ביותר לתיאור."""
    # CATEGORIES הוא {id: name} — בונים lookup הפוך לאימות התשובה
    _name_to_id = {name: str(cid) for cid, name in CATEGORIES.items()}
    # קטגוריית fallback — "כללי" (ID 80) אם קיים, אחרת הראשונה ברשימה
    _fallback_id = "80" if 80 in CATEGORIES else str(next(iter(CATEGORIES), "80"))
    _fallback_name = CATEGORIES.get(int(_fallback_id), "כללי")

    prompt = f"""בהתאם לתיאור המוצר, בחר את הקטגוריה המתאימה ביותר מהרשימה:
{CATEGORIES_LIST}

תיאור: {description}

החזר JSON בלבד: {{"name": "...", "id": "..."}}"""

    raw = _call_claude(
        [{"role": "user", "content": prompt}],
        system="אתה עוזר סיווג מוצרים. החזר JSON בלבד."
    )
    try:
        result = _parse_json(raw)
        name = result["name"]
        # אם Claude החזיר ID — השתמש בו; אחרת חפש לפי שם
        cat_id = result.get("id") or _name_to_id.get(name, _fallback_id)
        return name, str(cat_id)
    except Exception:
        return _fallback_name, _fallback_id