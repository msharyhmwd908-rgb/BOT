import asyncio
import logging
import os
from pathlib import Path
from threading import Thread

import discord
from discord.ext import commands
import requests
from flask import Flask, redirect, render_template, request, session, url_for

# ============================================================
# N9V BOT - MAIN
# Modern discord.py 2.x
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
COGS_DIR = BASE_DIR / "cogs"

TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = "1548502443636035774"
CLIENT_SECRET = "a26oXV8RjuIJz4aNpZNl9dG7aqRHwCZi"  
REDIRECT_URI = "https://bot-najm.apps.bot-hosting.cloud/callback"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("N9V")


# ============================================================
# FLASK WEB SERVER (Dashboard & Callback)
# ============================================================

app = Flask(__name__, template_folder=".", static_folder="static")
app.secret_key = os.urandom(24)  # مفتاح سري لتشغيل الجلسات (Sessions) بأمان


@app.route("/")
def home():
  return render_template(
      "index.html",
      username=session.get("username"),
      global_name=session.get("global_name"),
      avatar=session.get("avatar"),
  )


@app.route("/callback")
def callback():
  code = request.args.get("code")
  if not code:
    return "لم يتم استلام كود التحقق!", 400

  # تبديل كود التحقق بـ Access Token من ديسكورد
  token_url = "https://discord.com/api/oauth2/token"
  data = {
      "client_id": CLIENT_ID,
      "client_secret": CLIENT_SECRET,
      "grant_type": "authorization_code",
      "code": code,
      "redirect_uri": REDIRECT_URI,
  }
  headers = {"Content-Type": "application/x-www-form-urlencoded"}

  r = requests.post(token_url, data=data, headers=headers)
  token_json = r.json()
  access_token = token_json.get("access_token")

  if not access_token:
    return "فشل في الحصول على رمز الدخول من ديسكورد", 400

  # جلب بيانات المستخدم الحقيقية من ديسكورد
  user_headers = {"Authorization": f"Bearer {access_token}"}
  user_res = requests.get(
      "https://discord.com/api/users/@me", headers=user_headers
  )
  user_data = user_res.json()

  # تخزين البيانات في الجلسة لكل شخص لحاله
  session["username"] = user_data.get("username")
  session["global_name"] = user_data.get("global_name") or user_data.get(
      "username"
  )
  avatar_id = user_data.get("avatar")
  user_id = user_data.get("id")

  if avatar_id:
    session["avatar"] = (
        f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png"
    )
  else:
    session["avatar"] = "https://cdn.discordapp.com/embed/avatars/0.png"

  # العودة للصفحة الرئيسية وهي تلقائياً بتفتح الداشبورد للمستخدم
  return redirect(url_for("home"))


def run_web():
  app.run(host="0.0.0.0", port=25987, debug=False, use_reloader=False)


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
        case_insensitive=True,
    )
    self.loaded_extensions = []

  async def setup_hook(self):
    logger.info("========================================")
    logger.info("N9V BOT - Starting setup")
    logger.info("========================================")

    try:
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

if __name__ == "__main__":
  web_thread = Thread(target=run_web)
  web_thread.daemon = True
  web_thread.start()
  logger.info("Flask Web Server started in background thread.")

  bot = N9VBot()
  if TOKEN:
    bot.run(TOKEN)
  else:
    logger.error("DISCORD_TOKEN environment variable not found!")
