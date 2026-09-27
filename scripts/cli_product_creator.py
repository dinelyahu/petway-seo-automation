import json
import re
from anthropic import Anthropic
from bot.auth import create_driver, login
from bot.products import go_to_products, create_product
from bot.chat import generate_product_content, refine_product_content, BRANDS, VALID_WEIGHTS, scrape_product_images
from bot.categories import CATEGORIES, find_category

DIVIDER = "═" * 55
client = Anthropic()


def pick_brand(prefill: str = "") -> tuple[str, str]:
    """
    מתאים מותג לרשימה הסגורה ומחזיר (שם, value).
    אם prefill נמסר (מהשיחה) — Claude מתאים אוטומטית ללא שאלה.
    רק אם לא ידוע — שואל את המנהל פעם אחת.
    """
    brands_text = "\n".join(f"{name} (value={val})" for name, val in BRANDS.items())

    def _match(query: str) -> tuple[str, str]:
        """שולח ל-Claude ומחזיר (שם, value) מהרשימה הסגורה."""
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=60,
            system='החזר JSON בלבד: {"name": "...", "value": "..."}',
            messages=[{"role": "user", "content":
                f"מצא את ההתאמה הכי קרובה ל-'{query}' מהרשימה:\n{brands_text}\n"
                f"החזר את השם והvalue המדויקים מהרשימה."
            }]
        )
        raw = re.sub(r"^```(?:json)?\s*", "", response.content[0].text.strip(), flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE).strip()
        try:
            result = json.loads(raw)
            return result["name"], result["value"]
        except Exception:
            return "ללא הורה", "0"

    # ── אם יש מותג מהשיחה — מתאים אוטומטית ──
    if prefill:
        name, value = _match(prefill)
        print(f"\n  🏷️  מותג: {name}")
        return name, value

    # ── אחרת — שואל פעם אחת ──
    print(f"\n{DIVIDER}")
    print("🏷️  מותג המוצר")
    print(DIVIDER)
    while True:
        query = input("  שם המותג: ").strip()
        if not query:
            continue
        name, value = _match(query)
        confirm = input(f"  ✅ {name} — אישור? (Enter=כן / אחר=לא): ").strip().lower()
        if confirm in ("", "כן", "y", "yes"):
            return name, value


def clean_price(value: str) -> str:
    """מחזיר מספר בלבד מתוך קלט כמו '54 שקלים', '54 ש"ח', '54₪', '54 כסף'."""
    return re.sub(r"[^\d.]", "", value).strip()


# ─────────────────────────────────────────────────────────────
# בחירת משקל מרשימה ממוספרת
# ─────────────────────────────────────────────────────────────
def pick_weight(prompt_text: str = "בחר משקל") -> str:
    """מציג רשימה ממוספרת של משקלות ומחזיר את הערך המדויק שנבחר."""
    print(f"\n  📏 {prompt_text}:")
    for i, w in enumerate(VALID_WEIGHTS, 1):
        print(f"    {i:2}. {w}")
    while True:
        choice = input("  בחירה (מספר): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(VALID_WEIGHTS):
            selected = VALID_WEIGHTS[int(choice) - 1]
            print(f"  ✅ נבחר: {selected}")
            return selected
        print(f"  ⚠️  אנא הכנס מספר בין 1 ל-{len(VALID_WEIGHTS)}")


def pick_variations() -> list:
    """מאפשר למנהל להוסיף גדלים אחד אחד עם בחירת משקל מרשימה."""
    variations = []
    print("\n  📦 הוספת גדלים/וריאציות (לפחות אחד):")

    while True:
        idx = len(variations) + 1
        print(f"\n  — גודל {idx} —")

        title = input("  שם הוריאציה (לדוג׳: שקית 2 ק\"ג): ").strip()
        if not title:
            if not variations:
                print("  ⚠️  חייב להוסיף לפחות גודל אחד.")
                continue
            break

        price = clean_price(input("  מחיר (₪): ").strip())
        discount_raw = input("  מחיר מבצע (השאר ריק אם אין): ").strip()
        discount = clean_price(discount_raw) if discount_raw else ""
        weight = pick_weight(f"בחר את המשקל של '{title}'")

        # שאלה: האם זו וריאציית דיל זוגות?
        deal_input = input("  האם זו וריאציית דיל זוגות? (כן/לא, Enter=לא): ").strip().lower()
        is_deal = deal_input in ("כן", "y", "yes")

        v = {"title": title, "price": price, "weight": weight}
        if discount:
            v["price_discount"] = discount
        if is_deal:
            v["is_deal"] = True
        variations.append(v)

        more = input("\n  להוסיף עוד גודל? (כן/לא): ").strip().lower()
        if more not in ("כן", "y", "yes", ""):
            break

    return variations


def pick_image(product_title: str) -> list[str]:
    """
    שואל את המנהל על מקור תמונת המוצר (תמונה אחת בלבד).

    אפשרויות:
      1. URL של דף מוצר — Claude שולף ומוריד את התמונה הראשית אוטומטית
      2. נתיב מקומי לקובץ תמונה
      3. דילוג — ממשיך ללא תמונה
    """
    import os
    print(f"\n{DIVIDER}")
    print("🖼️  תמונת מוצר")
    print(DIVIDER)
    print("  [1] URL של דף מוצר (Claude יחלץ אוטומטית)")
    print("  [2] נתיב מקומי לקובץ תמונה")
    print("  [3] דלג (ללא תמונה)")

    while True:
        choice = input("\n  בחירה (1/2/3): ").strip()

        # ── אפשרות 1: URL אוטומטי — מוריד תמונה אחת בלבד ──
        if choice == "1":
            url = input("  🔗 הכנס URL של דף המוצר: ").strip()
            if not url.startswith("http"):
                print("  ⚠️  URL לא תקין — חייב להתחיל ב-http")
                continue

            paths = scrape_product_images(url, max_images=1)

            if not paths:
                print("  ⚠️  לא הורדה תמונה — נסה שוב או בחר אפשרות אחרת")
                continue

            print(f"  ✅ תמונה: {os.path.basename(paths[0])}")
            return paths[:1]

        # ── אפשרות 2: נתיב ידני ──
        elif choice == "2":
            raw_path = input("  נתיב לקובץ: ").strip().strip('"').strip("'")
            if not raw_path:
                continue
            abs_p = os.path.abspath(raw_path)
            if not os.path.isfile(abs_p):
                print(f"  ⚠️  קובץ לא נמצא: {abs_p}")
                continue
            print(f"  ✅ {os.path.basename(abs_p)}")
            return [abs_p]

        # ── אפשרות 3: דילוג ──
        elif choice == "3":
            print("  ℹ️  ממשיך ללא תמונה")
            return []

        else:
            print("  ⚠️  בחר 1, 2 או 3")


def pick_categories(product_title: str) -> list[str]:
    """
    Claude מוצא 5 קטגוריות מתאימות מתוך הרשימה הסטטית.
    המנהל בוחר מספר או מחפש מחדש. Enter ריק = סיום.
    """
    # בונה טקסט לפרומפט מהקטגוריות הסטטיות
    cats_text = "\n".join(f"{cid}: {name}" for cid, name in CATEGORIES.items())
    chosen_ids = []

    def find_top_matches(query: str) -> list[dict]:
        # קודם חיפוש מקומי מהיר
        local = [(str(cid), name) for cid, name in CATEGORIES.items()
                 if query.lower() in name.lower()]
        if local:
            return [{"id": cid, "name": name} for cid, name in local[:5]]

        # אם לא נמצא — שולח ל-Claude
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=300,
            system='אתה עוזר סיווג מוצרים. החזר JSON בלבד: {"matches": [{"id": "...", "name": "..."}, ...]}',
            messages=[{"role": "user", "content":
                f"מצא את 5 הקטגוריות הכי מתאימות לבקשה: '{query}'\n\n"
                f"קטגוריות:\n{cats_text}\n\n"
                f"החזר את שם הקטגוריה בדיוק כפי שמופיע ברשימה."
            }]
        )
        raw = re.sub(r"^```(?:json)?\s*", "", response.content[0].text.strip(), flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE).strip()
        try:
            return json.loads(raw).get("matches", [])
        except Exception:
            return []

    def pick_one(label: str, required: bool = False) -> str | None:
        while True:
            hint = "חובה" if required else "Enter לסיום"
            query = input(f"\n  {label} ({hint}): ").strip()
            if not query:
                if required:
                    print("  ⚠️  חובה לבחור קטגוריה ראשית.")
                    continue
                return None

            matches = find_top_matches(query)
            if not matches:
                print("  ⚠️  לא נמצאו תוצאות — נסה מחדש.")
                continue

            print("  תוצאות:")
            for i, m in enumerate(matches, 1):
                print(f"    {i}. {m['name']}")
            print("    0. חפש מחדש")

            choice = input(f"  בחר (0-{len(matches)}): ").strip()
            if choice == "0":
                continue
            if choice.isdigit() and 1 <= int(choice) <= len(matches):
                selected = matches[int(choice) - 1]
                print(f"  ✅ נבחר: {selected['name']}")
                return str(selected["id"])
            print("  ⚠️  בחירה לא תקינה.")

    print(f"\n  🗂️  שיוך קטגוריות עבור '{product_title}':")

    # קטגוריה ראשית — חובה
    chosen_ids.append(pick_one("🔵 קטגוריה ראשית", required=True))

    # קטגוריות משניות — Enter לסיום
    print("  (Enter ריק = סיום הוספת קטגוריות)")
    while True:
        cat_id = pick_one("🟡 קטגוריה משנית", required=False)
        if cat_id is None:
            break
        chosen_ids.append(cat_id)

    return chosen_ids


# ─────────────────────────────────────────────────────────────
# פרומפט איסוף חכם
# ─────────────────────────────────────────────────────────────
GATHER_SYSTEM = """אתה עוזר חכם של חנות חיות מחמד בשם Petway.
תפקידך לאסוף מהמנהל את הפרטים הבאים בלבד: שם מוצר, מותג, מחיר בסיס.
הגדלים והקטגוריה ייאספו בשלב נפרד — אל תשאל עליהם לעולם.

━━━ כללי הזהב ━━━
1. קרא את ההודעה הראשונה היטב — אם המנהל כבר סיפק שם + מותג + מחיר, אל תשאל שוב. עבור ישירות ל-JSON.
2. אם חסרים רק פרט אחד-שניים — שאל רק עליהם, בשאלה אחת קצרה וישירה.
3. תקן שגיאות כתיב בשמות מוצרים ומותגים בשקט (רויייאל קנין → רויאל קנין, אקאנה → אקאנה).
4. אל תאמת בחזרה ואל תחזור על מה שנאמר — פשוט שאל מה חסר.
5. ענה בעברית קצרה, ישירה, ידידותית — ללא כותרות או רשימות.

━━━ מתי להחזיר JSON ━━━
ברגע שיש לך שם + מותג + מחיר — החזר JSON בלבד, ללא שום טקסט נוסף:
{
  "status": "ready",
  "data": {
    "title": "שם מתוקן ומלא של המוצר",
    "brand": "שם מותג מתוקן",
    "price": "מספר בלבד"
  }
}
"""


def gather_basic_info() -> dict:
    """שיחת צ'אט לאיסוף שם, מותג, מחיר. Claude חכם — לא שואל מה שכבר נאמר."""
    print(f"\n{DIVIDER}")
    print("🐾  Petway AI – יצירת מוצר חדש")
    print(DIVIDER)
    print("ספר לי על המוצר (שם, מותג, מחיר — אפשר הכל בבת אחת):")
    print(f"{DIVIDER}\n")

    history = []

    while True:
        user_input = input("אתה: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("יציאה", "ביטול", "exit"):
            raise KeyboardInterrupt("ביטול.")

        history.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=400,
            system=GATHER_SYSTEM,
            messages=history,
        )
        reply = response.content[0].text.strip()
        history.append({"role": "assistant", "content": reply})

        try:
            cleaned = re.sub(r"^```(?:json)?\s*", "", reply, flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
            parsed = json.loads(cleaned)
            if parsed.get("status") == "ready":
                data = parsed["data"]
                data.pop("stock", None)  # מלאי לא בשימוש
                if data.get("price"):
                    data["price"] = clean_price(data["price"])
                print(f"\n✅ {data.get('title')} | {data.get('brand')} | {data.get('price')}₪")
                return data
        except (json.JSONDecodeError, KeyError):
            pass

        print(f"\nBot: {reply}\n")


def _category_name(category_id: str) -> str:
    for name, cid in CATEGORIES.items():
        if cid == category_id:
            return name
    return category_id


def confirm_product(product: dict) -> dict:
    """תצוגה מקדימה ואפשרות תיקון לפני העלאה."""
    while True:
        print(f"\n{DIVIDER}")
        print("📦 תצוגה מקדימה לפני העלאה:")
        print(f"  כותרת:    {product.get('title', '')}")
        print(f"  SEO:      {product.get('seo_title', '')}")
        print(f"  מותג:     {product.get('brand', '')}")
        cat_ids = product.get("category_ids") or ([product["category_id"]] if product.get("category_id") else [])
        if cat_ids:
            print(f"  קטגוריות: {', '.join(cat_ids)}")
        print(f"  תיאור:    {product.get('desc', '')}")
        print(f"  מחיר:     {product.get('price', '')} ₪", end="")
        if product.get("price_discount"):
            print(f"  |  מבצע: {product['price_discount']} ₪", end="")
        print()
        if product.get("variations"):
            print("  וריאציות:")
            for v in product["variations"]:
                print(f"    • {v.get('title','')} — {v.get('price','')} ₪  [{v.get('weight','')}]")
        if product.get("faqs"):
            print(f"  שאלות:    {len(product['faqs'])} שאלות ותשובות")
        if product.get("image_paths"):
            import os
            names = ", ".join(os.path.basename(p) for p in product["image_paths"])
            print(f"  תמונות:   {len(product['image_paths'])} קבצים — {names}")
        content = product.get("content", "")
        if content:
            preview = re.sub(r"<[^>]+>", " ", content)[:200].strip()
            print(f"  תוכן SEO: {preview}...")
        print(f"{DIVIDER}")

        choice = input("\n[1] העלה לאתר  [2] תקן משהו  [3] בטל\nבחירה: ").strip()
        if choice == "1":
            return product
        elif choice == "2":
            fix = input("מה לשנות? ").strip()
            if fix:
                print("🤖 מעדכן...")
                product = refine_product_content(product, fix)
        elif choice == "3":
            raise KeyboardInterrupt("המנהל ביטל.")
        else:
            print("אנא בחר 1, 2 או 3.")


def _detect_deal_label(variations: list) -> str | None:
    """
    סורק את שמות הוריאציות ומחזיר תווית דיל אוטומטית אם מזוהה.

    כללי זיהוי:
      • "זוגות" / "זוג" / "×2" / "x2" / "2 יח"  → "💥דיל זוגות"
      • "3 יח" / "×3" / "x3" / "שלישיה"          → "💥דיל 3 יח׳"
      • "4 יח" / "×4" / "x4" / "ארבעיה"          → "💥דיל 4 יח׳"

    מחזיר None אם לא זוהה דיל.
    """
    import re

    DEAL_PATTERNS = [
        # זוגות
        (r"זוג(?:ות)?|[x×]2\b|2\s*יח", "💥דיל זוגות"),
        # 3 יחידות
        (r"שלישי(?:ה|ית)?|[x×]3\b|3\s*יח", "💥דיל 3 יח׳"),
        # 4 יחידות
        (r"ארבעי(?:ה|ית)?|[x×]4\b|4\s*יח", "💥דיל 4 יח׳"),
    ]

    combined_titles = " ".join(v.get("title", "") for v in variations).lower()

    for pattern, label in DEAL_PATTERNS:
        if re.search(pattern, combined_titles, re.IGNORECASE):
            return label

    return None


if __name__ == "__main__":
    driver = None
    try:
        # שלב 1א: שיחה חופשית — שם, מותג, מחיר
        basic = gather_basic_info()

        # שלב 1ב: התאמת מותג לרשימה הסגורה — רק אם לא נאסף כבר
        # gather_basic_info מחזיר brand כשם טקסט, צריך להמיר ל-value
        brand_name, brand_value = pick_brand(prefill=basic.get("brand", ""))
        basic["brand"] = brand_name
        basic["brand_value"] = brand_value

        # שלב 1ג: בחירת קטגוריות מהקובץ הסטטי
        basic["category_ids"] = pick_categories(basic.get("title", ""))

        # שלב 1ד: הוספת גדלים עם בחירת משקל מרשימה
        basic["variations"] = pick_variations()

        # שלב 1ד.2: זיהוי תווית דיל לפי סימון is_deal מהוריאציות
        has_deal = any(v.get("is_deal") for v in basic.get("variations", []))
        if has_deal:
            basic["label"] = "דיל זוגות"
            print(f"\n  🏷️  תווית דיל הוגדרה אוטומטית: \"דיל זוגות\"")

        # שלב 1ה: תמונת מוצר (אופציונלי)
        basic["image_paths"] = pick_image(basic.get("title", ""))

        # שלב 2: Claude מייצר תוכן SEO מלא
        print("\n🤖 מייצר תוכן SEO מלא...")
        product = generate_product_content(basic)

        # שמירת שדות שעלולים ללכת לאיבוד
        if basic.get("label"):
            product["label"] = basic["label"]

        # שלב 3: תצוגה מקדימה + אישור
        product = confirm_product(product)

        # שלב 4: התחברות לאתר והעלאה
        print("\n🔄 מתחבר לאתר...")
        driver = create_driver()
        login(driver)
        go_to_products(driver)
        print(f"DEBUG label before upload: {product.get('label')}")
        create_product(driver, product)

        print("\n🎉 סיום!")
        input("⏸️  לחץ Enter לסגור...")

    except KeyboardInterrupt as e:
        print(f"\n⛔ {e}")
    except Exception as e:
        print(f"\n❌ שגיאה: {e}")
        import traceback; traceback.print_exc()
    finally:
        if driver:
            driver.quit()