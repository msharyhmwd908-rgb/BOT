import os
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands

# إعداد سيرفر Flask للحفاظ على تشغيل البوت 24/7 على منصات الاستضافة
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# إعدادات البوت والصلاحيات (Intents)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    try:
        # مزامنة أوامر السلاش مع دسكورد لكي تظهر للمستخدمين
        synced = await bot.tree.sync()
        print(f'تمت مزامنة {len(synced)} أمر/أوامر (Slash Commands).')
    except Exception as e:
        print(e)
    print(f'تم تسجيل الدخول بنجاح باسم: {bot.user}')

# تعريف أمر سلاش (Slash Command) جديد
@bot.tree.command(name="ping", description="أمر تجريبي للتأكد من استجابة البوت باستخدام السلاش")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message('Pong! 🏓 البوت شغال بأوامر السلاش وزي الفل.')

# تشغيل السيرفر الوهمي بالتزامن مع البوت
keep_alive()

# تشغيل البوت باستخدام التوكن من متغيرات البيئة
TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("خطأ: لم يتم العثور على DISCORD_TOKEN في متغيرات البيئة الخاصة بمنصة الاستضافة.")
