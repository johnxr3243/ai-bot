import discord
from discord.ext import commands, tasks
import asyncio
from itertools import cycle
import random

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# قائمة الحالات المتغيرة
statuses = [
    {"name": "Sienna AI Dashboard", "type": discord.ActivityType.streaming, "url": "https://twitch.tv/discord"},
    {"name": "/ask for help", "type": discord.ActivityType.listening},
    {"name": "120 Servers", "type": discord.ActivityType.watching},
    {"name": "!embed", "type": discord.ActivityType.playing}  # حالة إضافية
]

current_status = 0

@tasks.loop(seconds=15)
async def change_status():
    """تغيير حالة البوت كل 15 ثانية"""
    global current_status
    
    status = statuses[current_status]
    
    # تحديد نوع النشاط
    if status["type"] == discord.ActivityType.streaming:
        activity = discord.Streaming(
            name=status["name"],
            url=status.get("url", "https://twitch.tv/discord")
        )
    elif status["type"] == discord.ActivityType.listening:
        activity = discord.Activity(
            name=status["name"],
            type=discord.ActivityType.listening
        )
    elif status["type"] == discord.ActivityType.watching:
        activity = discord.Activity(
            name=status["name"],
            type=discord.ActivityType.watching
        )
    else:
        activity = discord.Game(name=status["name"])
    
    # تغيير الحالة
    await bot.change_presence(
        activity=activity,
        status=discord.Status.online
    )
    
    # تحديث الفهرس
    current_status = (current_status + 1) % len(statuses)

@bot.event
async def on_ready():
    print(f'✅ {bot.user} جاهز للتشغيل!')
    print(f'📊 حالات البوت: {len(statuses)} حالة')
    print(f'⏱️  وقت التبديل: 15 ثانية')
    print(f'🔗 رابط إضافة البوت:')
    print(f'https://discord.com/oauth2/authorize?client_id={bot.user.id}&scope=bot&permissions=8')
    
    # بدء تبديل الحالة
    change_status.start()
    
    # عرض الحالة الأولى
    await bot.change_presence(
        activity=discord.Streaming(
            name="Sienna AI Dashboard",
            url="https://twitch.tv/discord"
        ),
        status=discord.Status.online
    )

@bot.command()
async def embed(ctx, *, content=None):
    """
    إنشاء وإرسال رسالة Embed مخصصة
    
    أمثلة:
    !embed title=عنواني description=وصف
    !embed title=عنوان color=0xff0000 image=image.png
    !embed wizard (الوضع التفاعلي)
    """
    
    if content == "wizard" or content is None:
        # الوضع التفاعلي (Wizard)
        await embed_wizard(ctx)
        return
    
    # تحليل المحتوى
    params = parse_content(content)
    await send_embed(ctx, params)

async def embed_wizard(ctx):
    """الوضع التفاعلي لإنشاء Embed"""
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    embed_data = {}
    
    # دليل المستخدم
    guide = discord.Embed(
        title="🪄 معالج إنشاء Embed",
        description="سأساعدك في إنشاء رسالة Embed خطوة بخطوة\nأرسل 'تخطي' لأي خطوة للتجاوز\nأرسل 'إلغاء' للإلغاء",
        color=discord.Color.gold()
    )
    guide.add_field(name="🚦 الألوان المتاحة", value="red, blue, green, purple, gold, random", inline=False)
    guide.add_field(name="📌 مثال للألوان", value="`0xff0000` للأحمر\n`0x00ff00` للأخضر", inline=False)
    await ctx.send(embed=guide)
    
    try:
        # 1. العنوان
        await ctx.send("**الخطوة 1/8**: أرسل عنوان الرسالة (أو 'تخطي'):")
        title_msg = await bot.wait_for('message', timeout=60.0, check=check)
        if title_msg.content.lower() != 'تخطي':
            embed_data['title'] = title_msg.content
        
        # 2. الوصف
        await ctx.send("**الخطوة 2/8**: أرسل وصف الرسالة (أو 'تخطي'):")
        desc_msg = await bot.wait_for('message', timeout=60.0, check=check)
        if desc_msg.content.lower() != 'تخطي':
            embed_data['description'] = desc_msg.content
        
        # 3. اللون
        await ctx.send("**الخطوة 3/8**: أرسل اللون (اسم أو hex مثل 0xff0000) أو 'تخطي':")
        color_msg = await bot.wait_for('message', timeout=60.0, check=check)
        if color_msg.content.lower() not in ['تخطي', 'skip']:
            embed_data['color'] = color_msg.content
        
        # 4. الصورة الرئيسية
        await ctx.send("**الخطوة 4/8**: هل تريد إرفاق صورة رئيسية؟ أرسل 'نعم' أو 'تخطي':")
        img_msg = await bot.wait_for('message', timeout=60.0, check=check)
        if img_msg.content.lower() == 'نعم':
            await ctx.send("**📤 أرسل الصورة الآن:** (أرفق صورة في الرسالة)")
            img_attach = await bot.wait_for('message', timeout=60.0, check=check)
            if img_attach.attachments:
                embed_data['image'] = img_attach.attachments[0]
        
        # 5. الصورة المصغرة
        await ctx.send("**الخطوة 5/8**: هل تريد إرفاق صورة مصغرة؟ أرسل 'نعم' أو 'تخطي':")
        thumb_msg = await bot.wait_for('message', timeout=60.0, check=check)
        if thumb_msg.content.lower() == 'نعم':
            await ctx.send("**🖼️ أرسل الصورة المصغرة الآن:**")
            thumb_attach = await bot.wait_for('message', timeout=60.0, check=check)
            if thumb_attach.attachments:
                embed_data['thumbnail'] = thumb_attach.attachments[0]
        
        # 6. حقول إضافية
        await ctx.send("**الخطوة 6/8**: هل تريد إضافة حقول؟ أرسل عدد الحقول (0-5) أو 'تخطي':")
        fields_msg = await bot.wait_for('message', timeout=60.0, check=check)
        if fields_msg.content.isdigit() and 1 <= int(fields_msg.content) <= 5:
            fields_count = int(fields_msg.content)
            embed_data['fields'] = []
            
            for i in range(fields_count):
                await ctx.send(f"**الحقل {i+1}**: أرسل اسم الحقل:")
                field_name = await bot.wait_for('message', timeout=60.0, check=check)
                
                await ctx.send(f"**الحقل {i+1}**: أرسل قيمة الحقل:")
                field_value = await bot.wait_for('message', timeout=60.0, check=check)
                
                await ctx.send(f"**الحقل {i+1}**: هل تريد عرضه في سطر؟ (نعم/لا):")
                field_inline = await bot.wait_for('message', timeout=60.0, check=check)
                
                embed_data['fields'].append({
                    'name': field_name.content,
                    'value': field_value.content,
                    'inline': field_inline.content.lower() == 'نعم'
                })
        
        # 7. الفوتر
        await ctx.send("**الخطوة 7/8**: أرسل نص الفوتر (أو 'تخطي'):")
        footer_msg = await bot.wait_for('message', timeout=60.0, check=check)
        if footer_msg.content.lower() != 'تخطي':
            embed_data['footer'] = footer_msg.content
        
        # 8. رابط الفوتر
        await ctx.send("**الخطوة 8/8**: أرسل رابط صورة الفوتر (أو 'تخطي'):")
        footer_icon_msg = await bot.wait_for('message', timeout=60.0, check=check)
        if footer_icon_msg.content.lower() != 'تخطي':
            embed_data['footer_icon'] = footer_icon_msg.content
        
        # إرسال Embed النهائي
        await send_embed(ctx, embed_data, wizard_mode=True)
        
    except asyncio.TimeoutError:
        await ctx.send("⏰ انتهى الوقت! حاول مرة أخرى.")

def parse_content(content):
    """تحليل نص الأمر إلى معلمات"""
    params = {}
    
    # تقسيم المحتوى إلى أزواج مفتاح=قيمة
    parts = content.split()
    
    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            params[key.lower()] = value
    
    return params

async def send_embed(ctx, params, wizard_mode=False):
    """إنشاء وإرسال Embed"""
    
    # معالجة اللون
    color = discord.Color.default()
    if 'color' in params:
        color_str = params['color'].lower()
        color_map = {
            'red': discord.Color.red(),
            'blue': discord.Color.blue(),
            'green': discord.Color.green(),
            'purple': discord.Color.purple(),
            'gold': discord.Color.gold(),
            'random': discord.Color.random()
        }
        
        if color_str in color_map:
            color = color_map[color_str]
        elif color_str.startswith('0x'):
            try:
                color = discord.Color(int(color_str, 16))
            except:
                pass
    
    # إنشاء Embed
    embed = discord.Embed(color=color)
    
    # إضافة العناصر
    if 'title' in params:
        embed.title = params['title']
    
    if 'description' in params:
        embed.description = params['description']
    
    # إضافة الحقول (في وضع الكود)
    if 'field1' in params:
        for i in range(1, 6):
            field_name = f'field{i}_name'
            field_value = f'field{i}_value'
            field_inline = f'field{i}_inline'
            
            if field_name in params:
                inline = params.get(field_inline, 'false').lower() == 'true'
                embed.add_field(
                    name=params[field_name],
                    value=params.get(field_value, ''),
                    inline=inline
                )
    
    # إضافة الحقول (في الوضع التفاعلي)
    if 'fields' in params:
        for field in params['fields']:
            embed.add_field(
                name=field['name'],
                value=field['value'],
                inline=field.get('inline', False)
            )
    
    # الفوتر
    if 'footer' in params:
        footer_text = params['footer']
        footer_icon = params.get('footer_icon')
        embed.set_footer(text=footer_text, icon_url=footer_icon)
    
    # الصورة المصغرة
    if 'thumbnail' in params:
        if isinstance(params['thumbnail'], discord.Attachment):
            embed.set_thumbnail(url=params['thumbnail'].url)
        else:
            embed.set_thumbnail(url=params['thumbnail'])
    
    # الصورة الرئيسية
    if 'image' in params:
        if isinstance(params['image'], discord.Attachment):
            embed.set_image(url=params['image'].url)
        else:
            embed.set_image(url=params['image'])
    
    # التحقق من وجود محتوى
    if not embed.title and not embed.description and not embed.fields:
        if not wizard_mode:
            # عرض التعليمات
            help_embed = discord.Embed(
                title="📚 كيفية استخدام !embed",
                description="**طريقتان للاستخدام:**",
                color=discord.Color.blue()
            )
            
            help_embed.add_field(
                name="1️⃣ **الطريقة السريعة (كود)**",
                value="```!embed title=عنوانك description=وصفك color=blue```\n"
                      "```!embed title=مرحبا color=0xff0000 image=رابط_الصورة```",
                inline=False
            )
            
            help_embed.add_field(
                name="2️⃣ **الطريقة التفاعلية**",
                value="```!embed wizard```\n"
                      "ستسألك خطوة بخطوة عن كل عنصر",
                inline=False
            )
            
            help_embed.add_field(
                name="🎨 **الألوان المتاحة**",
                value="`red, blue, green, purple, gold, random` أو كود hex مثل `0xff0000`",
                inline=False
            )
            
            help_embed.add_field(
                name="📎 **مثال متكامل**",
                value="```!embed title=أهلا بالجميع description=هذا وصف color=gold "
                      "field1_name=معلومات field1_value=قيمة field1_inline=true "
                      "footer=حقوق النشر footer_icon=رابط_الأيقونة```",
                inline=False
            )
            
            await ctx.send(embed=help_embed)
            return
    
    # إرسال Embed
    try:
        await ctx.send(embed=embed)
        if wizard_mode:
            await ctx.send("✅ **تم إرسال الـEmbed بنجاح!**")
    except Exception as e:
        await ctx.send(f"❌ **حدث خطأ:** {str(e)}")

@bot.command()
async def example(ctx):
    """عرض أمثلة للاستخدام"""
    examples = discord.Embed(
        title="🔄 أمثلة لأمر !embed",
        color=discord.Color.green()
    )
    
    examples.add_field(
        name="مثال 1: رسالة بسيطة",
        value="```!embed title=مرحبا! description=أهلا وسهلا color=blue```",
        inline=False
    )
    
    examples.add_field(
        name="مثال 2: مع حقل",
        value="```!embed title=إشعار color=red description=تنبيه مهم "
              "field1_name=التفاصيل field1_value=هذا تنبيف عاجل field1_inline=false```",
        inline=False
    )
    
    examples.add_field(
        name="مثال 3: مع صور",
        value="```!embed title=صورة جميلة color=purple "
              "image=https://example.com/image.png "
              "thumbnail=https://example.com/thumb.png```",
        inline=False
    )
    
    examples.add_field(
        name="مثال 4: استخدام الوضع التفاعلي",
        value="```!embed wizard```",
        inline=False
    )
    
    await ctx.send(embed=examples)

@bot.command()
async def colors(ctx):
    """عرض الألوان المتاحة"""
    color_embed = discord.Embed(
        title="🎨 لوحة الألوان",
        description="الألوان المتاحة للاستخدام مع !embed",
        color=discord.Color.random()
    )
    
    colors_list = [
        ("🔴 الأحمر", "`red` أو `0xff0000`", discord.Color.red()),
        ("🔵 الأزرق", "`blue` أو `0x0000ff`", discord.Color.blue()),
        ("🟢 الأخضر", "`green` أو `0x00ff00`", discord.Color.green()),
        ("🟣 البنفسجي", "`purple` أو `0x800080`", discord.Color.purple()),
        ("🟡 الذهبي", "`gold` أو `0xffd700`", discord.Color.gold()),
        ("🌈 عشوائي", "`random`", discord.Color.random()),
    ]
    
    for name, code, color_obj in colors_list:
        color_embed.add_field(name=name, value=code, inline=True)
    
    color_embed.set_footer(text="يمكنك استخدام الأسماء أو أكواد HEX")
    await ctx.send(embed=color_embed)

@bot.command()
async def status(ctx):
    """عرض معلومات عن حالة البوت"""
    status_info = discord.Embed(
        title="📊 حالة البوت الحالية",
        color=discord.Color.blurple()
    )
    
    # الحالة الحالية
    current = statuses[current_status]
    status_types = {
        discord.ActivityType.streaming: "🎥 بث مباشر",
        discord.ActivityType.listening: "🎵 يستمع",
        discord.ActivityType.watching: "👀 يشاهد",
        discord.ActivityType.playing: "🎮 يلعب"
    }
    
    status_info.add_field(
        name="الحالة الحالية",
        value=f"**{current['name']}**\nنوع: {status_types.get(current['type'], 'غير معروف')}",
        inline=False
    )
    
    # جميع الحالات
    status_list = ""
    for i, status in enumerate(statuses):
        indicator = "➡️" if i == current_status else "⚪"
        status_list += f"{indicator} {status['name']}\n"
    
    status_info.add_field(
        name="جميع الحالات",
        value=status_list,
        inline=False
    )
    
    status_info.add_field(
        name="⏱️ وقت التبديل",
        value="كل 15 ثانية",
        inline=True
    )
    
    status_info.add_field(
        name="🔢 عدد الحالات",
        value=str(len(statuses)),
        inline=True
    )
    
    await ctx.send(embed=status_info)

@bot.command()
@commands.has_permissions(administrator=True)
async def add_status(ctx, *, status_info: str):
    """إضافة حالة جديدة للبوت (للمسؤولين فقط)"""
    try:
        # تحليل المدخلات (التنسيق: name:اسم النشاط type:النوع url:رابط)
        parts = status_info.split()
        new_status = {}
        
        for part in parts:
            if ':' in part:
                key, value = part.split(':', 1)
                new_status[key.strip()] = value.strip()
        
        # التأكد من وجود الاسم والنوع
        if 'name' not in new_status or 'type' not in new_status:
            await ctx.send("❌ يجب تحديد الاسم والنوع (name:النص type:streaming/listening/watching/playing)")
            return
        
        # تحويل النوع
        type_map = {
            'streaming': discord.ActivityType.streaming,
            'listening': discord.ActivityType.listening,
            'watching': discord.ActivityType.watching,
            'playing': discord.ActivityType.playing
        }
        
        if new_status['type'].lower() not in type_map:
            await ctx.send("❌ نوع النشاط غير صحيح. الاختيارات: streaming, listening, watching, playing")
            return
        
        new_status['type'] = type_map[new_status['type'].lower()]
        
        # إضافة للحالات
        statuses.append(new_status)
        
        await ctx.send(f"✅ تمت إضافة حالة جديدة: **{new_status['name']}**")
        
    except Exception as e:
        await ctx.send(f"❌ احدث خطأ: {str(e)}")

@bot.command()
@commands.has_permissions(administrator=True)
async def reload_status(ctx):
    """إعادة تحميل الحالات (للمسؤولين فقط)"""
    global current_status
    current_status = 0
    await ctx.send("🔄 تم إعادة تعيين الحالات إلى البداية")
