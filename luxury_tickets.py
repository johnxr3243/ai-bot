# luxury_tickets.py - نظام التذاكر الفاخم
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select, Modal, TextInput
import json
import os
from datetime import datetime, timedelta
import asyncio  
from typing import Dict, List, Optional

class LuxuryTickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "luxury_tickets_config.json"
        self.tickets_file = "luxury_tickets_data.json"
        
        # ألوان فاخمة داكنة
        self.colors = {
            'primary': 0x1a1a1a,      # أسود فاخر
            'secondary': 0x2d2d2d,    # رمادي داكن
            'success': 0x00d26a,      # أخضر فاتح
            'danger': 0xff4757,       # أحمر فاتح
            'warning': 0xff9f43,      # برتقالي
            'info': 0x2e86de,         # أزرق
            'dark': 0x0c0c0c,         # أسود داكن جداً
            'embed': 0x0f0f0f         # خلفية الإمبيد
        }
        
        # تصميم الأزرار
        self.button_styles = {
            'primary': discord.ButtonStyle.secondary,
            'success': discord.ButtonStyle.success,
            'danger': discord.ButtonStyle.danger,
            'secondary': discord.ButtonStyle.primary
        }
        
        # نظام الإعدادات
        self.default_config = {
            'ticket_channel': None,
            'log_channel': None,
            'archive_category': None,
            'admin_role': None,
            'support_role': None,
            'embed_settings': {
                'title': "🎫 نظام التذاكر الفاخم",
                'description': "اختر نوع التذكرة المناسب لك",
                'footer': "نظام التذاكر الفاخم © 2024",
                'thumbnail': None,
                'image': None,
                'color': self.colors['embed']
            },
            'ticket_types': [
                {"name": "الدعم الفني", "emoji": "🔧", "color": self.colors['info']},
                {"name": "الشكاوي", "emoji": "⚠️", "color": self.colors['danger']},
                {"name": "الاقتراحات", "emoji": "💡", "color": self.colors['success']},
                {"name": "الشراء", "emoji": "💰", "color": self.colors['warning']},
                {"name": "الشراكة", "emoji": "🤝", "color": self.colors['primary']},
                {"name": "أخرى", "emoji": "❓", "color": self.colors['secondary']}
            ]
        }
        self.config = self.load_config()
        self.tickets = self.load_tickets()
        if not self.auto_save.is_running():
            self.auto_save.start()
    
    def load_config(self):
        """تحميل الإعدادات"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"✅ تم تحميل الإعدادات من {self.config_file}")
                    return config
            except:
                pass
        return self.default_config.copy()
    
    def save_config(self):
        """حفظ الإعدادات"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ خطأ في حفظ الإعدادات: {e}")
    
    def load_tickets(self):
        """تحميل بيانات التذاكر"""
        if os.path.exists(self.tickets_file):
            try:
                with open(self.tickets_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"tickets": {}, "counter": 0}
    
    def save_tickets(self):
        """حفظ بيانات التذاكر"""
        try:
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump(self.tickets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ خطأ في حفظ التذاكر: {e}")
    
    @tasks.loop(minutes=5)
    async def auto_save(self):
        """حفظ تلقائي"""
        self.save_config()
        self.save_tickets()
    
    # ==================== أوامر الإعداد ====================
    
    @commands.command(name="تيكت_إعداد", aliases=['ticketsetup'])
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx):
        """إعداد النظام الكامل"""
        embed = discord.Embed(
            title="⚙️ **إعداد نظام التذاكر الفاخم**",
            description="**سيتم إعداد النظام بالكامل...**",
            color=self.colors['primary']
        )
        embed.set_footer(text="جاري الإعداد...")
        
        msg = await ctx.send(embed=embed)
        
        # 1. إنشاء رتب الأدمن
        admin_role = await ctx.guild.create_role(
            name="🎩 فريق الإدارة",
            color=discord.Color(self.colors['primary']),
            permissions=discord.Permissions.all(),
            reason="نظام التذاكر - فريق الإدارة"
        )
        
        # 2. إنشاء رتب الدعم
        support_role = await ctx.guild.create_role(
            name="🔧 فريق الدعم",
            color=discord.Color(self.colors['info']),
            permissions=discord.Permissions(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                manage_channels=True
            ),
            reason="نظام التذاكر - فريق الدعم"
        )
        
        # 3. إنشاء قسم التذاكر
        tickets_category = await ctx.guild.create_category(
            name="🎫 التذاكر المفتوحة",
            position=0
        )
        
        # 4. إنشاء قسم الأرشيف
        archive_category = await ctx.guild.create_category(
            name="📁 الأرشيف",
            position=1
        )
        
        # 5. إنشاء قناة التذاكر
        ticket_channel = await ctx.guild.create_text_channel(
            name="🎫-افتح-تذكرة",
            category=tickets_category,
            topic="نظام التذاكر الفاخم - اضغط لفتح تذكرة"
        )
        
        # 6. إنشاء قناة السجلات
        log_channel = await ctx.guild.create_text_channel(
            name="📊-سجلات-النظام",
            category=tickets_category,
            topic="سجلات جميع التذاكر والإجراءات"
        )
        
        # حفظ الإعدادات
        self.config['guild_id'] = str(ctx.guild.id)
        self.config['ticket_channel'] = ticket_channel.id
        self.config['log_channel'] = log_channel.id
        self.config['archive_category'] = archive_category.id
        self.config['admin_role'] = admin_role.id
        self.config['support_role'] = support_role.id
        self.save_config()
        
        # إرسال لوحة التذاكر
        await self.send_ticket_panel(ticket_channel)
        
        # تحديث الرسالة
        embed = discord.Embed(
            title="✅ **تم الإعداد بنجاح!**",
            description="**تم إنشاء النظام الفاخم بالكامل**",
            color=self.colors['success'],
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📋 **المكونات المنشأة:**",
            value=f"""
            • {admin_role.mention} - فريق الإدارة
            • {support_role.mention} - فريق الدعم
            • {tickets_category.name} - قسم التذاكر
            • {archive_category.name} - قسم الأرشيف
            • {ticket_channel.mention} - لوحة التذاكر
            • {log_channel.mention} - سجلات النظام
            """,
            inline=False
        )
        
        embed.add_field(
            name="🎯 **الأوامر المتاحة:**",
            value="""
            `!تيكت_لوحة` - إعادة إرسال اللوحة
            `!تيكت_إعدادات` - تعديل الإعدادات
            `!تيكت_تعديل` - تعديل تصميم اللوحة
            `!تيكت_صوره [رابط]` - إضافة صورة للوحة
            `!تيكت_تحديد_قناة` - تحديد قنوات مختلفة
            `!تيكت_إضافة_نوع` - إضافة نوع تذكرة جديد
            `!تيكت_قفل [رقم]` - قفل تذكرة (للأدمن)
            `!تيكت_قائمة` - عرض جميع التذاكر
            `!تيكت_أرشيف` - نقل تذكرة للأرشيف
            `!تيكت_إضافة` - إضافة عضو للتذكرة
            """,
            inline=False
        )
        
        await msg.edit(embed=embed)
        
        # إضافة الأدمن الحالي للرتبة
        await ctx.author.add_roles(admin_role)
    
    async def send_ticket_panel(self, channel):
        """إرسال لوحة التذاكر الفاخمة"""
        # بناء الإمبيد
        embed_settings = self.config.get('embed_settings', {})
        
        embed = discord.Embed(
            title=embed_settings.get('title', "🎫 نظام التذاكر الفاخم"),
            description=embed_settings.get('description', "اختر نوع التذكرة المناسب لك"),
            color=embed_settings.get('color', self.colors['embed']),
            timestamp=datetime.now()
        )
        
        # إضافة أنواع التذاكر
        ticket_types = self.config.get('ticket_types', [])
        for i, ttype in enumerate(ticket_types, 1):
            embed.add_field(
                name=f"{ttype.get('emoji', '🎫')} **{ttype.get('name', f'النوع {i}')}**",
                value=f"اضغط لفتح تذكرة {ttype.get('name', '')}",
                inline=True
            )
        
        # إضافة الصورة المصغرة والرئيسية
        if embed_settings.get('thumbnail'):
            embed.set_thumbnail(url=embed_settings['thumbnail'])
        
        if embed_settings.get('image'):
            embed.set_image(url=embed_settings['image'])
        
        embed.set_footer(text=embed_settings.get('footer', "نظام التذاكر الفاخم"))
        
        # بناء الأزرار
        view = View(timeout=None)
        
        for ttype in ticket_types:
            button = Button(
                label=ttype.get('name', 'تذكرة'),
                emoji=ttype.get('emoji', '🎫'),
                style=self.button_styles['primary'],
                custom_id=f"ticket_{ttype.get('name', 'default')}"
            )
            button.callback = lambda i, tt=ttype: self.create_luxury_ticket(i, tt)
            view.add_item(button)
        
        # زر إضافي لإدارة التذاكر (للأدمن فقط)
        admin_button = Button(
            label="إدارة التذاكر",
            emoji="⚙️",
            style=self.button_styles['secondary'],
            custom_id="ticket_admin_panel"
        )
        admin_button.callback = self.show_admin_panel
        view.add_item(admin_button)
        
        await channel.send(embed=embed, view=view)
    
    # ==================== إنشاء تذكرة فاخمة ====================
    
    async def create_luxury_ticket(self, interaction, ticket_type):
        """إنشاء تذكرة فاخمة"""
        user = interaction.user
        guild = interaction.guild
        
        # التحقق من وجود إعدادات
        if 'guild_id' not in self.config or str(guild.id) != self.config['guild_id']:
            await interaction.response.send_message("❌ النظام غير مثبت في هذا السيرفر!", ephemeral=True)
            return
        
        # زيادة العداد
        self.tickets['counter'] += 1
        ticket_id = self.tickets['counter']
        
        # إنشاء القناة
        category = guild.get_channel(self.config.get('archive_category'))
        if not category:
            category = await guild.create_category("🎫 التذاكر المفتوحة")
        
        # صلاحيات القناة
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                manage_channels=True,
                manage_messages=True
            )
        }
        
        # إضافة فريق الدعم والأدمن
        admin_role = guild.get_role(self.config.get('admin_role'))
        support_role = guild.get_role(self.config.get('support_role'))
        
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                manage_channels=True
            )
        
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True
            )
        
        # إنشاء القناة
        ticket_channel = await guild.create_text_channel(
            name=f"🎫-{ticket_id}-{user.name}",
            category=category,
            overwrites=overwrites,
            topic=f"تذكرة {ticket_type.get('name', '')} | {user.name} | #{ticket_id}"
        )
        
        # حفظ بيانات التذكرة
        ticket_key = f"{guild.id}_{ticket_id}"
        self.tickets['tickets'][ticket_key] = {
            'id': ticket_id,
            'user_id': user.id,
            'user_name': str(user),
            'channel_id': ticket_channel.id,
            'type': ticket_type.get('name', 'عام'),
            'color': ticket_type.get('color', self.colors['primary']),
            'status': 'مفتوحة',
            'created_at': datetime.now().isoformat(),
            'support_team': [],
            'messages': []
        }
        self.save_tickets()
        
        # إنشاء إمبيد التذكرة الفاخم
        embed = discord.Embed(
            title=f"🎫 **{ticket_type.get('name', 'تذكرة')} - #{ticket_id}**",
            description=f"""
            **مرحباً {user.mention}!**
            
            **✨ تم فتح تذكرتك الفاخمة بنجاح ✨**
            
            **📋 معلومات التذكرة:**
            • **النوع:** {ticket_type.get('name', 'تذكرة')} {ticket_type.get('emoji', '🎫')}
            • **الرقم:** `#{ticket_id}`
            • **التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
            • **الحالة:** 🟢 **مفتوحة**
            
            **💬 الرجاء شرح طلبك بالتفصيل...**
            
            **🎩 فريق الدعم سيرد عليك في أقرب وقت.**
            """,
            color=ticket_type.get('color', self.colors['primary']),
            timestamp=datetime.now()
        )
        
        # إضافة صورة إذا موجودة
        if ticket_type.get('image'):
            embed.set_image(url=ticket_type['image'])
        
        # إضافة صورة مصغرة
        if ticket_type.get('thumbnail'):
            embed.set_thumbnail(url=ticket_type['thumbnail'])
        
        embed.set_footer(text="نظام التذاكر الفاخم | يمكنك استخدام الاستيكر والصور")
        
        # أزرار التحكم الفاخمة
        control_view = View(timeout=None)
        
        # زر الإغلاق (أسود)
        close_btn = Button(
            label="🔒 إغلاق التذكرة",
            style=discord.ButtonStyle.secondary,
            custom_id=f"close_{ticket_id}"
        )
        close_btn.callback = lambda i: self.close_ticket(i, ticket_id)
        control_view.add_item(close_btn)
        
        # زر الأرشيف (رمادي داكن)
        archive_btn = Button(
            label="📁 نقل للأرشيف",
            style=discord.ButtonStyle.secondary,
            custom_id=f"archive_{ticket_id}"
        )
        archive_btn.callback = lambda i: self.archive_ticket(i, ticket_id)
        control_view.add_item(archive_btn)
        
        # زر إضافة عضو (أخضر فاتح)
        add_btn = Button(
            label="➕ إضافة عضو",
            style=discord.ButtonStyle.success,
            custom_id=f"add_{ticket_id}"
        )
        add_btn.callback = lambda i: self.add_user_modal(i, ticket_id)
        control_view.add_item(add_btn)
        
        # زر العودة (أزرق)
        reopen_btn = Button(
            label="🔓 إعادة فتح",
            style=discord.ButtonStyle.primary,
            custom_id=f"reopen_{ticket_id}"
        )
        reopen_btn.callback = lambda i: self.reopen_ticket(i, ticket_id)
        control_view.add_item(reopen_btn)
        
        # الإرسال
        await ticket_channel.send(
            content=f"{user.mention}" + 
                   (f" | {support_role.mention}" if support_role else "") +
                   (f" | {admin_role.mention}" if admin_role else ""),
            embed=embed,
            view=control_view
        )
        
        # رد للمستخدم
        await interaction.response.send_message(
            f"✅ **✨ تم إنشاء تذكرتك الفاخمة! ✨**\n\n" +
            f"**🎫 التذكرة:** #{ticket_id}\n" +
            f"**🔗 الرابط:** {ticket_channel.mention}\n" +
            f"**🎩 فريق الدعم:** {support_role.mention if support_role else 'سيتم التعيين قريباً'}",
            ephemeral=True
        )
        
        # تسجيل في السجلات
        await self.log_action(
            f"🎫 **تم فتح تذكرة جديدة**\n\n" +
            f"**المستخدم:** {user.mention}\n" +
            f"**النوع:** {ticket_type.get('name', 'تذكرة')}\n" +
            f"**الرقم:** #{ticket_id}\n" +
            f"**القناة:** {ticket_channel.mention}"
        )
    
    # ==================== أوامر التحكم ====================
    
    @commands.command(name="تيكت_قفل", aliases=['ticketclose'])
    @commands.has_permissions(manage_channels=True)
    async def close_ticket_command(self, ctx, ticket_id: int = None):
        """قفل تذكرة (للأدمن)"""
        if not ticket_id:
            # البحث عن التذكرة الحالية
            ticket_key = await self.find_ticket_by_channel(ctx.channel.id)
            if not ticket_key:
                await ctx.send("❌ هذه القناة ليست تذكرة!")
                return
            ticket_id = self.tickets['tickets'][ticket_key]['id']
        
        await self.close_ticket_manual(ctx, ticket_id)
    
    async def close_ticket_manual(self, ctx, ticket_id):
        """قفل تذكرة يدوياً"""
        guild_id = str(ctx.guild.id)
        ticket_key = f"{guild_id}_{ticket_id}"
        
        if ticket_key not in self.tickets['tickets']:
            await ctx.send(f"❌ التذكرة #{ticket_id} غير موجودة!")
            return
        
        ticket = self.tickets['tickets'][ticket_key]
        
        # تحديث الحالة
        ticket['status'] = 'مغلقة'
        ticket['closed_at'] = datetime.now().isoformat()
        ticket['closed_by'] = ctx.author.id
        self.save_tickets()
        
        # إرسال إمبيد الإغلاق
        embed = discord.Embed(
            title="🔒 **تم إغلاق التذكرة**",
            description=f"**تم إغلاق التذكرة بواسطة {ctx.author.mention}**",
            color=self.colors['danger'],
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📋 **معلومات الإغلاق:**",
            value=f"""
            **التذكرة:** #{ticket_id}
            **النوع:** {ticket['type']}
            **المستخدم:** <@{ticket['user_id']}>
            **تاريخ الإغلاق:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
            """,
            inline=False
        )
        
        embed.set_footer(text="سيتم نقل التذكرة للأرشيف خلال 10 ثواني")
        
        channel = ctx.guild.get_channel(ticket['channel_id'])
        if channel:
            await channel.send(embed=embed)
            
            # نقل للأرشيف بعد 10 ثواني
            await asyncio.sleep(10)
            
            archive_category = ctx.guild.get_channel(self.config.get('archive_category'))
            if archive_category:
                await channel.edit(category=archive_category, name=f"🔒-{channel.name}")
            
            # منع الكتابة
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        
        await ctx.send(f"✅ **تم إغلاق التذكرة #{ticket_id}**")
        
        # تسجيل في السجلات
        await self.log_action(
            f"🔒 **تم إغلاق تذكرة**\n\n" +
            f"**الرقم:** #{ticket_id}\n" +
            f"**بواسطة:** {ctx.author.mention}\n" +
            f"**المستخدم:** <@{ticket['user_id']}>"
        )
    
    async def close_ticket(self, interaction, ticket_id):
        """قفل تذكرة عبر الزر"""
        await self.close_ticket_manual(interaction, ticket_id)
    
    @commands.command(name="تيكت_أرشيف", aliases=['ticketarchive'])
    @commands.has_permissions(manage_channels=True)
    async def archive_ticket_command(self, ctx, ticket_id: int = None):
        """نقل تذكرة للأرشيف"""
        if not ticket_id:
            ticket_key = await self.find_ticket_by_channel(ctx.channel.id)
            if not ticket_key:
                await ctx.send("❌ هذه القناة ليست تذكرة!")
                return
            ticket_id = self.tickets['tickets'][ticket_key]['id']
        
        await self.archive_ticket_manual(ctx, ticket_id)
    
    async def archive_ticket_manual(self, ctx, ticket_id):
        """نقل تذكرة للأرشيف يدوياً"""
        guild_id = str(ctx.guild.id)
        ticket_key = f"{guild_id}_{ticket_id}"
        
        if ticket_key not in self.tickets['tickets']:
            await ctx.send(f"❌ التذكرة #{ticket_id} غير موجودة!")
            return
        
        ticket = self.tickets['tickets'][ticket_key]
        
        # نقل القناة
        channel = ctx.guild.get_channel(ticket['channel_id'])
        if channel:
            archive_category = ctx.guild.get_channel(self.config.get('archive_category'))
            if archive_category:
                await channel.edit(category=archive_category, name=f"📁-{channel.name}")
                
                embed = discord.Embed(
                    title="📁 **تم نقل التذكرة للأرشيف**",
                    description=f"تم نقل التذكرة للأرشيف بواسطة {ctx.author.mention}",
                    color=self.colors['secondary']
                )
                await channel.send(embed=embed)
        
        await ctx.send(f"✅ **تم نقل التذكرة #{ticket_id} للأرشيف**")
    
    async def archive_ticket(self, interaction, ticket_id):
        """نقل تذكرة للأرشيف عبر الزر"""
        await self.archive_ticket_manual(interaction, ticket_id)
    
    # ==================== أوامر التعديل ====================
    
    @commands.command(name="تيكت_تعديل", aliases=['ticketedit'])
    @commands.has_permissions(administrator=True)
    async def edit_panel(self, ctx, setting: str = None, *, value: str = None):
        """تعديل تصميم لوحة التذاكر"""
        if not setting or not value:
            embed = discord.Embed(
                title="⚙️ **تعديل لوحة التذاكر**",
                description="**استخدم:**\n`!تيكت_تعديل [الإعداد] [القيمة]`",
                color=self.colors['primary']
            )
            
            embed.add_field(
                name="📝 **الإعدادات المتاحة:**",
                value="""
                `title` - عنوان اللوحة
                `description` - وصف اللوحة
                `footer` - نص الفوتر
                `color` - لون الإمبيد (كود HEX)
                """,
                inline=False
            )
            
            embed.add_field(
                name="💡 **أمثلة:**",
                value="""
                `!تيكت_تعديل title 🎫 مركز الدعم الفاخم`
                `!تيكت_تعديل description اختر نوع التذكرة المناسب`
                `!تيكت_تعديل footer نظام التذاكر الفاخم © 2024`
                `!تيكت_تعديل color #0f0f0f`
                """,
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        # التحقق من وجود إعدادات الإمبيد
        if 'embed_settings' not in self.config:
            self.config['embed_settings'] = {}
        
        # تحديث الإعداد
        if setting in ['title', 'description', 'footer', 'color']:
            if setting == 'color':
                # تحويل HEX إلى عدد صحيح
                try:
                    value = int(value.replace('#', ''), 16)
                except:
                    await ctx.send("❌ **لون غير صحيح!**\nاستخدم تنسيق HEX مثل: `#0f0f0f`")
                    return
            
            self.config['embed_settings'][setting] = value
            self.save_config()
            
            embed = discord.Embed(
                title="✅ **تم التعديل بنجاح**",
                description=f"**تم تحديث `{setting}` إلى:**\n```{value}```",
                color=self.colors['success']
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ **إعداد غير صحيح!**\nاستخدم `!تيكت_تعديل` لرؤية الإعدادات المتاحة")
    
    @commands.command(name="تيكت_صوره", aliases=['ticketimage'])
    @commands.has_permissions(administrator=True)
    async def set_image(self, ctx, image_type: str = None, *, image_url: str = None):
        """إضافة صورة للوحة التذاكر"""
        if not image_type or not image_url:
            embed = discord.Embed(
                title="🖼️ **إضافة صورة للوحة**",
                description="**استخدم:**\n`!تيكت_صوره [النوع] [الرابط]`",
                color=self.colors['primary']
            )
            
            embed.add_field(
                name="📸 **الأنواع:**",
                value="""
                `thumbnail` - صورة مصغرة
                `image` - صورة رئيسية
                `sticker` - استيكر (إيموجي كبير)
                """,
                inline=False
            )
            
            embed.add_field(
                name="💡 **أمثلة:**",
                value="""
                `!تيكت_صوره thumbnail https://example.com/image.png`
                `!تيكت_صوره image https://example.com/banner.jpg`
                `!تيكت_صوره sticker https://cdn.discordapp.com/stickers/12345.png`
                """,
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        if image_type not in ['thumbnail', 'image', 'sticker']:
            await ctx.send("❌ **نوع غير صحيح!**\nاستخدم: `thumbnail`, `image`, أو `sticker`")
            return
        
        # التحقق من الرابط
        if not image_url.startswith(('http://', 'https://')):
            await ctx.send("❌ **رابط غير صحيح!**\nيجب أن يبدأ بـ `http://` أو `https://`")
            return
        
        # تحديث الإعداد
        if 'embed_settings' not in self.config:
            self.config['embed_settings'] = {}
        
        self.config['embed_settings'][image_type] = image_url
        self.save_config()
        
        embed = discord.Embed(
            title="✅ **تم إضافة الصورة**",
            description=f"**تم إضافة {image_type} بنجاح!**",
            color=self.colors['success']
        )
        
        # عرض الصورة
        if image_type == 'thumbnail':
            embed.set_thumbnail(url=image_url)
        elif image_type == 'image':
            embed.set_image(url=image_url)
        elif image_type == 'sticker':
            embed.add_field(name="📎 **الاستيكر:**", value=f"[رابط الاستيكر]({image_url})", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="تيكت_تحديد_قناة", aliases=['ticketsetchannel'])
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx, channel_type: str = None, channel: discord.TextChannel = None):
        """تحديد قنوات النظام"""
        if not channel_type or not channel:
            embed = discord.Embed(
                title="📌 **تحديد القنوات**",
                description="**استخدم:**\n`!تيكت_تحديد_قناة [النوع] [#القناة]`",
                color=self.colors['primary']
            )
            
            embed.add_field(
                name="🎯 **الأنواع:**",
                value="""
                `ticket` - قناة لوحة التذاكر
                `log` - قناة السجلات
                """,
                inline=False
            )
            
            embed.add_field(
                name="💡 **أمثلة:**",
                value="""
                `!تيكت_تحديد_قناة ticket #🎫-تذاكر`
                `!تيكت_تحديد_قناة log #📊-سجلات`
                """,
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        if channel_type not in ['ticket', 'log']:
            await ctx.send("❌ **نوع غير صحيح!**\nاستخدم: `ticket` أو `log`")
            return
        
        # تحديث الإعداد
        if channel_type == 'ticket':
            self.config['ticket_channel'] = channel.id
            key = "لوحة التذاكر"
        else:
            self.config['log_channel'] = channel.id
            key = "السجلات"
        
        self.save_config()
        
        embed = discord.Embed(
            title="✅ **تم التحديد بنجاح**",
            description=f"**تم تعيين {key} إلى:**\n{channel.mention}",
            color=self.colors['success']
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="تيكت_إضافة_نوع", aliases=['ticketaddtype'])
    @commands.has_permissions(administrator=True)
    async def add_ticket_type(self, ctx, emoji: str = None, *, name: str = None):
        """إضافة نوع تذكرة جديد"""
        if not emoji or not name:
            embed = discord.Embed(
                title="🎨 **إضافة نوع تذكرة جديد**",
                description="**استخدم:**\n`!تيكت_إضافة_نوع [الإيموجي] [الاسم]`",
                color=self.colors['primary']
            )
            
            embed.add_field(
                name="💡 **مثال:**",
                value="`!تيكت_إضافة_نوع 🎮 دعم الألعاب`",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        # التحقق من وجود قائمة الأنواع
        if 'ticket_types' not in self.config:
            self.config['ticket_types'] = []
        
        # إضافة النوع الجديد
        new_type = {
            "name": name,
            "emoji": emoji,
            "color": self.colors['primary']
        }
        
        self.config['ticket_types'].append(new_type)
        self.save_config()
        
        embed = discord.Embed(
            title="✅ **تم الإضافة بنجاح**",
            description=f"**تم إضافة نوع تذكرة جديد:**\n{emoji} **{name}**",
            color=self.colors['success']
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="تيكت_لوحة", aliases=['ticketpanel'])
    @commands.has_permissions(administrator=True)
    async def resend_panel(self, ctx):
        """إعادة إرسال لوحة التذاكر"""
        if 'ticket_channel' not in self.config or not self.config['ticket_channel']:
            await ctx.send("❌ **لم يتم تعيين قناة التذاكر!**\nاستخدم `!تيكت_إعداد` أولاً")
            return
        
        channel = ctx.guild.get_channel(self.config['ticket_channel'])
        if not channel:
            await ctx.send("❌ **القناة غير موجودة!**")
            return
        
        # محو الرسائل القديمة
        try:
            await channel.purge(limit=10)
        except:
            pass
        
        # إرسال اللوحة الجديدة
        await self.send_ticket_panel(channel)
        
        embed = discord.Embed(
            title="✅ **تم إعادة إرسال اللوحة**",
            description=f"**تم إرسال لوحة التذاكر إلى:**\n{channel.mention}",
            color=self.colors['success']
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="تيكت_إضافة", aliases=['ticketadd'])
    @commands.has_permissions(manage_channels=True)
    async def add_to_ticket(self, ctx, member: discord.Member, ticket_id: int = None):
        """إضافة عضو للتذكرة"""
        if not ticket_id:
            # البحث في القناة الحالية
            ticket_key = await self.find_ticket_by_channel(ctx.channel.id)
            if not ticket_key:
                await ctx.send("❌ **هذه القناة ليست تذكرة!**\nحدد رقم التذكرة")
                return
            ticket = self.tickets['tickets'][ticket_key]
        else:
            # البحث بالرقم
            guild_id = str(ctx.guild.id)
            ticket_key = f"{guild_id}_{ticket_id}"
            if ticket_key not in self.tickets['tickets']:
                await ctx.send(f"❌ **التذكرة #{ticket_id} غير موجودة!**")
                return
            ticket = self.tickets['tickets'][ticket_key]
        
        # إضافة العضو للتذكرة
        channel = ctx.guild.get_channel(ticket['channel_id'])
        if not channel:
            await ctx.send("❌ **قناة التذكرة غير موجودة!**")
            return
        
        # إضافة الصلاحيات
        await channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True
        )
        
        # إضافة للبيانات
        if member.id not in ticket['support_team']:
            ticket['support_team'].append(member.id)
            self.save_tickets()
        
        embed = discord.Embed(
            title="✅ **تمت الإضافة بنجاح**",
            description=f"**تم إضافة {member.mention} للتذكرة #{ticket['id']}**",
            color=self.colors['success']
        )
        
        # إرسال إشعار في قناة التذكرة
        ticket_embed = discord.Embed(
            description=f"👋 **تمت إضافة {member.mention} لهذه التذكرة بواسطة {ctx.author.mention}**",
            color=self.colors['info']
        )
        await channel.send(embed=ticket_embed)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="تيكت_قائمة", aliases=['ticketlist'])
    @commands.has_permissions(manage_channels=True)
    async def list_tickets(self, ctx, status: str = "مفتوحة"):
        """عرض قائمة التذاكر"""
        guild_id = str(ctx.guild.id)
        
        # فلترة التذاكر
        tickets_list = []
        for key, ticket in self.tickets['tickets'].items():
            if key.startswith(guild_id):
                if ticket['status'].lower() == status.lower():
                    tickets_list.append(ticket)
        
        if not tickets_list:
            embed = discord.Embed(
                title=f"📋 **التذاكر {status}**",
                description=f"**لا توجد تذاكر {status} حالياً**",
                color=self.colors['secondary']
            )
            await ctx.send(embed=embed)
            return
        
        # بناء القائمة
        embed = discord.Embed(
            title=f"📋 **التذاكر {status}**",
            description=f"**عدد التذاكر:** {len(tickets_list)}",
            color=self.colors['primary'],
            timestamp=datetime.now()
        )
        
        for ticket in tickets_list[:10]:  # عرض أول 10 فقط
            status_emoji = "🟢" if ticket['status'] == 'مفتوحة' else "🔴"
            channel_mention = f"<#{ticket['channel_id']}>"
            
            embed.add_field(
                name=f"{status_emoji} **#{ticket['id']} - {ticket['type']}**",
                value=f"""
                **المستخدم:** <@{ticket['user_id']}>
                **القناة:** {channel_mention}
                **التاريخ:** {ticket['created_at'][:10]}
                """,
                inline=False
            )
        
        if len(tickets_list) > 10:
            embed.add_field(
                name="📄 **صفحات إضافية**",
                value=f"**+{len(tickets_list) - 10} تذاكر أخرى**",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="تيكت_إعدادات", aliases=['ticketsettings'])
    @commands.has_permissions(administrator=True)
    async def show_settings_command(self, ctx):
        """عرض إعدادات النظام"""
        embed = discord.Embed(
            title="⚙️ **إعدادات نظام التذاكر الفاخم**",
            description="**جميع إعدادات النظام الحالية**",
            color=self.colors['primary'],
            timestamp=datetime.now()
        )
        
        # معلومات القنوات
        ticket_channel = ctx.guild.get_channel(self.config.get('ticket_channel', 0))
        log_channel = ctx.guild.get_channel(self.config.get('log_channel', 0))
        archive_category = ctx.guild.get_channel(self.config.get('archive_category', 0))
        
        embed.add_field(
            name="📁 **القنوات:**",
            value=f"""
            **لوحة التذاكر:** {ticket_channel.mention if ticket_channel else '❌'}
            **سجلات النظام:** {log_channel.mention if log_channel else '❌'}
            **قسم الأرشيف:** {archive_category.mention if archive_category else '❌'}
            """,
            inline=False
        )
        
        # معلومات الأدوار
        admin_role = ctx.guild.get_role(self.config.get('admin_role', 0))
        support_role = ctx.guild.get_role(self.config.get('support_role', 0))
        
        embed.add_field(
            name="👥 **الأدوار:**",
            value=f"""
            **فريق الإدارة:** {admin_role.mention if admin_role else '❌'}
            **فريق الدعم:** {support_role.mention if support_role else '❌'}
            """,
            inline=False
        )
        
        # إعدادات الإمبيد
        embed_settings = self.config.get('embed_settings', {})
        
        embed.add_field(
            name="🎨 **تصميم اللوحة:**",
            value=f"""
            **العنوان:** {embed_settings.get('title', 'افتراضي')}
            **الوصف:** {embed_settings.get('description', 'افتراضي')[:50]}...
            **اللون:** `{hex(embed_settings.get('color', self.colors['embed']))}`
            **الصورة:** {'✅' if embed_settings.get('image') else '❌'}
            **الصورة المصغرة:** {'✅' if embed_settings.get('thumbnail') else '❌'}
            """,
            inline=False
        )
        
        # أنواع التذاكر
        ticket_types = self.config.get('ticket_types', [])
        
        types_text = ""
        for ttype in ticket_types:
            types_text += f"{ttype.get('emoji', '🎫')} {ttype.get('name', 'نوع')}\n"
        
        if types_text:
            embed.add_field(
                name="🎫 **أنواع التذاكر:**",
                value=types_text,
                inline=False
            )
        
        # إحصائيات
        total_tickets = len([k for k in self.tickets['tickets'].keys() if k.startswith(str(ctx.guild.id))])
        
        embed.add_field(
            name="📊 **الإحصائيات:**",
            value=f"""
            **إجمالي التذاكر:** {total_tickets}
            **آخر تذكرة:** #{self.tickets.get('counter', 0)}
            **التذاكر المفتوحة:** {len([t for t in self.tickets['tickets'].values() if t.get('status') == 'مفتوحة'])}
            """,
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # ==================== وظائف مساعدة ====================
    
    async def find_ticket_by_channel(self, channel_id):
        """البحث عن تذكرة باستخدام معرف القناة"""
        for key, ticket in self.tickets['tickets'].items():
            if ticket['channel_id'] == channel_id:
                return key
        return None
    
    async def add_user_modal(self, interaction, ticket_id):
        """فتح نافذة إضافة عضو"""
        modal = AddUserModal(self, ticket_id)
        await interaction.response.send_modal(modal)
    
    async def reopen_ticket(self, interaction, ticket_id):
        """إعادة فتح تذكرة"""
        guild_id = str(interaction.guild.id)
        ticket_key = f"{guild_id}_{ticket_id}"
        
        if ticket_key not in self.tickets['tickets']:
            await interaction.response.send_message("❌ التذكرة غير موجودة!", ephemeral=True)
            return
        
        ticket = self.tickets['tickets'][ticket_key]
        ticket['status'] = 'مفتوحة'
        self.save_tickets()
        
        channel = interaction.guild.get_channel(ticket['channel_id'])
        if channel:
            # إعادة السماح بالكتابة
            await channel.set_permissions(interaction.guild.default_role, send_messages=True)
            
            embed = discord.Embed(
                title="🔓 **تم إعادة فتح التذكرة**",
                description=f"تم إعادة فتح التذكرة بواسطة {interaction.user.mention}",
                color=self.colors['success']
            )
            await channel.send(embed=embed)
        
        await interaction.response.send_message("✅ تم إعادة فتح التذكرة!", ephemeral=True)
    
    async def show_admin_panel(self, interaction):
        """عرض لوحة التحكم للأدمن"""
        if not await self.is_admin(interaction.user):
            await interaction.response.send_message("❌ **ليس لديك صلاحية!**", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚙️ **لوحة تحكم الأدمن**",
            description="**اختر الإجراء المطلوب:**",
            color=self.colors['dark'],
            timestamp=datetime.now()
        )
        
        view = View(timeout=60)
        
        # أزرار التحكم
        buttons = [
            ("📋 قائمة التذاكر", discord.ButtonStyle.primary, "list_tickets"),
            ("⚙️ الإعدادات", discord.ButtonStyle.secondary, "settings"),
            ("🔄 تحديث اللوحة", discord.ButtonStyle.success, "refresh_panel"),
            ("📊 الإحصائيات", discord.ButtonStyle.secondary, "stats")
        ]
        
        for label, style, custom_id in buttons:
            button = Button(label=label, style=style)
            
            async def callback(i, cid=custom_id):
                if cid == "list_tickets":
                    await self.show_ticket_list(i)
                elif cid == "settings":
                    await self.show_settings_panel(i)
                elif cid == "refresh_panel":
                    await self.refresh_panel(i)
                elif cid == "stats":
                    await self.show_stats_panel(i)
            
            button.callback = callback
            view.add_item(button)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def is_admin(self, user):
        """التحقق إذا كان المستخدم أدمن"""
        if user.guild_permissions.administrator:
            return True
        
        admin_role = user.guild.get_role(self.config.get('admin_role', 0))
        if admin_role and admin_role in user.roles:
            return True
        
        return False
    
    async def log_action(self, message):
        """تسجيل الإجراءات في قناة السجلات"""
        try:
            if 'log_channel' in self.config and self.config['log_channel']:
                guild = self.bot.get_guild(int(self.config.get('guild_id', 0)))
                if guild:
                    channel = guild.get_channel(self.config['log_channel'])
                    if channel:
                        embed = discord.Embed(
                            description=message,
                            color=self.colors['secondary'],
                            timestamp=datetime.now()
                        )
                        await channel.send(embed=embed)
        except:
            pass
    
    async def show_ticket_list(self, interaction):
        """عرض قائمة التذاكر"""
        guild_id = str(interaction.guild.id)
        
        # جمع التذاكر
        open_tickets = []
        closed_tickets = []
        
        for key, ticket in self.tickets['tickets'].items():
            if key.startswith(guild_id):
                if ticket['status'] == 'مفتوحة':
                    open_tickets.append(ticket)
                else:
                    closed_tickets.append(ticket)
        
        embed = discord.Embed(
            title="📋 **قائمة التذاكر**",
            description="**إحصائيات التذاكر**",
            color=self.colors['primary'],
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🟢 **التذاكر المفتوحة:**",
            value=f"**عددها:** {len(open_tickets)}",
            inline=True
        )
        
        embed.add_field(
            name="🔴 **التذاكر المغلقة:**",
            value=f"**عددها:** {len(closed_tickets)}",
            inline=True
        )
        
        if open_tickets:
            tickets_text = ""
            for ticket in open_tickets[:5]:
                tickets_text += f"• **#{ticket['id']}** - {ticket['type']} (<@{ticket['user_id']}>)\n"
            
            embed.add_field(
                name="🎫 **آخر التذاكر المفتوحة:**",
                value=tickets_text,
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def show_settings_panel(self, interaction):
        """عرض إعدادات النظام"""
        embed = discord.Embed(
            title="⚙️ **إعدادات النظام**",
            description="**استخدم الأوامر التالية:**",
            color=self.colors['dark']
        )
        
        embed.add_field(
            name="🎨 **التصميم:**",
            value="""
            `!تيكت_تعديل` - تعديل النصوص
            `!تيكت_صوره` - إضافة صور
            `!تيكت_إضافة_نوع` - إضافة أنواع جديدة
            """,
            inline=False
        )
        
        embed.add_field(
            name="📌 **القنوات:**",
            value="""
            `!تيكت_تحديد_قناة` - تعيين القنوات
            `!تيكت_لوحة` - إعادة إرسال اللوحة
            """,
            inline=False
        )
        
        embed.add_field(
            name="👥 **الإدارة:**",
            value="""
            `!تيكت_قفل` - قفل تذكرة
            `!تيكت_أرشيف` - نقل للأرشيف
            `!تيكت_إضافة` - إضافة عضو
            `!تيكت_قائمة` - عرض التذاكر
            """,
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def refresh_panel(self, interaction):
        """تحديث لوحة التذاكر"""
        await self.resend_panel(interaction)
        await interaction.response.edit_message(
            content="✅ **تم تحديث لوحة التذاكر**",
            embed=None,
            view=None
        )
    
    async def show_stats_panel(self, interaction):
        """عرض الإحصائيات"""
        guild_id = str(interaction.guild.id)
        
        total = len([k for k in self.tickets['tickets'].keys() if k.startswith(guild_id)])
        open_count = len([t for t in self.tickets['tickets'].values() 
                         if t.get('status') == 'مفتوحة' and str(interaction.guild.id) in t.get('channel_id', '')])
        
        embed = discord.Embed(
            title="📊 **إحصائيات النظام**",
            color=self.colors['info'],
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📈 **النظرة العامة:**",
            value=f"""
            ```yaml
            الإجمالي: {total}
            المفتوحة: {open_count}
            المغلقة: {total - open_count}
            النسبة: {(open_count/total*100) if total > 0 else 0:.1f}%
            ```
            """,
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

# ==================== مودال إضافة مستخدم ====================

class AddUserModal(Modal):
    def __init__(self, ticket_system, ticket_id):
        super().__init__(title="إضافة عضو للتذكرة")
        self.ticket_system = ticket_system
        self.ticket_id = ticket_id
        
        self.user_input = TextInput(
            label="معرف العضو",
            placeholder="أدخل الـ ID الخاص بالعضو",
            style=discord.TextStyle.short,
            required=True
        )
        
        self.add_item(self.user_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_input.value)
            member = interaction.guild.get_member(user_id)
            
            if not member:
                await interaction.response.send_message("❌ العضو غير موجود!", ephemeral=True)
                return
            
            # استخدام الأمر لإضافة العضو
            ctx = await self.ticket_system.bot.get_context(interaction.message)
            ctx.author = interaction.user
            ctx.channel = interaction.channel
            
            command = self.ticket_system.bot.get_command('تيكت_إضافة')
            await ctx.invoke(command, member=member, ticket_id=self.ticket_id)
            
            await interaction.response.send_message(f"✅ تمت إضافة {member.mention}!", ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ أدخل معرف صحيح!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

# ==================== إعداد النظام ====================

async def setup(bot):
    """إضافة النظام للبوت"""
    await bot.add_cog(LuxuryTickets(bot))
    print("✨ **نظام التذاكر الفاخم جاهز!**")