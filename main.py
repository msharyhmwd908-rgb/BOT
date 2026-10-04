import os
import asyncio
import logging
from pathlib import Path
from threading import Thread

import discord
from discord.ext import commands
from flask import Flask, render_template, request


# ============================================================
# N9V BOT - MAIN
# Modern discord.py 2.x
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
COGS_DIR = BASE_DIR / "cogs"

TOKEN = os.getenv("DISCORD_TOKEN")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("N9V")


# ============================================================
# FLASK WEB SERVER (Dashboard & Callback)
# ============================================================

# ضبط مسار القوالب ومجلد الـ static الصحيح
app = Flask(__name__, template_folder='.', static_folder='static')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "لم يتم استلام كود التحقق!", 400
    return f"تم تسجيل الدخول بنجاح يا حمود! كود التحقق الخاص بك هو: {code}"

def run_web():
    # تشغيل السيرفر على البورت الخاص بالاستضافة
    app.run(host='0.0.0.0', port=25987, debug=False, use_reloader=False)


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True


# ============================================================
# BOT
# ============================================================

class N9VBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        self.loaded_extensions = []

    async def setup_hook(self):
        logger.info("========================================")
        logger.info("N9V BOT - Starting setup")
        logger.info("========================================")

        try:
            # تحديث ومزامنة الأوامر لحل مشكلة الأوامر القديمة التي لم تُحذف
            synced = await self.tree.sync()
            logger.info(f"Successfully synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("N9V Bot is fully online and ready!")


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == '__main__':
    # 1. تشغيل سيرفر الويب في خلفية مستقلة ليعمل الموقع والـ Callback
    web_thread = Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()
    logger.info("Flask Web Server started in background thread.")

    # 2. تشغيل بوت ديسكورد
    bot = N9VBot()
    if TOKEN:
        bot.run(TOKEN)
    else:
        logger.error("DISCORD_TOKEN environment variable not found!")
