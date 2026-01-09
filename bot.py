import discord
from discord.ext import commands, tasks
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

if not DISCORD_TOKEN:
    print("⚠️ WARNING: DISCORD_TOKEN not set! Bot will not run.")
    print("ℹ️ Add DISCORD_TOKEN to Railway variables to enable bot.")
    DISCORD_TOKEN = None
else:
    print(f"✅ Discord Token found. Bot starting...")

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
file_last_modified = {}
bot_start_time = datetime.now()

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

@tasks.loop(hours=24)
async def cleanup_old_data():
    """تنظيف المحادثات القديمة"""
    try:
        for user_id in list(user_conversation_history.keys()):
            if len(user_conversation_history[user_id]) > 50:
                user_conversation_history[user_id] = user_conversation_history[user_id][-30:]
                save_user_data(user_id)
                print(f"🔄 تنظيف محادثات المستخدم {user_id}")
    except Exception as e:
        print(f"❌ خطأ في التنظيف: {e}")

@bot.event
async def on_ready():
    print(f"✨ **البوت شغال** دلوقتي كـ {bot.user}")
    load_data()
    watch_files.start()
    cleanup_old_data.start()
    bot.loop.create_task(check_inactive_users())
    bot.loop.create_task(check_reminders_task())
    print(f"✅ تم تحميل {len(user_data)} مستخدم")

def get_quick_response(message, user_data):
    """ردود سريعة مبرمجة"""
    message_lower = message.lower().strip()
    lang = user_data.get("language", "ar")
    
    quick_responses = {
        "ar": {
            "مرحبا": ["أهلاً وسهلاً! 😊", "مرحباً بك! 🌟", "أهلين! 💫", "أهلاً بك يا صديقي! 🎉"],
            "كيف حالك": ["تمام والحمدلله! 🙏", "بخير شكراً لك! 😄", "كويسة، وأنت؟ 💖", "أنا بخير، شكراً لسؤالك! 🌸"],
            "احبك": ["💖 وأنت عزيز!", "أنا بحبك كمان يا غالي! 🌹", "💕 شكراً لك!", "أنت رائع! 😍"],
            "باي": ["مع السلامة! 👋", "أشوفك بعدين! ✨", "باي، أراك قريباً! 💫", "وداعاً! 🌙"],
            "شكرا": ["العفو! 😊", "على الرحب والسعة! 🌟", "دي فرحتي! 💖", "أنت تستاهل! 🎁"],
            "صباح الخير": ["صباح النور! ☀️", "صباحك سعيد! 🌸", "صباح الخير يا جميل! 🌅"],
            "مساء الخير": ["مساء النور! 🌙", "مسائك سعيد! ✨", "مساء الخير والعافية! 🌹"],
        },
        "en": {
            "hi": ["Hello! 😊", "Hi there! 🌟", "Hey! 💫", "Hi, nice to see you! 🎉"],
            "hello": ["Hello! 😊", "Hi there! 🌟", "Hey! 💫", "Hi, nice to see you! 🎉"],
            "how are you": ["I'm good, thanks! 🙏", "Doing well! 😄", "Great, and you? 💖", "I'm fine, thank you! 🌸"],
            "i love you": ["💖 You're sweet!", "Love you too! 🌹", "💕 Thank you!", "You're amazing! 😍"],
            "bye": ["Goodbye! 👋", "See you later! ✨", "Bye, see you soon! 💫", "Farewell! 🌙"],
            "thank you": ["You're welcome! 😊", "My pleasure! 🌟", "Anytime! 💖", "You deserve it! 🎁"],
            "good morning": ["Good morning! ☀️", "Morning sunshine! 🌸", "Have a great morning! 🌅"],
            "good evening": ["Good evening! 🌙", "Evening! ✨", "Have a lovely evening! 🌹"],
        }
    }
    
    lang_dict = quick_responses.get(lang, {})
    for key, responses in lang_dict.items():
        if key in message_lower:
            return random.choice(responses)
    
    return None

async def get_ai_response(user_message, user_id):
    """
    البوت يتكلم عادي (بدون Embeds) - فقط ردود OpenAI عادية
    """
    uid = str(user_id)
    if uid not in user_data:
        load_single_user(uid)

    data = user_data.get(uid, {})
    state = data.get("state", "waiting_language")
    lang = data.get("language", "ar")
    name = data.get("bot_name", "Sienna")

    # التحقق من الردود السريعة أولاً
    quick_reply = get_quick_response(user_message, data)
    if quick_reply:
        return quick_reply

    # ----------------- waiting_language -----------------
    if state == "waiting_language":
        choice = user_message.strip().lower()
        if choice in ["عربي", "1", "ar"]:
            data["language"], data["state"] = "ar", "waiting_user_name"
            save_user_data(uid)
            return ["```diff\n+ تم اختيار اللغة العربية +\n```", "اكتب اسمك الحقيقي:"]
        elif choice in ["english", "2", "en"]:
            data["language"], data["state"] = "en", "waiting_user_name"
            save_user_data(uid)
            return ["```diff\n+ English selected +\n```", "Write your real name:"]
        return "```css\n[ ⚠️ يجب تفعيل البوت أولاً ]\n```استخدم: `!activate MYSECRET123`"

    # ----------------- waiting_user_name -----------------
    if state == "waiting_user_name":
        name_candidate = user_message.strip()
        if 2 <= len(name_candidate) <= 20:
            data["user_name"], data["state"] = name_candidate, "waiting_age"
            save_user_data(uid)
            return [f"```css\n[ 👤 أهلاً وسهلاً يا {data['user_name']} ]\n```", "عشان نكمل، اكتب عمرك:", "`(رقم فقط)`"]
        return "```css\n[ ⚠️ الاسم لازم بين 2 و20 حرف ]\n```جرب اسماً أقصر أو أطول"

    # ----------------- waiting_age -----------------
    if state == "waiting_age":
        try:
            age = int(user_message.strip())
            if age < 14:
                return "```diff\n- عذراً، السن غير مسموح\n```يجب أن يكون 14 سنة أو أكثر"
            data["age"], data["state"] = age, "waiting_bot_name"
            save_user_data(uid)
            return [f"```diff\n+ تم حفظ العمر : {age} سنة +\n```", "قولي اسمي اللي تحبه:", "`(بين 2 و20 حرف)`"]
        except:
            return "```css\n[ ⚠️ الرجاء إدخال عمر صحيح ]\n```أدخل رقماً فقط مثل: 18"

    # ----------------- waiting_bot_name -----------------
    if state == "waiting_bot_name":
        bot_name_candidate = user_message.strip()
        if 2 <= len(bot_name_candidate) <= 20:
            data["bot_name"], data["state"], data["activated"] = bot_name_candidate, "normal", True
            save_user_data(uid)
            return [
                "```css\n[ ✓ تم اكتمال الإعداد بنجاح ]\n```",
                f"""```ini
┌────────────────────────────┐
│ الاسم    : {data.get('user_name','')}
│ العمر   : {data.get('age','')} سنة
│ اسمي الآن: {data.get('bot_name','')}
└────────────────────────────┘
```""",
                "✨ يمكنك البدء بالحديث معي الآن"
            ]
        return "```css\n[ ⚠️ اسم البوت لازم بين 2 و20 حرف ]\n```جرب اسماً مختلفاً"

    # ----------------- Normal chat -----------------
    if not data.get("activated"):
        return "```css\n[ 🔒 غير مفعل ]\n```يجب إكمال عملية التفعيل أولاً\nاستخدم: `!activate MYSECRET123`"

    # ----------------- AI Chat Response -----------------
    traits = data.get("traits", {"curiosity": 50, "sensitivity": 50, "happiness": 50, "sadness": 20, "boldness": 50, "kindness": 50, "shyness": 20, "intelligence": 80})
    
    system_prompt = f"أنت {name} بنت مصرية عادية 20-22 سنة. شخصيتك حقيقية. "
    system_prompt += f"(الشخصية: فضول {traits['curiosity']}%، حساسية {traits['sensitivity']}%، ذكاء {traits['intelligence']}%) "
    system_prompt += "بتزعلي بتفرحي بتضايقي بتغيري مزاجك حسب الكلام. استخدمي إيموجي واحد بس (😭 أو 🤭 أو 🤤). محترمه من غير سكس. ردي بذكاء."

    if data.get("sex_mode"):
        system_prompt += " الآن في وضع سكس كوني جريئة جدًا وصريحة فاحشة ووصفي بالتفصيل."

    if uid not in user_conversation_history:
        user_conversation_history[uid] = []
    user_conversation_history[uid].append({"role": "user", "content": user_message, "time": datetime.now().isoformat()})

    try:
        # بناء سياق المحادثة
        conversation_context = []
        
        # أضف ذكريات قديمة (عشوائية)
        if len(user_conversation_history[uid]) > 15:
            old_messages = user_conversation_history[uid][:-8]
            if len(old_messages) > 0:
                sample = random.sample(old_messages, min(2, len(old_messages)))
                conversation_context.extend(sample)
        
        # أضف آخر 6 رسائل
        conversation_context.extend(user_conversation_history[uid][-6:])
        
        response = await client.chat.completions.create(
            model="x-ai/grok-4.1-fast",
            messages=[{"role": "system", "content": system_prompt}] + conversation_context,
            temperature=0.85 if data.get("sex_mode") else 0.75,
            max_tokens=600 if data.get("sex_mode") else 350,
        )
        ai_reply = response.choices[0].message.content.strip()
        user_conversation_history[uid].append({"role": "assistant", "content": ai_reply, "time": datetime.now().isoformat()})
        save_user_data(uid)
        
        return ai_reply
        
    except Exception as e:
        return f"```css\n[ ⚠️ خطأ تقني ]\n```حدث خطأ: `{str(e)[:100]}`\nيرجى المحاولة مرة أخرى لاحقاً"

@bot.command()
async def activate(ctx, *, code: str):
    if ctx.guild is not None:
        embed = discord.Embed(
            title="🚫 غير مسموح",
            description="**هذه الخاصية متاحة فقط في الرسائل الخاصة**",
            color=discord.Color.red()
        )
        embed.set_footer(text="أرسل لي رسالة خاصة للبدء")
        await ctx.send(embed=embed)
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
            "joined_at": datetime.now().isoformat(),
            "traits": {"curiosity": 50, "sensitivity": 50, "happiness": 50, "sadness": 20, "boldness": 50, "kindness": 50, "shyness": 20, "intelligence": 80}
        }
        user_last_active[user_id_str] = datetime.now()
        save_user_data(user_id_str)

        # إنشاء Embed للتفعيل الناجح
        embed = discord.Embed(
            title="✅ **تم تفعيل البوت بنجاح!**",
            description="**مرحباً بك في رحلة الإعداد**",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🌍 **الخطوة الأولى**",
            value="**اختر لغة المحادثة:**",
            inline=False
        )
        
        embed.add_field(
            name="📝 **الخيارات المتاحة**",
            value="""```css
            [1] عربي   - للغة العربية
            [2] English - للغة الإنجليزية
            ```""",
            inline=False
        )
        
        embed.add_field(
            name="💡 **طريقة الإدخال**",
            value="أرسل إما:\n• **عربي** أو **1**\n• **English** أو **2**",
            inline=False
        )
        
        embed.set_footer(text="ابدأ باختيار لغتك المفضلة")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🌍.png")
        
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ **كود التفعيل غير صحيح**",
            description="**الكود الذي أدخلته غير صالح**",
            color=discord.Color.red()
        )
        embed.add_field(
            name="🔑 **الكود الصحيح**",
            value="```MYSECRET123```",
            inline=False
        )
        embed.add_field(
            name="📝 **المحاولة مرة أخرى**",
            value="استخدم الأمر:\n```!activate MYSECRET123```",
            inline=False
        )
        embed.set_footer(text="تأكد من كتابة الكود بشكل صحيح")
        await ctx.send(embed=embed)

@bot.command(aliases=['mode'])
async def sex(ctx, mode: str = None):
    if ctx.guild is None and str(ctx.author.id) in user_data and user_data[str(ctx.author.id)].get("activated", False):
        data = user_data[str(ctx.author.id)]
        if data.get("age", 0) < 18:
            embed = discord.Embed(
                title="🚫 **غير مسموح**",
                description="**العمر أقل من 18 سنة**\nهذه الخاصية متاحة فقط للأشخاص فوق 18 سنة",
                color=discord.Color.red()
            )
            embed.set_footer(text="يجب أن تكون بالغاً لاستخدام هذه الميزة")
            await ctx.send(embed=embed)
            return

        if mode and mode.lower() in ['off', 'خلاص', 'كفايه', 'وقفي']:
            data["sex_mode"] = False
            status = "معطل ❌"
            status_en = "OFF ❌"
        elif mode and mode.lower() in ['on', 'تشغيل', 'شغل']:
            data["sex_mode"] = True
            status = "مفعل ✅"
            status_en = "ON ✅"
        else:
            data["sex_mode"] = not data.get("sex_mode", False)
            status = "مفعل ✅" if data["sex_mode"] else "معطل ❌"
            status_en = "ON ✅" if data["sex_mode"] else "OFF ❌"

        lang = data.get("language", "ar")
        
        if lang == "ar":
            embed = discord.Embed(
                title="⚡ **وضع السكس**",
                description=f"**الحالة الحالية:** {status}",
                color=discord.Color.purple() if data["sex_mode"] else discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            if data["sex_mode"]:
                embed.add_field(
                    name="🔞 **تحذير**",
                    value="**تم تفعيل الوضع الجنسي**\nسيصبح البوت أكثر صراحة وجرأة",
                    inline=False
                )
                embed.add_field(
                    name="⚠️ **ملاحظة**",
                    value="يمكنك إيقاف هذا الوضع بأي وقت باستخدام:\n```!sex off```",
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ **طبيعي**",
                    value="**تم إيقاف الوضع الجنسي**\nالعودة إلى الوضع الطبيعي",
                    inline=False
                )
        else:
            embed = discord.Embed(
                title="⚡ **Sex Mode**",
                description=f"**Current Status:** {status_en}",
                color=discord.Color.purple() if data["sex_mode"] else discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            if data["sex_mode"]:
                embed.add_field(
                    name="🔞 **Warning**",
                    value="**Sex mode activated**\nBot will become more explicit and bold",
                    inline=False
                )
                embed.add_field(
                    name="⚠️ **Note**",
                    value="You can turn this off anytime using:\n```!sex off```",
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ **Normal**",
                    value="**Sex mode deactivated**\nReturning to normal mode",
                    inline=False
                )

        user_id_str = str(ctx.author.id)
        if not data.get("sex_mode"):
            try:
                user_conversation_history[user_id_str] = []
            except Exception:
                user_conversation_history[user_id_str] = []

        save_user_data(user_id_str)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="🔒 **غير مفعل**",
            description="**يجب تفعيل البوت أولاً**",
            color=discord.Color.red()
        )
        embed.add_field(
            name="📝 **كيف تفعل البوت؟**",
            value="استخدم الأمر:\n```!activate MYSECRET123```",
            inline=False
        )
        embed.set_footer(text="ابدأ بالتسجيل أولاً")
        await ctx.send(embed=embed)

@bot.command(aliases=['مساعدة', 'مساعد', 'h', 'commands', 'help'])
async def show_help(ctx):
    if ctx.guild is not None:
        return

    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        embed = discord.Embed(
            title="🎮 **تفعيل البوت**",
            description="لبدء استخدام البوت، يجب تفعيله أولاً",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📝 **كيفية التفعيل**",
            value="أرسل الأمر التالي:\n```!activate MYSECRET123```",
            inline=False
        )
        
        embed.add_field(
            name="🔑 **رمز التفعيل**",
            value="```MYSECRET123```",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ **معلومات**",
            value="بعد التفعيل، ستتم إرشادك خلال خطوات الإعداد",
            inline=False
        )
        
        embed.set_footer(text="ابدأ رحلتك مع البوت الآن!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🎮.png")
        
        await ctx.send(embed=embed)
        return

    lang = user_data[user_id_str].get("language", "ar")

    if lang == "ar":
        embed = discord.Embed(
            title="📚 **مركز المساعدة**",
            description="**جميع أوامر البوت منظمة في فئات مختلفة**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🎫 **التفعيل والإعداد**",
            value="""
            ```css
            [!] !activate [كود]   - تفعيل البوت
            [!] !profile          - ملفك الشخصي
            [!] !format           - حذف بياناتك
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="💬 **المحادثة والتواصل**",
            value="""
            ```css
            [!] !help             - هذه القائمة
            [!] !clearchat        - مسح المحادثة
            [!] !daily            - الجائزة اليومية
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="🎮 **الألعاب والترفيه**",
            value="""
            ```css
            [!] !truth            - سؤال صراحة
            [!] !luck             - اختبار الحظ
            [!] !level            - مستوى وخبرتك
            [!] !top              - لوحة المتصدرين
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="⚙️ **الإعدادات المتقدمة**",
            value="""
            ```css
            [!] !sex              - تبديل وضع السكس
            [!] !sex on           - تشغيل وضع السكس
            [!] !sex off          - إيقاف وضع السكس
            [!] !reminder         - إضافة تذكير
            ```
            """,
            inline=False
        )
        
        embed.set_footer(text=f"طلب بواسطة {ctx.author.name} • استمر في المحادثة!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/❓.png")
        
    else:
        embed = discord.Embed(
            title="📚 **Help Center**",
            description="**All bot commands organized in categories**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🎫 **Activation & Setup**",
            value="""
            ```css
            [!] !activate [code]  - Activate bot
            [!] !profile          - Your profile
            [!] !format           - Delete your data
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="💬 **Chat & Communication**",
            value="""
            ```css
            [!] !help             - This list
            [!] !clearchat        - Clear chat
            [!] !daily            - Daily reward
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="🎮 **Games & Entertainment**",
            value="""
            ```css
            [!] !truth            - Truth question
            [!] !luck             - Luck test
            [!] !level            - Level & XP
            [!] !top              - Leaderboard
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="⚙️ **Advanced Settings**",
            value="""
            ```css
            [!] !sex              - Toggle sex mode
            [!] !sex on           - Turn on sex mode
            [!] !sex off          - Turn off sex mode
            [!] !reminder         - Add reminder
            ```
            """,
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.name} • Continue chatting!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/❓.png")
    
    await ctx.send(embed=embed)

@bot.command(aliases=['بروفايلي', 'profile'])
async def my_profile(ctx):
    if ctx.guild is not None:
        return

    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        embed = discord.Embed(
            title="🎮 **تفعيل البوت**",
            description="لبدء استخدام البوت، يجب تفعيله أولاً",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📝 **كيفية التفعيل**",
            value="أرسل الأمر التالي:\n```!activate MYSECRET123```",
            inline=False
        )
        
        embed.add_field(
            name="🔑 **رمز التفعيل**",
            value="```MYSECRET123```",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ **معلومات**",
            value="بعد التفعيل، ستتم إرشادك خلال خطوات الإعداد",
            inline=False
        )
        
        embed.set_footer(text="ابدأ رحلتك مع البوت الآن!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🎮.png")
        
        await ctx.send(embed=embed)
        return

    data = user_data[user_id_str]
    progress = user_progress.get(user_id_str, {"level": 1, "xp": 0, "messages": 0})
    lang = data.get("language", "ar")

    # حساب نسبة التقدم
    level = progress.get("level", 1)
    xp = progress.get("xp", 0)
    xp_needed = level * 100
    progress_percent = min(100, int((xp / xp_needed) * 100))
    
    # إنشاء شريط التقدم
    progress_bar = "█" * (progress_percent // 10) + "░" * (10 - (progress_percent // 10))
    
    if lang == "ar":
        embed = discord.Embed(
            title=f"👤 **الملف الشخصي • {data.get('user_name', 'زائر')}**",
            description="**معلوماتك الشخصية وإحصائياتك**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # معلومات الشخصية
        embed.add_field(
            name="📋 **المعلومات الشخصية**",
            value=f"""
            ```yaml
            الاسم: {data.get('user_name', 'غير معروف')}
            العمر: {data.get('age', 'غير معروف')} سنة
            اللغة: {data.get('language', 'عربي')}
            تاريخ التسجيل: {data.get('joined_at', 'غير معروف')[:10]}
            ```
            """,
            inline=False
        )
        
        # الإحصائيات
        embed.add_field(
            name="📊 **الإحصائيات**",
            value=f"""
            ```css
            [📈] المستوى: {level}
            [✨] الخبرة: {xp}/{xp_needed}
            [💬] الرسائل: {progress.get('messages', 0)}
            [🔞] وضع السكس: {'✅ مفعل' if data.get('sex_mode') else '❌ معطل'}
            ```
            """,
            inline=False
        )
        
        # شريط التقدم
        embed.add_field(
            name=f"📊 **التقدم • {progress_percent}%**",
            value=f"```[{progress_bar}]```",
            inline=False
        )
        
        # سمات الشخصية
        traits = data.get("traits", {})
        if traits:
            traits_text = "\n".join([f"• **{k}:** {v}%" for k, v in traits.items()])
            embed.add_field(
                name="🌟 **سمات الشخصية**",
                value=f"```{traits_text}```",
                inline=False
            )
        
        embed.set_footer(text=f"آخر نشاط: {datetime.now().strftime('%H:%M')}")
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else "https://cdn.discordapp.com/emojis/👤.png")
        
    else:
        embed = discord.Embed(
            title=f"👤 **Your Profile • {data.get('user_name', 'Visitor')}**",
            description="**Your personal information and statistics**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📋 **Personal Information**",
            value=f"""
            ```yaml
            Name: {data.get('user_name', 'Unknown')}
            Age: {data.get('age', 'Unknown')} years
            Language: {data.get('language', 'Arabic')}
            Joined: {data.get('joined_at', 'Unknown')[:10]}
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="📊 **Statistics**",
            value=f"""
            ```css
            [📈] Level: {level}
            [✨] XP: {xp}/{xp_needed}
            [💬] Messages: {progress.get('messages', 0)}
            [🔞] Sex Mode: {'✅ ON' if data.get('sex_mode') else '❌ OFF'}
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name=f"📊 **Progress • {progress_percent}%**",
            value=f"```[{progress_bar}]```",
            inline=False
        )
        
        traits = data.get("traits", {})
        if traits:
            traits_text = "\n".join([f"• **{k}:** {v}%" for k, v in traits.items()])
            embed.add_field(
                name="🌟 **Personality Traits**",
                value=f"```{traits_text}```",
                inline=False
            )
        
        embed.set_footer(text=f"Last active: {datetime.now().strftime('%I:%M %p')}")
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else "https://cdn.discordapp.com/emojis/👤.png")

    await ctx.send(embed=embed)

@bot.command(aliases=['مستوى', 'level'])
async def rank(ctx):
    if ctx.guild is not None:
        return

    user_id_str = str(ctx.author.id)
    if user_id_str in user_progress:
        data = user_progress[user_id_str]
        user_data_obj = user_data.get(user_id_str, {})
        lang = user_data_obj.get("language", "ar")
        
        level = data.get('level', 1)
        xp = data.get('xp', 0)
        xp_needed = level * 100
        progress_percent = min(100, int((xp / xp_needed) * 100))
        level_bar = "█" * (progress_percent // 10) + "░" * (10 - (progress_percent // 10))
        
        if lang == "ar":
            embed = discord.Embed(
                title=f"📊 **المستوى {level}**",
                description="**معلومات مستوى وخبرتك**",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="✨ **التقدم**",
                value=f"""
                ```css
                [📈] المستوى: {level}
                [💎] الخبرة: {xp}/{xp_needed}
                [📊] النسبة: {progress_percent}%
                ```
                """,
                inline=False
            )
            
            embed.add_field(
                name=f"📊 **شريط التقدم • {progress_percent}%**",
                value=f"```[{level_bar}]```",
                inline=False
            )
            
            # رسالة تشجيعية حسب المستوى
            if level < 5:
                encouragement = "💪 **استمر!** أنت في بداية رحلتك"
            elif level < 10:
                encouragement = "🚀 **ممتاز!** أنت تتقدم بسرعة"
            elif level < 15:
                encouragement = "🎯 **رائع!** أنت محترف الآن"
            else:
                encouragement = "👑 **أسطوري!** أنت من أفضل المستخدمين"
            
            embed.add_field(
                name="🌟 **تشجيع**",
                value=encouragement,
                inline=False
            )
            
            embed.set_footer(text="كل رسالة تكتبها تزيد من خبرتك!")
            
        else:
            embed = discord.Embed(
                title=f"📊 **Level {level}**",
                description="**Your level and experience information**",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="✨ **Progress**",
                value=f"""
                ```css
                [📈] Level: {level}
                [💎] XP: {xp}/{xp_needed}
                [📊] Percentage: {progress_percent}%
                ```
                """,
                inline=False
            )
            
            embed.add_field(
                name=f"📊 **Progress Bar • {progress_percent}%**",
                value=f"```[{level_bar}]```",
                inline=False
            )
            
            if level < 5:
                encouragement = "💪 **Keep going!** You're just starting"
            elif level < 10:
                encouragement = "🚀 **Excellent!** You're progressing fast"
            elif level < 15:
                encouragement = "🎯 **Awesome!** You're a pro now"
            else:
                encouragement = "👑 **Legendary!** You're one of the best"
            
            embed.add_field(
                name="🌟 **Encouragement**",
                value=encouragement,
                inline=False
            )
            
            embed.set_footer(text="Every message you send increases your XP!")
        
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="📝 **ابدأ المحادثة**",
            description="**لا توجد بيانات بعد**\nابدأ بالتحدث مع البوت لترى مستواك!",
            color=discord.Color.blue()
        )
        embed.set_footer(text="اكتب رسالة لتبدأ!")
        await ctx.send(embed=embed)

@bot.command(aliases=['صراحة', 'truth'])
async def truth_or_dare(ctx):
    if ctx.guild is not None:
        return
    
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        embed = discord.Embed(
            title="🎮 **تفعيل البوت**",
            description="لبدء استخدام البوت، يجب تفعيله أولاً",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📝 **كيفية التفعيل**",
            value="أرسل الأمر التالي:\n```!activate MYSECRET123```",
            inline=False
        )
        
        embed.add_field(
            name="🔑 **رمز التفعيل**",
            value="```MYSECRET123```",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ **معلومات**",
            value="بعد التفعيل، ستتم إرشادك خلال خطوات الإعداد",
            inline=False
        )
        
        embed.set_footer(text="ابدأ رحلتك مع البوت الآن!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🎮.png")
        
        await ctx.send(embed=embed)
        return
    
    lang = user_data[user_id_str].get("language", "ar")
    
    if lang == "ar":
        questions = [
            "**آخر مرة** كذبت فيها على مين؟ ولماذا؟",
            "**أكثر حاجة** تخاف منها في الحياة؟ ولماذا هذه بالتحديد؟",
            "**أحلامك** السرية إيه؟ اللي ما حدش يعرفها؟",
            "**لو تقدر** تغير حاجة واحدة في ماضيك، هتغير إيه؟",
            "**أكبر غلطة** عملتها في حياتك؟ وليه تعتبر أنها كانت غلطة؟",
            "**أكثر موقف** محرج حصل لك؟ شاركه معنا!",
            "**لو عندك** فرصة تلتقي بشخص واحد فقط، هتختار مين؟",
            "**أكثر صفة** فيك بتكرهها؟ وليه مش قادر تتخلص منها؟"
        ]
        
        question = random.choice(questions)
        
        embed = discord.Embed(
            title="❓ **سؤال صراحة**",
            description=f"**{question}**",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="💡 **كيف تلعب؟**",
            value="**أجب بصراحة ولا تكذب!**\nشارك إجابتك مع البوت",
            inline=False
        )
        
        embed.set_footer(text="كن صادقاً! 🎯")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/❓.png")
        
    else:
        questions = [
            "**Last time** you lied to someone? Why did you do it?",
            "**Biggest fear** you have in life? Why this specific fear?",
            "**Secret dreams** you have? The ones nobody knows about?",
            "**If you could** change one thing in your past, what would it be?",
            "**Biggest mistake** you made in life? Why do you consider it a mistake?",
            "**Most embarrassing moment** you've experienced? Share it with us!",
            "**If you could** meet only one person, who would you choose?",
            "**Worst trait** you have? Why can't you get rid of it?"
        ]
        
        question = random.choice(questions)
        
        embed = discord.Embed(
            title="❓ **Truth Question**",
            description=f"**{question}**",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="💡 **How to play?**",
            value="**Answer honestly, don't lie!**\nShare your answer with the bot",
            inline=False
        )
        
        embed.set_footer(text="Be honest! 🎯")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/❓.png")
    
    await ctx.send(embed=embed)

@bot.command(aliases=['حظ', 'luck'])
async def luck_test(ctx):
    if ctx.guild is not None:
        return
    
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        embed = discord.Embed(
            title="🎮 **تفعيل البوت**",
            description="لبدء استخدام البوت، يجب تفعيله أولاً",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📝 **كيفية التفعيل**",
            value="أرسل الأمر التالي:\n```!activate MYSECRET123```",
            inline=False
        )
        
        embed.add_field(
            name="🔑 **رمز التفعيل**",
            value="```MYSECRET123```",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ **معلومات**",
            value="بعد التفعيل، ستتم إرشادك خلال خطوات الإعداد",
            inline=False
        )
        
        embed.set_footer(text="ابدأ رحلتك مع البوت الآن!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🎮.png")
        
        await ctx.send(embed=embed)
        return
    
    luck = random.randint(1, 100)
    user_data_obj = user_data.get(user_id_str, {})
    lang = user_data_obj.get("language", "ar")
    
    # تحديد نتيجة الحظ
    if luck > 90:
        result = "✨ **أسطوري!**" if lang == "ar" else "✨ **Legendary!**"
        emoji = "🏆"
        color = discord.Color.gold()
    elif luck > 75:
        result = "🔥 **مذهل!**" if lang == "ar" else "🔥 **Amazing!**"
        emoji = "⭐"
        color = discord.Color.orange()
    elif luck > 60:
        result = "😊 **جيد!**" if lang == "ar" else "😊 **Good!**"
        emoji = "✅"
        color = discord.Color.green()
    elif luck > 40:
        result = "😐 **متوسط!**" if lang == "ar" else "😐 **Average!**"
        emoji = "➖"
        color = discord.Color.blue()
    elif luck > 20:
        result = "😕 **سيء!**" if lang == "ar" else "😕 **Bad!**"
        emoji = "⚠️"
        color = discord.Color.orange()
    else:
        result = "😢 **مزرية!**" if lang == "ar" else "😢 **Terrible!**"
        emoji = "💔"
        color = discord.Color.red()
    
    # إنشاء شريط الحظ
    luck_bar = "🍀" * (luck // 20) + "⚪" * (5 - (luck // 20))
    
    if lang == "ar":
        embed = discord.Embed(
            title=f"{emoji} **اختبار الحظ**",
            description="**كيف هو حظك اليوم؟**",
            color=color,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🎰 **النتيجة**",
            value=f"""
            ```css
            [📊] النسبة: {luck}%
            [🎯] التقييم: {result}
            [📈] الرمز: [{luck_bar}]
            ```
            """,
            inline=False
        )
        
        # نص حسب نتيجة الحظ
        if luck > 90:
            advice = "**اليوم يومك!** استغل هذه الطاقة الإيجابية"
        elif luck > 75:
            advice = "**أيامك جميلة!** استمر في ما تفعله"
        elif luck > 60:
            advice = "**لا بأس!** الأمور على ما يرام"
        elif luck > 40:
            advice = "**متوسط!** يمكن أن يكون أفضل"
        elif luck > 20:
            advice = "**انتبه!** حاول تجنب المخاطر اليوم"
        else:
            advice = "**اصبر!** الغد أفضل إن شاء الله"
        
        embed.add_field(
            name="💡 **نصيحة اليوم**",
            value=advice,
            inline=False
        )
        
        embed.set_footer(text="الحظ يتغير كل يوم! ✨")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🍀.png")
        
    else:
        embed = discord.Embed(
            title=f"{emoji} **Luck Test**",
            description="**How's your luck today?**",
            color=color,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🎰 **Result**",
            value=f"""
            ```css
            [📊] Percentage: {luck}%
            [🎯] Rating: {result}
            [📈] Symbol: [{luck_bar}]
            ```
            """,
            inline=False
        )
        
        if luck > 90:
            advice = "**Today is your day!** Use this positive energy"
        elif luck > 75:
            advice = "**Beautiful days!** Keep doing what you're doing"
        elif luck > 60:
            advice = "**Not bad!** Things are okay"
        elif luck > 40:
            advice = "**Average!** Could be better"
        elif luck > 20:
            advice = "**Be careful!** Try to avoid risks today"
        else:
            advice = "**Be patient!** Tomorrow will be better"
        
        embed.add_field(
            name="💡 **Today's Advice**",
            value=advice,
            inline=False
        )
        
        embed.set_footer(text="Luck changes every day! ✨")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🍀.png")
    
    await ctx.send(embed=embed)

@bot.command(aliases=['يومي', 'daily'])
async def daily_reward(ctx):
    if ctx.guild is not None:
        return
    
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        embed = discord.Embed(
            title="🎮 **تفعيل البوت**",
            description="لبدء استخدام البوت، يجب تفعيله أولاً",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📝 **كيفية التفعيل**",
            value="أرسل الأمر التالي:\n```!activate MYSECRET123```",
            inline=False
        )
        
        embed.add_field(
            name="🔑 **رمز التفعيل**",
            value="```MYSECRET123```",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ **معلومات**",
            value="بعد التفعيل، ستتم إرشادك خلال خطوات الإعداد",
            inline=False
        )
        
        embed.set_footer(text="ابدأ رحلتك مع البوت الآن!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🎮.png")
        
        await ctx.send(embed=embed)
        return
    
    # تحقق من آخر مرة أخذ فيها الجائزة
    last_daily = user_data[user_id_str].get("last_daily")
    today = datetime.now().strftime("%Y-%m-%d")
    
    if last_daily == today:
        lang = user_data[user_id_str].get("language", "ar")
        
        if lang == "ar":
            embed = discord.Embed(
                title="⏰ **لقد أخذت جائزتك اليومية**",
                description="**لقد حصلت على جائزتك اليومية بالفعل!**",
                color=discord.Color.orange()
            )
            
            # حساب الوقت المتبقي
            now = datetime.now()
            tomorrow = datetime(now.year, now.month, now.day) + timedelta(days=1)
            time_left = tomorrow - now
            hours_left = time_left.seconds // 3600
            minutes_left = (time_left.seconds % 3600) // 60
            
            embed.add_field(
                name="⏳ **الوقت المتبقي**",
                value=f"**{hours_left} ساعة و {minutes_left} دقيقة**\nحتى الجائزة التالية",
                inline=False
            )
            
            embed.set_footer(text="ارجع غداً للحصول على جائزة جديدة!")
            
        else:
            embed = discord.Embed(
                title="⏰ **Already Claimed Daily Reward**",
                description="**You already claimed your daily reward today!**",
                color=discord.Color.orange()
            )
            
            now = datetime.now()
            tomorrow = datetime(now.year, now.month, now.day) + timedelta(days=1)
            time_left = tomorrow - now
            hours_left = time_left.seconds // 3600
            minutes_left = (time_left.seconds % 3600) // 60
            
            embed.add_field(
                name="⏳ **Time Left**",
                value=f"**{hours_left} hours and {minutes_left} minutes**\nuntil next reward",
                inline=False
            )
            
            embed.set_footer(text="Come back tomorrow for a new reward!")
        
        await ctx.send(embed=embed)
        return
    
    # إعطاء الجائزة
    reward_xp = random.randint(50, 150)
    streak = user_data[user_id_str].get("daily_streak", 0) + 1
    
    # مكافآت إضافية حسب التسلسل
    bonus = 0
    lang = user_data[user_id_str].get("language", "ar")
    
    if streak >= 7:
        bonus = 100
        bonus_text = "🎉 **مكافأة أسبوعية!** +100 XP" if lang == "ar" else "🎉 **Weekly bonus!** +100 XP"
    elif streak >= 3:
        bonus = 50
        bonus_text = "✨ **مكافأة متتالية!** +50 XP" if lang == "ar" else "✨ **Streak bonus!** +50 XP"
    
    total_xp = reward_xp + bonus
    
    # اختيار رسالة عشوائية
    reward_messages = [
        "🎁 **هدية اليوم!**",
        "💎 **كنز ثمين!**",
        "✨ **مفاجأة سعيدة!**",
        "🌟 **نجمة الحظ!**",
        "🪙 **ذهب خالص!**"
    ]
    
    reward_message = random.choice(reward_messages)
    
    # تحديث البيانات
    user_data[user_id_str]["last_daily"] = today
    user_data[user_id_str]["daily_streak"] = streak
    
    if user_id_str not in user_progress:
        user_progress[user_id_str] = {"level": 1, "xp": 0, "messages": 0}
    
    user_progress[user_id_str]["xp"] = user_progress[user_id_str].get("xp", 0) + total_xp
    save_user_data(user_id_str)
    
    if lang == "ar":
        embed = discord.Embed(
            title=reward_message,
            description="**🎊 مبروك! حصلت على جائزتك اليومية**",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📦 **محتويات الجائزة**",
            value=f"""
            ```css
            [💎] الخبرة: +{reward_xp} XP
            [✨] المكافأة: +{bonus} XP
            [💰] الإجمالي: +{total_xp} XP
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="🔥 **التسلسل**",
            value=f"**{streak} يوم متتالي**\nاستمر لتزيد مكافآتك!",
            inline=False
        )
        
        if bonus > 0:
            embed.add_field(
                name="🎯 **مكافأة إضافية**",
                value=bonus_text,
                inline=False
            )
        
        # التحقق من الترقية
        current_level = user_progress[user_id_str].get("level", 1)
        xp_needed = current_level * 100
        current_xp = user_progress[user_id_str].get("xp", 0)
        
        if current_xp >= xp_needed:
            embed.add_field(
                name="🎉 **ترقية!**",
                value=f"**تهانينا! لقد ارتقيت إلى المستوى {current_level + 1}**",
                inline=False
            )
        
        embed.set_footer(text="ارجع غداً لجائزة أكبر! 🎁")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🎁.png")
        
    else:
        embed = discord.Embed(
            title=reward_message,
            description="**🎊 Congratulations! You got your daily reward**",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📦 **Reward Contents**",
            value=f"""
            ```css
            [💎] XP: +{reward_xp} XP
            [✨] Bonus: +{bonus} XP
            [💰] Total: +{total_xp} XP
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="🔥 **Streak**",
            value=f"**{streak} consecutive days**\nKeep going for bigger rewards!",
            inline=False
        )
        
        if bonus > 0:
            embed.add_field(
                name="🎯 **Extra Bonus**",
                value=bonus_text,
                inline=False
            )
        
        current_level = user_progress[user_id_str].get("level", 1)
        xp_needed = current_level * 100
        current_xp = user_progress[user_id_str].get("xp", 0)
        
        if current_xp >= xp_needed:
            embed.add_field(
                name="🎉 **Level Up!**",
                value=f"**Congratulations! You leveled up to Level {current_level + 1}**",
                inline=False
            )
        
        embed.set_footer(text="Come back tomorrow for a bigger reward! 🎁")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🎁.png")
    
    await ctx.send(embed=embed)

@bot.command(aliases=['تذكير', 'remind'])
async def reminder(ctx, time: str, *, message: str):
    if ctx.guild is not None:
        return
    
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        embed = discord.Embed(
            title="🎮 **تفعيل البوت**",
            description="لبدء استخدام البوت، يجب تفعيله أولاً",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📝 **كيفية التفعيل**",
            value="أرسل الأمر التالي:\n```!activate MYSECRET123```",
            inline=False
        )
        
        embed.add_field(
            name="🔑 **رمز التفعيل**",
            value="```MYSECRET123```",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ **معلومات**",
            value="بعد التفعيل، ستتم إرشادك خلال خطوات الإعداد",
            inline=False
        )
        
        embed.set_footer(text="ابدأ رحلتك مع البوت الآن!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🎮.png")
        
        await ctx.send(embed=embed)
        return
    
    try:
        # تحقق من تنسيق الوقت
        datetime.strptime(time, "%H:%M")
        
        if user_id_str not in user_reminders:
            user_reminders[user_id_str] = []
        
        # إضافة التذكير
        reminder_data = {
            "time": time,
            "message": message,
            "created_at": datetime.now().isoformat(),
            "id": len(user_reminders[user_id_str]) + 1
        }
        
        user_reminders[user_id_str].append(reminder_data)
        save_user_data(user_id_str)
        
        lang = user_data[user_id_str].get("language", "ar")
        
        if lang == "ar":
            embed = discord.Embed(
                title="✅ **تم إضافة التذكير**",
                description="**سيتم تذكيرك في الوقت المحدد**",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="🕐 **الوقت**",
                value=f"**`{time}`**",
                inline=True
            )
            
            embed.add_field(
                name="📝 **الرسالة**",
                value=f"**{message}**",
                inline=True
            )
            
            embed.add_field(
                name="📌 **رقم التذكير**",
                value=f"**#{reminder_data['id']}**",
                inline=False
            )
            
            embed.add_field(
                name="💡 **معلومات**",
                value="سأرسل لك رسالة تذكير في الوقت المحدد",
                inline=False
            )
            
            embed.set_footer(text="لن أنسى تذكيرك! ⏰")
            
        else:
            embed = discord.Embed(
                title="✅ **Reminder Added**",
                description="**You will be reminded at the specified time**",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="🕐 **Time**",
                value=f"**`{time}`**",
                inline=True
            )
            
            embed.add_field(
                name="📝 **Message**",
                value=f"**{message}**",
                inline=True
            )
            
            embed.add_field(
                name="📌 **Reminder ID**",
                value=f"**#{reminder_data['id']}**",
                inline=False
            )
            
            embed.add_field(
                name="💡 **Information**",
                value="I'll send you a reminder message at the specified time",
                inline=False
            )
            
            embed.set_footer(text="I won't forget your reminder! ⏰")
        
        await ctx.send(embed=embed)
        
    except ValueError:
        lang = user_data[user_id_str].get("language", "ar")
        
        if lang == "ar":
            embed = discord.Embed(
                title="⚠️ **خطأ في التنسيق**",
                description="**تنسيق الوقت غير صحيح**",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="📝 **الصيغة الصحيحة**",
                value="استخدم تنسيق 24 ساعة:\n```HH:MM```",
                inline=False
            )
            
            embed.add_field(
                name="💡 **أمثلة**",
                value="```14:30   (02:30 مساءً)\n09:15   (09:15 صباحاً)\n23:45   (11:45 مساءً)```",
                inline=False
            )
            
            embed.set_footer(text="جرب مرة أخرى بالتنسيق الصحيح")
            
        else:
            embed = discord.Embed(
                title="⚠️ **Format Error**",
                description="**Wrong time format**",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="📝 **Correct Format**",
                value="Use 24-hour format:\n```HH:MM```",
                inline=False
            )
            
            embed.add_field(
                name="💡 **Examples**",
                value="```14:30   (02:30 PM)\n09:15   (09:15 AM)\n23:45   (11:45 PM)```",
                inline=False
            )
            
            embed.set_footer(text="Try again with the correct format")
        
        await ctx.send(embed=embed)

@bot.command(aliases=['تذكري', 'reminders'])
async def show_reminders(ctx):
    if ctx.guild is not None:
        return
    
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        embed = discord.Embed(
            title="🎮 **تفعيل البوت**",
            description="لبدء استخدام البوت، يجب تفعيله أولاً",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📝 **كيفية التفعيل**",
            value="أرسل الأمر التالي:\n```!activate MYSECRET123```",
            inline=False
        )
        
        embed.add_field(
            name="🔑 **رمز التفعيل**",
            value="```MYSECRET123```",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ **معلومات**",
            value="بعد التفعيل، ستتم إرشادك خلال خطوات الإعداد",
            inline=False
        )
        
        embed.set_footer(text="ابدأ رحلتك مع البوت الآن!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🎮.png")
        
        await ctx.send(embed=embed)
        return
    
    reminders_list = user_reminders.get(user_id_str, [])
    lang = user_data[user_id_str].get("language", "ar")
    
    if not reminders_list:
        if lang == "ar":
            embed = discord.Embed(
                title="📝 **لا توجد تذكيرات**",
                description="**لم تقم بإضافة أي تذكيرات بعد**",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="💡 **كيف تضيف تذكير؟**",
                value="استخدم الأمر:\n```!reminder [الوقت] [الرسالة]```",
                inline=False
            )
            
            embed.set_footer(text="أضف أول تذكير لك الآن!")
            
        else:
            embed = discord.Embed(
                title="📝 **No Reminders**",
                description="**You haven't added any reminders yet**",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="💡 **How to add a reminder?**",
                value="Use the command:\n```!reminder [time] [message]```",
                inline=False
            )
            
            embed.set_footer(text="Add your first reminder now!")
        
        await ctx.send(embed=embed)
        return
    
    if lang == "ar":
        embed = discord.Embed(
            title=f"📋 **قائمة التذكيرات • {len(reminders_list)}**",
            description="**جميع تذكيراتك المنشأة**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for reminder in reminders_list[:10]:  # عرض أول 10 تذكيرات فقط
            created_time = datetime.fromisoformat(reminder.get("created_at", datetime.now().isoformat()))
            time_diff = datetime.now() - created_time
            
            if time_diff.days > 0:
                time_text = f"منذ {time_diff.days} يوم"
            elif time_diff.seconds > 3600:
                time_text = f"منذ {time_diff.seconds // 3600} ساعة"
            else:
                time_text = f"منذ {time_diff.seconds // 60} دقيقة"
            
            embed.add_field(
                name=f"⏰ **#{reminder.get('id', '?')} • {reminder.get('time', '??:??')}**",
                value=f"""
                ```{reminder.get('message', 'بدون رسالة')}```
                **{time_text}**
                """,
                inline=False
            )
        
        if len(reminders_list) > 10:
            embed.add_field(
                name="📄 **صفحة إضافية**",
                value=f"**+{len(reminders_list) - 10} تذكيرات أخرى**\nاستخدم `!reminder [وقت] [رسالة]` لإضافة المزيد",
                inline=False
            )
        
        embed.set_footer(text=f"آخر تحديث: {datetime.now().strftime('%H:%M')}")
        
    else:
        embed = discord.Embed(
            title=f"📋 **Reminders List • {len(reminders_list)}**",
            description="**All your created reminders**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for reminder in reminders_list[:10]:
            created_time = datetime.fromisoformat(reminder.get("created_at", datetime.now().isoformat()))
            time_diff = datetime.now() - created_time
            
            if time_diff.days > 0:
                time_text = f"{time_diff.days} days ago"
            elif time_diff.seconds > 3600:
                time_text = f"{time_diff.seconds // 3600} hours ago"
            else:
                time_text = f"{time_diff.seconds // 60} minutes ago"
            
            embed.add_field(
                name=f"⏰ **#{reminder.get('id', '?')} • {reminder.get('time', '??:??')}**",
                value=f"""
                ```{reminder.get('message', 'No message')}```
                **{time_text}**
                """,
                inline=False
            )
        
        if len(reminders_list) > 10:
            embed.add_field(
                name="📄 **Additional Page**",
                value=f"**+{len(reminders_list) - 10} more reminders**\nUse `!reminder [time] [message]` to add more",
                inline=False
            )
        
        embed.set_footer(text=f"Last update: {datetime.now().strftime('%I:%M %p')}")
    
    await ctx.send(embed=embed)

@bot.command(aliases=['مسح_شات', 'clearchat'])
async def clear_chat(ctx, limit: int = 50):
    if ctx.guild is not None:
        return
    
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        embed = discord.Embed(
            title="🎮 **تفعيل البوت**",
            description="لبدء استخدام البوت، يجب تفعيله أولاً",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📝 **كيفية التفعيل**",
            value="أرسل الأمر التالي:\n```!activate MYSECRET123```",
            inline=False
        )
        
        embed.add_field(
            name="🔑 **رمز التفعيل**",
            value="```MYSECRET123```",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ **معلومات**",
            value="بعد التفعيل، ستتم إرشادك خلال خطوات الإعداد",
            inline=False
        )
        
        embed.set_footer(text="ابدأ رحلتك مع البوت الآن!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🎮.png")
        
        await ctx.send(embed=embed)
        return
    
    # إرسال رسالة تأكيد
    lang = user_data[user_id_str].get("language", "ar")
    
    if lang == "ar":
        embed = discord.Embed(
            title="🧹 **جارٍ مسح المحادثة**",
            description=f"**جاري حذف آخر {limit} رسالة...**",
            color=discord.Color.orange()
        )
        embed.set_footer(text="قد تستغرق العملية بضع ثوانٍ")
    else:
        embed = discord.Embed(
            title="🧹 **Clearing Chat**",
            description=f"**Deleting last {limit} messages...**",
            color=discord.Color.orange()
        )
        embed.set_footer(text="This may take a few seconds")
    
    await ctx.send(embed=embed)
    
    # مسح الرسائل
    deleted = 0
    async for msg in ctx.channel.history(limit=limit + 1):
        if msg.author == bot.user or msg.author == ctx.author:
            try:
                await msg.delete()
                deleted += 1
                await asyncio.sleep(0.1)  # تجنب rate limiting
            except:
                pass
    
    # رسالة النتيجة
    if lang == "ar":
        embed = discord.Embed(
            title="✅ **تم مسح المحادثة**",
            description=f"**تم حذف {deleted} رسالة بنجاح**",
            color=discord.Color.green()
        )
        embed.set_footer(text="المحادثة الآن نظيفة!")
    else:
        embed = discord.Embed(
            title="✅ **Chat Cleared**",
            description=f"**Successfully deleted {deleted} messages**",
            color=discord.Color.green()
        )
        embed.set_footer(text="Chat is now clean!")
    
    result_msg = await ctx.send(embed=embed)
    await asyncio.sleep(3)
    await result_msg.delete()

@bot.command(aliases=['فرمت', 'format'])
async def format_user(ctx):
    if ctx.guild is not None:
        return
    
    user_id_str = str(ctx.author.id)
    if user_id_str not in user_data or not user_data[user_id_str].get("activated", False):
        embed = discord.Embed(
            title="🎮 **تفعيل البوت**",
            description="لبدء استخدام البوت، يجب تفعيله أولاً",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📝 **كيفية التفعيل**",
            value="أرسل الأمر التالي:\n```!activate MYSECRET123```",
            inline=False
        )
        
        embed.add_field(
            name="🔑 **رمز التفعيل**",
            value="```MYSECRET123```",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ **معلومات**",
            value="بعد التفعيل، ستتم إرشادك خلال خطوات الإعداد",
            inline=False
        )
        
        embed.set_footer(text="ابدأ رحلتك مع البوت الآن!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🎮.png")
        
        await ctx.send(embed=embed)
        return

    lang = user_data[user_id_str].get("language", "ar")
    
    if lang == "ar":
        embed = discord.Embed(
            title="⚠️ **تأكيد حذف البيانات**",
            description="**هل أنت متأكد أنك تريد حذف جميع بياناتك؟**",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="❌ **ما سيتم حذفه**",
            value="""
            ```diff
            - جميع محادثاتك
            - ملفك الشخصي
            - إحصائياتك
            - تذكيراتك
            - إعداداتك
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="✅ **ماذا يبقى؟**",
            value="**يمكنك إعادة التسجيل من جديد**\nباستخدام `!activate MYSECRET123`",
            inline=False
        )
        
        embed.set_footer(text="هذا الإجراء لا يمكن التراجع عنه!")
        
    else:
        embed = discord.Embed(
            title="⚠️ **Confirm Data Deletion**",
            description="**Are you sure you want to delete all your data?**",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="❌ **What will be deleted**",
            value="""
            ```diff
            - All your conversations
            - Your profile
            - Your statistics
            - Your reminders
            - Your settings
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="✅ **What remains?**",
            value="**You can register again**\nusing `!activate MYSECRET123`",
            inline=False
        )
        
        embed.set_footer(text="This action cannot be undone!")
    
    await ctx.send(embed=embed)
    
    # انتظر رد المستخدم
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        response = await bot.wait_for('message', timeout=30.0, check=check)
        
        if response.content.lower() in ["نعم", "yes", "y", "✅"]:
            # حذف البيانات
            user_data.pop(user_id_str, None)
            user_progress.pop(user_id_str, None)
            user_reminders.pop(user_id_str, None)
            user_conversation_history.pop(user_id_str, None)

            file_path = os.path.join(DATA_DIR, f"{user_id_str}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
            
            if lang == "ar":
                embed = discord.Embed(
                    title="✅ **تم حذف جميع بياناتك**",
                    description="**تم حذف جميع معلوماتك بنجاح**",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="🔄 **إعادة البدء**",
                    value="يمكنك إعادة التسجيل الآن باستخدام:\n```!activate MYSECRET123```",
                    inline=False
                )
                
                embed.set_footer(text="نراكم قريباً إن شاء الله!")
                
            else:
                embed = discord.Embed(
                    title="✅ **All Data Deleted**",
                    description="**All your information has been successfully deleted**",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="🔄 **Start Over**",
                    value="You can register again now using:\n```!activate MYSECRET123```",
                    inline=False
                )
                
                embed.set_footer(text="See you soon!")
            
            await ctx.send(embed=embed)
            
        else:
            if lang == "ar":
                embed = discord.Embed(
                    title="❌ **تم الإلغاء**",
                    description="**تم إلغاء عملية حذف البيانات**",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="بياناتك محفوظة بأمان")
            else:
                embed = discord.Embed(
                    title="❌ **Cancelled**",
                    description="**Data deletion has been cancelled**",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="Your data is safely kept")
            
            await ctx.send(embed=embed)
            
    except asyncio.TimeoutError:
        if lang == "ar":
            embed = discord.Embed(
                title="⏰ **انتهى الوقت**",
                description="**انتهى وقت الانتظار، تم إلغاء العملية**",
                color=discord.Color.orange()
            )
            embed.set_footer(text="بياناتك محفوظة بأمان")
        else:
            embed = discord.Embed(
                title="⏰ **Time Out**",
                description="**Waiting time expired, operation cancelled**",
                color=discord.Color.orange()
            )
            embed.set_footer(text="Your data is safely kept")
        
        await ctx.send(embed=embed)

@bot.command(aliases=['المتصدرين', 'top'])
async def leaderboard(ctx, page: int = 1):
    if ctx.guild is not None:
        return
    
    # جمع بيانات جميع المستخدمين
    leaderboard_data = []
    for user_id, progress in user_progress.items():
        if user_data.get(user_id, {}).get("activated", False):
            leaderboard_data.append({
                "user_id": user_id,
                "level": progress.get("level", 1),
                "xp": progress.get("xp", 0),
                "messages": progress.get("messages", 0),
                "user_name": user_data.get(user_id, {}).get("user_name", f"User{user_id[-4:]}")
            })
    
    # ترتيب حسب المستوى ثم XP
    leaderboard_data.sort(key=lambda x: (x["level"], x["xp"]), reverse=True)
    
    # عرض صفحة معينة
    items_per_page = 10
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    if start_idx >= len(leaderboard_data):
        embed = discord.Embed(
            title="📊 **لا توجد بيانات كافية**",
            description="**لا يوجد مستخدمون كافون في اللوحة**",
            color=discord.Color.blue()
        )
        embed.set_footer(text="ابدأ المحادثة لتظهر هنا!")
        await ctx.send(embed=embed)
        return
    
    # الحصول على لغة المستخدم الحالي
    user_id_str = str(ctx.author.id)
    lang = user_data.get(user_id_str, {}).get("language", "ar")
    
    if lang == "ar":
        embed = discord.Embed(
            title=f"🏆 **لوحة المتصدرين • الصفحة {page}**",
            description="**أفضل المستخدمين حسب المستوى والخبرة**",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        # العثور على ترتيب المستخدم الحالي
        user_rank = None
        for i, user in enumerate(leaderboard_data, start=1):
            if user["user_id"] == user_id_str:
                user_rank = i
                break
        
        if user_rank:
            embed.add_field(
                name="🎯 **ترتيبك**",
                value=f"**#{user_rank} • {user_data.get(user_id_str, {}).get('user_name', 'أنت')}**\nالمستوى: {user_progress.get(user_id_str, {}).get('level', 1)}",
                inline=False
            )
        
        # بناء جدول المتصدرين
        leaderboard_text = "```css\n"
        leaderboard_text += "┌───┬──────────────────┬──────┬─────────┐\n"
        leaderboard_text += "│ # │      الاسم       │المستوى│ الرسائل │\n"
        leaderboard_text += "├───┼──────────────────┼──────┼─────────┤\n"
        
        for i, user in enumerate(leaderboard_data[start_idx:end_idx], start=start_idx+1):
            rank_emoji = ""
            if i == 1:
                rank_emoji = "🥇 "
            elif i == 2:
                rank_emoji = "🥈 "
            elif i == 3:
                rank_emoji = "🥉 "
            
            username = user["user_name"]
            if len(username) > 12:
                username = username[:12] + ".."
            
            leaderboard_text += f"│{i:3}│ {rank_emoji}{username:14} │ LV{user['level']:3} │ {user['messages']:7} │\n"
        
        leaderboard_text += "└───┴──────────────────┴──────┴─────────┘\n"
        leaderboard_text += f"📊 إجمالي اللاعبين: {len(leaderboard_data)}\n```"
        
        embed.add_field(
            name="📈 **الترتيب**",
            value=leaderboard_text,
            inline=False
        )
        
        total_pages = (len(leaderboard_data) + items_per_page - 1) // items_per_page
        if total_pages > 1:
            embed.add_field(
                name="📄 **التنقل**",
                value=f"الصفحة **{page}/{total_pages}**\nاستخدم `!top [رقم الصفحة]` للتنقل",
                inline=False
            )
        
        embed.set_footer(text="استمر في المحادثة لتصعد في الترتيب!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🏆.png")
        
    else:
        embed = discord.Embed(
            title=f"🏆 **Leaderboard • Page {page}**",
            description="**Top users by level and experience**",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        # Find current user's rank
        user_rank = None
        for i, user in enumerate(leaderboard_data, start=1):
            if user["user_id"] == user_id_str:
                user_rank = i
                break
        
        if user_rank:
            embed.add_field(
                name="🎯 **Your Rank**",
                value=f"**#{user_rank} • {user_data.get(user_id_str, {}).get('user_name', 'You')}**\nLevel: {user_progress.get(user_id_str, {}).get('level', 1)}",
                inline=False
            )
        
        # Build leaderboard table
        leaderboard_text = "```css\n"
        leaderboard_text += "┌───┬──────────────────┬──────┬─────────┐\n"
        leaderboard_text += "│ # │       Name       │ Level│ Messages│\n"
        leaderboard_text += "├───┼──────────────────┼──────┼─────────┤\n"
        
        for i, user in enumerate(leaderboard_data[start_idx:end_idx], start=start_idx+1):
            rank_emoji = ""
            if i == 1:
                rank_emoji = "🥇 "
            elif i == 2:
                rank_emoji = "🥈 "
            elif i == 3:
                rank_emoji = "🥉 "
            
            username = user["user_name"]
            if len(username) > 12:
                username = username[:12] + ".."
            
            leaderboard_text += f"│{i:3}│ {rank_emoji}{username:14} │ LV{user['level']:3} │ {user['messages']:7} │\n"
        
        leaderboard_text += "└───┴──────────────────┴──────┴─────────┘\n"
        leaderboard_text += f"📊 Total Players: {len(leaderboard_data)}\n```"
        
        embed.add_field(
            name="📈 **Ranking**",
            value=leaderboard_text,
            inline=False
        )
        
        total_pages = (len(leaderboard_data) + items_per_page - 1) // items_per_page
        if total_pages > 1:
            embed.add_field(
                name="📄 **Navigation**",
                value=f"Page **{page}/{total_pages}**\nUse `!top [page number]` to navigate",
                inline=False
            )
        
        embed.set_footer(text="Keep chatting to climb the ranks!")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/🏆.png")
    
    await ctx.send(embed=embed)

@bot.command(aliases=['إحصائيات', 'stats'])
@commands.is_owner()  # للمالك فقط
async def bot_stats(ctx):
    """إحصائيات البوت (للمالك فقط)"""
    try:
        total_users = len([uid for uid, data in user_data.items() if data.get("activated", False)])
        active_today = len([uid for uid, data in user_data.items() 
                           if data.get("activated", False) and 
                           datetime.fromisoformat(data.get("joined_at", "2023-01-01")).date() == datetime.now().date()])
        
        total_messages = sum([p.get("messages", 0) for p in user_progress.values()])
        uptime = datetime.now() - bot_start_time
        
        # تحليل الذاكرة
        memory_info = ""
        memory_info += f"• المستخدمون: {len(user_data)}\n"
        memory_info += f"• المحادثات: {sum([len(h) for h in user_conversation_history.values()])}\n"
        memory_info += f"• الملفات: {len([f for f in os.listdir(DATA_DIR) if f.endswith('.json')]) if os.path.exists(DATA_DIR) else 0}"
        
        embed = discord.Embed(
            title="📊 **إحصائيات البوت**",
            description="**معلومات وأداء النظام**",
            color=discord.Color.dark_green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👥 **المستخدمون**",
            value=f"""
            ```yaml
            النشطون: {total_users}
            الجدد اليوم: {active_today}
            الرسائل: {total_messages}
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="⏱️ **وقت التشغيل**",
            value=f"""
            ```css
            [📅] بدأ: {bot_start_time.strftime('%Y-%m-%d %H:%M')}
            [⏳] الوقت: {uptime.days} يوم
            [🕐] الساعات: {uptime.seconds // 3600} ساعة
            ```
            """,
            inline=False
        )
        
        embed.add_field(
            name="💾 **الذاكرة**",
            value=f"```{memory_info}```",
            inline=False
        )
        
        embed.add_field(
            name="📈 **الأداء**",
            value=f"""
            ```css
            [⚡] البوت: {'🟢 Online' if bot.is_ready() else '🔴 Offline'}
            [🔧] المهام: {len(bot.cogs)} مهمة نشطة
            [💬] القنوات: {len(bot.guilds)} سيرفر
            ```
            """,
            inline=False
        )
        
        embed.set_footer(text=f"آخر تحديث: {datetime.now().strftime('%H:%M:%S')}")
        embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else "https://cdn.discordapp.com/emojis/🤖.png")
        
        await ctx.send(embed=embed)
        
    except commands.NotOwner:
        embed = discord.Embed(
            title="🚫 **غير مصرح**",
            description="**هذا الأمر متاح فقط لمطور البوت**",
            color=discord.Color.red()
        )
        embed.set_footer(text="تحتاج إلى صلاحيات المالك")
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="⚠️ **خطأ في الإحصائيات**",
            description=f"**حدث خطأ:**\n```{str(e)[:100]}```",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

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
                                    if lang == "ar":
                                        messages = [
                                            "💭 **انت رحت فين؟** أنتظر ردك!",
                                            "😢 **انت زعلت مني ولا حاجه؟** ما تتغيبش عليا!",
                                            "✨ **فينك كل ده؟** اشتقتلك!",
                                            "🎭 **كارف وا كدا يعني؟** تعال كلمني!",
                                            "💔 **زهقت مني ولا ايه؟** ما تسيبنيش!"
                                        ]
                                    else:
                                        messages = [
                                            "💭 **Where did you go?** Waiting for your reply!",
                                            "😢 **Are you upset with me?** Don't disappear on me!",
                                            "✨ **Where have you been?** I miss you!",
                                            "🎭 **Ignoring me like that?** Come talk to me!",
                                            "💔 **Getting tired of me?** Don't leave me!"
                                        ]
                                    
                                    message = random.choice(messages)
                                    
                                    await user.send(f"```css\n[ ⏰ إشعار ]\n```{message}")
                                    notified_users.add(user_id_str)
                                except:
                                    pass
        except:
            pass
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
                            lang = user_data.get(user_id_str, {}).get("language", "ar")
                            
                            if lang == "ar":
                                await user.send(f"```css\n[ ⏰ تذكير ]\n```**{reminder.get('message', 'بدون رسالة')}**")
                            else:
                                await user.send(f"```css\n[ ⏰ Reminder ]\n```**{reminder.get('message', 'No message')}**")
                            
                            reminders.remove(reminder)
                            save_user_data(user_id_str)
                        except:
                            pass
            await asyncio.sleep(60)
        except:
            await asyncio.sleep(60)

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

        # التعامل مع الردود العادية (بدون Embeds)
        if isinstance(reply, (list, tuple)):
            for r in reply:
                if r:
                    await message.channel.send(r)
                    await asyncio.sleep(0.12)
        else:
            if reply:
                await message.channel.send(reply)
            
        # تحديث XP والمستوى
        if uid in user_progress:
            user_progress[uid]["messages"] = user_progress[uid].get("messages", 0) + 1
            user_progress[uid]["xp"] = user_progress[uid].get("xp", 0) + random.randint(2, 8)
            
            # تحقق من الترقية
            current_level = user_progress[uid].get("level", 1)
            xp_needed = current_level * 100
            if user_progress[uid]["xp"] >= xp_needed:
                user_progress[uid]["level"] = current_level + 1
                user_progress[uid]["xp"] = 0
                
                # إرسال رسالة ترقية
                lang = user_data.get(uid, {}).get("language", "ar")
                if lang == "ar":
                    await message.channel.send(f"```css\n[ 🎉 تهانينا! ]\n```**لقد ارتقيت إلى المستوى {current_level + 1}!** ⭐")
                else:
                    await message.channel.send(f"```css\n[ 🎉 Congratulations! ]\n```**You leveled up to Level {current_level + 1}!** ⭐")
            
            save_user_data(uid)
        
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
            "joined_at": datetime.now().isoformat(),
            "traits": {"curiosity": 50, "sensitivity": 50, "happiness": 50, "sadness": 20, "boldness": 50, "kindness": 50, "shyness": 20, "intelligence": 80}
        }
        user_progress[user_id] = {"level": 1, "xp": 0, "messages": 0}
        user_reminders[user_id] = []
        user_conversation_history[user_id] = []
        save_user_data(user_id)
    return True

# ============================================
# نظام التذاكر الفاخم
# ============================================

# ============================================
# تشغيل البوت
# ============================================

@bot.event
async def on_ready():
    print(f"✨ **البوت شغال** دلوقتي كـ {bot.user}")
    load_data()
    # تشغيل المهام الجانبية
    if not watch_files.is_running(): watch_files.start()
    if not cleanup_old_data.is_running(): cleanup_old_data.start()
    
    bot.loop.create_task(check_inactive_users())
    bot.loop.create_task(check_reminders_task())
    
    # تحميل نظام التذاكر من الملف الثاني
    try:
        from luxury_tickets import setup
        await setup(bot)
        print("✅ تم تحميل نظام التذاكر")
    except Exception as e:
        print(f"❌ خطأ في تحميل نظام التذاكر: {e}")

if __name__ == "__main__":
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("❌ لم يتم العثور على التوكن DISCORD_TOKEN")

if __name__ == "__main__":
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("❌ Cannot start bot: DISCORD_TOKEN not provided.")
        print("ℹ️ Web server will still run. Configure DISCORD_TOKEN in Railway variables.")
        # Keep the process alive so Railway doesn't restart
        import time
        while True:
            time.sleep(60)