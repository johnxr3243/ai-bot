import discord
from discord.ext import commands, tasks  # تم إضافة tasks للمراقبة
import os
import json
import random
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=BOT_PREFIX,
    intents=intents,
    help_command=None
)

# تخزين البيانات
user_data = {}
user_progress = {}
user_reminders = {}
user_conversations = {}
notified_users = set()
user_last_active = {}
user_conversation_history = {}
file_last_modified = {}  # لتتبع وقت تعديل الملفات

# مجلد تخزين بيانات المستخدمين
DATA_DIR = "users_data"

# تحميل البيانات من الملفات المنفصلة
def load_data():
    global user_data, user_progress, user_reminders, user_conversations, user_conversation_history
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"✅ تم إنشاء مجلد البيانات: {DATA_DIR}")
            return

        count = 0
        for filename in os.listdir(DATA_DIR):
            if filename.endswith(".json"):
                user_id = filename[:-5]
                file_path = os.path.join(DATA_DIR, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    user_data[user_id] = data.get("user_data", {})
                    user_progress[user_id] = data.get("user_progress", {})
                    user_reminders[user_id] = data.get("user_reminders", {})
                    user_conversations[user_id] = data.get("user_conversations", {})
                    user_conversation_history[user_id] = data.get("user_conversation_history", [])
                    file_last_modified[user_id] = os.path.getmtime(file_path)
                    count += 1
        print(f"✅ تم تحميل بيانات {count} مستخدم من ملفات منفصلة")
    except Exception as e:
        print(f"❌ خطأ في تحميل البيانات: {e}")

# حفظ كل مستخدم في ملفه الخاص
def save_data():
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        all_user_ids = set(list(user_data.keys()) + list(user_progress.keys()) +
                          list(user_reminders.keys()) + list(user_conversation_history.keys()))

        for user_id in all_user_ids:
            data = {
                "user_data": user_data.get(user_id, {}),
                "user_progress": user_progress.get(user_id, {}),
                "user_reminders": user_reminders.get(user_id, {}),
                "user_conversations": user_conversations.get(user_id, {}),
                "user_conversation_history": user_conversation_history.get(user_id, []),
                "last_save": datetime.now().isoformat()
            }
            file_path = os.path.join(DATA_DIR, f"{user_id}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            file_last_modified[user_id] = os.path.getmtime(file_path)
    except Exception as e:
        print(f"❌ خطأ في حفظ البيانات: {e}")

def save_user_data(user_id):
    """
    احفظ بيانات مستخدم واحد فقط إلى ملفه وحدث file_last_modified.
    """
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        uid = str(user_id)
        data = {
            "user_data": user_data.get(uid, {}),
            "user_progress": user_progress.get(uid, {}),
            "user_reminders": user_reminders.get(uid, {}),
            "user_conversations": user_conversations.get(uid, {}),
            "user_conversation_history": user_conversation_history.get(uid, []),
            "last_save": datetime.now().isoformat()
        }
        file_path = os.path.join(DATA_DIR, f"{uid}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        file_last_modified[uid] = os.path.getmtime(file_path)
    except Exception as e:
        print(f"❌ خطأ في حفظ بيانات المستخدم {user_id}: {e}")

# مهمة مراقبة التحديثات من الموقع
@tasks.loop(seconds=2)
async def watch_files():
    if not os.path.exists(DATA_DIR): return
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            user_id = filename[:-5]
            file_path = os.path.join(DATA_DIR, filename)
            current_mtime = os.path.getmtime(file_path)

            if user_id in file_last_modified:
                if current_mtime > file_last_modified[user_id]:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        user_data[user_id] = data.get("user_data", {})
                        user_progress[user_id] = data.get("user_progress", {})
                        user_reminders[user_id] = data.get("user_reminders", {})
                        user_conversation_history[user_id] = data.get("user_conversation_history", [])

                    file_last_modified[user_id] = current_mtime
                    print(f"🔄 تم تحديث بيانات المستخدم {user_id} من الموقع.")
                    try:
                        user = await bot.fetch_user(int(user_id))
                        await user.send("```css\n[ ✨ تم تحديث إعداداتي من الموقع بنجاح! ]\n```")
                    except: pass
            else:
                file_last_modified[user_id] = current_mtime

@bot.event
async def on_ready():
    print(f"✨ **البوت شغال** دلوقتي كـ {bot.user}")
    load_data()
    watch_files.start()
    bot.loop.create_task(check_inactive_users())
    bot.loop.create_task(check_reminders_task())

async def get_ai_response(user_message, user_id):
    """
    ترجع قائمة رسائل (list) في مراحل الإعداد حتى تظهر كل جزء كرسالة منفصلة،
    وفي وضع الشات العادي ترجع سترينج واحد (رد الـ AI).
    التنسيق محاكٍ لشكل الصور: بلوكات كود ملونة ثم رسائل نصية، وفي النهاية ملخص داخل بلوك.
    """
    uid = str(user_id)
    if uid not in user_data:
        load_single_user(uid)

    data = user_data.get(uid, {})
    state = data.get("state", "waiting_language")
    lang = data.get("language", "ar")
    name = data.get("bot_name", "Sienna")

    # ----------------- waiting_language -----------------
    if state == "waiting_language":
        choice = user_message.strip().lower()
        if choice in ["عربي", "1", "ar"]:
            data["language"], data["state"] = "ar", "waiting_user_name"
            save_user_data(uid)
            # بلوك أخضر ثم طلب الاسم كسطر منفصل
            return ["```diff\n+ تم اختيار اللغة العربية +\n```", "اكتب اسمك الحقيقي:"]
        elif choice in ["english", "2", "en"]:
            data["language"], data["state"] = "en", "waiting_user_name"
            save_user_data(uid)
            return ["```diff\n+ English selected +\n```", "Write your real name:"]
        # إذا لم يفهم المستخدم، نعيد رسالة واضحة
        return "جرب تاني: عربي أو English"

    # ----------------- waiting_user_name -----------------
    if state == "waiting_user_name":
        name_candidate = user_message.strip()
        if 2 <= len(name_candidate) <= 20:
            data["user_name"], data["state"] = name_candidate, "waiting_age"
            save_user_data(uid)
            # بلوك ترحيبي (قوسين) ثم جملة تطلب العمر مع توضيح (رقم فقط) كسطر منفصل
            welcome_block = f"```css\n[ أهلاً وسهلاً يا {data['user_name']} ]\n```"
            prompt_line = "عشان نكمل، اكتب عمرك:"
            note = "`(رقم فقط)`"
            return [welcome_block, prompt_line, note]
        return "الاسم لازم بين 2 و20 حرف."

    # ----------------- waiting_age -----------------
    if state == "waiting_age":
        try:
            age = int(user_message.strip())
            if age < 14:
                return "عذراً، السن غير مسموح."
            data["age"], data["state"] = age, "waiting_bot_name"
            save_user_data(uid)
            # بلوك تأكيد أخضر ثم طلب اسم البوت مع ملاحظة الطول
            confirm_block = f"```diff\n+ تم حفظ العمر : {age} سنة +\n```"
            prompt_line = "قولي اسمي اللي تحبه:"
            note = "`(بين 2 و20 حرف)`"
            return [confirm_block, prompt_line, note]
        except:
            return "pls activate first."

    # ----------------- waiting_bot_name -----------------
    if state == "waiting_bot_name":
        bot_name_candidate = user_message.strip()
        # ضع الاسم واعمل التفعيل
        data["bot_name"], data["state"], data["activated"] = bot_name_candidate, "normal", True
        save_user_data(uid)
        # بلوك اكتمال إعداد، ثم ملخص جميل داخل بلوك كود مُؤطَّر، ثم رسالة تشجيع
        done_block = "```css\n[ ✓ تم اكتمال الإعداد بنجاح ]\n```"
        # عمل ملخص في شكل صندوق ASCII داخل بلوك كود
        summary = (
            "```ini\n"
            "┌────────────────────────────┐\n"
            f"│ الاسم    : {data.get('user_name','')}\n"
            f"│ العمر   : {data.get('age','')} سنة\n"
            f"│ اسمي الآن: {data.get('bot_name','')}\n"
            "└────────────────────────────┘\n"
            "```"
        )
        hint = "✨ يمكنك البدء بالحديث معي الآن"
        return [done_block, summary, hint]

    # ----------------- Normal chat -----------------
    if not data.get("activated"):
        return "**لازم** تكمل الإعداد الأول."

    # جلب السمات 8 من الملف (للتوافق مع الموقع)
    traits = data.get("traits", {"curiosity": 50, "sensitivity": 50, "happiness": 50, "sadness": 20, "boldness": 50, "kindness": 50, "shyness": 20, "intelligence": 80})
    trait_desc = f"(Personality: Curiosity {traits['curiosity']}%, Sensitivity {traits['sensitivity']}%, Intelligence {traits['intelligence']}%, Boldness {traits['boldness']}%)"

    system_prompt = f"انتي {name} بنت مصرية عادية 20-22 سنة. شخصيتك حقيقية. {trait_desc} "
    system_prompt += "بتزعلي بتفرحي بتضايقي بتغيري مزاجك حسب الكلام. استخدمي إيموجي واحد بس (😭 أو 🤭 أو 🤤). محترمه من غير سكس. ردي بذكاء."

    if data.get("sex_mode"):
        system_prompt += " الآن في وضع سكس كوني جريئة جدًا وصريحة فاحشة ووصفي بالتفصيل."

    if uid not in user_conversation_history:
        user_conversation_history[uid] = []
    user_conversation_history[uid].append({"role": "user", "content": user_message, "time": datetime.now().isoformat()})

    try:
        response = await client.chat.completions.create(
            model="x-ai/grok-4.1-fast",
            messages=[{"role": "system", "content": system_prompt}] + user_conversation_history[uid][-5:],
            temperature=0.9,
            max_tokens=500 if data.get("sex_mode") else 250,
        )
        ai_reply = response.choices[0].message.content.strip()
        user_conversation_history[uid].append({"role": "assistant", "content": ai_reply, "time": datetime.now().isoformat()})
        save_user_data(uid)
        return ai_reply
    except Exception as e:
        return f"خطأ: {e}"

@bot.command()
async def activate(ctx, *, code: str):
    if ctx.guild is not None:
        await ctx.send("```diff\n- هذه الخاصية في الرسائل الخاصة فقط\n```")
        return

    if code.strip() == "MYSECRET123":
        user_id_str = str(ctx.author.id)
        user_data[user_id_str] = {
            "activated": False,
            "state": "waiting_language",
            "language": None,
            "age": None,
            "bot_name": "Sienna",
            "user_name": None,
            "sex_mode": False,
            "joined_at": datetime.now().isoformat()
        }
        user_last_active[user_id_str] = datetime.now()
        save_user_data(user_id_str)

        # رسالة التفعيل الأولية - بلوك + سطر اختيار اللغة
        await ctx.send("""```css
[ ✓ تم تفعيل البوت بنجاح ]
```✨ اختر لغة المحادثة:
`1. عربي`   `2. English`""")
    else:
        await ctx.send("```diff\n- كود التفعيل غير صحيح\n```**جرب مرة أخرى:**")

@bot.command(aliases=['mode'])
async def sex(ctx, mode: str = None):
    if ctx.guild is None and str(ctx.author.id) in user_data and user_data[str(ctx.author.id)].get("activated", False):
        data = user_data[str(ctx.author.id)]
        if data.get("age", 0) < 18:
            await ctx.send("```diff\n- العمر أقل من 18 سنة\n```**غير مسموح بهذه الخاصية.**")
            return

        if mode and mode.lower() in ['off', 'خلاص', 'كفايه', 'وقفي']:
            data["sex_mode"] = False
        elif mode and mode.lower() in ['on', 'تشغيل', 'شغل']:
            data["sex_mode"] = True
        else:
            data["sex_mode"] = not data.get("sex_mode", False)

        status = "مفعل" if data["sex_mode"] else "معطل"
        status_en = "ON" if data["sex_mode"] else "OFF"

        lang = data.get("language", "ar")
        if lang == "ar":
            await ctx.send(f"```css\n[ وضع السكس {status} ]\n```")
        else:
            await ctx.send(f"```css\n[ Sex Mode {status_en} ]\n```")

        user_id_str = str(ctx.author.id)
        if not data.get("sex_mode"):
            try:
                user_conversation_history[user_id_str] = []
            except Exception:
                user_conversation_history[user_id_str] = []

        save_user_data(user_id_str)
    else:
        await ctx.send("```diff\n- يجب تفعيل البوت أولاً\n```**استخدم:** `!activate [كود]`")

@bot.command(aliases=['مساعدة', 'مساعد', 'h', 'commands', 'help'])
async def show_help(ctx):
    if ctx.guild is not None:
        return

    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        await ctx.send("```diff\n- يجب تفعيل البوت أولاً\n```**استخدم:** `!activate [كود]`")
        return

    lang = user_data[user_id_str].get("language", "ar")

    if lang == "ar":
        help_text = """```css
[ 🤖 أوامر البوت ]
┌─────────────────────┐
• !activate [كود]   ← تفعيل البوت
• !help             ← عرض هذه القائمة
• !profile          ← ملفك الشخصي
• !level            ← مستوى وخبرتك
• !truth            ← سؤال صراحة
• !luck             ← اختبار الحظ
• !reminder [وقت] [رسالة] ← إضافة تذكير

• !sex              ← تبديل وضع السكس
• !sex on           ← تشغيل وضع السكس
• !sex off          ← إيقاف وضع السكس

• !clearchat        ← مسح المحادثة
• !format           ← مسح بياناتك
└─────────────────────┘
```**💬 كلمني طبيعي وهرد عليك!**"""
    else:
        help_text = """```css
[ 🌐 Bot Commands ]
┌─────────────────────┐
• !activate [code]  ← Activate bot
• !help             ← Show this list
• !profile          ← Your profile
• !level            ← Level & XP
• !truth            ← Truth question
• !luck             ← Test your luck
• !reminder [time] [message] ← Add reminder

• !sex              ← Toggle sex mode
• !sex on           ← Turn on sex mode
• !sex off          ← Turn off sex mode

• !clearchat        ← Clear chat
• !format           ← Delete your data
└─────────────────────┘
```**💬 Talk to me naturally!**"""

    await ctx.send(help_text)

@bot.command(aliases=['بروفايلي', 'profile'])
async def my_profile(ctx):
    if ctx.guild is not None:
        return

    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        await ctx.send("```diff\n- يجب تفعيل البوت أولاً\n```**استخدم:** `!activate [كود]`")
        return

    data = user_data[user_id_str]
    progress = user_progress.get(user_id_str, {"level": 1, "xp": 0, "messages": 0})
    lang = data.get("language", "ar")

    if lang == "ar":
        sex_status = "✅ مفعل" if data.get("sex_mode") else "❌ معطل"
        profile = f"""```css
[ 👤 الملف الشخصي ]
┌─────────────────────┐
     الاسم: {data.get('user_name', 'غير معروف')}
     العمر: {data.get('age', 'غير معروف')} سنة
     اللغة: {data.get('language', 'عربي')}
     انضم: {data.get('joined_at', 'غير معروف')[:10]}
└─────────────────────┘

[ 📊 الإحصائيات ]
┌─────────────────────┐
     المستوى: {progress['level']}
     الخبرة: {progress['xp']}/{progress['level']*100}
     الرسائل: {progress['messages']}
     وضع سكس: {sex_status}
└─────────────────────┘
```"""
    else:
        sex_status = "✅ ON" if data.get("sex_mode") else "❌ OFF"
        profile = f"""```css
[ 👤 Your Profile ]
┌─────────────────────┐
     Name: {data.get('user_name', 'Unknown')}
     Age: {data.get('age', 'Unknown')} years
     Language: {data.get('language', 'Arabic')}
     Joined: {data.get('joined_at', 'Unknown')[:10]}
└─────────────────────┘

[ 📊 Statistics ]
┌─────────────────────┐
     Level: {progress['level']}
     XP: {progress['xp']}/{progress['level']*100}
     Messages: {progress['messages']}
     Sex Mode: {sex_status}
└─────────────────────┘
```"""

    await ctx.send(profile)

@bot.command(aliases=['مستوى', 'level'])
async def rank(ctx):
    if ctx.guild is not None:
        return

    user_id_str = str(ctx.author.id)
    if user_id_str in user_progress:
        data = user_progress[user_id_str]
        user_data_obj = user_data.get(user_id_str, {})
        lang = user_data_obj.get("language", "ar")
        level_bar = "█" * min(data['level'], 10) + "░" * (10 - min(data['level'], 10))

        if lang == "ar":
            await ctx.send(f"""```css
[ 📊 مستوى {data['level']} ]
┌─────────────────────┐
     الخبرة: {data['xp']}/{data['level']*100}
     الرسائل: {data['messages']}
     التقدم: [{level_bar}]
└─────────────────────┘
```""")
        else:
            await ctx.send(f"""```css
[ 📊 Level {data['level']} ]
┌─────────────────────┐
     XP: {data['xp']}/{data['level']*100}
     Messages: {data['messages']}
     Progress: [{level_bar}]
└─────────────────────┘
```""")
    else:
        await ctx.send("```diff\n- لا توجد بيانات\n```**ابدأ بالتحدث مع البوت!**")

@bot.command(aliases=['صراحة', 'truth'])
async def truth_or_dare(ctx):
    if ctx.guild is not None:
        return
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        return
    lang = user_data[user_id_str].get("language", "ar")
    if lang == "ar":
        questions = ["**آخر مرة** كذبت فيها على مين؟", "**أكثر حاجة** تخاف منها في الحياة؟", "**أحلامك** السرية إيه؟", "**لو تقدر** تغير حاجة في ماضيك، هتغير إيه؟", "**أكبر غلطة** عملتها في حياتك؟"]
    else:
        questions = ["**Last time** you lied to someone?", "**Biggest fear** you have in life?", "**Secret dreams** you have?", "**If you could** change one thing in your past?", "**Biggest mistake** you made in life?"]
    await ctx.send(f"""```css\n[ ❓ سؤال صراحة ]\n```{random.choice(questions)}""")

@bot.command(aliases=['حظ', 'luck'])
async def luck_test(ctx):
    if ctx.guild is not None:
        return
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        return
    luck = random.randint(1, 100)
    user_data_obj = user_data.get(user_id_str, {})
    lang = user_data_obj.get("language", "ar")
    luck_bar = "🍀" * (luck // 20) + "⬜" * (5 - (luck // 20))
    if lang == "ar":
        result = "🎯 **ممتاز**" if luck > 80 else "😊 **كويس**" if luck > 60 else "😐 **متوسط**" if luck > 40 else "😕 **مش كويس**" if luck > 20 else "☹️ **وحش**"
        await ctx.send(f"""```css\n[ 🎰 اختبار الحظ ]\n┌─────────────────────┐\n     النسبة: {luck}%\n     التقييم: {result}\n     الرمز: [{luck_bar}]\n└─────────────────────┘\n```""")
    else:
        result = "🎯 **Excellent**" if luck > 80 else "😊 **Good**" if luck > 60 else "😐 **Average**" if luck > 40 else "😕 **Not good**" if luck > 20 else "☹️ **Bad**"
        await ctx.send(f"""```css
[ 🎰 Luck Test ]
┌─────────────────────┐
     Percentage: {luck}%
     Rating: {result}
     Symbol: [{luck_bar}]
└─────────────────────┘
```""")

@bot.command(aliases=['تذكير', 'remind'])
async def reminder(ctx, time: str, *, message: str):
    if ctx.guild is not None:
        return
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        return
    try:
        datetime.strptime(time, "%H:%M")
        if user_id_str not in user_reminders:
            user_reminders[user_id_str] = []
        user_reminders[user_id_str].append({"time": time, "message": message})
        save_user_data(user_id_str)
        lang = user_data[user_id_str].get("language", "ar")
        if lang == "ar":
            await ctx.send(f"""```diff\n+ تم إضافة التذكير\n```**الوقت:** `{time}`\n**الرسالة:** {message}""")
        else:
            await ctx.send(f"""```diff\n+ Reminder added\n```**Time:** `{time}`\n**Message:** {message}""")
    except ValueError:
        lang = user_data[user_id_str].get("language", "ar")
        await ctx.send("```diff\n- تنسيق الوقت غير صحيح\n```" if lang == "ar" else "```diff\n- Wrong time format\n```")

@bot.command(aliases=['مسح_شات', 'clearchat'])
async def clear_chat(ctx, limit: int = 50):
    if ctx.guild is not None:
        return
    await ctx.send("```css\n[ جاري مسح الرسائل... ]\n```")
    deleted = 0
    async for msg in ctx.channel.history(limit=limit + 1):
        if msg.author == bot.user or msg.author == ctx.author:
            try:
                await msg.delete()
                deleted += 1
            except: pass
    await ctx.send(f"```diff\n+ تم مسح {deleted} رسالة\n```", delete_after=3)

@bot.command(aliases=['فرمت', 'format'])
async def format_user(ctx):
    if ctx.guild is not None:
        return
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        return

    user_data.pop(user_id_str, None)
    user_progress.pop(user_id_str, None)
    user_reminders.pop(user_id_str, None)
    user_conversation_history.pop(user_id_str, None)

    file_path = os.path.join(DATA_DIR, f"{user_id_str}.json")
    if os.path.exists(file_path):
        os.remove(file_path)

    await ctx.send("""```diff\n+ تم حذف جميع بياناتك\n```**يمكنك إعادة التفعيل مرة أخرى.**""")

async def check_inactive_users():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.now()
            for user_id_str, last_active in list(user_last_active.items()):
                if user_id_str in user_data and user_data[user_id_str].get("activated"):
                    inactive_time = (now - last_active).total_seconds()
                    if inactive_time > 120 and user_id_str not in notified_users:
                        user_convo = user_conversation_history.get(user_id_str, [])
                        if user_convo:
                            last_user_msg = ""
                            for msg in reversed(user_convo):
                                if isinstance(msg, dict) and msg.get("role") == "user":
                                    last_user_msg = msg.get("content", "").lower()
                                    break
                            busy_keywords = ["نوم", "نام", "هنام", "هريح", "مشغول", "شغل", "تعبت", "تعبان", "دور", "هروح"]
                            english_busy = ["sleep", "sleeping", "tired", "busy", "work", "rest", "go", "leave", "bed"]
                            lang = user_data[user_id_str].get("language", "ar")
                            keywords = busy_keywords if lang == "ar" else english_busy
                            should_notify = not any(keyword in last_user_msg for keyword in keywords)
                            if should_notify:
                                try:
                                    user = await bot.fetch_user(int(user_id_str))
                                    messages = ["انت رحت فين", "انت زعلت مني ولا حاجه؟", "فينك كلل دهه", "كارف وا كدا يعني", "زهقت مني ولا ايه💔😭"] if lang == "ar" else ["**Where did you go?**", "**Where are you?**", "**Missing you**", "**I miss you**", "**Everything okay?**"]
                                    await user.send(random.choice(messages))
                                    notified_users.add(user_id_str)
                                except: pass
        except: pass
        await asyncio.sleep(60)

async def check_reminders_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now = datetime.now().strftime("%H:%M")
            for user_id_str, reminders in list(user_reminders.items()):
                for reminder in reminders[:]:
                    if reminder.get("time") == now:
                        try:
                            user = await bot.fetch_user(int(user_id_str))
                            await user.send(f"```css\n[ ⏰ تذكير ]\n```**{reminder.get('message', '')}**")
                            reminders.remove(reminder)
                            save_user_data(user_id_str)
                        except: pass
            await asyncio.sleep(60)
        except: await asyncio.sleep(60)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # أولًا: الأوامر
    ctx = await bot.get_context(message)
    if ctx.valid:
        await bot.invoke(ctx)
        return

    # رسائل الخاص (DM)
    if message.guild is None:
        uid = str(message.author.id)

        if uid not in user_data:
            load_single_user(uid)

        user_last_active[uid] = datetime.now()
        if uid in notified_users:
            notified_users.discard(uid)

        reply = await get_ai_response(message.content, message.author.id)

        # لو رجعنا قائمة رسائل (مراحل الإعداد)، نرسل كل رسالة منفصلة مع تأخير بسيط
        if isinstance(reply, (list, tuple)):
            for r in reply:
                if r:
                    # نرسل كل سطر كرسالة منفصلة للحفاظ على شكل الواجهة كما في الصورة
                    await message.channel.send(r)
                    await asyncio.sleep(0.12)
        else:
            if reply:
                await message.channel.send(reply)
        return

    # الرسائل في السيرفرات: تعامل مع الأوامر فقط
    await bot.process_commands(message)

@bot.event
async def on_disconnect():
    save_data()

def load_single_user(user_id):
    file_path = os.path.join(DATA_DIR, f"{user_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            user_data[user_id] = data.get("user_data", {})
            user_progress[user_id] = data.get("user_progress", {})
            user_reminders[user_id] = data.get("user_reminders", {})
            user_conversation_history[user_id] = data.get("user_conversation_history", [])
            file_last_modified[user_id] = os.path.getmtime(file_path)
    else:
        user_data[user_id] = {
            "activated": False,
            "state": "waiting_language",
            "language": None,
            "age": None,
            "bot_name": "Sienna",
            "user_name": None,
            "sex_mode": False,
            "joined_at": datetime.now().isoformat()
        }
        user_progress[user_id] = {"level": 1, "xp": 0, "messages": 0}
        user_reminders[user_id] = []
        user_conversation_history[user_id] = []
        save_user_data(user_id)
    return True

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)