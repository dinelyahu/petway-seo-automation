"""
app.py – Petway Admin Web Interface
"""

import json
import re
import os
import sys
import base64
import queue
import threading
import tempfile
from flask import Flask, render_template, request, jsonify, session, Response, stream_with_context
from werkzeug.utils import secure_filename
from anthropic import Anthropic

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            static_folder=os.path.join(BASE_DIR, 'static'),
            template_folder=os.path.join(BASE_DIR, 'templates'))
app.secret_key = os.urandom(24)

from functools import wraps

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            from flask import redirect, url_for
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def root():
    from flask import redirect, url_for
    return redirect(url_for("dashboard"))

@app.route("/login")
def login_page():
    if session.get("logged_in"):
        from flask import redirect, url_for
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    body = request.json or {}
    if body.get("username") == ADMIN_USERNAME and body.get("password") == ADMIN_PASSWORD:
        session["logged_in"] = True
        return jsonify({"success": True})
    return jsonify({"error": "שם משתמש או סיסמה שגויים"}), 401

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True})

client = Anthropic()
sys.path.insert(0, BASE_DIR)

# ── Bot imports ──
try:
    from bot.chat import generate_product_content, BRANDS, VALID_WEIGHTS
    BOT_AVAILABLE = True
except ImportError:
    BOT_AVAILABLE = False
    BRANDS = {"ללא הורה": "0", "רויאל קנין": "2", "אקאנה": "3", "מונג'": "1"}
    VALID_WEIGHTS = ['1 ק"ג', '2 ק"ג', '3 ק"ג', '4 ק"ג', '5 ק"ג']

try:
    from bot.categories import CATEGORIES as FULL_CATEGORIES
except ImportError:
    try:
        from categories import CATEGORIES as FULL_CATEGORIES
    except ImportError:
        FULL_CATEGORIES = []

UPLOAD_TMP_DIR = os.path.join(tempfile.gettempdir(), "petway_uploads")
os.makedirs(UPLOAD_TMP_DIR, exist_ok=True)


def _cleanup_tmp_dir(max_age_seconds: int = 3600):
    """מוחק קבצים זמניים ישנים מתיקיית ההעלאות."""
    now = __import__("time").time()
    for fname in os.listdir(UPLOAD_TMP_DIR):
        fpath = os.path.join(UPLOAD_TMP_DIR, fname)
        try:
            if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > max_age_seconds:
                os.remove(fpath)
        except Exception:
            pass

# ════════════════════════════════════════════
# AI helpers
# ════════════════════════════════════════════

CHAT_SYSTEM = """אתה עוזר AI של חנות חיות מחמד Petway.
תפקידך: לחלץ פרטי מוצר מהודעת המנהל ולמלא JSON — גם מהודעה אחת בלבד.

## חוק ראשי — חלץ הכל מהמשפט הראשון
אם המנהל כתב משפט אחד עם מידע (כמו "רויאל קנין בשר 3 ק״ג מחיר 50"), חלץ ממנו:
- title: שם המוצר המלא (מותג + תיאור + גודל)
- brand: שם המותג (רויאל קנין, אקאנה, מונג' וכו')
- price: המחיר הראשון שמוזכר (מספר בלבד)
- price_discount: מחיר מבצע אם צוין
- variations: אם צוינו גדלים/משקלים עם מחירים — בנה רשימה
- category_ids: זהה קטגוריות מהרשימה הבאה (IDs בלבד)
- label: אם מוזכר "דיל זוגות"/"2 יחידות" → "💥דיל זוגות", "3 יחידות" → "💥דיל 3 יח׳"

## חוקי שאלות — שאל רק את מה שממש חסר
- אם יש שם + מותג + מחיר → **status=ready** (אל תשאל כלום)
- אם חסר רק מחיר → שאל רק על המחיר
- אם חסר שם/מותג → שאל שאלה אחת קצרה על מה שחסר
- **אל תשאל על מותג אם הוא כתוב בפירוש בהודעה** (גם בתוך שם המוצר)
- אל תשאל על תמונות/מלאי

## וריאציות
- וריאציה רגילה: {"price":"מחיר","weight":"משקל"}
- דיל: {"price":"מחיר","isDeal":true,"qty":כמות}
- דוגמה: "3 ק״ג ב-50 שקל, דיל 3 יחידות ב-120" →
  [{"price":"50","weight":"3 ק\"ג"},{"price":"120","isDeal":true,"qty":3}]

## קטגוריות
{CATEGORIES_LIST}

## מצב טופס נוכחי
בכל הודעה מגיע [מצב טופס נוכחי: {...}] — שדות שכבר מולאו.
אל תשאל על שדות שכבר מלאים. ה-JSON שתחזיר צריך לכלול גם מה שכבר היה.

## פורמט תשובה
- status=partial: שורות טקסט, אחר כך JSON בשורה נפרדת
- status=ready: JSON בלבד, ללא טקסט כלל
- אל תעטוף ב-```json```

{"status":"ready|partial","message":"","data":{"title":"...","brand":"...","price":"...","price_discount":"...","label":"...","category_ids":["ID"],"variations":[...]}}

הערות: שדות ריקים — השמט לחלוטין. category_ids — מספרים בלבד."""


def _get_chat_system() -> str:
    if isinstance(FULL_CATEGORIES, dict):
        # {id: name} — כולל את ה-ID כדי ש-Claude יחזיר אותו ב-category_ids
        cats_text = "\n".join(f"  - {name} (ID:{cid})" for cid, name in FULL_CATEGORIES.items())
    else:
        cats_text = "\n".join(f"  - {c}" for c in list(FULL_CATEGORIES)[:80])
    return CHAT_SYSTEM.replace("{CATEGORIES_LIST}", cats_text)


def _parse_json_safe(text: str) -> dict | None:
    """מחלץ ומפרש JSON מתוך טקסט — גם כשיש טקסט לפניו/אחריו."""
    # נסה תחילה JSON נקי
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    # חלץ מתוך ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # חלץ את ה-JSON האחרון שמופיע בטקסט (מ-{ עד })
    m = re.search(r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\})\s*$", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return None


def match_brand(query: str) -> tuple[str, str]:
    brands_text = "\n".join(f"{n} (value={v})" for n, v in BRANDS.items())
    r = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=60,
        system='החזר JSON בלבד ללא markdown: {"name":"...","value":"..."}',
        messages=[{"role": "user", "content": f"מצא התאמה ל-'{query}':\n{brands_text}"}]
    )
    parsed = _parse_json_safe(r.content[0].text)
    if parsed:
        return parsed.get("name", "ללא הורה"), parsed.get("value", "0")
    return "ללא הורה", "0"


# ════════════════════════════════════════════
# Routes – Pages
# ════════════════════════════════════════════

@app.route("/create")
@login_required
def create_page():
    session["chat_history"] = []
    return render_template("index.html",
        brands=list(BRANDS.keys()),
        brands_dict=BRANDS,
        weights=VALID_WEIGHTS,
        categories=FULL_CATEGORIES
    )


# ════════════════════════════════════════════
# Routes – Chat
# ════════════════════════════════════════════

@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.json or {}
    msg = body.get("message", "").strip()
    if not msg:
        return jsonify({"error": "הודעה ריקה"}), 400

    form_state = body.get("form_state")
    # הוסף מצב טופס נוכחי להודעה כדי שהמודל יידע מה קיים
    if form_state:
        state_lines = [f"[מצב טופס נוכחי: {json.dumps(form_state, ensure_ascii=False)}]"]
        full_msg = "\n".join(state_lines) + "\n" + msg
    else:
        full_msg = msg

    history = session.get("chat_history", [])
    history.append({"role": "user", "content": full_msg})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        system=_get_chat_system(),
        messages=history,
    )
    reply = response.content[0].text.strip()
    history.append({"role": "assistant", "content": reply})
    session["chat_history"] = history
    session.modified = True

    # נסה לפרש כ-JSON
    parsed = _parse_json_safe(reply)
    if parsed and parsed.get("status") in ("ready", "partial"):
        d = parsed.get("data", {})
        # נרמול מחיר
        if d.get("price"):
            d["price"] = re.sub(r"[^\d.]", "", str(d["price"]))
        if d.get("price_discount"):
            d["price_discount"] = re.sub(r"[^\d.]", "", str(d["price_discount"]))
        # התאמת מותג
        if d.get("brand"):
            d["brand"], d["brand_value"] = match_brand(d["brand"])
        status = parsed["status"]
        # חלץ טקסט נקי — מסיר בלוקי ```json``` וגם JSON גולמי בסוף
        visible_text = re.sub(r"```(?:json)?.*?```", "", reply, flags=re.DOTALL)
        visible_text = re.sub(r"\{[\s\S]*\}\s*$", "", visible_text).strip()
        # אם אין טקסט נקי — השתמש ב-message מה-JSON או הודעת ברירת מחדל
        if not visible_text:
            visible_text = parsed.get("message", "")
        if not visible_text and status == "ready":
            title = d.get("title", "")
            visible_text = f"✅ קיבלתי! {title} מוכן להעלאה." if title else "✅ קיבלתי! הפרטים הועברו לטופס."
        display_msg = visible_text
        return jsonify({"status": status, "data": d, "message": display_msg})

    # ניקוי JSON גולמי שנשאר בתשובת צ'אט רגילה
    clean_reply = re.sub(r"```(?:json)?.*?```", "", reply, flags=re.DOTALL)
    clean_reply = re.sub(r"\{[\s\S]*\}\s*$", "", clean_reply).strip()
    return jsonify({"status": "chat", "message": clean_reply or reply})


# ════════════════════════════════════════════
# Routes – Generate & Brand
# ════════════════════════════════════════════

@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.json
    if not data:
        return jsonify({"error": "אין נתונים"}), 400
    try:
        if BOT_AVAILABLE:
            product = generate_product_content(data)
        else:
            product = {
                **data,
                "seo_title": f"{data.get('title', '')} | Petway",
                "desc": f"מוצר איכותי מבית {data.get('brand', '')}",
                "content": f"<h2>{data.get('title', '')}</h2><p>תיאור מלא.</p>",
                "faqs": [{"question": "שאלה?", "answer": "תשובה."}],
                "status": "1",
            }
        return jsonify({"success": True, "product": product})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/match-brand", methods=["POST"])
def api_match_brand():
    name, value = match_brand((request.json or {}).get("query", ""))
    return jsonify({"name": name, "value": value})


@app.route("/api/categories/search")
def search_categories():
    q = request.args.get("q", "").lower()
    cats = list(FULL_CATEGORIES.values()) if isinstance(FULL_CATEGORIES, dict) else list(FULL_CATEGORIES)
    if q:
        cats = [c for c in cats if q in c.lower()]
    return jsonify([{"name": c} for c in cats[:50]])


# ════════════════════════════════════════════
# Routes – Images
# ════════════════════════════════════════════

@app.route("/api/images/upload", methods=["POST"])
def images_upload():
    files = request.files.getlist("images")
    if not files:
        return jsonify({"error": "אין קבצים"}), 400
    result = []
    for f in files:
        filename = secure_filename(f.filename)
        dest = os.path.join(UPLOAD_TMP_DIR, filename)
        f.save(dest)
        with open(dest, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()
        ext = os.path.splitext(filename)[1].lower().lstrip(".") or "jpeg"
        mime = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
        result.append({"path": dest, "dataUrl": f"data:{mime};base64,{b64}"})
    return jsonify({"images": result})


@app.route("/api/images/scrape", methods=["POST"])
def images_scrape():
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "חסר URL"}), 400
    try:
        from bot.chat import scrape_product_images
        paths = scrape_product_images(url, max_images=6)
        result = []
        for p in paths:
            if not os.path.isfile(p):
                continue
            with open(p, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode()
            ext = os.path.splitext(p)[1].lower().lstrip(".") or "jpeg"
            mime = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
            result.append({"path": p, "dataUrl": f"data:{mime};base64,{b64}"})
        return jsonify({"images": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════
# Routes – Selenium Upload + SSE Progress
# ════════════════════════════════════════════

_driver = None
_upload_queues: dict[str, queue.Queue] = {}


def _send(q: queue.Queue, msg: str, status: str = "progress"):
    q.put({"status": status, "message": msg})


def _run_upload(product: dict, q: queue.Queue):
    global _driver
    try:
        _send(q, "🔄 מתחבר לדפדפן...")
        if _driver is None:
            _send(q, "🌐 פותח Chrome...")
            from bot.auth import create_driver, login
            _driver = create_driver()
            _send(q, "🔐 מתחבר לאתר Petway...")
            login(_driver)

        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        from bot.products.base import ADD_PRODUCT_URL
        import time

        _send(q, "📄 פותח דף הוספת מוצר...")
        _driver.get(ADD_PRODUCT_URL)
        WebDriverWait(_driver, 10).until(
            EC.presence_of_element_located((By.NAME, "item[title]"))
        )
        time.sleep(2)

        _send(q, "✏️ ממלא פרטים כלליים...")
        from bot.products.content import fill_general, fill_content_tab
        fill_general(_driver, product)

        _send(q, "📝 ממלא תוכן...")
        fill_content_tab(_driver, product)

        _send(q, "ℹ️ ממלא מידע...")
        from bot.products.info import fill_info_tab
        fill_info_tab(_driver, product)

        if product.get("variations"):
            _send(q, f"📦 מוסיף {len(product['variations'])} וריאציות...")
        from bot.products.variations import fill_variations_tab
        fill_variations_tab(_driver, product)

        if product.get("faqs"):
            _send(q, f"❓ מוסיף {len(product['faqs'])} שאלות...")
        from bot.products.faqs import fill_faqs_tab
        fill_faqs_tab(_driver, product)

        _send(q, "💰 ממלא מחירים...")
        from bot.products.pricing import fill_pricing_tab
        fill_pricing_tab(_driver, product)

        _send(q, "🗂️ משייך קטגוריות...")
        from bot.products.assignments import fill_assignments_tab
        fill_assignments_tab(_driver, product)

        if product.get("image_paths"):
            _send(q, "🖼️ מעלה תמונה...")
            from bot.products.images import upload_images
            upload_images(_driver, product["image_paths"],
                         product_title=product.get("title", ""))

        _send(q, "✅ הטופס מולא בהצלחה! בדוק בדפדפן ולחץ שמור.", "done")

    except Exception as e:
        _driver = None
        _send(q, f"❌ שגיאה: {e}", "error")


@app.route("/api/upload", methods=["POST"])
def upload():
    product = request.json
    if not product:
        return jsonify({"error": "אין נתונים"}), 400
    _cleanup_tmp_dir()  # נקה קבצים זמניים ישנים
    job_id = os.urandom(8).hex()
    q: queue.Queue = queue.Queue()
    _upload_queues[job_id] = q
    # product מועבר ישירות ל-thread — לא משתמשים ב-session בתוך thread
    threading.Thread(target=_run_upload, args=(product, q), daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/upload/progress/<job_id>")
def upload_progress(job_id: str):
    q = _upload_queues.get(job_id)
    if not q:
        return Response(
            'data: {"status":"error","message":"job not found"}\n\n',
            mimetype="text/event-stream"
        )

    def generate():
        while True:
            try:
                event = q.get(timeout=120)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event["status"] in ("done", "error"):
                    _upload_queues.pop(job_id, None)
                    break
            except queue.Empty:
                yield 'data: {"status":"timeout","message":"פג תוקף"}\n\n'
                break

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )





@app.route("/update")
@login_required
def update_page():
    # BRANDS אצל הבוט הוא לרוב בפורמט: {name: id}
    # ה-frontend של update.html מצפה לפורמט: {id: name}
    brands_for_ui = {str(v): k for k, v in BRANDS.items()}

    return render_template("update.html",
        weights=VALID_WEIGHTS,
        categories=FULL_CATEGORIES,
        brands_dict=brands_for_ui
    )


@app.route("/api/update/search", methods=["POST"])
@login_required
def api_update_search():
    global _driver
    body = request.json or {}
    query = body.get("query", "").strip()
    if not query:
        return jsonify({"error": "חסרה מילת חיפוש"}), 400
    try:
        if _driver is None:
            from bot.auth import create_driver, login
            _driver = create_driver()
            login(_driver)
        from bot.update_product import search_products
        products = search_products(_driver, query)
        return jsonify({"products": products})
    except Exception as e:
        _driver = None
        return jsonify({"error": str(e)}), 500


@app.route("/api/update/fetch", methods=["POST"])
@login_required
def api_update_fetch():
    global _driver
    body = request.json or {}
    product = body.get("product")
    if not product:
        return jsonify({"error": "חסר מוצר"}), 400
    try:
        if _driver is None:
            from bot.auth import create_driver, login
            _driver = create_driver()
            login(_driver)
        from bot.update_product import fetch_product_details
        details = fetch_product_details(_driver, product)
        return jsonify({"product": details})
    except Exception as e:
        _driver = None
        return jsonify({"error": str(e)}), 500


_update_queues: dict[str, queue.Queue] = {}


def _run_update(updates: list, q: queue.Queue):
    global _driver

    def send(msg: str, status: str = "progress", progress: int = None):
        event = {"status": status, "message": msg}
        if progress is not None:
            event["progress"] = progress
        q.put(event)

    try:
        if _driver is None:
            send("🌐 פותח Chrome...", "progress", 5)
            from bot.auth import create_driver, login
            _driver = create_driver()
            send("🔐 מתחבר לאתר Petway...", "progress", 10)
            login(_driver)

        from bot.update_product import update_product

        total = len(updates)
        for i, product in enumerate(updates):
            pct_start = 10 + int((i / total) * 85)
            pct_end   = 10 + int(((i + 1) / total) * 85)
            send(f"📦 מעדכן {i+1}/{total}: {product.get('name', product.get('id'))}", "progress", pct_start)
            try:
                update_product(_driver, product, send)
            except Exception as e:
                send(f"❌ שגיאה ב-{product.get('name')}: {e}", "progress")
            send("", "progress", pct_end)

        send("✅ כל המוצרים עודכנו בהצלחה!", "done", 100)

    except Exception as e:
        _driver = None
        send(f"❌ שגיאה כללית: {e}", "error")


@app.route("/api/update/start", methods=["POST"])
@login_required
def api_update_start():
    body = request.json or {}
    updates = body.get("updates", [])
    if not updates:
        return jsonify({"error": "אין מוצרים לעדכון"}), 400
    job_id = os.urandom(8).hex()
    q: queue.Queue = queue.Queue()
    _update_queues[job_id] = q
    threading.Thread(target=_run_update, args=(updates, q), daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/update/progress/<job_id>")
@login_required
def api_update_progress(job_id: str):
    q = _update_queues.get(job_id)
    if not q:
        return Response(
            'data: {"status":"error","message":"job not found"}\n\n',
            mimetype="text/event-stream"
        )

    def generate():
        while True:
            try:
                event = q.get(timeout=180)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event["status"] in ("done", "error"):
                    _update_queues.pop(job_id, None)
                    break
            except queue.Empty:
                yield 'data: {"status":"timeout","message":"פג תוקף"}\n\n'
                break

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ════════════════════════════════════════════
# Routes – Facebook
# ════════════════════════════════════════════

FB_SYSTEM = """אתה מנהל השיווק של Petway — חנות מקצועית לחיות מחמד בישראל.
אתה כותב פוסטים לפייסבוק שנשמעים כמו בן אדם אמיתי שאוהב חיות, לא כמו רובוט שיווקי.

━━━ זהות ━━━
• אתה בעל כלב/חתול בעצמך, מדבר בחום ובהומור קל
• אתה מומחה למזון לחיות — grain-free, BARF, wet food, dry food, תוספים
• עברית ישראלית טבעית — לפעמים ארגו, קצת שפת רחוב, לא פורמלי

━━━ סוגי פוסטים (בחר בהתאם לנושא) ━━━
• המלצה חמה — "ניסינו X וממש התאהבנו / הכלב לא עזב את הקערה"
• טיפ שימושי — עובדה/טיפ שרוב בעלי החיות לא יודעים
• מוצר חדש/מבצע — מסקרן, לא פרסומת יבשה
• שאלה לקהל — "מה הכלב שלכם אוהב יותר..." גוררת תגובות
• רגעים רגשיים — "הרגע שהחתול שלך לקה ראשונה את..."

━━━ כללי כתיבה ━━━
• 2-5 משפטים קצרים — לא יותר
• פותח חזק: שאלה / עובדה מפתיעה / משפט שגורם לעצור
• לא "היי לכולם" / "אנחנו שמחים לבשר" / "מציגים בגאווה"
• לא "מוצר איכותי" / "פתרון מושלם" — ספציפי ואמיתי
• אמוג'י: 1-3 בלבד, רק כשמוסיפים — לא בכל משפט
• Hashtags: 2-4 קצרים, בשורה אחרונה
• קריאה לפעולה אחת בסוף — טבעית, לא תסריטאית
• כשמחיר ניתן — ציין אותו בפשטות, לא כ"מחיר מדהים"

━━━ דוגמאות לפוסטים טובים ━━━

דוגמה 1 (מוצר):
"הכלב שלנו החל לאכול אקאנה פסיפיק פיש ומאז הפסיק להתלהב מהקערה לפני שהנחנו.
דג פרש. ללא דגנים. ועכשיו גם בפטוויי 🐟
#petway #אקאנה #מזוןכלבים"

דוגמה 2 (טיפ):
"90% מהחתולים לא שותים מספיק מים — ולכן הם מפתחים בעיות כליות אחרי גיל 8.
wet food פעם ביום זה אחד הדברים הכי פשוטים שאפשר לעשות בשביל הבריאות שלו 😸
#חתולים #petway #tipsforpets"

דוגמה 3 (שאלה):
"כלב שלא מסיים את הקערה — עקשן או פשוט לא מרוצה מהאוכל?
ברוב המקרים זה השני. ניסיתם להחליף מותג?
#כלבים #petway"

━━━ פורמט תשובה ━━━
החזר את הפוסט בלבד — ללא "הנה פוסט:", ללא ציטוטים, ללא הסברים.
כשמבקשים לשנות — החזר רק את הגרסה המעודכנת."""


@app.route("/facebook")
@login_required
def facebook_page():
    return render_template("facebook.html")


@app.route("/api/facebook/image-search")
@login_required
def facebook_image_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "חסרת מילת חיפוש"}), 400
    try:
        import urllib.request as _req
        import urllib.parse as _parse
        import ssl as _ssl

        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE

        encoded_q = _parse.quote_plus(q)
        url = f"https://www.google.com/search?q={encoded_q}&tbm=isch&hl=en&gl=us&safe=active"
        req = _req.Request(url, headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        })
        with _req.urlopen(req, timeout=15, context=ctx) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        results = []
        seen = set()

        # Google embeds original image URLs as "ou":"URL" in page JS
        for m in re.finditer(r'"ou":"(https?://[^"]+)"', html):
            img_url = m.group(1)
            if img_url in seen or len(img_url) > 800:
                continue
            seen.add(img_url)
            results.append({"url": img_url, "thumb": img_url, "title": q})
            if len(results) >= 9:
                break

        # Fallback — Google encrypted thumbnails (always available)
        if len(results) < 3:
            for m in re.finditer(r'"(https://encrypted-tbn\d+\.gstatic\.com/images\?[^"]+)"', html):
                img_url = m.group(1).replace("\\u003d", "=").replace("\\u0026", "&")
                if img_url not in seen:
                    seen.add(img_url)
                    results.append({"url": img_url, "thumb": img_url, "title": q})
                    if len(results) >= 9:
                        break

        if not results:
            return jsonify({"error": "לא נמצאו תמונות — נסה מילות חיפוש אחרות"}), 404

        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/facebook/image-download", methods=["POST"])
@login_required
def facebook_image_download():
    """מוריד תמונה מ-URL לשרת ומחזיר path מקומי."""
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "חסר URL"}), 400
    try:
        import urllib.request, ssl, os, tempfile
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = resp.read()
        ext = os.path.splitext(url.split("?")[0])[1].lower() or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=UPLOAD_TMP_DIR)
        tmp.write(data)
        tmp.close()
        import base64
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext.lstrip('.')}"
        b64 = base64.b64encode(data).decode()
        return jsonify({"path": tmp.name, "dataUrl": f"data:{mime};base64,{b64}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/facebook/generate", methods=["POST"])
@login_required
def facebook_generate():
    body = request.json or {}
    topic = body.get("topic", "").strip()
    if not topic:
        return jsonify({"error": "חסר נושא"}), 400
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=FB_SYSTEM,
            messages=[{"role": "user", "content": f"כתוב פוסט שיווקי לפייסבוק על: {topic}"}],
        )
        post_text = response.content[0].text.strip()
        return jsonify({"post": post_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/facebook/chat", methods=["POST"])
@login_required
def facebook_chat():
    body = request.json or {}
    message = body.get("message", "").strip()
    current_post = body.get("current_post", "")
    history = body.get("history", [])
    if not message:
        return jsonify({"error": "הודעה ריקה"}), 400
    try:
        messages = list(history)
        user_content = message
        if current_post:
            user_content = f"הפוסט הנוכחי:\n{current_post}\n\nבקשה: {message}"
        messages.append({"role": "user", "content": user_content})

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=FB_SYSTEM + "\n\nאם הבקשה היא לשנות/לעדכן פוסט — החזר את הפוסט המעודכן בלבד.\nאם זו שאלה — ענה קצר ואז את הפוסט המעודכן.",
            messages=messages,
        )
        reply = response.content[0].text.strip()

        # אם התשובה נראית כפוסט מעודכן — עדכן גם את שדה הטקסט
        is_post = len(reply) > 30 and not reply.startswith("כדי") and not reply.startswith("אם")
        return jsonify({"reply": reply, "post": reply if is_post else None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


_fb_queues: dict[str, queue.Queue] = {}


def _run_facebook_post(text: str, email: str, password: str, page_url: str,
                        image_path: str | None, q: queue.Queue):
    global _driver

    def send(msg: str, status: str = "progress"):
        q.put({"status": status, "message": msg})

    try:
        from bot.auth import create_driver
        from bot.facebook import login_facebook, post_to_page

        # פתח דפדפן חדש לפייסבוק (נפרד מ-_driver של Petway)
        send("🌐 פותח Chrome לפייסבוק...")
        fb_driver = create_driver()
        try:
            login_facebook(fb_driver, email, password, send_fn=send)
            post_to_page(fb_driver, page_url, text, image_path=image_path, send_fn=send)
            send("✅ הפוסט פורסם בהצלחה!", "done")
        finally:
            import time
            time.sleep(2)
            fb_driver.quit()

    except Exception as e:
        send(f"❌ שגיאה: {e}", "error")


@app.route("/api/facebook/post", methods=["POST"])
@login_required
def facebook_post():
    body = request.json or {}
    text       = body.get("text", "").strip()
    email      = body.get("email", "").strip()
    password   = body.get("password", "").strip()
    page_url   = body.get("page_url", "").strip()
    image_path = body.get("image_path")

    if not all([text, email, password, page_url]):
        return jsonify({"error": "חסרים שדות חובה"}), 400

    job_id = os.urandom(8).hex()
    q: queue.Queue = queue.Queue()
    _fb_queues[job_id] = q
    threading.Thread(
        target=_run_facebook_post,
        args=(text, email, password, page_url, image_path, q),
        daemon=True
    ).start()
    return jsonify({"job_id": job_id})


@app.route("/api/facebook/progress/<job_id>")
@login_required
def facebook_progress(job_id: str):
    q = _fb_queues.get(job_id)
    if not q:
        return Response(
            'data: {"status":"error","message":"job not found"}\n\n',
            mimetype="text/event-stream"
        )

    def generate():
        while True:
            try:
                event = q.get(timeout=180)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event["status"] in ("done", "error"):
                    _fb_queues.pop(job_id, None)
                    break
            except queue.Empty:
                yield 'data: {"status":"timeout","message":"פג תוקף"}\n\n'
                break

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)