import os
import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands


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

            # يمنع ظهور رسالة افتراضية للأوامر غير الموجودة
            help_command=None,

            # يساعد Discord في التعامل مع الأوامر
            case_insensitive=True
        )

        self.loaded_extensions = []

    # ========================================================
    # SETUP HOOK
    # ========================================================

    async def setup_hook(self):

        logger.info("========================================")
        logger.info("N9V BOT - Starting setup")
        logger.info("========================================")

        await self.load_all_cogs()

        await self.register_persistent_views()

        try:

            synced = await self.tree.sync()

            logger.info(
                f"Slash Commands synced: {len(synced)}"
            )

        except Exception:

            logger.exception(
                "Failed to sync Slash Commands"
            )

    # ========================================================
    # LOAD COGS
    # ========================================================

    async def load_all_cogs(self):

        if not COGS_DIR.exists():

            logger.error(
                f"Cogs folder not found: {COGS_DIR}"
            )

            return

        # ترتيب الملفات حتى يكون التحميل ثابت
        files = sorted(COGS_DIR.glob("*.py"))

        for file in files:

            if file.name.startswith("_"):
                continue

            extension = f"cogs.{file.stem}"

            try:

                await self.load_extension(
                    extension
                )

                self.loaded_extensions.append(
                    extension
                )

                logger.info(
                    f"Loaded Cog: {extension}"
                )

            except commands.ExtensionAlreadyLoaded:

                logger.warning(
                    f"Already loaded: {extension}"
                )

            except commands.NoEntryPointError:

                logger.error(
                    f"FAILED: {extension}"
                )

                logger.error(
                    "هذا الملف لا يحتوي على:"
                )

                logger.error(
                    "async def setup(bot):"
                )

            except Exception:

                logger.exception(
                    f"Failed to load Cog: {extension}"
                )

        logger.info(
            f"Loaded {len(self.loaded_extensions)} Cog(s)"
        )

    # ========================================================
    # PERSISTENT VIEWS
    # ========================================================

    async def register_persistent_views(self):

        """
        تسجيل الـPersistent Views.
        الأزرار تستمر بالعمل حتى بعد Restart.
        """

        # ----------------------------------------------------
        # Suggestions
        # ----------------------------------------------------

        try:

            from cogs.suggestions import (
                MainPanelView,
                ColorSelectView,
                SuggestionActionView
            )

            self.add_view(
                MainPanelView()
            )

            self.add_view(
                ColorSelectView()
            )

            self.add_view(
                SuggestionActionView()
            )

            logger.info(
                "Suggestions Persistent Views registered."
            )

        except ModuleNotFoundError:

            logger.info(
                "Suggestions Cog غير موجود، تم التخطي."
            )

        except ImportError as e:

            logger.warning(
                f"Suggestions Views غير متوفرة: {e}"
            )

        except Exception:

            logger.exception(
                "Failed to register Suggestions Views"
            )

        # ----------------------------------------------------
        # Tickets
        # ----------------------------------------------------
        #
        # tickets.py عندنا يسجل الـViews بنفسه داخل setup().
        # لذلك لا نسجلها هنا مرة ثانية.
        #
        # هذا يمنع مشكلة:
        # Duplicate custom_id / View already registered
        # ----------------------------------------------------

        logger.info(
            "Persistent Views registration completed."
        )

    # ========================================================
    # READY
    # ========================================================

    async def on_ready(self):

        logger.info("========================================")

        if self.user:

            logger.info(
                f"Logged in as: {self.user} "
                f"(ID: {self.user.id})"
            )

        logger.info(
            f"Guilds: {len(self.guilds)}"
        )

        logger.info(
            f"Cogs: {len(self.loaded_extensions)}"
        )

        logger.info(
            "N9V BOT is ONLINE."
        )

        logger.info("========================================")


    # ========================================================
    # GLOBAL ERROR
    # ========================================================

    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError
    ):

        if isinstance(
            error,
            commands.CommandNotFound
        ):
            return

        if isinstance(
            error,
            commands.MissingPermissions
        ):

            try:

                await ctx.send(
                    "❌ ما عندك الصلاحيات المطلوبة."
                )

            except discord.HTTPException:
                pass

            return

        if isinstance(
            error,
            commands.MissingRequiredArgument
        ):

            try:

                await ctx.send(
                    "❌ ناقصك أحد المدخلات المطلوبة."
                )

            except discord.HTTPException:
                pass

            return

        logger.exception(
            "Unhandled command error:",
            exc_info=error
        )


# ============================================================
# CREATE BOT
# ============================================================

bot = N9VBot()


# ============================================================
# START
# ============================================================

async def main():

    if not TOKEN:

        logger.critical(
            "DISCORD_TOKEN غير موجود في Environment Variables."
        )

        return

    try:

        await bot.start(TOKEN)

    except discord.LoginFailure:

        logger.critical(
            "Discord Token غير صحيح."
        )

    except discord.PrivilegedIntentsRequired:

        logger.critical(
            "البوت يحتاج Privileged Intents."
        )

        logger.critical(
            "فعّل Members Intent و Message Content Intent "
            "من Discord Developer Portal."
        )

    except Exception:

        logger.exception(
            "Bot crashed بسبب خطأ غير متوقع."
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        logger.info(
            "Bot stopped manually."
        )
