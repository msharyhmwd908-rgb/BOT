import os
import asyncio
import discord
from discord.ext import commands

# تفعيل الـ Intents بالكامل لضمان قراءة البيانات والمنشنات
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # تسجيل الـ Views الدائمة لكي تعمل الأزرار حتى بعد عمل Restart
    try:
        from cogs.suggestions import MainPanelView, ColorSelectView, SuggestionActionView
        bot.add_view(MainPanelView())
        bot.add_view(ColorSelectView())
        bot.add_view(SuggestionActionView())
    except Exception as e:
        print(f"خطأ في تسجيل الـ Views: {e}")

    try:
        synced = await bot.tree.sync()
        print(f'تمت مزامنة {len(synced)} أمر/أوامر (Slash Commands).')
    except Exception as e:
        print(f"خطأ في المزامنة: {e}")
        
    print(f'تم تسجيل الدخول بنجاح باسم: {bot.user}')

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

if __name__ == "__main__":
    asyncio.run(main())
