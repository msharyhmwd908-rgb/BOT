import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import re
from datetime import datetime, timedelta, timezone


DB_FILE = "admin.db"


# =========================
# DATABASE
# =========================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_bans (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            unban_at TEXT NOT NULL,
            banned_by INTEGER NOT NULL,
            reason TEXT
        )
    """)

    conn.commit()
    conn.close()


def add_temp_ban(guild_id, user_id, unban_at, banned_by, reason):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM temp_bans WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )

    cursor.execute("""
        INSERT INTO temp_bans
        (guild_id, user_id, unban_at, banned_by, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (
        guild_id,
        user_id,
        unban_at,
        banned_by,
        reason
    ))

    conn.commit()
    conn.close()


# =========================
# HELPERS
# =========================

def parse_duration(value: str):
    """
    أمثلة:
    10m = 10 دقائق
    1h  = ساعة
    2d  = يومين
    1w  = أسبوع
    """

    match = re.fullmatch(
        r"\s*(\d+)\s*(s|m|h|d|w)\s*",
        value.lower()
    )

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if amount <= 0:
        return None

    units = {
        "s": timedelta(seconds=amount),
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
        "w": timedelta(weeks=amount)
    }

    return units[unit]


def duration_text(value: str):
    duration = parse_duration(value)

    if not duration:
        return "مدة غير صحيحة"

    seconds = int(duration.total_seconds())

    if seconds < 60:
        return f"{seconds} ثانية"

    if seconds < 3600:
        return f"{seconds // 60} دقيقة"

    if seconds < 86400:
        return f"{seconds // 3600} ساعة"

    if seconds < 604800:
        return f"{seconds // 86400} يوم"

    return f"{seconds // 604800} أسبوع"


async def get_member_from_message(message: discord.Message):
    if message.mentions:
        return message.mentions[0]

    # دعم ID العضو أيضًا
    if message.content.strip().isdigit():
        try:
            member = message.guild.get_member(
                int(message.content.strip())
            )

            if member:
                return member

        except ValueError:
            pass

    return None


async def ask_for_member(interaction: discord.Interaction):
    await interaction.response.send_message(
        "👤 **حدد الشخص**\n"
        "منشن العضو اللي تبي تطبق عليه العقوبة.",
        ephemeral=True
    )

    def check(message):
        return (
            message.author.id == interaction.user.id
            and message.guild.id == interaction.guild.id
            and (
                message.mentions
                or message.content.strip().isdigit()
            )
        )

    try:
        message = await interaction.client.wait_for(
            "message",
            timeout=60,
            check=check
        )

        member = await get_member_from_message(message)

        if not member:
            return None

        return member

    except TimeoutError:
        return None


# =========================
# CONFIRM VIEW
# =========================

class ConfirmView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=30)

        self.value = None

    @discord.ui.button(
        label="تنفيذ",
        emoji="✅",
        style=discord.ButtonStyle.success
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        self.value = True

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="✅ تم تنفيذ العملية.",
            embed=None,
            view=self
        )

        self.stop()

    @discord.ui.button(
        label="إلغاء",
        emoji="❌",
        style=discord.ButtonStyle.danger
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        self.value = False

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="❌ تم إلغاء العملية.",
            embed=None,
            view=self
        )

        self.stop()


# =========================
# ADMIN PANEL
# =========================

class AdminPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="باند",
        emoji="🔨",
        style=discord.ButtonStyle.danger,
        custom_id="admin_ban"
    )
    async def ban_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = await ask_for_member(interaction)

        if not member:
            await interaction.followup.send(
                "❌ ما قدرت أحدد العضو.",
                ephemeral=True
            )
            return

        if member.id == interaction.user.id:
            await interaction.followup.send(
                "❌ ما تقدر تطبق العقوبة على نفسك.",
                ephemeral=True
            )
            return

        if member.top_role >= interaction.user.top_role:
            await interaction.followup.send(
                "❌ ما تقدر تعاقب عضو رتبته مساوية أو أعلى من رتبتك.",
                ephemeral=True
            )
            return

        await interaction.followup.send(
            "⏱️ **حدد مدة الباند**\n\n"
            "اكتب المدة بالشكل هذا:\n"
            "`10m` = 10 دقائق\n"
            "`1h` = ساعة\n"
            "`1d` = يوم\n"
            "`1w` = أسبوع\n\n"
            "أو اكتب `permanent` للباند الدائم.",
            ephemeral=True
        )

        def check(message):
            return (
                message.author.id == interaction.user.id
                and message.guild.id == interaction.guild.id
            )

        try:
            message = await interaction.client.wait_for(
                "message",
                timeout=60,
                check=check
            )

        except TimeoutError:
            await interaction.followup.send(
                "⌛ انتهى وقت الاختيار.",
                ephemeral=True
            )
            return

        duration_input = message.content.strip().lower()

        # باند دائم
        if duration_input in ["permanent", "perm", "دائم"]:

            embed = discord.Embed(
                title="⚠️ تأكيد الباند",
                description=(
                    f"👤 العضو: {member.mention}\n"
                    f"🔨 العقوبة: باند\n"
                    f"⏱️ المدة: دائم"
                ),
                color=discord.Color.red()
            )

            view = ConfirmView()

            await interaction.followup.send(
                embed=embed,
                view=view,
                ephemeral=True
            )

            await view.wait()

            if view.value:
                try:
                    await interaction.guild.ban(
                        member,
                        reason=f"Permanent ban by {interaction.user}"
                    )

                except discord.Forbidden:
                    await interaction.followup.send(
                        "❌ البوت ما عنده صلاحية الباند أو العضو أعلى من البوت.",
                        ephemeral=True
                    )

            return

        duration = parse_duration(duration_input)

        if not duration:
            await interaction.followup.send(
                "❌ المدة غير صحيحة.\nمثال: `10m` أو `2h` أو `7d`",
                ephemeral=True
            )
            return

        unban_at = datetime.now(timezone.utc) + duration

        embed = discord.Embed(
            title="⚠️ تأكيد الباند",
            description=(
                f"👤 العضو: {member.mention}\n"
                f"🔨 العقوبة: باند\n"
                f"⏱️ المدة: {duration_text(duration_input)}\n"
                f"🕐 ينتهي: <t:{int(unban_at.timestamp())}:R>"
            ),
            color=discord.Color.red()
        )

        view = ConfirmView()

        await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )

        await view.wait()

        if not view.value:
            return

        try:
            await interaction.guild.ban(
                member,
                reason=f"Temporary ban by {interaction.user}"
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ البوت ما عنده صلاحية الباند.",
                ephemeral=True
            )
            return

        add_temp_ban(
            interaction.guild.id,
            member.id,
            unban_at.isoformat(),
            interaction.user.id,
            "Temporary ban"
        )

        await interaction.followup.send(
            f"🔨 تم تبنيد {member.mention} لمدة "
            f"**{duration_text(duration_input)}**.",
            ephemeral=True
        )

    @discord.ui.button(
        label="كك",
        emoji="👢",
        style=discord.ButtonStyle.danger,
        custom_id="admin_kick"
    )
    async def kick_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = await ask_for_member(interaction)

        if not member:
            await interaction.followup.send(
                "❌ ما قدرت أحدد العضو.",
                ephemeral=True
            )
            return

        if member.id == interaction.user.id:
            await interaction.followup.send(
                "❌ ما تقدر تكك نفسك.",
                ephemeral=True
            )
            return

        if member.top_role >= interaction.user.top_role:
            await interaction.followup.send(
                "❌ ما تقدر تكك عضو رتبته مساوية أو أعلى من رتبتك.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="⚠️ تأكيد الكك",
            description=(
                f"👤 العضو: {member.mention}\n"
                f"👢 الإجراء: كك"
            ),
            color=discord.Color.orange()
        )

        view = ConfirmView()

        await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )

        await view.wait()

        if not view.value:
            return

        try:
            await member.kick(
                reason=f"Kick by {interaction.user}"
            )

            await interaction.followup.send(
                f"👢 تم تكك {member.mention}.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ البوت ما عنده صلاحية الكك.",
                ephemeral=True
            )

    @discord.ui.button(
        label="تايم",
        emoji="⏱️",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_timeout"
    )
    async def timeout_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        member = await ask_for_member(interaction)

        if not member:
            await interaction.followup.send(
                "❌ ما قدرت أحدد العضو.",
                ephemeral=True
            )
            return

        if member.id == interaction.user.id:
            await interaction.followup.send(
                "❌ ما تقدر تعطي نفسك تايم.",
                ephemeral=True
            )
            return

        if member.top_role >= interaction.user.top_role:
            await interaction.followup.send(
                "❌ ما تقدر تعطي تايم لعضو رتبته مساوية أو أعلى من رتبتك.",
                ephemeral=True
            )
            return

        await interaction.followup.send(
            "⏱️ **حدد مدة التايم**\n\n"
            "اكتب مثل:\n"
            "`10m` = 10 دقائق\n"
            "`1h` = ساعة\n"
            "`1d` = يوم",
            ephemeral=True
        )

        def check(message):
            return (
                message.author.id == interaction.user.id
                and message.guild.id == interaction.guild.id
            )

        try:
            message = await interaction.client.wait_for(
                "message",
                timeout=60,
                check=check
            )

        except TimeoutError:
            await interaction.followup.send(
                "⌛ انتهى وقت الاختيار.",
                ephemeral=True
            )
            return

        duration_input = message.content.strip().lower()
        duration = parse_duration(duration_input)

        if not duration:
            await interaction.followup.send(
                "❌ المدة غير صحيحة.",
                ephemeral=True
            )
            return

        if duration > timedelta(days=28):
            await interaction.followup.send(
                "❌ أقصى مدة للتايم هي 28 يوم.",
                ephemeral=True
            )
            return

        until = datetime.now(timezone.utc) + duration

        embed = discord.Embed(
            title="⚠️ تأكيد التايم",
            description=(
                f"👤 العضو: {member.mention}\n"
                f"⏱️ المدة: {duration_text(duration_input)}\n"
                f"🕐 ينتهي: <t:{int(until.timestamp())}:R>"
            ),
            color=discord.Color.orange()
        )

        view = ConfirmView()

        await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )

        await view.wait()

        if not view.value:
            return

        try:
            await member.timeout(
                until,
                reason=f"Timeout by {interaction.user}"
            )

            await interaction.followup.send(
                f"⏱️ تم إعطاء {member.mention} تايم لمدة "
                f"**{duration_text(duration_input)}**.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ البوت ما عنده صلاحية التايم.",
                ephemeral=True
            )


# =========================
# COG
# =========================

class Admin(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.unban_expired.start()

    def cog_unload(self):
        self.unban_expired.cancel()

    @app_commands.command(
        name="admin",
        description="فتح لوحة الإدارة"
    )
    @app_commands.default_permissions(administrator=True)
    async def admin(self, interaction: discord.Interaction):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ ما عندك صلاحية تستخدم لوحة الإدارة.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🛡️ لوحة الإدارة",
            description=(
                "هذي لوحة الإدارة، من هنا تقدر تدير أمور السيرفر كلها "
                "بمكان واحد، وتتابع شغل الإدارة والعمليات اللي تصير أول بأول."
            ),
            color=discord.Color.from_rgb(100, 0, 20)
        )

        embed.set_footer(text="N9V・ADMIN CENTER")

        await interaction.response.send_message(
            embed=embed,
            view=AdminPanelView()
        )

    @tasks.loop(seconds=10)
    async def unban_expired(self):

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT guild_id, user_id, unban_at
            FROM temp_bans
        """)

        rows = cursor.fetchall()

        now = datetime.now(timezone.utc)

        for guild_id, user_id, unban_at in rows:

            try:
                expire_time = datetime.fromisoformat(unban_at)

                if now >= expire_time:

                    guild = self.bot.get_guild(guild_id)

                    if guild:
                        try:
                            await guild.unban(
                                discord.Object(id=user_id),
                                reason="Temporary ban expired"
                            )
                        except discord.NotFound:
                            pass
                        except discord.Forbidden:
                            pass

                    cursor.execute("""
                        DELETE FROM temp_bans
                        WHERE guild_id = ? AND user_id = ?
                    """, (guild_id, user_id))

        conn.commit()
        conn.close()

    @unban_expired.before_loop
    async def before_unban_expired(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    init_db()

    bot.add_view(AdminPanelView())

    await bot.add_cog(Admin(bot))
