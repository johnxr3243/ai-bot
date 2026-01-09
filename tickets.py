# tickets.py - نظام التذاكر الكامل
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
import json
import os
from datetime import datetime, timedelta
import asyncio
import random

class TicketsSystem(commands.Cog):
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
    
    @commands.command(name="تيكت", aliases=['ticket', 'تیكت'])
    @commands.has_permissions(administrator=True)
    async def setup_ticket_system(self, ctx):
        """إعداد نظام التذاكر الكامل"""
        guild = ctx.guild
        guild_id = str(guild.id)
        
        # إنشاء رتبة فريق الدعم
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
        
        # إنشاء قسم التذاكر المفتوحة
        open_category = await guild.create_category(
            name="🎫 التذاكر المفتوحة",
            position=0
        )
        
        # إنشاء قسم الأرشيف
        archive_category = await guild.create_category(
            name="📁 الأرشيف",
            position=1
        )
        
        # إنشاء قناة لوحة التحكم
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
        
        # إنشاء قناة السجلات
        logs_channel = await guild.create_text_channel(
            name="📊-سجلات-التذاكر",
            category=open_category,
            topic="سجلات جميع التذاكر"
        )
        
        # حفظ الإعدادات
        self.settings[guild_id] = {
            'support_role': support_role.id,
            'open_category': open_category.id,
            'archive_category': archive_category.id,
            'panel_channel': panel_channel.id,
            'logs_channel': logs_channel.id,
            'setup_by': ctx.author.id,
            'setup_date': datetime.now().isoformat(),
            'ticket_counter': 0
        }
        
        self.save_data()
        
        # إرسال لوحة التحكم
        await self.send_panel(panel_channel)
        
        # رسالة النجاح
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
            """,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.set_footer(text="اضغط على الزر المناسب")
        
        # إنشاء أزرار
        view = View(timeout=None)
        
        buttons = [
            ("الدعم الفني", "🔧", discord.ButtonStyle.primary, 'tech'),
            ("الشكاوي", "⚠️", discord.ButtonStyle.danger, 'complaint'),
            ("الاقتراحات", "💡", discord.ButtonStyle.success, 'suggestion'),
            ("الشراء", "💰", discord.ButtonStyle.secondary, 'purchase'),
            ("الشراكة", "🤝", discord.ButtonStyle.primary, 'partnership'),
            ("الأخرى", "❓", discord.ButtonStyle.secondary, 'other')
        ]
        
        for label, emoji, style, ticket_type in buttons:
            button = Button(label=label, emoji=emoji, style=style)
            button.callback = lambda i, tt=ticket_type: self.create_ticket(i, tt)
            view.add_item(button)
        
        await channel.send(embed=embed, view=view)
    
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
            name=f"{emoji}-{user.name[:15]}",
            category=open_category,
            overwrites=overwrites,
            topic=f"{type_name} - {user.name}"
        )
        
        # إرسال رسالة الترحيب
        embed = discord.Embed(
            title=f"{emoji} **{type_name}**",
            description=f"مرحباً {user.mention}!\n\nفضلاً اشرح مشكلتك وسيقوم فريق الدعم بالرد عليك قريباً.",
            color=self.colors.get(ticket_type, discord.Color.blue())
        )
        
        # أزرار التحكم
        view = View(timeout=None)
        
        close_button = Button(label="إغلاق", emoji="🔒", style=discord.ButtonStyle.red)
        
        async def close_callback(interaction2):
            await ticket_channel.delete()
            await interaction2.response.send_message("✅ تم حذف التذكرة", ephemeral=True)
        
        close_button.callback = close_callback
        view.add_item(close_button)
        
        await ticket_channel.send(embed=embed, view=view)
        
        # إرسال رد للمستخدم
        await interaction.response.send_message(
            f"✅ **تم إنشاء تذكرتك!**\n\n🔗 **اذهب للتذكرة:** {ticket_channel.mention}",
            ephemeral=True
        )
    
    @tasks.loop(minutes=5)
    async def check_closed_tickets(self):
        """فحص التذاكر المغلقة"""
        pass  # يمكنك إضافة منطق هنا لاحقاً
    
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
        panel_channel = ctx.guild.get_channel(settings.get('panel_channel', 0))
        logs_channel = ctx.guild.get_channel(settings.get('logs_channel', 0))
        support_role = ctx.guild.get_role(settings.get('support_role', 0))
        
        embed.add_field(
            name="📁 **القنوات**",
            value=f"""
            **لوحة التذاكر:** {panel_channel.mention if panel_channel else '❌'}
            **سجلات النظام:** {logs_channel.mention if logs_channel else '❌'}
            """,
            inline=False
        )
        
        embed.add_field(
            name="👥 **الأدوار**",
            value=f"**فريق الدعم:** {support_role.mention if support_role else '❌'}",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """إضافة النظام للبوت"""
    await bot.add_cog(TicketsSystem(bot))
    print("✅ نظام التذاكر جاهز للاستخدام!")