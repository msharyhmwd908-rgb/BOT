import discord
from discord.ext import commands
import sqlite3
import asyncio
import io
from datetime import datetime


# ============================================================
# N9V TICKET SYSTEM
# ============================================================

TICKET_CATEGORY_ID = 1548014683695620116
PANEL_CHANNEL_ID = 1548014911932858398
LOG_CHANNEL_ID = 1495450684731162664

ADMIN_ROLE_ID = 1498008105819177240
OWNER_ROLE_ID = 1497718287956443249
COOWNER_ROLE_ID = 1497608751551746179

PANEL_IMAGE = "https://a.top4top.io/p_3910nb9nm0.png"

DB_FILE = "tickets.db"

BURGUNDY = discord.Color.from_rgb(100, 0, 20)


# ============================================================
# DATABASE
# ============================================================

db = sqlite3.connect(DB_FILE, check_same_thread=False)
db.row_factory = sqlite3.Row

db.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    channel_id INTEGER PRIMARY KEY,
    ticket_number INTEGER NOT NULL,
    ticket_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    opener_id INTEGER NOT NULL,
    opened_at TEXT NOT NULL,
    claimed_by INTEGER DEFAULT 0,
    claimed_at TEXT DEFAULT '',
    closed_by INTEGER DEFAULT 0,
    closed_at TEXT DEFAULT '',
    close_reason TEXT DEFAULT '',
    status TEXT DEFAULT 'مفتوح',
    mention_count INTEGER DEFAULT 0
)
""")

db.commit()


# ============================================================
# HELPERS
# ============================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def next_ticket_number():
    row = db.execute(
        "SELECT MAX(ticket_number) AS number FROM tickets"
    ).fetchone()

    if not row or row["number"] is None:
        return 1

    return row["number"] + 1


def get_ticket(channel_id):
    return db.execute(
        "SELECT * FROM tickets WHERE channel_id = ?",
        (channel_id,)
    ).fetchone()


def is_staff(member: discord.Member):
    staff_ids = {
        ADMIN_ROLE_ID,
        OWNER_ROLE_ID,
        COOWNER_ROLE_ID
    }

    return any(role.id in staff_ids for role in member.roles)


def find_member(guild, value):

    value = value.strip()

    if value.isdigit():
        member = guild.get_member(int(value))

        if member:
            return member

    member = guild.get_member_named(value)

    if member:
        return member

    value = value.lower().lstrip("@")

    for member in guild.members:
        if member.name.lower() == value:
            return member

        if member.display_name.lower() == value:
            return member

    return None


# ============================================================
# TICKET EMBED
# ============================================================

def ticket_embed(guild, channel_id):

    ticket = get_ticket(channel_id)

    if not ticket:
        return discord.Embed(
            title="🎫 N9V・TICKET DATA",
            description="لا توجد بيانات للتكت.",
            color=BURGUNDY
        )

    opener = guild.get_member(ticket["opener_id"])
    claimed = (
        guild.get_member(ticket["claimed_by"])
        if ticket["claimed_by"]
        else None
    )
    closed = (
        guild.get_member(ticket["closed_by"])
        if ticket["closed_by"]
        else None
    )

    embed = discord.Embed(
        title="🎫 N9V・TICKET DATA",
        color=BURGUNDY
    )

    embed.description = (
        "═══════════════════════════╗\n"
        "    🎫 **N9V・TICKET DATA**\n"
        "╚════════════════════════════╝"
    )

    embed.add_field(
        name="🆔 رقم التكت",
        value=f"`#{ticket['ticket_number']:04d}`",
        inline=False
    )

    embed.add_field(
        name="📂 نوع التكت",
        value=ticket["ticket_type"],
        inline=False
    )

    embed.add_field(
        name="📝 سبب فتح التكت",
        value=ticket["reason"][:1024],
        inline=False
    )

    embed.add_field(
        name="👤 فاتح التكت",
        value=opener.mention if opener else f"`{ticket['opener_id']}`",
        inline=False
    )

    embed.add_field(
        name="🕐 وقت الفتح",
        value=ticket["opened_at"],
        inline=False
    )

    embed.add_field(
        name="🛡️ الإداري المستلم",
        value=claimed.mention if claimed else "—",
        inline=False
    )

    embed.add_field(
        name="⏱️ وقت الاستلام",
        value=ticket["claimed_at"] or "—",
        inline=False
    )

    embed.add_field(
        name="🔒 الإداري المُغلق",
        value=closed.mention if closed else "—",
        inline=False
    )

    embed.add_field(
        name="🕰️ وقت الإغلاق",
        value=ticket["closed_at"] or "—",
        inline=False
    )

    embed.add_field(
        name="📊 حالة التكت",
        value=ticket["status"],
        inline=False
    )

    embed.add_field(
        name="📌 سبب الإغلاق",
        value=ticket["close_reason"] or "—",
        inline=False
    )

    embed.add_field(
        name="🩸 N9V・SUPPORT",
        value="════════════════════════════",
        inline=False
    )

    return embed


# ============================================================
# CREATE TICKET
# ============================================================

async def create_ticket(interaction, ticket_type, reason):

    guild = interaction.guild

    category = guild.get_channel(TICKET_CATEGORY_ID)

    if not category:

        await interaction.response.send_message(
            "❌ فئة التذاكر غير موجودة.",
            ephemeral=True
        )

        return

    # منع فتح أكثر من تكت
    for channel in category.channels:

        data = get_ticket(channel.id)

        if data and data["opener_id"] == interaction.user.id:

            await interaction.response.send_message(
                f"❌ عندك تكت مفتوح بالفعل: {channel.mention}",
                ephemeral=True
            )

            return

    number = next_ticket_number()

    if ticket_type == "شكوى على إداري":
        prefix = "شكوى"

    elif ticket_type == "شكوى على عضو":
        prefix = "شكوى"

    elif ticket_type == "استفسار":
        prefix = "استفسار"

    else:
        prefix = "دعم"

    channel_name = f"{prefix}・{number:04d}"

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),

        interaction.user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True
        )
    }

    # الإدارة
    for role_id in (
        ADMIN_ROLE_ID,
        OWNER_ROLE_ID,
        COOWNER_ROLE_ID
    ):

        role = guild.get_role(role_id)

        if role:

            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                manage_messages=True
            )

    try:

        channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"N9V Ticket | {ticket_type}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ البوت لا يملك صلاحية إنشاء الرومات.",
            ephemeral=True
        )

        return

    # حفظ البيانات
    db.execute("""
        INSERT INTO tickets (
            channel_id,
            ticket_number,
            ticket_type,
            reason,
            opener_id,
            opened_at,
            status,
            mention_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        channel.id,
        number,
        ticket_type,
        reason,
        interaction.user.id,
        now(),
        "مفتوح",
        0
    ))

    db.commit()

    await interaction.response.send_message(
        f"🎫 تم فتح تذكرتك: {channel.mention}",
        ephemeral=True
    )

    # ========================================================
    # منشن الإدارة تلقائياً
    # ========================================================

    mentions = []

    for role_id in (
        ADMIN_ROLE_ID,
        OWNER_ROLE_ID,
        COOWNER_ROLE_ID
    ):

        role = guild.get_role(role_id)

        if role:
            mentions.append(role.mention)

    if mentions:

        await channel.send(
            "📢 **تكت جديد يحتاج إلى الدعم**\n"
            + " ".join(mentions),
            allowed_mentions=discord.AllowedMentions(
                roles=True
            )
        )

    # ========================================================
    # رسالة التكت
    # ========================================================

    await channel.send(
        content=(
            f"أهلًا {interaction.user.mention} 👋\n\n"
            "تم فتح تذكرتك بنجاح.\n"
            "يرجى الانتظار حتى يتم استلام التكت من الإدارة.\n\n"
            "📌 **ملاحظة:**\n"
            "إذا كانت الشكوى تحتاج إلى دليل، أرسل الدليل داخل التكت."
        ),
        embed=ticket_embed(guild, channel.id),
        view=TicketControls()
    )


# ============================================================
# SUPPORT MODAL
# ============================================================

class SupportModal(discord.ui.Modal, title="🛠️ دعم فني"):

    problem = discord.ui.TextInput(
        label="ما هي مشكلتك؟",
        placeholder="اكتب مشكلتك هنا...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500
    )

    async def on_submit(self, interaction):

        await create_ticket(
            interaction,
            "دعم فني",
            self.problem.value
        )


# ============================================================
# COMPLAINT MODAL
# ============================================================

class ComplaintModal(discord.ui.Modal):

    def __init__(self, target_type):

        self.target_type = target_type

        super().__init__(
            title=f"⚠️ شكوى على {target_type}"
        )

        self.target = discord.ui.TextInput(
            label=f"يوزر {target_type}",
            placeholder="اكتب اليوزر أو ID",
            required=True,
            max_length=100
        )

        self.reason = discord.ui.TextInput(
            label="سبب الشكوى",
            placeholder="اكتب سبب الشكوى...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.add_item(self.target)
        self.add_item(self.reason)

    async def on_submit(self, interaction):

        reason = (
            f"👤 **{self.target_type}:** "
            f"{self.target.value}\n\n"
            f"📝 **سبب الشكوى:**\n"
            f"{self.reason.value}\n\n"
            "📎 **الدليل:**\n"
            "أرسل الدليل داخل التكت."
        )

        await create_ticket(
            interaction,
            f"شكوى على {self.target_type}",
            reason
        )


# ============================================================
# CLOSE MODAL
# ============================================================

class CloseModal(discord.ui.Modal, title="🔒 إغلاق التكت"):

    solved = discord.ui.TextInput(
        label="هل تم حل المشكلة؟",
        placeholder="نعم / لا",
        required=True,
        max_length=30
    )

    reason = discord.ui.TextInput(
        label="سبب الإغلاق",
        placeholder="اكتب سبب الإغلاق...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ مانت أدمن، روح نام 😴",
                ephemeral=True
            )

            return

        ticket = get_ticket(interaction.channel.id)

        if not ticket:

            await interaction.response.send_message(
                "❌ بيانات التكت غير موجودة.",
                ephemeral=True
            )

            return

        if ticket["status"] == "مغلق":

            await interaction.response.send_message(
                "❌ التكت يتم إغلاقه بالفعل.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🔒 بدأ إغلاق التكت.\n"
            "سيتم الإغلاق خلال **15 ثانية**.",
            ephemeral=True
        )

        await asyncio.sleep(15)

        # تحديث البيانات
        db.execute("""
            UPDATE tickets
            SET closed_by = ?,
                closed_at = ?,
                close_reason = ?,
                status = ?
            WHERE channel_id = ?
        """, (
            interaction.user.id,
            now(),
            f"حل المشكلة: {self.solved.value}\n"
            f"سبب الإغلاق: {self.reason.value}",
            "مغلق",
            interaction.channel.id
        ))

        db.commit()

        ticket = get_ticket(
            interaction.channel.id
        )

        # ====================================================
        # التقييم
        # ====================================================

        if ticket and ticket["claimed_by"]:

            opener = interaction.guild.get_member(
                ticket["opener_id"]
            )

            if opener:

                try:

                    await opener.send(
                        embed=discord.Embed(
                            title="⭐ N9V・تقييم التكت",
                            description=(
                                f"تم إغلاق تذكرتك "
                                f"`#{ticket['ticket_number']:04d}`.\n\n"
                                "قيّم الإداري الذي استلم تذكرتك:"
                            ),
                            color=BURGUNDY
                        ),
                        view=RatingView(
                            interaction.guild.id,
                            ticket["claimed_by"],
                            ticket["ticket_number"]
                        )
                    )

                except discord.Forbidden:
                    pass

        # ====================================================
        # إرسال نسخة التكت
        # ====================================================

        await send_transcript(
           
