# main_bot.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# تحميل التوكن
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# إعدادات البوت
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ البوت متصل باسم: {bot.user}')
    print('🎫 نظام التذاكر الفاخم جاهز')

# تحميل نظام التذاكر
async def load_extensions():
    try:
        await bot.load_extension('luxury_tickets_fixed')
        print('✅ تم تحميل نظام التذاكر')
    except Exception as e:
        print(f'❌ خطأ في تحميل النظام: {e}')

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

# تشغيل البوت
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())