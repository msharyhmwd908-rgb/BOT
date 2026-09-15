import discord
from discord.ext import commands
import sqlite3
import io
from datetime import datetime

# =========================
# CONFIG
# =========================

CREATOR_ID = 1495450684731162664

CATEGORY_ID = 1548014683695620116
PANEL_CHANNEL_ID = 1548014911932858398
LOG_CHANNEL_ID = 1495450684731162664

STAFF_ROLES = [
    1498008105819177240,
    1497718287956443249,
    1497608751551746179
]

COLOR = discord.Color.from_rgb(100, 0, 20)

# =========================
# DATABASE
# =========================

db = sqlite3.connect("tickets.db", check_same_thread=False)

db.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    channel_id INTEGER PRIMARY KEY,
    number INTEGER,
    type TEXT,
    reason TEXT,
    opener INTEGER,
    opened TEXT,
    claimed INTEGER DEFAULT 0,
    claimed_at TEXT DEFAULT '',
    closed INTEGER DEFAULT 0,
    closed_at TEXT DEFAULT '',
    close_reason TEXT DEFAULT ''
)
""")

db.commit()


def time_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def staff(member):
    return any(r.id in STAFF_ROLES for r in member.roles)


def get_ticket(channel_id):
    return db.execute(
        "SELECT * FROM tickets WHERE channel_id=?",
        (channel_id,)
    ).fetchone()


def next_number():
    x = db.execute(
        "SELECT MAX(number) FROM tickets"
    ).fetchone()[0]

    return (x or 0) + 1


# =========================
# TICKET INFO
# =========================

def info_embed(guild, channel_id):

    t = get_ticket(channel_id)

    if not t:
        return discord.Embed(
            title="🎫 N9V・TICKET",
            description="لا توجد بيانات.",
            color=COLOR
        )

    opener = guild.get_member(t[4])
    claimed = guild.get_member(t[6]) if t[6] else None
    closed = guild.get_member(t[8]) if t[8] else None

    e = discord.Embed(
        title="🎫 N9V・TICKET DATA",
        color=COLOR
    )

    fields = [
        ("🆔 رقم التكت", f"`#{t[1]:04d}`"),
        ("📂 نوع التكت", t[2]),
        ("📝 سبب الفتح", t[3][:1024]),
        ("👤 صاحب التكت", opener.mention if opener else str(t[4])),
        ("🕐 وقت الفتح", t[5]),
        ("🛡️ الإداري المستلم", claimed.mention if claimed else "—"),
        ("⏱️ وقت الاستلام", t[7] or "—"),
        ("🔒 الإداري المُغلق", closed.mention if closed else "—"),
        ("🕰️ وقت الإغلاق", t[9] or "—"),
        ("📊 الحالة", "مغلق" if t[8] else "مفتوح"),
        ("📌 سبب الإغلاق", t[10] or "—")
    ]

    for name, value in fields:
        e.add_field(
            name=name,
            value=value,
            inline=False
        )

    e.set_footer(text="N9V・SUPPORT")
    return e


# =========================
# CREATE TICKET
# =========================

async def create_ticket(interaction, ticket_type, reason):

    guild = interaction.guild
    category = guild.get_channel(CATEGORY_ID)

    if not category:
        return await interaction.response.send_message(
            "❌ كاتيجوري التكت غير موجود.",
            ephemeral=True
        )

    for ch in category.channels:

        t = get_ticket(ch.id)

        if t and t[4] == interaction.user.id and not t[8]:
            return await interaction.response.send_message(
                f"❌ عندك تكت مفتوح بالفعل: {ch.mention}",
                ephemeral=True
            )

    number = next_number()

    prefix = {
        "دعم فني": "دعم",
        "استفسار": "استفسار",
        "شكوى": "شكوى"
    }.get(ticket_type, "تكت")

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

    for rid in STAFF_ROLES:

        role = guild.get_role(rid)

        if role:

            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                manage_messages=True
            )

    channel = await guild.create_text_channel(
        f"{prefix}・{number:04d}",
        category=category,
        overwrites=overwrites
    )

    db.execute("""
        INSERT INTO tickets
        (channel_id,number,type,reason,opener,opened)
        VALUES (?,?,?,?,?,?)
    """, (
        channel.id,
        number,
        ticket_type,
        reason,
        interaction.user.id,
        time_now()
    ))

    db.commit()

    await interaction.response.send_message(
        f"🎫 تم فتح تذكرتك: {channel.mention}",
        ephemeral=True
    )

    roles = [
        guild.get_role(rid).mention
        for rid in STAFF_ROLES
        if guild.get_role(rid)
    ]

    if roles:

        await channel.send(
            "📢 **تكت جديد يحتاج إلى الدعم**\n" +
            " ".join(roles),
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

    await channel.send(
        f"أهلًا {interaction.user.mention} 👋\n"
        "تم فتح تذكرتك بنجاح، يرجى الانتظار حتى يتم استلامها.",
        embed=info_embed(guild, channel.id),
        view=TicketControls()
    )


# =========================
# MODALS
# =========================

class SupportModal(discord.ui.Modal, title="🛠️ دعم فني"):

    reason = discord.ui.TextInput(
        label="وش مشكلتك؟",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction):

        await create_ticket(
            interaction,
            "دعم فني",
            self.reason.value
        )


class InquiryModal(discord.ui.Modal, title="❓ استفسار"):

    reason = discord.ui.TextInput(
        label="وش استفسارك؟",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction):

        await create_ticket(
            interaction,
            "استفسار",
            self.reason.value
        )


class ComplaintModal(discord.ui.Modal, title="⚠️ شكوى"):

    target = discord.ui.TextInput(
        label="الشخص المشتكى عليه",
        placeholder="ID أو Username",
        max_length=100
    )

    reason = discord.ui.TextInput(
        label="سبب الشكوى",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction):

        text = (
            f"👤 المشتكى عليه: {self.target.value}\n\n"
            f"📝 السبب:\n{self.reason.value}"
        )

        await create_ticket(
            interaction,
            "شكوى",
            text
        )


class CloseModal(discord.ui.Modal, title="🔒 إغلاق التكت"):

    reason = discord.ui.TextInput(
        label="سبب الإغلاق",
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    async def on_submit(self, interaction):

        if not staff(interaction.user) and interaction.user.id != CREATOR_ID:

            return await interaction.response.send_message(
                "❌ هذا الإجراء للإدارة فقط.",
                ephemeral=True
            )

        t = get_ticket(interaction.channel.id)

        if not t or t[8]:

            return await interaction.response.send_message(
                "❌ التكت مغلق بالفعل.",
                ephemeral=True
            )

        db.execute("""
            UPDATE tickets
            SET closed=?, closed_at=?, close_reason=?
            WHERE channel_id=?
        """, (
            interaction.user.id,
            time_now(),
            self.reason.value,
            interaction.channel.id
        ))

        db.commit()

        await interaction.response.send_message(
            "🔒 جاري إغلاق التكت وحفظ النسخة..."
        )

        await send_transcript(
            interaction.guild,
            interaction.channel
        )

        await interaction.channel.delete()


class MemberModal(discord.ui.Modal):

    def __init__(self, remove=False):

        self.remove = remove

        super().__init__(
            title="➖ إزالة عضو" if remove else "➕ إضافة عضو"
        )

        self.user = discord.ui.TextInput(
            label="ID العضو",
            max_length=100
        )

        self.add_item(self.user)

    async def on_submit(self, interaction):

        if not staff(interaction.user) and interaction.user.id != CREATOR_ID:

            return await interaction.response.send_message(
                "❌ هذا الإجراء للإدارة فقط.",
                ephemeral=True
            )

        member = None

        if self.user.value.isdigit():

            member = interaction.guild.get_member(
                int(self.user.value)
            )

        if not member:

            return await interaction.response.send_message(
                "❌ ما لقيت العضو.",
                ephemeral=True
            )

        if self.remove:

            await interaction.channel.set_permissions(
                member,
                overwrite=None
            )

            msg = f"✅ تمت إزالة {member.mention}."

        else:

            await interaction.channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

            msg = f"✅ تمت إضافة {member.mention}."

        await interaction.response.send_message(msg)


# =========================
# TICKET CONTROLS
# =========================

class TicketControls(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

    @discord.ui.button(
        label="استلام",
        emoji="🛡️",
        style=discord.ButtonStyle.success,
        custom_id="n9v_claim"
    )
    async def claim(self, interaction, button):

        if not staff(interaction.user) and interaction.user.id != CREATOR_ID:

            return await interaction.response.send_message(
                "❌ هذا الإجراء للإدارة فقط.",
                ephemeral=True
            )

        t = get_ticket(interaction.channel.id)

        if not t:

            return await interaction.response.send_message(
                "❌ هذا ليس تكت.",
                ephemeral=True
            )

        if t[6]:

            return await interaction.response.send_message(
                "❌ هذا التكت مستلم بالفعل.",
                ephemeral=True
            )

        db.execute("""
            UPDATE tickets
            SET claimed=?, claimed_at=?
            WHERE channel_id=?
        """, (
            interaction.user.id,
            time_now(),
            interaction.channel.id
        ))

        db.commit()

        await interaction.response.edit_message(
            embed=info_embed(
                interaction.guild,
                interaction.channel.id
            ),
            view=self
        )

        await interaction.channel.send(
            f"🛡️ تم استلام التكت بواسطة {interaction.user.mention}."
        )

    @discord.ui.button(
        label="إغلاق",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="n9v_close"
    )
    async def close(self, interaction, button):

        await interaction.response.send_modal(
            CloseModal()
        )

    @discord.ui.button(
        label="تنبيه الإدارة",
        emoji="📢",
        style=discord.ButtonStyle.primary,
        custom_id="n9v_notify"
    )
    async def notify(self, interaction, button):

        roles = [
            interaction.guild.get_role(rid).mention
            for rid in STAFF_ROLES
            if interaction.guild.get_role(rid)
        ]

        await interaction.response.send_message(
            "📢 **تم تنبيه الإدارة**\n" +
            " ".join(roles),
            allowed_mentions=discord.AllowedMentions(roles=True)
        )

    @discord.ui.button(
        label="إضافة عضو",
        emoji="➕",
        style=discord.ButtonStyle.secondary,
        custom_id="n9v_add"
    )
    async def add(self, interaction, button):

        await interaction.response.send_modal(
            MemberModal(False)
        )

    @discord.ui.button(
        label="إزالة عضو",
        emoji="➖",
        style=discord.ButtonStyle.secondary,
        custom_id="n9v_remove"
    )
    async def remove(self, interaction, button):

        await interaction.response.send_modal(
            MemberModal(True)
        )


# =========================
# PANEL
# =========================

class TicketPanel(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

    @discord.ui.button(
        label="دعم فني",
        emoji="🛠️",
        style=discord.ButtonStyle.secondary,
        custom_id="n9v_support"
    )
    async def support(self, interaction, button):

        await interaction.response.send_modal(
            SupportModal()
        )

    @discord.ui.button(
        label="استفسار",
        emoji="❓",
        style=discord.ButtonStyle.secondary,
        custom_id="n9v_inquiry"
    )
    async def inquiry(self, interaction, button):

        await interaction.response.send_modal(
            InquiryModal()
        )

    @discord.ui.button(
        label="شكوى",
        emoji="⚠️",
        style=discord.ButtonStyle.danger,
        custom_id="n9v_complaint"
    )
    async def complaint(self, interaction, button):

        await interaction.response.send_modal(
            ComplaintModal()
        )


# =========================
# TRANSCRIPT
# =========================

async def send_transcript(guild, channel):

    log = guild.get_channel(LOG_CHANNEL_ID)

    if not log:
        return

    lines = []

    async for msg in channel.history(
        limit=None,
        oldest_first=True
    ):

        content = msg.content or "[بدون نص]"

        if msg.attachments:

            content += "\n" + "\n".join(
                a.url for a in msg.attachments
            )

        lines.append(
            f"[{msg.created_at:%Y-%m-%d %H:%M:%S}] "
            f"{msg.author} ({msg.author.id}): {content}"
        )

    t = get_ticket(channel.id)

    number = t[1] if t else 0

    text = (
        "N9V TICKET TRANSCRIPT\n"
        "=====================\n\n"
        f"Server: {guild.name}\n"
        f"Ticket: #{number:04d}\n"
        f"Channel: {channel.name}\n\n"
        + "\n".join(lines)
    )

    file = discord.File(
        io.BytesIO(text.encode("utf-8")),
        filename=f"ticket-{number:04d}.txt"
    )

    await log.send(
        embed=info_embed(guild, channel.id),
        file=file
    )


# =========================
# COG
# =========================

class Tickets(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    async def cog_load(self):

        self.bot.add_view(TicketPanel())
        self.bot.add_view(TicketControls())

    @discord.app_commands.command(
        name="setup-ticket",
        description="إرسال لوحة التكت"
    )
    async def setup_ticket(self, interaction):

        if (
            interaction.user.id != CREATOR_ID
            and not interaction.user.guild_permissions.administrator
        ):

            return await interaction.response.send_message(
                "❌ هذا الأمر مخصص للإدارة فقط.",
                ephemeral=True
            )

        channel = interaction.guild.get_channel(
            PANEL_CHANNEL_ID
        )

        if not channel:

            return await interaction.response.send_message(
                "❌ روم لوحة التكت غير موجود.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="🎫 N9V・TICKET",
            description=(
                "════════════════════\n\n"
                "🩸 **دعم السيرفر**\n\n"
                "اختر نوع التكت المناسب لك:\n\n"
                "🛠️ دعم فني\n"
                "❓ استفسار\n"
                "⚠️ شكوى\n\n"
                "════════════════════"
            ),
            color=COLOR
        )

        embed.set_footer(
            text="N9V・SUPPORT SYSTEM"
        )

        await channel.send(
            embed=embed,
            view=TicketPanel()
        )

        await interaction.response.send_message(
            f"✅ تم إرسال اللوحة في {channel.mention}",
            ephemeral=True
        )


# =========================
# SETUP
# =========================

async def setup(bot):

    await bot.add_cog(Tickets(bot))
