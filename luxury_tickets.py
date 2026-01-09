import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Bot ready: {bot.user}')
    print(f'🆔 Bot ID: {bot.user.id}')
    print('🎫 Loading ticket system...')
    
    # Load ticket system
    try:
        await bot.load_extension('luxury_tickets_english')
        print('✅ Ticket system loaded successfully!')
    except Exception as e:
        print(f'❌ Failed to load ticket system: {e}')

@bot.command()
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f'🏓 Pong! {latency}ms')

@bot.command()
async def reload(ctx):
    """Reload ticket system (admin only)"""
    if ctx.author.guild_permissions.administrator:
        try:
            await bot.reload_extension('luxury_tickets_english')
            await ctx.send('✅ Ticket system reloaded!')
        except Exception as e:
            await ctx.send(f'❌ Error: {str(e)}')
    else:
        await ctx.send('❌ Admin only!')

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Missing DISCORD_TOKEN in .env file")

        # luxury_tickets_english.py - Complete Luxury Ticket System
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select, Modal, TextInput
import json
import os
from datetime import datetime, timedelta
import asyncio
import traceback

# ==================== MODALS (OUTSIDE MAIN CLASS) ====================

class TicketCreationModal(Modal):
    def __init__(self, cog_instance):
        super().__init__(title="🎫 Open New Ticket")
        self.cog = cog_instance
        
        self.subject = TextInput(
            label="Subject",
            placeholder="Brief description of your issue",
            style=discord.TextStyle.short,
            required=True,
            max_length=100
        )
        
        self.description = TextInput(
            label="Description",
            placeholder="Detailed explanation...",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
        )
        
        self.add_item(self.subject)
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # Create ticket with modal data
        await self.cog.create_ticket_from_modal(interaction, self.subject.value, self.description.value or "No description provided")

class AddMemberModal(Modal):
    def __init__(self, cog_instance, ticket_id):
        super().__init__(title="➕ Add Member to Ticket")
        self.cog = cog_instance
        self.ticket_id = ticket_id
        
        self.member_id = TextInput(
            label="Member ID",
            placeholder="Enter member's Discord ID",
            style=discord.TextStyle.short,
            required=True
        )
        
        self.add_item(self.member_id)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            member_id = int(self.member_id.value)
            member = interaction.guild.get_member(member_id)
            
            if not member:
                await interaction.response.send_message("❌ Member not found!", ephemeral=True)
                return
            
            # Add member using cog method
            ctx = await self.cog.bot.get_context(interaction.message)
            if ctx is None:
                # Create a simple context if needed
                class SimpleCtx:
                    def __init__(self, guild, channel, author):
                        self.guild = guild
                        self.channel = channel
                        self.author = author
                        self.send = interaction.response.send_message
                
                ctx = SimpleCtx(interaction.guild, interaction.channel, interaction.user)
            
            await self.cog.add_member_to_ticket(ctx, self.ticket_id, member)
            await interaction.response.send_message(f"✅ Added {member.mention} to ticket #{self.ticket_id}", ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Invalid ID format! Use numbers only.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# ==================== MAIN TICKET SYSTEM CLASS ====================

class LuxuryTickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "tickets_config.json"
        self.tickets_file = "tickets_data.json"
        
        # Luxury colors
        self.colors = {
            'primary': 0x1a1a1a,
            'success': 0x00d26a,
            'danger': 0xff4757,
            'warning': 0xff9f43,
            'info': 0x2e86de,
            'embed': 0x0f0f0f,
            'dark': 0x0c0c0c,
            'secondary': 0x2d2d2d
        }
        
        # Load data
        self.config = self.load_config()
        self.tickets = self.load_tickets()
        
        # Start auto-save
        self.bot.loop.create_task(self.start_auto_save())
    
    # ==================== BASIC FUNCTIONS ====================
    
    async def start_auto_save(self):
        """Start auto-save task"""
        await self.bot.wait_until_ready()
        if not self.auto_save.is_running():
            self.auto_save.start()
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Default configuration
        return {
            'guild_id': None,
            'ticket_channel': None,
            'log_channel': None,
            'archive_category': None,
            'admin_role': None,
            'support_role': None,
            'embed_settings': {
                'title': "🎫 Luxury Ticket System",
                'description': "Click button to open a ticket",
                'footer': "Premium Support System",
                'color': self.colors['embed']
            },
            'ticket_types': [
                {"name": "Technical", "emoji": "🔧", "color": self.colors['info']},
                {"name": "Billing", "emoji": "💰", "color": self.colors['warning']},
                {"name": "General", "emoji": "💬", "color": self.colors['primary']}
            ]
        }
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")
    
    def load_tickets(self):
        """Load tickets data"""
        if os.path.exists(self.tickets_file):
            try:
                with open(self.tickets_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"tickets": {}, "counter": 0, "history": []}
    
    def save_tickets(self):
        """Save tickets data"""
        try:
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump(self.tickets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Tickets save error: {e}")
    
    @tasks.loop(minutes=5)
    async def auto_save(self):
        """Auto-save data"""
        self.save_config()
        self.save_tickets()
    
    @auto_save.before_loop
    async def before_auto_save(self):
        """Wait for bot to be ready"""
        await self.bot.wait_until_ready()
    
    # ==================== HELP COMMAND ====================
    
    @commands.command(name="tickethelp")
    async def ticket_help(self, ctx):
        """Shows detailed help for all ticket commands"""
        embed = discord.Embed(
            title="🎫 **LUXURY TICKET SYSTEM - COMMAND GUIDE**",
            description="Complete guide to all ticket commands",
            color=self.colors['primary']
        )
        
        embed.add_field(
            name="⚙️ **SETUP COMMANDS (ADMIN)**",
            value="""
            **`!ticket_setup`** - Initializes complete system
            **`!ticket_config`** - Shows current configuration
            **`!ticket_panel`** - Resends ticket panel
            **`!ticket_promote @member`** - Add to support team
            **`!ticket_demote @member`** - Remove from support team
            """,
            inline=False
        )
        
        embed.add_field(
            name="👤 **USER COMMANDS**",
            value="""
            **`!ticket`** - Opens a new support ticket
            **`!mytickets`** - Shows your open tickets
            **`!ticket_info`** - Shows ticket information
            """,
            inline=False
        )
        
        embed.add_field(
            name="🔧 **SUPPORT TEAM COMMANDS**",
            value="""
            **`!ticket_close`** - Closes current ticket
            **`!ticket_close [number]`** - Closes specific ticket
            **`!ticket_add @member`** - Adds member to ticket
            **`!ticket_claim`** - Claims ticket for yourself
            **`!ticket_list`** - Lists all open tickets
            """,
            inline=False
        )
        
        embed.add_field(
            name="📊 **INFO COMMANDS**",
            value="""
            **`!ticket_stats`** - System statistics
            **`!ticket_info [number]`** - Ticket details
            **`!ticket_list closed`** - Closed tickets
            """,
            inline=False
        )
        
        embed.add_field(
            name="💡 **QUICK TIPS**",
            value="""
            1. Start with `!ticket_setup`
            2. Test with `!ticket`
            3. Manage with `!ticket_list`
            4. Get help with `!tickethelp`
            """,
            inline=False
        )
        
        embed.set_footer(text="System ready to use")
        await ctx.send(embed=embed)
    
    # ==================== SETUP COMMAND ====================
    
    @commands.command(name="ticket_setup")
    @commands.has_permissions(administrator=True)
    async def ticket_setup(self, ctx):
        """Initializes the complete ticket system"""
        try:
            embed = discord.Embed(
                title="⚙️ **STARTING SETUP**",
                description="Creating luxury ticket system...",
                color=self.colors['primary']
            )
            msg = await ctx.send(embed=embed)
            
            # Save guild ID
            self.config['guild_id'] = str(ctx.guild.id)
            
            # Create admin role
            admin_role = discord.utils.get(ctx.guild.roles, name="🎩 Admin Team")
            if not admin_role:
                admin_role = await ctx.guild.create_role(
                    name="🎩 Admin Team",
                    color=discord.Color(self.colors['primary']),
                    hoist=True,
                    mentionable=True
                )
            
            # Create support role
            support_role = discord.utils.get(ctx.guild.roles, name="🔧 Support Team")
            if not support_role:
                support_role = await ctx.guild.create_role(
                    name="🔧 Support Team",
                    color=discord.Color(self.colors['info']),
                    hoist=True,
                    mentionable=True
                )
            
            # Create tickets category
            tickets_category = discord.utils.get(ctx.guild.categories, name="🎫 Tickets")
            if not tickets_category:
                tickets_category = await ctx.guild.create_category(
                    name="🎫 Tickets",
                    position=0
                )
            
            # Create archive category
            archive_category = discord.utils.get(ctx.guild.categories, name="📁 Archive")
            if not archive_category:
                archive_category = await ctx.guild.create_category(
                    name="📁 Archive",
                    position=1
                )
            
            # Create ticket channel
            ticket_channel = discord.utils.get(ctx.guild.text_channels, name="🎫-open-ticket")
            if not ticket_channel:
                ticket_channel = await ctx.guild.create_text_channel(
                    name="🎫-open-ticket",
                    category=tickets_category,
                    topic="Click button or type !ticket to open a ticket"
                )
            
            # Create log channel
            log_channel = discord.utils.get(ctx.guild.text_channels, name="📊-logs")
            if not log_channel:
                log_channel = await ctx.guild.create_text_channel(
                    name="📊-logs",
                    category=tickets_category,
                    topic="Ticket system logs"
                )
            
            # Save configuration
            self.config['admin_role'] = admin_role.id
            self.config['support_role'] = support_role.id
            self.config['ticket_channel'] = ticket_channel.id
            self.config['log_channel'] = log_channel.id
            self.config['archive_category'] = archive_category.id
            self.save_config()
            
            # Send ticket panel
            await self.send_ticket_panel(ticket_channel)
            
            # Update message
            success_embed = discord.Embed(
                title="✅ **SETUP COMPLETE**",
                description="Luxury ticket system is now ready!",
                color=self.colors['success']
            )
            
            success_embed.add_field(
                name="📁 **CREATED CATEGORIES**",
                value=f"""
                • {tickets_category.mention} - Active tickets
                • {archive_category.mention} - Archived tickets
                """,
                inline=False
            )
            
            success_embed.add_field(
                name="📍 **CREATED CHANNELS**",
                value=f"""
                • {ticket_channel.mention} - Open tickets here
                • {log_channel.mention} - System logs
                """,
                inline=False
            )
            
            success_embed.add_field(
                name="👥 **CREATED ROLES**",
                value=f"""
                • {admin_role.mention} - System administrators
                • {support_role.mention} - Support team
                """,
                inline=False
            )
            
            success_embed.add_field(
                name="🎯 **NEXT STEPS**",
                value="""
                1. Add members to support team: `!ticket_promote @member`
                2. Test the system: Type `!ticket` in any channel
                3. View all commands: `!tickethelp`
                """,
                inline=False
            )
            
            await msg.edit(embed=success_embed)
            
            # Add command user to admin role
            await ctx.author.add_roles(admin_role)
            
            # Log setup
            await self.log_action(f"System setup completed by {ctx.author.mention}")
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ **SETUP FAILED**",
                description=f"Error: {str(e)}",
                color=self.colors['danger']
            )
            await ctx.send(embed=error_embed)
            print(f"Setup error: {traceback.format_exc()}")
    
    # ==================== TICKET PANEL ====================
    
    async def send_ticket_panel(self, channel):
        """Sends the ticket panel to specified channel"""
        embed_settings = self.config.get('embed_settings', {})
        
        embed = discord.Embed(
            title=embed_settings.get('title', "🎫 Luxury Ticket System"),
            description=embed_settings.get('description', "Click button below to open a ticket"),
            color=embed_settings.get('color', self.colors['embed'])
        )
        
        # Add ticket types
        ticket_types = self.config.get('ticket_types', [])
        if ticket_types:
            types_text = "\n".join([
                f"{t.get('emoji', '🎫')} **{t.get('name', 'Ticket')}**" 
                for t in ticket_types
            ])
            embed.add_field(name="**Available Ticket Types:**", value=types_text, inline=False)
        
        embed.set_footer(text=embed_settings.get('footer', "Premium Support"))
        
        # Create view with buttons
        view = View(timeout=None)
        
        # Main ticket button
        ticket_btn = Button(
            label="🎫 Open Ticket",
            style=discord.ButtonStyle.primary,
            custom_id="open_ticket_main"
        )
        
        async def ticket_callback(interaction):
            await self.open_ticket_handler(interaction)
        
        ticket_btn.callback = ticket_callback
        view.add_item(ticket_btn)
        
        # Admin panel button
        admin_btn = Button(
            label="⚙️ Admin Panel",
            style=discord.ButtonStyle.secondary,
            custom_id="admin_panel_main"
        )
        
        async def admin_callback(interaction):
            await self.show_admin_panel(interaction)
        
        admin_btn.callback = admin_callback
        view.add_item(admin_btn)
        
        # Help button
        help_btn = Button(
            label="❓ Help",
            style=discord.ButtonStyle.success,
            custom_id="help_main"
        )
        
        async def help_callback(interaction):
            await self.show_help_modal(interaction)
        
        help_btn.callback = help_callback
        view.add_item(help_btn)
        
        await channel.send(embed=embed, view=view)
    
    # ==================== TICKET CREATION ====================
    
    async def open_ticket_handler(self, interaction):
        """Handles ticket creation from button"""
        # Create modal for ticket details
        modal = TicketCreationModal(self)  # ✅ NOW DEFINED
        await interaction.response.send_modal(modal)
    
    async def create_ticket_from_modal(self, interaction, subject, description):
        """Creates ticket from modal data"""
        try:
            # Increment counter
            self.tickets['counter'] += 1
            ticket_id = self.tickets['counter']
            
            user = interaction.user
            guild = interaction.guild
            
            # Get or create category
            category = guild.get_channel(self.config.get('archive_category'))
            if not category:
                category = await guild.create_category("🎫 Tickets")
            
            # Channel permissions
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
            
            # Add support role if exists
            support_role = guild.get_role(self.config.get('support_role'))
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_messages=True
                )
            
            # Create ticket channel
            ticket_channel = await guild.create_text_channel(
                name=f"ticket-{ticket_id}",
                category=category,
                overwrites=overwrites,
                topic=f"Ticket #{ticket_id} - {user.name} - {subject[:50]}"
            )
            
            # Save ticket data
            ticket_key = f"{guild.id}_{ticket_id}"
            self.tickets['tickets'][ticket_key] = {
                'id': ticket_id,
                'user_id': user.id,
                'user_name': str(user),
                'channel_id': ticket_channel.id,
                'subject': subject,
                'description': description,
                'status': 'open',
                'created_at': datetime.now().isoformat(),
                'support_team': [],
                'priority': 'normal',
                'tags': []
            }
            self.save_tickets()
            
            # Send welcome message
            embed = discord.Embed(
                title=f"🎫 Ticket #{ticket_id}",
                description=f"""
                **Welcome {user.mention}!**
                
                **Subject:** {subject}
                **Description:** {description}
                
                **Status:** 🟢 **OPEN**
                **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
                
                A support team member will assist you shortly.
                """,
                color=self.colors['primary']
            )
            
            # Control buttons
            view = View(timeout=None)
            
            # Close button
            close_btn = Button(label="🔒 Close", style=discord.ButtonStyle.danger)
            
            async def close_callback(i):
                await self.close_ticket_command(i, ticket_id)
            
            close_btn.callback = close_callback
            view.add_item(close_btn)
            
            # Claim button (for support)
            claim_btn = Button(label="✅ Claim", style=discord.ButtonStyle.success)
            
            async def claim_callback(i):
                await self.claim_ticket(i, ticket_id)
            
            claim_btn.callback = claim_callback
            view.add_item(claim_btn)
            
            # Add member button
            add_btn = Button(label="➕ Add Member", style=discord.ButtonStyle.primary)
            
            async def add_callback(i):
                await self.add_member_modal(i, ticket_id)
            
            add_btn.callback = add_callback
            view.add_item(add_btn)
            
            # Send to ticket channel
            await ticket_channel.send(
                content=f"{user.mention}" + (f" {support_role.mention}" if support_role else ""),
                embed=embed,
                view=view
            )
            
            # Send confirmation to user
            await interaction.followup.send(
                f"""
                ✅ **Ticket Created Successfully!**
                
                **Ticket:** #{ticket_id}
                **Channel:** {ticket_channel.mention}
                **Subject:** {subject}
                
                Your support team will respond soon.
                """,
                ephemeral=True
            )
            
            # Log creation
            await self.log_action(
                f"🎫 Ticket #{ticket_id} created by {user.mention}\n"
                f"**Subject:** {subject}"
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error creating ticket: {str(e)}",
                ephemeral=True
            )
            print(f"Ticket creation error: {traceback.format_exc()}")
    
    # ==================== TICKET COMMANDS ====================
    
    @commands.command(name="ticket")
    async def create_ticket_command(self, ctx, *, subject: str = None):
        """Opens a new support ticket"""
        if subject:
            # Quick ticket with subject
            await ctx.send(
                f"🎫 **Quick Ticket Mode**\n"
                f"Subject: **{subject}**\n\n"
                f"For detailed tickets, use the button in the ticket channel."
            )
        else:
            # Guide to ticket creation
            embed = discord.Embed(
                title="🎫 Open a Ticket",
                description="You can open a ticket in two ways:",
                color=self.colors['info']
            )
            
            embed.add_field(
                name="1. Quick Ticket",
                value="Type `!ticket [your issue]`\nExample: `!ticket Payment problem`",
                inline=False
            )
            
            embed.add_field(
                name="2. Detailed Ticket",
                value="Go to the ticket channel and click the button for more options",
                inline=False
            )
            
            channel_id = self.config.get('ticket_channel')
            if channel_id:
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    embed.add_field(
                        name="Ticket Channel",
                        value=f"Visit: {channel.mention}",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
    
    @commands.command(name="ticket_close")
    @commands.has_permissions(manage_channels=True)
    async def close_ticket_command(self, ctx, ticket_id: int = None):
        """Closes a ticket"""
        if not ticket_id:
            # Find ticket in current channel
            ticket = await self.find_ticket_by_channel(ctx.channel.id)
            if not ticket:
                await ctx.send("❌ This is not a ticket channel!")
                return
            ticket_id = ticket['id']
        
        # Close the ticket
        await self.close_ticket_action(ctx, ticket_id)
    
    async def close_ticket_action(self, ctx, ticket_id):
        """Performs ticket closing"""
        guild_id = str(ctx.guild.id)
        ticket_key = f"{guild_id}_{ticket_id}"
        
        if ticket_key not in self.tickets['tickets']:
            await ctx.send(f"❌ Ticket #{ticket_id} not found!")
            return
        
        ticket = self.tickets['tickets'][ticket_key]
        
        # Update status
        ticket['status'] = 'closed'
        ticket['closed_at'] = datetime.now().isoformat()
        ticket['closed_by'] = ctx.author.id
        self.save_tickets()
        
        # Get channel
        channel = ctx.guild.get_channel(ticket['channel_id'])
        if channel:
            # Lock channel
            await channel.set_permissions(
                ctx.guild.default_role,
                send_messages=False
            )
            
            # Send closure message
            embed = discord.Embed(
                title="🔒 Ticket Closed",
                description=f"Closed by {ctx.author.mention}",
                color=self.colors['danger']
            )
            
            embed.add_field(
                name="Ticket Information",
                value=f"""
                **ID:** #{ticket_id}
                **User:** <@{ticket['user_id']}>
                **Subject:** {ticket.get('subject', 'No subject')}
                **Opened:** {ticket['created_at'][:10]}
                **Closed:** {datetime.now().strftime('%Y-%m-%d')}
                """,
                inline=False
            )
            
            await channel.send(embed=embed)
        
        await ctx.send(f"✅ Ticket #{ticket_id} has been closed.")
        
        # Log action
        await self.log_action(
            f"🔒 Ticket #{ticket_id} closed by {ctx.author.mention}\n"
            f"User: <@{ticket['user_id']}>"
        )
    
    @commands.command(name="ticket_list")
    @commands.has_permissions(manage_channels=True)
    async def list_tickets_command(self, ctx, status: str = "open"):
        """Lists tickets with specified status"""
        guild_id = str(ctx.guild.id)
        
        # Filter tickets
        filtered_tickets = []
        for key, ticket in self.tickets['tickets'].items():
            if key.startswith(guild_id):
                if ticket.get('status', '').lower() == status.lower():
                    filtered_tickets.append(ticket)
        
        if not filtered_tickets:
            embed = discord.Embed(
                title=f"📋 {status.upper()} TICKETS",
                description=f"No {status} tickets found.",
                color=self.colors['secondary']
            )
            await ctx.send(embed=embed)
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"📋 {status.upper()} TICKETS",
            description=f"Found {len(filtered_tickets)} tickets",
            color=self.colors['primary']
        )
        
        for ticket in filtered_tickets[:10]:  # Show first 10
            status_emoji = "🟢" if ticket['status'] == 'open' else "🔴"
            user_mention = f"<@{ticket['user_id']}>"
            
            embed.add_field(
                name=f"{status_emoji} #{ticket['id']} - {ticket.get('subject', 'No subject')[:30]}",
                value=f"""
                **User:** {user_mention}
                **Created:** {ticket['created_at'][:10]}
                **Channel:** <#{ticket['channel_id']}>
                """,
                inline=False
            )
        
        if len(filtered_tickets) > 10:
            embed.set_footer(text=f"+{len(filtered_tickets) - 10} more tickets...")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="ticket_add")
    @commands.has_permissions(manage_channels=True)
    async def add_to_ticket_command(self, ctx, member: discord.Member, ticket_id: int = None):
        """Adds member to ticket"""
        if not ticket_id:
            # Find ticket in current channel
            ticket = await self.find_ticket_by_channel(ctx.channel.id)
            if not ticket:
                await ctx.send("❌ This is not a ticket channel!")
                return
            ticket_id = ticket['id']
        
        await self.add_member_to_ticket(ctx, ticket_id, member)
    
    async def add_member_to_ticket(self, ctx, ticket_id, member):
        """Adds member to specific ticket"""
        guild_id = str(ctx.guild.id)
        ticket_key = f"{guild_id}_{ticket_id}"
        
        if ticket_key not in self.tickets['tickets']:
            await ctx.send(f"❌ Ticket #{ticket_id} not found!")
            return
        
        ticket = self.tickets['tickets'][ticket_key]
        
        # Get channel
        channel = ctx.guild.get_channel(ticket['channel_id'])
        if not channel:
            await ctx.send("❌ Ticket channel not found!")
            return
        
        # Add permissions
        await channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )
        
        # Update ticket data
        if member.id not in ticket['support_team']:
            ticket['support_team'].append(member.id)
            self.save_tickets()
        
        # Notify in ticket channel
        ticket_embed = discord.Embed(
            description=f"👋 {member.mention} was added to this ticket by {ctx.author.mention}",
            color=self.colors['success']
        )
        await channel.send(embed=ticket_embed)
        
        await ctx.send(f"✅ {member.mention} added to ticket #{ticket_id}")
    
    async def add_member_modal(self, interaction, ticket_id):
        """Shows modal to add member"""
        modal = AddMemberModal(self, ticket_id)
        await interaction.response.send_modal(modal)
    
    @commands.command(name="ticket_claim")
    @commands.has_permissions(manage_channels=True)
    async def claim_ticket_command(self, ctx, ticket_id: int = None):
        """Claims ticket for yourself"""
        if not ticket_id:
            # Find ticket in current channel
            ticket = await self.find_ticket_by_channel(ctx.channel.id)
            if not ticket:
                await ctx.send("❌ This is not a ticket channel!")
                return
            ticket_id = ticket['id']
        
        await self.claim_ticket(ctx, ticket_id)
    
    async def claim_ticket(self, ctx, ticket_id):
        """Claims a specific ticket"""
        guild_id = str(ctx.guild.id)
        ticket_key = f"{guild_id}_{ticket_id}"
        
        if ticket_key not in self.tickets['tickets']:
            await ctx.send(f"❌ Ticket #{ticket_id} not found!")
            return
        
        ticket = self.tickets['tickets'][ticket_key]
        
        # Check if already claimed
        if ctx.author.id in ticket.get('claimed_by', []):
            await ctx.send("❌ You already claimed this ticket!")
            return
        
        # Claim ticket
        if 'claimed_by' not in ticket:
            ticket['claimed_by'] = []
        ticket['claimed_by'].append(ctx.author.id)
        self.save_tickets()
        
        # Get channel
        channel = ctx.guild.get_channel(ticket['channel_id'])
        if channel:
            embed = discord.Embed(
                description=f"🎯 **Ticket claimed by {ctx.author.mention}**",
                color=self.colors['success']
            )
            await channel.send(embed=embed)
        
        await ctx.send(f"✅ You claimed ticket #{ticket_id}")
    
    @commands.command(name="ticket_info")
    async def ticket_info_command(self, ctx, ticket_id: int = None):
        """Shows ticket information"""
        if not ticket_id:
            # Find ticket in current channel
            ticket = await self.find_ticket_by_channel(ctx.channel.id)
            if not ticket:
                await ctx.send("❌ This is not a ticket channel!")
                return
            ticket_id = ticket['id']
        
        await self.show_ticket_info(ctx, ticket_id)
    
    async def show_ticket_info(self, ctx, ticket_id):
        """Shows detailed ticket info"""
        guild_id = str(ctx.guild.id)
        ticket_key = f"{guild_id}_{ticket_id}"
        
        if ticket_key not in self.tickets['tickets']:
            await ctx.send(f"❌ Ticket #{ticket_id} not found!")
            return
        
        ticket = self.tickets['tickets'][ticket_key]
        
        embed = discord.Embed(
            title=f"🎫 Ticket #{ticket_id} Information",
            color=self.colors['info']
        )
        
        # Basic info
        status_emoji = "🟢" if ticket['status'] == 'open' else "🔴"
        created = datetime.fromisoformat(ticket['created_at']).strftime('%Y-%m-%d %H:%M')
        
        embed.add_field(
            name="Basic Information",
            value=f"""
            **Status:** {status_emoji} {ticket['status'].upper()}
            **User:** <@{ticket['user_id']}>
            **Subject:** {ticket.get('subject', 'No subject')}
            **Created:** {created}
            """,
            inline=False
        )
        
        # Support team
        support_team = ticket.get('support_team', [])
        if support_team:
            team_mentions = "\n".join([f"• <@{uid}>" for uid in support_team])
            embed.add_field(name="Support Team", value=team_mentions, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="mytickets")
    async def my_tickets_command(self, ctx):
        """Shows user's open tickets"""
        user_id = ctx.author.id
        guild_id = str(ctx.guild.id)
        
        # Find user's tickets
        user_tickets = []
        for key, ticket in self.tickets['tickets'].items():
            if key.startswith(guild_id) and ticket['user_id'] == user_id:
                if ticket.get('status') == 'open':
                    user_tickets.append(ticket)
        
        if not user_tickets:
            embed = discord.Embed(
                title="📋 Your Open Tickets",
                description="You have no open tickets.",
                color=self.colors['secondary']
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📋 Your Open Tickets",
            description=f"You have {len(user_tickets)} open ticket(s)",
            color=self.colors['primary']
        )
        
        for ticket in user_tickets:
            channel = ctx.guild.get_channel(ticket['channel_id'])
            channel_mention = channel.mention if channel else "Channel not found"
            
            embed.add_field(
                name=f"🎫 #{ticket['id']} - {ticket.get('subject', 'No subject')[:30]}",
                value=f"""
                **Channel:** {channel_mention}
                **Created:** {ticket['created_at'][:10]}
                **Status:** 🟢 OPEN
                """,
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="ticket_config")
    @commands.has_permissions(administrator=True)
    async def show_config_command(self, ctx):
        """Shows current system configuration"""
        embed = discord.Embed(
            title="⚙️ System Configuration",
            color=self.colors['primary']
        )
        
        # Guild info
        embed.add_field(
            name="Server",
            value=f"ID: `{self.config.get('guild_id', 'Not set')}`",
            inline=False
        )
        
        # Channels
        channels_info = []
        for name, cid in [
            ("Ticket Channel", "ticket_channel"),
            ("Log Channel", "log_channel"),
            ("Archive Category", "archive_category")
        ]:
            channel_id = self.config.get(cid)
            if channel_id:
                channel = ctx.guild.get_channel(channel_id)
                channels_info.append(f"**{name}:** {channel.mention if channel else 'Not found'}")
            else:
                channels_info.append(f"**{name}:** Not set")
        
        embed.add_field(name="Channels", value="\n".join(channels_info), inline=False)
        
        # Roles
        roles_info = []
        for name, rid in [
            ("Admin Role", "admin_role"),
            ("Support Role", "support_role")
        ]:
            role_id = self.config.get(rid)
            if role_id:
                role = ctx.guild.get_role(role_id)
                roles_info.append(f"**{name}:** {role.mention if role else 'Not found'}")
            else:
                roles_info.append(f"**{name}:** Not set")
        
        embed.add_field(name="Roles", value="\n".join(roles_info), inline=False)
        
        # Stats
        guild_id = str(ctx.guild.id)
        total_tickets = len([k for k in self.tickets['tickets'].keys() if k.startswith(guild_id)])
        open_tickets = len([t for t in self.tickets['tickets'].values() 
                          if t.get('status') == 'open' and guild_id in str(t.get('channel_id', ''))])
        
        embed.add_field(
            name="Statistics",
            value=f"""
            **Total Tickets:** {total_tickets}
            **Open Tickets:** {open_tickets}
            **Ticket Counter:** #{self.tickets.get('counter', 0)}
            """,
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="ticket_panel")
    @commands.has_permissions(administrator=True)
    async def resend_panel_command(self, ctx):
        """Resends the ticket panel"""
        channel_id = self.config.get('ticket_channel')
        if not channel_id:
            await ctx.send("❌ Ticket channel not set! Use `!ticket_setup` first")
            return
        
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            await ctx.send("❌ Ticket channel not found!")
            return
        
        # Clear old messages
        try:
            await channel.purge(limit=10)
        except:
            pass
        
        # Send new panel
        await self.send_ticket_panel(channel)
        
        await ctx.send(f"✅ Ticket panel sent to {channel.mention}")
    
    @commands.command(name="ticket_promote")
    @commands.has_permissions(administrator=True)
    async def promote_to_support(self, ctx, member: discord.Member):
        """Promotes member to support team"""
        role_id = self.config.get('support_role')
        if not role_id:
            await ctx.send("❌ Support role not set! Use `!ticket_setup` first")
            return
        
        role = ctx.guild.get_role(role_id)
        if not role:
            await ctx.send("❌ Support role not found!")
            return
        
        # Add role
        await member.add_roles(role)
        
        embed = discord.Embed(
            title="✅ Promotion Successful",
            description=f"{member.mention} is now a member of the support team!",
            color=self.colors['success']
        )
        
        await ctx.send(embed=embed)
        
        # Log action
        await self.log_action(f"👑 {member.mention} promoted to support team by {ctx.author.mention}")
    
    @commands.command(name="ticket_demote")
    @commands.has_permissions(administrator=True)
    async def demote_from_support(self, ctx, member: discord.Member):
        """Removes member from support team"""
        role_id = self.config.get('support_role')
        if not role_id:
            await ctx.send("❌ Support role not set!")
            return
        
        role = ctx.guild.get_role(role_id)
        if not role:
            await ctx.send("❌ Support role not found!")
            return
        
        # Remove role
        await member.remove_roles(role)
        
        embed = discord.Embed(
            title="✅ Demotion Successful",
            description=f"{member.mention} removed from support team.",
            color=self.colors['warning']
        )
        
        await ctx.send(embed=embed)
        
        # Log action
        await self.log_action(f"⬇️ {member.mention} removed from support team by {ctx.author.mention}")
    
    @commands.command(name="ticket_stats")
    async def show_stats(self, ctx):
        """Shows system statistics"""
        guild_id = str(ctx.guild.id)
        
        # Calculate stats
        total_tickets = len([k for k in self.tickets['tickets'].keys() if k.startswith(guild_id)])
        open_tickets = len([t for t in self.tickets['tickets'].values() 
                          if t.get('status') == 'open' and guild_id in str(t.get('channel_id', ''))])
        closed_tickets = total_tickets - open_tickets
        
        embed = discord.Embed(
            title="📊 System Statistics",
            color=self.colors['info']
        )
        
        embed.add_field(
            name="Ticket Counts",
            value=f"""
            **Total Tickets:** {total_tickets}
            **Open Tickets:** {open_tickets}
            **Closed Tickets:** {closed_tickets}
            **Completion Rate:** {(closed_tickets/total_tickets*100) if total_tickets > 0 else 0:.1f}%
            """,
            inline=False
        )
        
        embed.add_field(
            name="Performance",
            value=f"""
            **Next Ticket ID:** #{self.tickets.get('counter', 0) + 1}
            **System Status:** ✅ Active
            """,
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # ==================== HELPER FUNCTIONS ====================
    
    async def find_ticket_by_channel(self, channel_id):
        """Finds ticket by channel ID"""
        for ticket in self.tickets['tickets'].values():
            if ticket.get('channel_id') == channel_id:
                return ticket
        return None
    
    async def show_admin_panel(self, interaction):
        """Shows admin panel"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚙️ Admin Control Panel",
            description="Select an action:",
            color=self.colors['dark']
        )
        
        view = View(timeout=60)
        
        # List tickets button
        list_btn = Button(label="📋 List Tickets", style=discord.ButtonStyle.primary)
        
        async def list_callback(i):
            ctx = await self.bot.get_context(interaction.message)
            if ctx:
                ctx.author = interaction.user
                ctx.guild = interaction.guild
                ctx.channel = interaction.channel
                await self.list_tickets_command(ctx, "open")
            await i.response.defer()
        
        list_btn.callback = list_callback
        view.add_item(list_btn)
        
        # Stats button
        stats_btn = Button(label="📊 Statistics", style=discord.ButtonStyle.success)
        
        async def stats_callback(i):
            ctx = await self.bot.get_context(interaction.message)
            if ctx:
                ctx.author = interaction.user
                ctx.guild = interaction.guild
                ctx.channel = interaction.channel
                await self.show_stats(ctx)
            await i.response.defer()
        
        stats_btn.callback = stats_callback
        view.add_item(stats_btn)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def show_help_modal(self, interaction):
        """Shows help modal"""
        embed = discord.Embed(
            title="❓ Need Help?",
            description="Here's how to use the ticket system:",
            color=self.colors['info']
        )
        
        embed.add_field(
            name="For Users",
            value="Use `!ticket` or click the button above to open a ticket",
            inline=False
        )
        
        embed.add_field(
            name="For Support Team",
            value="Use commands like `!ticket_close`, `!ticket_add`, etc.",
            inline=False
        )
        
        embed.add_field(
            name="For Administrators",
            value="Use `!ticket_setup`, `!ticket_config`, `!ticket_promote`, etc.",
            inline=False
        )
        
        embed.add_field(
            name="Full Command List",
            value="Type `!tickethelp` to see all commands with explanations",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def log_action(self, message):
        """Logs action to log channel"""
        try:
            channel_id = self.config.get('log_channel')
            if channel_id:
                guild_id = self.config.get('guild_id')
                if guild_id:
                    guild = self.bot.get_guild(int(guild_id))
                    if guild:
                        channel = guild.get_channel(channel_id)
                        if channel:
                            embed = discord.Embed(
                                description=message,
                                color=self.colors['secondary'],
                                timestamp=datetime.now()
                            )
                            await channel.send(embed=embed)
        except Exception as e:
            print(f"Log error: {e}")

# ==================== SETUP FUNCTION ====================

async def setup(bot):
    """Adds the cog to the bot"""
    try:
        await bot.add_cog(LuxuryTickets(bot))
        print("✅ Luxury Ticket System loaded successfully!")
    except Exception as e:
        print(f"❌ Error loading ticket system: {e}")
        traceback.print_exc()