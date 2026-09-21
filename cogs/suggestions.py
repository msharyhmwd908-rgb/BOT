import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import re


# ==========================================
# الإعدادات
# ==========================================

PANEL_COLOR = 0x640014

DB_NAME = "suggestions.db"


# ==========================================
# قاعدة البيانات
# ==========================================

db = sqlite3.connect(DB_NAME)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    color INTEGER NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS votes (
    suggestion_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    vote TEXT NOT NULL,
    PRIMARY KEY (suggestion_id, user_id)
)
""")

db.commit()


# ==========================================
# الألوان
# ==========================================

COLORS = {
    "🔴 أحمر": 0xE74C3C,
    "🟠 برتقالي": 0xE67E22,
    "🟡 أصفر": 0xF1C40F,
    "🟢 أخضر": 0x2ECC71,
    "🔵 أزرق": 0x3498DB,
    "🟣 بنفسجي": 0x9B59B6,
    "🩷 وردي": 0xFF69B4,
    "🩵 سماوي": 0x00D9FF,
    "⚪ أبيض": 0xECF0F1,
    "⚫ أسود": 0x1C1C1C,
    "🟤 بني": 0x8B4513,
}


# ==========================================
# أدوات
# ==========================================

def valid_hex(value: str):
    """
    يسمح للعضو بكتابة لون HEX اختياري.
    """
    if not value:
        return None

    value = value.strip().replace("#", "")

    if not re.fullmatch(r"[0-9A-Fa-f]{6}", value):
        return None

    return int(value, 16)


def get_votes(suggestion_id: int):
    cursor.execute(
        "SELECT user_id, vote FROM votes WHERE suggestion_id = ?",
        (suggestion_id,)
    )

    rows = cursor.fetchall()

    supporters = []
    opponents = []

    for user_id, vote in rows:
        if vote == "yes":
            supporters.append(user_id)
        elif vote == "no":
            opponents.append(user_id)

    return supporters, opponents


def make_mentions(ids):
    if not ids:
        return "لا يوجد"

    mentions = []

    for user_id in ids:
        mentions.append(f"<@{user_id}>")

    return "، ".join(mentions)


def build_embed(data):
    suggestion_id = data["id"]

    supporters, opponents = get_votes(suggestion_id)

    embed = discord.Embed(
        title=f"💡 اقتراح #{suggestion_id:03d}",
        description=data["description"],
        color=data["color"]
    )

    embed.add_field(
        name="📝 اسم الاقتراح",
        value=data["title"],
        inline=False
    )

    embed.add_field(
        name="👤 صاحب الاقتراح",
        value=f"<@{data['author_id']}>",
        inline=False
    )

    embed.add_field(
        name="📊 التصويت",
        value=(
            f"🟢 **مؤيدون:** {len(supporters)}\n"
            f"🔴 **معارضون:** {len(opponents)}"
        ),
        inline=False
    )

    embed.add_field(
        name="🟢 المؤيدون",
        value=make_mentions(supporters),
        inline=False
    )

    embed.add_field(
        name="🔴 المعارضون",
        value=make_mentions(opponents),
        inline=False
    )

    embed.set_footer(
        text="N9V・SUGGESTIONS"
    )

    return embed


# ==========================================
# Modal كتابة الاقتراح
# ==========================================

class SuggestionModal(discord.ui.Modal, title="📝 كتابة اقتراح"):

    suggestion_name = discord.ui.TextInput(
        label="اسم الاقتراح",
        placeholder="مثال: إضافة روم فعاليات",
        required=True,
        max_length=100
    )

    suggestion_description = discord.ui.TextInput(
        label="وصف الاقتراح",
        placeholder="اشرح اقتراحك بالتفصيل...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    color = discord.ui.TextInput(
        label="لون الاقتراح - اختياري",
        placeholder="مثال: #8B0000 أو اتركه فارغ",
        required=False,
        max_length=7
    )

    async def on_submit(self, interaction: discord.Interaction):

        selected_color = valid_hex(self.color.value)

        if self.color.value and selected_color is None:
            return await interaction.response.send_message(
                "❌ لون الـHEX غير صحيح.\nمثال صحيح: `#8B0000`",
                ephemeral=True
            )

        if selected_color is not None:
            await create_suggestion(
                interaction,
                self.suggestion_name.value,
                self.suggestion_description.value,
                selected_color
            )
            return

        # إذا ما اختار لون، نعرض له قائمة الألوان
        await interaction.response.send_message(
            "🎨 **اختر لون الاقتراح**\n\n"
            "اختيار اللون اختياري، وإذا ما تبي لون مخصص اختر "
            "**⚫ الافتراضي**.",
            view=ColorSelectView(
                interaction.user.id,
                self.suggestion_name.value,
                self.suggestion_description.value
            ),
            ephemeral=True
        )


# ==========================================
# اختيار اللون
# ==========================================

class ColorSelect(discord.ui.Select):

    def __init__(self, user_id, title, description):

        self.user_id = user_id
        self.title_text = title
        self.description_text = description

        options = [
            discord.SelectOption(
                label="أحمر",
                emoji="🔴",
                value="red"
            ),
            discord.SelectOption(
                label="برتقالي",
                emoji="🟠",
                value="orange"
            ),
            discord.SelectOption(
                label="أصفر",
                emoji="🟡",
                value="yellow"
            ),
            discord.SelectOption(
                label="أخضر",
                emoji="🟢",
                value="green"
            ),
            discord.SelectOption(
                label="أزرق",
                emoji="🔵",
                value="blue"
            ),
            discord.SelectOption(
                label="بنفسجي",
                emoji="🟣",
                value="purple"
            ),
            discord.SelectOption(
                label="وردي",
                emoji="🩷",
                value="pink"
            ),
            discord.SelectOption(
                label="سماوي",
                emoji="🩵",
                value="cyan"
            ),
            discord.SelectOption(
                label="أبيض",
                emoji="⚪",
                value="white"
            ),
            discord.SelectOption(
                label="أسود",
                emoji="⚫",
                value="black"
            ),
            discord.SelectOption(
                label="بني",
                emoji="🟤",
                value="brown"
            ),
        ]

        super().__init__(
            placeholder="🎨 اختر لون الاقتراح",
            options=options,
            custom_id="suggestion:color"
        )

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ هذه القائمة مو لك.",
                ephemeral=True
            )

        color_map = {
            "red": 0xE74C3C,
            "orange": 0xE67E22,
            "yellow": 0xF1C40F,
            "green": 0x2ECC71,
            "blue": 0x3498DB,
            "purple": 0x9B59B6,
            "pink": 0xFF69B4,
            "cyan": 0x00D9FF,
            "white": 0xECF0F1,
            "black": 0x1C1C1C,
            "brown": 0x8B4513,
        }

        color = color_map[self.values[0]]

        await create_suggestion(
            interaction,
            self.title_text,
            self.description_text,
            color
        )


class ColorSelectView(discord.ui.View):

    def __init__(self, user_id, title, description):
        super().__init__(timeout=120)

        self.add_item(
            ColorSelect(
                user_id,
                title,
                description
            )
        )


# ==========================================
# إنشاء الاقتراح
# ==========================================

async def create_suggestion(
    interaction,
    title,
    description,
    color
):

    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        return await interaction.followup.send(
            "❌ ما أقدر أرسل الاقتراح هنا.",
            ephemeral=True
        )

    cursor.execute("""
        INSERT INTO suggestions
        (guild_id, channel_id, message_id, author_id, title, description, color)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        interaction.guild.id,
        channel.id,
        0,
        interaction.user.id,
        title,
        description,
        color
    ))

    suggestion_id = cursor.lastrowid
    db.commit()

    data = {
        "id": suggestion_id,
        "author_id": interaction.user.id,
        "title": title,
        "description": description,
        "color": color
    }

    embed = build_embed(data)

    message = await channel.send(
        content=f"💡 اقتراح جديد من <@{interaction.user.id}>",
        embed=embed,
        view=SuggestionVoteView(suggestion_id)
    )

    cursor.execute(
        "UPDATE suggestions SET message_id = ? WHERE id = ?",
        (message.id, suggestion_id)
    )

    db.commit()

    await interaction.followup.send(
        f"✅ تم إرسال اقتراحك بنجاح!\n"
        f"💡 رقم الاقتراح: **#{suggestion_id:03d}**",
        ephemeral=True
    )


# ==========================================
# التصويت
# ==========================================

class SuggestionVoteView(discord.ui.View):

    def __init__(self, suggestion_id):
        super().__init__(timeout=None)

        self.suggestion_id = suggestion_id

    @discord.ui.button(
        label="أوافق",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        custom_id="suggestion:yes"
    )
    async def yes_vote(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await handle_vote(
            interaction,
            self.suggestion_id,
            "yes"
        )

    @discord.ui.button(
        label="لا أوافق",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        custom_id="suggestion:no"
    )
    async def no_vote(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await handle_vote(
            interaction,
            self.suggestion_id,
            "no"
        )


# ==========================================
# معالجة التصويت
# ==========================================

async def handle_vote(
    interaction,
    suggestion_id,
    vote_type
):

    cursor.execute(
        "SELECT * FROM suggestions WHERE id = ?",
        (suggestion_id,)
    )

    suggestion = cursor.fetchone()

    if not suggestion:
        return await interaction.response.send_message(
            "❌ الاقتراح غير موجود.",
            ephemeral=True
        )

    # الأعمدة:
    # id, guild_id, channel_id, message_id,
    # author_id, title, description, color

    cursor.execute("""
        SELECT vote
        FROM votes
        WHERE suggestion_id = ? AND user_id = ?
    """, (
        suggestion_id,
        interaction.user.id
    ))

    old_vote = cursor.fetchone()

    # نفس التصويت مرة ثانية
    if old_vote and old_vote[0] == vote_type:
        return await interaction.response.send_message(
            "⚠️ أنت مصوّت بهذا الخيار من قبل.",
            ephemeral=True
        )

    # إذا كان مصوت بالجهة الثانية، نغير تصويته
    if old_vote:
        cursor.execute("""
            UPDATE votes
            SET vote = ?
            WHERE suggestion_id = ? AND user_id = ?
        """, (
            vote_type,
            suggestion_id,
            interaction.user.id
        ))

        message_text = "🔄 تم تغيير تصويتك."

    else:
        cursor.execute("""
            INSERT INTO votes
            (suggestion_id, user_id, vote)
            VALUES (?, ?, ?)
        """, (
            suggestion_id,
            interaction.user.id,
            vote_type
        ))

        message_text = "✅ تم تسجيل تصويتك."

    db.commit()

    data = {
        "id": suggestion[0],
        "author_id": suggestion[4],
        "title": suggestion[5],
        "description": suggestion[6],
        "color": suggestion[7]
    }

    embed = build_embed(data)

    try:
        await interaction.message.edit(
            embed=embed,
            view=SuggestionVoteView(suggestion_id)
        )
    except Exception:
        pass

    await interaction.response.send_message(
        message_text,
        ephemeral=True
    )


# ==========================================
# لوحة الاقتراحات
# ==========================================

class SuggestionsPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="كتابة اقتراح",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        custom_id="suggestions_panel:write"
    )
    async def write_suggestion(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            SuggestionModal()
        )


# ==========================================
# Cog
# ==========================================

class Suggestions(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="suggestions",
        description="إرسال لوحة الاقتراحات"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def suggestions(
        self,
        interaction: discord.Interaction
    ):

        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                "❌ ما عندك صلاحية استخدام لوحة الاقتراحات.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="💡 لوحة الاقتراحات",
            description=(
                "عندك فكرة أو اقتراح ودك تشوفه بالسيرفر؟\n"
                "اكتب اقتراحك من هنا، عبّ البيانات واختر اللون "
                "اللي يعجبك، والباقي علينا. 👌"
            ),
            color=PANEL_COLOR
        )

        embed.set_footer(
            text="N9V・SUGGESTIONS"
        )

        await interaction.response.send_message(
            embed=embed,
            view=SuggestionsPanelView()
        )


# ==========================================
# Setup
# ==========================================

async def setup(bot):

    bot.add_view(SuggestionsPanelView())

    # إعادة تسجيل أزرار التصويت القديمة بعد إعادة تشغيل البوت
    cursor.execute("""
        SELECT id
        FROM suggestions
    """)

    suggestions = cursor.fetchall()

    for (suggestion_id,) in suggestions:
        bot.add_view(
            SuggestionVoteView(suggestion_id)
        )

    await bot.add_cog(Suggestions(bot))
