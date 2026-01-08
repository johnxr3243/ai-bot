import os
import json
import httpx
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "sienna_key_999"))

# التأكد من المجلدات
for folder in ["static", "templates", "users_data"]:
    if not os.path.exists(folder): os.makedirs(folder)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
DATA_DIR = "users_data"

# ----- Translations dictionary -----
TRANSLATIONS = {
    "en": {
        "brand": "Sienna AI",
        "system_online": "SYSTEM ONLINE",
        "access_control": "Access Control",
        "login_with_discord": "LOGIN WITH DISCORD",
        "secure_note": "Secure OAuth2 Authentication",
        "overview": "OVERVIEW",
        "characters": "CHARACTERS",
        "unit_presets": "Unit Presets",
        "new_plus": "NEW +",
        "identity_name": "Identity Name",
        "neural_language": "Neural Language",
        "personality_matrix": "Personality Matrix",
        "save_deploy": "SAVE AND DEPLOY NEURAL CHANGES",
        "sex_mode_title": "Hazardous Protocol: SEX MODE",
        "sex_mode_note": "Requires unit age validation (18+)",
        "synchronized": "Synchronized!",
        "logout": "LOGOUT UNIT",
        "locked_preset_hint": "🔒 Locked preset — create New to edit",
        "welcome_dashboard_title": "Mastering The Neural Core",
        "welcome_dashboard_sub": "Your SIENNA unit is operating in",
        "messages_label": "msgs",
        "current_mode": "Current Mode",
        "active": "ACTIVE",
    },
    "ar": {
        "brand": "SIENNA AI",
        "system_online": "النظام متصل",
        "access_control": "التحكم في الدخول",
        "login_with_discord": "تسجيل الدخول بـ Discord",
        "secure_note": "مصادقة OAuth2 آمنة",
        "overview": "النظرة العامة",
        "characters": "الشخصيات",
        "unit_presets": "قوالب الوحدات",
        "new_plus": "جديد +",
        "identity_name": "اسم الشخصية",
        "neural_language": "لغة الشبكة",
        "personality_matrix": "مصفوفة الشخصية",
        "save_deploy": "حفظ ونشر التعديلات",
        "sex_mode_title": "بروتوكول خطر: وضع السكس",
        "sex_mode_note": "يتطلب التحقق من العمر (18+)",
        "synchronized": "تم التزامن!",
        "logout": "تسجيل خروج",
        "locked_preset_hint": "🔒 قالب مقفل — لإنشاء شخصية قابلة للتعديل اضغط جديد",
        "welcome_dashboard_title": "السيطرة على النواة العصبية",
        "welcome_dashboard_sub": "وحدة SIENNA تعمل في الوضع",
        "messages_label": "رسائل",
        "current_mode": "الوضع الحالي",
        "active": "نشط",
    }
}
# ------------------------------------

def default_user_file_structure():
    return {
        "user_data": {
            "activated": False,
            "state": "waiting_language",
            "language": "ar",
            "age": None,
            "bot_name": "Sienna",
            "user_name": None,
            "sex_mode": False,
            "notifications": False,
            "traits": {"curiosity":50,"sensitivity":50,"happiness":50,"sadness":20,"boldness":50,"kindness":50,"shyness":20,"intelligence":80},
            "custom_presets": []
        },
        "user_progress": {"level":1,"xp":0,"messages":0},
        "user_reminders": [],
        "user_conversation_history": []
    }

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if request.session.get("user"): return RedirectResponse(url="/dashboard")
    # choose language from session or default
    lang = request.session.get("lang", "ar")
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ar"])
    return templates.TemplateResponse("login.html", {"request": request, "t": t, "lang": lang})

@app.get("/login")
async def login():
    if not CLIENT_ID or not REDIRECT_URI:
        return RedirectResponse(url="/?error=missing_config")
    url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify"
    return RedirectResponse(url=url)

@app.get("/callback")
async def callback(request: Request, code: str):
    async with httpx.AsyncClient() as client:
        data = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        res = await client.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
        token_json = res.json()
        if "access_token" not in token_json: return RedirectResponse(url="/?error=failed")
        
        user_res = await client.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {token_json['access_token']}"})
        request.session["user"] = user_res.json()
        # store language choice if present in session already, else default
        request.session.setdefault("lang", "ar")
        return RedirectResponse(url="/dashboard")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = request.session.get("user")
    if not user: return RedirectResponse(url="/")
    
    # language selection (if query param ?lang=.. then update session)
    qlang = request.query_params.get("lang")
    if qlang in TRANSLATIONS:
        request.session["lang"] = qlang
    lang = request.session.get("lang", "ar")
    t = TRANSLATIONS.get(lang, TRANSLATIONS["ar"])

    file_path = os.path.join(DATA_DIR, f"{user['id']}.json")
    data = None
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        # create default file for this user
        data = default_user_file_structure()
        # set joined_at
        data["user_data"]["joined_at"] = None
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    settings = data.get("user_data", {})
    activated = settings.get("activated", False)
    settings["messages"] = data.get("user_progress", {}).get("messages", 0)
    # ensure defaults
    default_traits = {"curiosity": 50, "sensitivity": 50, "happiness": 50, "sadness": 20, "boldness":50,"kindness":50,"shyness":20,"intelligence":80}
    for k,v in default_traits.items():
        settings.setdefault("traits", {}).setdefault(k, v)
    settings.setdefault("bot_name", "Sienna")
    settings.setdefault("language", lang)
    settings.setdefault("sex_mode", False)
    settings.setdefault("notifications", False)
    settings.setdefault("messages", 0)
    settings.setdefault("custom_presets", [])

    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "settings": settings, "activated": activated, "t": t, "lang": lang})

@app.post("/save")
async def save(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/", status_code=303)

    form = await request.form()
    # extract values safely
    bot_name = form.get("bot_name", "").strip() or "Sienna"
    lang = form.get("lang", request.session.get("lang", "ar"))
    sex_mode = True if form.get("sex_mode") == "on" else False
    notifications = True if form.get("notifications") == "on" else False

    # traits (ensure ints)
    def int_field(name, default):
        try:
            return int(form.get(name, default))
        except:
            return default

    curiosity = int_field("curiosity", 50)
    sensitivity = int_field("sensitivity", 50)
    happiness = int_field("happiness", 50)
    sadness = int_field("sadness", 20)
    boldness = int_field("boldness", 50)
    kindness = int_field("kindness", 50)
    shyness = int_field("shyness", 20)
    intelligence = int_field("intelligence", 80)

    file_path = os.path.join(DATA_DIR, f"{user['id']}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = default_user_file_structure()

    # Update fields
    user_data = data.setdefault("user_data", {})
    user_data["bot_name"] = bot_name
    user_data["language"] = lang
    user_data["sex_mode"] = sex_mode
    user_data["notifications"] = notifications
    user_data["traits"] = {
        "curiosity": curiosity, "sensitivity": sensitivity,
        "happiness": happiness, "sadness": sadness,
        "boldness": boldness, "kindness": kindness,
        "shyness": shyness, "intelligence": intelligence
    }

    # Save custom preset if bot_name not one of locked built-in presets (Sienna, Roxy, ...)
    locked_names = {"sienna","roxy","laila","maya","sarah","luna","raven","zara","ivy","cleo"}
    if bot_name.lower() not in locked_names:
        custom_presets = user_data.setdefault("custom_presets", [])
        # replace existing with same name or append
        existing = next((p for p in custom_presets if p.get("name","").lower() == bot_name.lower()), None)
        preset_obj = {
            "name": bot_name,
            "curiosity": curiosity, "sensitivity": sensitivity, "intelligence": intelligence,
            "kindness": kindness, "happiness": happiness, "sadness": sadness,
            "boldness": boldness, "shyness": shyness,
            "locked": False
        }
        if existing:
            existing.update(preset_obj)
        else:
            custom_presets.append(preset_obj)

    # persist
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # update session language
    request.session["lang"] = lang

    return RedirectResponse(url="/dashboard?success=1", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)