# tickets.py - النظام الكامل
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
import json
import os
from datetime import datetime, timedelta
import asyncio
import random

# ===============================
# نظام التذاكر المتكامل
# ===============================

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "tickets_data.json"
        self.tickets = {}
        self.settings = {}
        self.load_data()
        
        # ألوان الـ Embeds
        self.colors = {
            'tech': 0x3498db,      # أزرق - الدعم الفني
            'complaint': 0xe74c3c, # أحمر - الشكاوي
            'suggestion': 0x2ecc71,# أخضر - الاقتراحات
            'purchase': 0xf1c40f,  # أصفر - الشراء
            'partnership': 0x9b59b6, # بنفسجي - الشراكة
            'other': 0x95a5a6     # رمادي - أخرى
        }
        
        # إيموجيات
        self.emojis = {
            'tech': '🔧',
            'complaint': '⚠️',
            'suggestion': '💡',
            'purchase': '💰',
            'partnership': '🤝',
            'other': '❓'
        }
        
        # أنواع التذاكر العربية
        self.ticket_types_ar = {
            'tech': 'الدعم الفني',
            'complaint': 'الشكاوي',
            'suggestion': 'الاقتراحات',
            'purchase': 'الشراء',
            'partnership': 'الشراكة',
            'other': 'الأخرى'
        }
        
        self.check_closed_tickets.start()
    
    # ========== تحميل البيانات ==========
    def load_data(self):
        """تحميل بيانات التذاكر"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tickets = data.get('tickets', {})
                    self.settings = data.get('settings', {})
                    print(f"✅ تم تحميل {len(self.tickets)} تذكرة")
            else:
                print("📁 لا توجد بيانات سابقة")
        except Exception as e:
            print(f"❌ خطأ في تحميل البيانات: {e}")
            self.tickets = {}
            self.settings = {}
    
    # ========== حفظ البيانات ==========
    def save_data(self):
        """حفظ بيانات التذاكر"""
        try:
            data = {
                'tickets': self.tickets,
                'settings': self.settings,
                'last_save': datetime.now().isoformat()
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ خطأ في حفظ البيانات: {e}")
    
    # ========== الأمر الرئيسي ==========
    @commands.command(name="تيكت", aliases=['ticket', 'تیكت'])
    @commands.has_permissions(administrator=True)
    async def setup_ticket_system(self, ctx):
        """إعداد نظام التذاكر الكامل"""
        guild = ctx.guild
        guild_id = str(guild.id)
        
        # 1. إنشاء رتبة فريق الدعم
        support_role = await guild.create_role(
            name="🔧 فريق الدعم",
            color=discord.Color.blue(),
            permissions=discord.Permissions(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            ),
            reason="نظام التذاكر - فريق الدعم"
        )
        
        # 2. إنشاء قسم التذاكر المفتوحة
        open_category = await guild.create_category(
            name="🎫 التذاكر المفتوحة",
            position=0
        )
        
        # 3. إنشاء قسم الأرشيف
        archive_category = await guild.create_category(
            name="📁 الأرشيف",
            position=1
        )
        
        # 4. إنشاء قناة لوحة التحكم
        panel_overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                add_reactions=False
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True
            ),
            support_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True
            )
        }
        
        panel_channel = await guild.create_text_channel(
            name="🎫-افتح-تذكرة",
            category=open_category,
            overwrites=panel_overwrites,
            topic="اضغط على الزر لفتح تذكرة جديدة"
        )
        
        # 5. إنشاء قناة السجلات
        logs_channel = await guild.create_text_channel(
            name="📊-سجلات-التذاكر",
            category=open_category,
            topic="سجلات جميع التذاكر"
        )
        
        # 6. إنشاء قناة الإحصائيات
        stats_channel = await guild.create_text_channel(
            name="📈-إحصائيات",
            category=open_category,
            topic="إحصائيات التذاكر"
        )
        
        # حفظ الإعدادات
        self.settings[guild_id] = {
            'support_role': support_role.id,
            'open_category': open_category.id,
            'archive_category': archive_category.id,
            'panel_channel': panel_channel.id,
            'logs_channel': logs_channel.id,
            'stats_channel': stats_channel.id,
            'setup_by': ctx.author.id,
            'setup_date': datetime.now().isoformat(),
            'ticket_counter': 0
        }
        
        self.save_data()
        
        # 7. إرسال لوحة التحكم
        await self.send_panel(panel_channel)
        
        # 8. رسالة النجاح
        embed = discord.Embed(
            title="✅ **تم إعداد نظام التذاكر بنجاح!**",
            description="**تم إنشاء النظام بالكامل**",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📋 **ما تم إنشاؤه:**",
            value=f"""
            **1.** رتبة {support_role.mention}
            **2.** قسم {open_category.name}
            **3.** قسم {archive_category.name}
            **4.** قناة {panel_channel.mention}
            **5.** قناة {logs_channel.mention}
            **6.** قناة {stats_channel.mention}
            """,
            inline=False
        )
        
        embed.add_field(
            name="🎯 **الخطوات التالية:**",
            value="""
            1. أضف أعضاء لفريق الدعم
            2. اشرح للناس كيفية فتح التذاكر
            3. استخدم `!إعدادت` لرؤية الإعدادات
            """,
            inline=False
        )
        
        embed.set_footer(text=f"بواسطة {ctx.author.name}")
        await ctx.send(embed=embed)
        
        # 9. تسجيل في السجلات
        await self.log_action(guild_id, f"🚀 **تم إعداد النظام**\nبواسطة: {ctx.author.mention}")
    
    # ========== لوحة التحكم ==========
    async def send_panel(self, channel):
        """إرسال لوحة فتح التذاكر"""
        embed = discord.Embed(
            title="🎫 **مركز الدعم والتذاكر**",
            description="""
            **مرحباً بك في مركز الدعم!**
            
            **اختر نوع التذكرة المناسب لمشكلتك:**
            
            🔧 **الدعم الفني** - للمشاكل التقنية
            ⚠️ **الشكاوي** - للتقديم شكوى
            💡 **الاقتراحات** - لاقتراح أفكار
            💰 **الشراء** - للاستفسارات المالية
            🤝 **الشراكة** - لطلبات الشراكة
            ❓ **الأخرى** - لأي استفسار آخر
            
            **سيتم إنشاء قناة خاصة بك وفريق الدعم فقط.**
            """,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.set_footer(text="اضغط على الزر المناسب")
        embed.set_image(url="https://cdn.discordapp.com/attachments/1063638269886615683/1063638270352171079/ticket_banner.png")
        
        # إنشاء أزرار
        class TicketView(View):
            def __init__(self, ticket_system):
                super().__init__(timeout=None)
                self.ticket_system = ticket_system
            
            @discord.ui.button(label="الدعم الفني", emoji="🔧", style=discord.ButtonStyle.primary, custom_id="ticket_tech")
            async def tech_callback(self, interaction: discord.Interaction, button: Button):
                await self.ticket_system.create_ticket(interaction, 'tech')
            
            @discord.ui.button(label="الشكاوي", emoji="⚠️", style=discord.ButtonStyle.danger, custom_id="ticket_complaint")
            async def complaint_callback(self, interaction: discord.Interaction, button: Button):
                await self.ticket_system.create_ticket(interaction, 'complaint')
            
            @discord.ui.button(label="الاقتراحات", emoji="💡", style=discord.ButtonStyle.success, custom_id="ticket_suggestion")
            async def suggestion_callback(self, interaction: discord.Interaction, button: Button):
                await self.ticket_system.create_ticket(interaction, 'suggestion')
            
            @discord.ui.button(label="الشراء", emoji="💰", style=discord.ButtonStyle.secondary, custom_id="ticket_purchase")
            async def purchase_callback(self, interaction: discord.Interaction, button: Button):
                await self.ticket_system.create_ticket(interaction, 'purchase')
            
            @discord.ui.button(label="الشراكة", emoji="🤝", style=discord.ButtonStyle.primary, custom_id="ticket_partnership")
            async def partnership_callback(self, interaction: discord.Interaction, button: Button):
                await self.ticket_system.create_ticket(interaction, 'partnership')
            
            @discord.ui.button(label="الأخرى", emoji="❓", style=discord.ButtonStyle.secondary, custom_id="ticket_other")
            async def other_callback(self, interaction: discord.Interaction, button: Button):
                await self.ticket_system.create_ticket(interaction, 'other')
        
        view = TicketView(self)
        await channel.send(embed=embed, view=view)
    
    # ========== إنشاء تذكرة ==========
    async def create_ticket(self, interaction, ticket_type):
        """إنشاء تذكرة جديدة"""
        user = interaction.user
        guild = interaction.guild
        guild_id = str(guild.id)
        
        if guild_id not in self.settings:
            await interaction.response.send_message("❌ النظام غير مثبت! اطلب من الأدمن استخدام `!تيكت`", ephemeral=True)
            return
        
        # زيادة العداد
        self.settings[guild_id]['ticket_counter'] += 1
        ticket_id = self.settings[guild_id]['ticket_counter']
        
        # الحصول على الإعدادات
        settings = self.settings[guild_id]
        open_category = guild.get_channel(settings['open_category'])
        support_role = guild.get_role(settings['support_role'])
        
        if not open_category:
            await interaction.response.send_message("❌ قسم التذاكر غير موجود!", ephemeral=True)
            return
        
        # إنشاء القناة
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                manage_channels=True,
                manage_messages=True
            )
        }
        
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                read_message_history=True
            )
        
        # اسم القناة
        emoji = self.emojis.get(ticket_type, '🎫')
        type_name = self.ticket_types_ar.get(ticket_type, 'تذكرة')
        
        ticket_channel = await guild.create_text_channel(
            name=f"{emoji}-{ticket_id}-{user.name[:15]}",
            category=open_category,
            overwrites=overwrites,
            topic=f"{type_name} - المستخدم: {user} | ID: {ticket_id}"
        )
        
        # حفظ بيانات التذكرة
        ticket_key = f"{guild_id}_{ticket_id}"
        
        self.tickets[ticket_key] = {
            'id': ticket_id,
            'user_id': user.id,
            'user_name': str(user),
            'channel_id': ticket_channel.id,
            'type': ticket_type,
            'type_name': type_name,
            'status': 'مفتوح',
            'created_at': datetime.now().isoformat(),
            'created_by': user.id,
            'messages_count': 0,
            'support_team': [],
            'closed_at': None,
            'closed_by': None
        }
        
        self.save_data()
        
        # إرسال رسالة الترحيب
        embed = discord.Embed(
            title=f"{emoji} **{type_name} - #{ticket_id}**",
            description=f"""
            **مرحباً {user.mention}!**
            
            **تم فتح تذكرتك بنجاح!**
            
            **📋 المعلومات:**
            • **النوع:** {type_name}
            • **الرقم:** #{ticket_id}
            • **التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
            • **الحالة:** 🟢 مفتوحة
            
            **💬 الرجاء شرح مشكلتك/استفسارك بالتفصيل...**
            
            **👥 فريق الدعم سيرد عليك قريباً.**
            """,
            color=self.colors.get(ticket_type, discord.Color.blue()),
            timestamp=datetime.now()
        )
        
        # أزرار التحكم
        class TicketControlView(View):
            def __init__(self, ticket_system, ticket_id):
                super().__init__(timeout=None)
                self.ticket_system = ticket_system
                self.ticket_id = ticket_id
            
            @discord.ui.button(label="إغلاق", emoji="🔒", style=discord.ButtonStyle.danger, custom_id=f"close_{ticket_id}")
            async def close_callback(self, interaction: discord.Interaction, button: Button):
                await self.ticket_system.close_ticket(interaction, self.ticket_id)
            
            @discord.ui.button(label="إضافة عضو", emoji="➕", style=discord.ButtonStyle.success, custom_id=f"add_{ticket_id}")
            async def add_callback(self, interaction: discord.Interaction, button: Button):
                await interaction.response.send_modal(AddUserModal(self.ticket_system, self.ticket_id))
            
            @discord.ui.button(label="أرشيف", emoji="📁", style=discord.ButtonStyle.secondary, custom_id=f"archive_{ticket_id}")
            async def archive_callback(self, interaction: discord.Interaction, button: Button):
                await self.ticket_system.archive_ticket(interaction, self.ticket_id)
        
        view = TicketControlView(self, ticket_id)
        
        # الإرسال
        await ticket_channel.send(
            content=f"{user.mention}" + (f" | {support_role.mention}" if support_role else ""),
            embed=embed,
            view=view
        )
        
        # رد للمستخدم
        await interaction.response.send_message(
            f"✅ **تم إنشاء تذكرتك!**\n\n🔗 **اذهب للتذكرة:** {ticket_channel.mention}",
            ephemeral=True
        )
        
        # تسجيل في السجلات
        await self.log_action(guild_id, f"🎫 **تم فتح تذكرة جديدة**\n\n**المستخدم:** {user.mention}\n**النوع:** {type_name}\n**الرقم:** #{ticket_id}\n**القناة:** {ticket_channel.mention}")
        
        # تحديث الإحصائيات
        await self.update_stats(guild_id)
    
    # ========== إغلاق تذكرة ==========
    async def close_ticket(self, interaction, ticket_id):
        """إغلاق تذكرة"""
        guild = interaction.guild
        guild_id = str(guild.id)
        ticket_key = f"{guild_id}_{ticket_id}"
        
        if ticket_key not in self.tickets:
            await interaction.response.send_message("❌ التذكرة غير موجودة!", ephemeral=True)
            return
        
        ticket = self.tickets[ticket_key]
        
        # التحقق من الصلاحيات
        user = interaction.user
        can_close = False
        
        if user.guild_permissions.administrator:
            can_close = True
        elif user.guild_permissions.manage_channels:
            can_close = True
        elif user.id == ticket['user_id']:
            can_close = True
        else:
            # التحقق إذا كان في فريق الدعم
            settings = self.settings.get(guild_id, {})
            support_role_id = settings.get('support_role')
            if support_role_id:
                support_role = guild.get_role(support_role_id)
                if support_role and support_role in user.roles:
                    can_close = True
        
        if not can_close:
            await interaction.response.send_message("❌ ليس لديك صلاحية إغلاق هذه التذكرة!", ephemeral=True)
            return
        
        # تحديث بيانات التذكرة
        ticket['status'] = 'مغلقة'
        ticket['closed_at'] = datetime.now().isoformat()
        ticket['closed_by'] = user.id
        
        # إرسال رسالة الإغلاق
        channel = guild.get_channel(ticket['channel_id'])
        if channel:
            embed = discord.Embed(
                title="🔒 **تم إغلاق التذكرة**",
                description=f"""
                **تم إغلاق هذه التذكرة بواسطة {user.mention}**
                
                **📋 معلومات الإغلاق:**
                • **التذكرة:** #{ticket_id}
                • **النوع:** {ticket['type_name']}
                • **المستخدم:** <@{ticket['user_id']}>
                • **تاريخ الإغلاق:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
                
                **📁 سيتم نقل القناة للأرشيف خلال 10 ثواني...**
                """,
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            await channel.send(embed=embed)
            
            # الانتظار ثم النقل
            await asyncio.sleep(10)
            
            # نقل للأرشيف
            settings = self.settings.get(guild_id, {})
            archive_category_id = settings.get('archive_category')
            if archive_category_id:
                archive_category = guild.get_channel(archive_category_id)
                if archive_category:
                    await channel.edit(category=archive_category, name=f"🔒-{channel.name}")
            
            # منع الكتابة
            await channel.set_permissions(guild.default_role, send_messages=False)
        
        self.save_data()
        
        await interaction.response.send_message("✅ تم إغلاق التذكرة!", ephemeral=True)
        
        # تسجيل في السجلات
        await self.log_action(guild_id, f"🔒 **تم إغلاق تذكرة**\n\n**الرقم:** #{ticket_id}\n**بواسطة:** {user.mention}\n**المستخدم:** <@{ticket['user_id']}>")
        
        # تحديث الإحصائيات
        await self.update_stats(guild_id)
    
    # ========== أرشيف تذكرة ==========
    async def archive_ticket(self, interaction, ticket_id):
        """نقل تذكرة للأرشيف"""
        guild = interaction.guild
        guild_id = str(guild.id)
        ticket_key = f"{guild_id}_{ticket_id}"
        
        if ticket_key not in self.tickets:
            await interaction.response.send_message("❌ التذكرة غير موجودة!", ephemeral=True)
            return
        
        ticket = self.tickets[ticket_key]
        
        # التحقق من الصلاحيات
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ تحتاج صلاحية إدارة القنوات!", ephemeral=True)
            return
        
        # نقل القناة
        channel = guild.get_channel(ticket['channel_id'])
        if channel:
            settings = self.settings.get(guild_id, {})
            archive_category_id = settings.get('archive_category')
            
            if archive_category_id:
                archive_category = guild.get_channel(archive_category_id)
                if archive_category:
                    await channel.edit(category=archive_category, name=f"📁-{channel.name}")
                    
                    embed = discord.Embed(
                        title="📁 **تم نقل التذكرة للأرشيف**",
                        description=f"تم نقل التذكرة للأرشيف بواسطة {interaction.user.mention}",
                        color=discord.Color.dark_grey()
                    )
                    
                    await channel.send(embed=embed)
        
        await interaction.response.send_message("✅ تم نقل التذكرة للأرشيف!", ephemeral=True)
        await self.log_action(guild_id, f"📁 **تم نقل تذكرة للأرشيف**\n**الرقم:** #{ticket_id}\n**بواسطة:** {interaction.user.mention}")
    
    # ========== تسجيل الإجراءات ==========
    async def log_action(self, guild_id, message):
        """تسجيل الإجراء في قناة السجلات"""
        try:
            settings = self.settings.get(guild_id, {})
            logs_channel_id = settings.get('logs_channel')
            
            if logs_channel_id:
                guild = self.bot.get_guild(int(guild_id))
                if guild:
                    logs_channel = guild.get_channel(logs_channel_id)
                    if logs_channel:
                        embed = discord.Embed(
                            description=message,
                            color=discord.Color.blue(),
                            timestamp=datetime.now()
                        )
                        await logs_channel.send(embed=embed)
        except:
            pass
    
    # ========== تحديث الإحصائيات ==========
    async def update_stats(self, guild_id):
        """تحديث قناة الإحصائيات"""
        try:
            settings = self.settings.get(guild_id, {})
            stats_channel_id = settings.get('stats_channel')
            
            if stats_channel_id:
                guild = self.bot.get_guild(int(guild_id))
                if guild:
                    stats_channel = guild.get_channel(stats_channel_id)
                    if stats_channel:
                        # حساب الإحصائيات
                        tickets_data = {k: v for k, v in self.tickets.items() if k.startswith(guild_id)}
                        
                        total = len(tickets_data)
                        open_tickets = len([t for t in tickets_data.values() if t['status'] == 'مفتوح'])
                        closed_tickets = len([t for t in tickets_data.values() if t['status'] == 'مغلقة'])
                        
                        # حساب حسب النوع
                        types_stats = {}
                        for ticket in tickets_data.values():
                            ttype = ticket.get('type_name', 'غير معروف')
                            types_stats[ttype] = types_stats.get(ttype, 0) + 1
        
                        # بناء الرسالة
                        embed = discord.Embed(
                            title="📊 **إحصائيات التذاكر**",
                            description=f"**آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                            color=discord.Color.gold(),
                            timestamp=datetime.now()
                        )
                        
                        embed.add_field(
                            name="📈 **النظرة العامة**",
                            value=f"""
                            ```yaml
                            الإجمالي: {total}
                            المفتوحة: {open_tickets}
                            المغلقة: {closed_tickets}
                            نسبة الإغلاق: {(closed_tickets/total*100) if total > 0 else 0:.1f}%
                            ```
                            """,
                            inline=False
                        )
                        
                        # إحصائيات الأنواع
                        if types_stats:
                            types_text = ""
                            for ttype, count in types_stats.items():
                                types_text += f"• **{ttype}:** {count}\n"
                            
                            embed.add_field(
                                name="🏷️ **التوزيع حسب النوع**",
                                value=types_text,
                                inline=False
                            )
                        
                        # التذاكر اليوم
                        today = datetime.now().date()
                        today_tickets = len([
                            t for t in tickets_data.values() 
                            if datetime.fromisoformat(t['created_at']).date() == today
                        ])
                        
                        embed.add_field(
                            name="📅 **اليوم**",
                            value=f"**تم فتح {today_tickets} تذكرة اليوم**",
                            inline=False
                        )
                        
                        # محو الرسائل القديمة وإرسال الجديدة
                        await stats_channel.purge(limit=10)
                        await stats_channel.send(embed=embed)
        except Exception as e:
            print(f"❌ خطأ في تحديث الإحصائيات: {e}")
    
    # ========== مهام دورية ==========
    @tasks.loop(minutes=5)
    async def check_closed_tickets(self):
        """فحص التذاكر المغلقة ونقلها للأرشيف"""
        try:
            for guild_id_str in list(self.settings.keys()):
                guild = self.bot.get_guild(int(guild_id_str))
                if not guild:
                    continue
                
                settings = self.settings[guild_id_str]
                archive_category_id = settings.get('archive_category')
                
                if not archive_category_id:
                    continue
                
                archive_category = guild.get_channel(archive_category_id)
                if not archive_category:
                    continue
                
                # البحث عن تذاكر مغلقة في قسم المفتوحة
                open_category_id = settings.get('open_category')
                if open_category_id:
                    open_category = guild.get_channel(open_category_id)
                    if open_category:
                        for channel in open_category.channels:
                            if isinstance(channel, discord.TextChannel):
                                # البحث عن التذكرة
                                for ticket_key, ticket in self.tickets.items():
                                    if ticket_key.startswith(guild_id_str) and ticket['channel_id'] == channel.id:
                                        if ticket['status'] == 'مغلقة':
                                            # نقل للأرشيف
                                            await channel.edit(category=archive_category, name=f"🔒-{channel.name}")
        except:
            pass
    
    # ========== أوامر الإدارة ==========
    @commands.command(name="إعدادت", aliases=['settings'])
    @commands.has_permissions(manage_channels=True)
    async def show_settings(self, ctx):
        """عرض إعدادات نظام التذاكر"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.settings:
            embed = discord.Embed(
                title="❌ **النظام غير مثبت**",
                description="استخدم `!تيكت` لإعداد النظام أولاً",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        settings = self.settings[guild_id]
        
        embed = discord.Embed(
            title="⚙️ **إعدادات نظام التذاكر**",
            description="**جميع إعدادات النظام الحالية**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # الحصول على أسماء القنوات
        tickets_channel = ctx.guild.get_channel(settings.get('panel_channel', 0))
        logs_channel = ctx.guild.get_channel(settings.get('logs_channel', 0))
        stats_channel = ctx.guild.get_channel(settings.get('stats_channel', 0))
        support_role = ctx.guild.get_role(settings.get('support_role', 0))
        
        embed.add_field(
            name="📁 **القنوات**",
            value=f"""
            **لوحة التذاكر:** {tickets_channel.mention if tickets_channel else '❌'}
            **سجلات النظام:** {logs_channel.mention if logs_channel else '❌'}
            **الإحصائيات:** {stats_channel.mention if stats_channel else '❌'}
            """,
            inline=False
        )
        
        embed.add_field(
            name="👥 **الأدوار**",
            value=f"**فريق الدعم:** {support_role.mention if support_role else '❌'}",
            inline=False
        )
        
        # إحصائيات
        tickets_data = {k: v for k, v in self.tickets.items() if k.startswith(guild_id)}
        
        embed.add_field(
            name="📊 **الإحصائيات**",
            value=f"""
            **عدد التذاكر:** {len(tickets_data)}
            **آخر تذكرة:** #{settings.get('ticket_counter', 0)}
            **تاريخ الإعداد:** {settings.get('setup_date', 'غير معروف')[:10]}
            """,
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="تذاكر", aliases=['tickets'])
    async def show_tickets(self, ctx, status: str = "all"):
        """عرض التذاكر"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.settings:
            await ctx.send("❌ النظام غير مثبت!")
            return
        
        # فلترة التذاكر
        tickets_list = []
        for key, ticket in self.tickets.items():
            if key.startswith(guild_id):
                if status == "all" or ticket['status'] == status:
                    tickets_list.append(ticket)
        
        if not tickets_list:
            await ctx.send(f"📭 لا توجد تذاكر {f'بالحالة {status}' if status != 'all' else ''}")
            return
        
        # عرض النتائج
        embed = discord.Embed(
            title=f"📋 **التذاكر** ({len(tickets_list)})",
            color=discord.Color.blue()
        )
        
        for ticket in tickets_list[-5:]:  # آخر 5 تذاكر
            status_emoji = "🟢" if ticket['status'] == 'مفتوح' else "🔴"
            
            embed.add_field(
                name=f"{status_emoji} #{ticket['id']} - {ticket['type_name']}",
                value=f"**المستخدم:** <@{ticket['user_id']}>\n**الحالة:** {ticket['status']}\n**التاريخ:** {ticket['created_at'][:10]}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="إحصاء", aliases=['stats'])
    async def show_stats(self, ctx):
        """عرض إحصائيات التذاكر"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.settings:
            await ctx.send("❌ النظام غير مثبت!")
            return
        
        await self.update_stats(guild_id)
        await ctx.send("✅ تم تحديث الإحصائيات في القناة المخصصة!")
    
    @commands.command(name="أضف_لدعم", aliases=['addsupport'])
    @commands.has_permissions(administrator=True)
    async def add_to_support(self, ctx, member: discord.Member):
        """إضافة عضو لفريق الدعم"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.settings:
            await ctx.send("❌ النظام غير مثبت!")
            return
        
        support_role_id = self.settings[guild_id].get('support_role')
        if not support_role_id:
            await ctx.send("❌ رتبة فريق الدعم غير موجودة!")
            return
        
        support_role = ctx.guild.get_role(support_role_id)
        if not support_role:
            await ctx.send("❌ رتبة فريق الدعم غير موجودة!")
            return
        
        await member.add_roles(support_role)
        
        embed = discord.Embed(
            title="✅ **تمت الإضافة لفريق الدعم**",
            description=f"تم إضافة {member.mention} لـ {support_role.mention}",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
        await self.log_action(guild_id, f"👥 **تم إضافة عضو لفريق الدعم**\n\n**العضو:** {member.mention}\n**بواسطة:** {ctx.author.mention}")
    
    @commands.command(name="إعادة_تيكت", aliases=['resetpanel'])
    @commands.has_permissions(manage_channels=True)
    async def reset_panel(self, ctx):
        """إعادة إرسال لوحة التذاكر"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.settings:
            await ctx.send("❌ النظام غير مثبت!")
            return
        
        panel_channel_id = self.settings[guild_id].get('panel_channel')
        if not panel_channel_id:
            await ctx.send("❌ قناة التذاكر غير موجودة!")
            return
        
        panel_channel = ctx.guild.get_channel(panel_channel_id)
        if not panel_channel:
            await ctx.send("❌ قناة التذاكر غير موجودة!")
            return
        
        # محو الرسائل القديمة
        await panel_channel.purge(limit=100)
        
        # إرسال اللوحة الجديدة
        await self.send_panel(panel_channel)
        
        await ctx.send("✅ تم إعادة إرسال لوحة التذاكر!")
        await self.log_action(guild_id, f"🔄 **تم إعادة إرسال لوحة التذاكر**\n\n**بواسطة:** {ctx.author.mention}")

# ========== مودال إضافة مستخدم ==========
class AddUserModal(discord.ui.Modal):
    def __init__(self, ticket_system, ticket_id):
        super().__init__(title="إضافة عضو للتذكرة")
        self.ticket_system = ticket_system
        self.ticket_id = ticket_id
        
        self.user_id_input = discord.ui.TextInput(
            label="معرف العضو",
            placeholder="أدخل الـ ID الخاص بالعضو",
            required=True,
            max_length=20
        )
        
        self.add_item(self.user_id_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.user_id_input.value)
            guild = interaction.guild
            
            # البحث عن العضو
            member = guild.get_member(user_id)
            if not member:
                # محاولة البحث برا
                try:
                    member = await guild.fetch_member(user_id)
                except:
                    await interaction.response.send_message("❌ العضو غير موجود في السيرفر!", ephemeral=True)
                    return
            
            # البحث عن التذكرة
            guild_id = str(guild.id)
            ticket_key = f"{guild_id}_{self.ticket_id}"
            
            if ticket_key not in self.ticket_system.tickets:
                await interaction.response.send_message("❌ التذكرة غير موجودة!", ephemeral=True)
                return
            
            ticket = self.ticket_system.tickets[ticket_key]
            channel = guild.get_channel(ticket['channel_id'])
            
            if not channel:
                await interaction.response.send_message("❌ قناة التذكرة غير موجودة!", ephemeral=True)
                return
            
            # إضافة الصلاحيات
            await channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
            
            await interaction.response.send_message(f"✅ تمت إضافة {member.mention} للتذكرة!", ephemeral=True)
            
            # إرسال إشعار في القناة
            await channel.send(f"👋 **تمت إضافة {member.mention} لهذه التذكرة بواسطة {interaction.user.mention}**")
            
        except ValueError:
            await interaction.response.send_message("❌ أدخل معرف صحيح!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

# ========== إعداد النظام ==========
async def setup(bot):
    """إضافة النظام للبوت"""
    await bot.add_cog(TicketSystem(bot))
    print("✅ نظام التذاكر الكامل جاهز!")