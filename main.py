import os
import asyncio
import discord
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f'تمت مزامنة {len(synced)} أمر/أوامر (Slash Commands).')
    except Exception as e:
        print(e)
    print(f'تم تسجيل الدخول بنجاح باسم: {bot.user}')

# تحميل الملفات الفرعية من مجلد cogs تلقائياً
async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

async def main():
    async with bot:
        await load_extensions()
        TOKEN = os.getenv('DISCORD_TOKEN')
        if TOKEN:
            await bot.start(TOKEN)
        else:
            print("خطأ: لم يتم العثور على DISCORD_TOKEN في متغيرات البيئة.")

asyncio.run(main())
