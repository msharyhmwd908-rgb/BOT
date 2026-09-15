# cogs/tickets.py
# N9V Ticket System
# discord.py 2.x

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import asyncio
import io
from datetime import datetime


# ============================================================
# CONFIG
# ============================================================

TICKET_CATEGORY_ID = 1548014683695620116
PANEL_CHANNEL_ID = 1548014911932858398
LOG_CHANNEL_ID = 1495450684731162664

ADMIN_ROLE_ID = 1498008105819177240
OWNER_ROLE_ID = 1497718287956443249
COOWNER_ROLE_ID = 1497608751551746179

PANEL_IMAGE = "https://a.top4top.io/p_3910nb9nm0.png"

DB_FILE = "tickets.db"

BURGUNDY = discord.Color.from_rgb(105, 0, 20)


# ============================================================
# DATABASE
# ============================================================

db = sqlite3.connect(DB_FILE, check_same_thread=False)
db.row_factory = sqlite3.Row

cursor = db.cursor()

cursor.execute("""
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


# لو عندك قاعدة بيانات قديمة
try:
    cursor.execute(
        "ALTER TABLE tickets ADD COLUMN mention_count INTEGER DEFAULT 0"
    )
    db.commit()
except sqlite3.OperationalError:
    pass


def current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_next_ticket_number():
    cursor.execute(
        "SELECT MAX(ticket_number) AS max_number FROM tickets"
    )

    row = cursor.fetchone()

    if row is None or row["max_number"] is None:
        return 1

    return row["max_number"] + 1


def get_ticket(channel_id):
    cursor.execute(
        "SELECT * FROM tickets WHERE channel_id = ?",
        (channel_id,)
    )

    return cursor.fetchone()


def is_staff(member: discord.Member):
    staff_roles = {
        ADMIN_ROLE_ID,
        OWNER_ROLE_ID,
        COOWNER_ROLE_ID
    }

    return any(role.id in staff_roles for role in member.roles)


def find_member(guild: discord.Guild, value: str):

    value = value.strip()

    # ID
    if value.isdigit():
        member = guild.get_member(int(value))

        if member:
            return member

    # username / display name
    member = guild.get_member_named(value)

    if member:
        return member

    clean = value.lower().lstrip("@")

    for member in guild.members:

        if member.name.lower() == clean:
            return member

        if member.display_name.lower() == clean:
            return member

        if str(member).lower() == clean:
            return member

    return None


# ============================================================
# TICKET DATA EMBED
# ============================================================

def build_ticket_embed(guild: discord.Guild, channel_id: int):

    ticket = get_ticket(channel_id)

    if not ticket:

        return discord.Embed(
            title="🎫 N9V・TICKET DATA",
            description="لا توجد بيانات للتكت.",
            color=BURGUNDY
        )

    opener = guild.get_member(ticket["opener_id"])

    claimer = None

    if ticket["claimed_by"]:
        claimer = guild.get_member(ticket["claimed_by"])

    closer = None

    if ticket["closed_by"]:
        closer = guild.get_member(ticket["closed_by"])

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
        value=claimer.mention if claimer else "—",
        inline=False
    )

    embed.add_field(
        name="⏱️ وقت الاستلام",
        value=ticket["claimed_at"] or "—",
        inline=False
    )

    embed.add_field(
        name="🔒 الإداري المُغلق",
        value=closer.mention if closer else "—",
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

async def create_ticket(
    interaction: discord.Interaction,
    ticket_type: str,
    reason: str
):

    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ لا يمكن فتح تكت هنا.",
            ephemeral=True
        )
        return

    category = guild.get_channel(TICKET_CATEGORY_ID)

    if category is None:
        await interaction.response.send_message(
            "❌ فئة التذاكر غير موجودة.",
            ephemeral=True
        )
        return

    # منع أكثر من تكت
    for channel in category.channels:

        ticket = get_ticket(channel.id)

        if ticket and ticket["opener_id"] == interaction.user.id:
            await interaction.response.send_message(
                f"❌ عندك تكت مفتوح بالفعل: {channel.mention}",
                ephemeral=True
            )
            return

    number = get_next_ticket_number()

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

    # صلاحيات الإدارة
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
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"N9V Ticket - {ticket_type}"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ البوت ما عنده صلاحية إنشاء الرومات.",
            ephemeral=True
        )

        return

    # حفظ البيانات
    cursor.execute("""
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
        current_time(),
        "مفتوح",
        0
    ))

    db.commit()

    await interaction.response.send_message(
        f"🎫 تم فتح تذكرتك: {channel.mention}",
        ephemeral=True
    )

    # ========================================================
    # منشن الإدارة عند فتح التكت
    # ========================================================

    role_mentions = []

    for role_id in (
        ADMIN_ROLE_ID,
        OWNER_ROLE_ID,
        COOWNER_ROLE_ID
    ):

        role = guild.get_role(role_id)

        if role:
            role_mentions.append(role.mention)

    if role_mentions:

        await channel.send(
            "📢 **تكت جديد يحتاج إلى الدعم**\n"
            + " ".join(role_mentions),
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
            "يرجى الانتظار حتى يتم استلام التكت من أحد الإداريين.\n\n"
            "📌 **ملاحظة:**\n"
            "إذا كانت شكواك تحتاج إلى دليل، أرسل الدليل داخل التكت."
        ),
        embed=build_ticket_embed(
            guild,
            channel.id
        ),
        view=TicketControls()
    )


# ============================================================
# SUPPORT MODAL
# ============================================================

class SupportModal(discord.ui.Modal, title="🛠️ دعم فني"):

    problem = discord.ui.TextInput(
        label="ما هي مشكلتك؟",
        placeholder="اكتب مشكلتك بالتفصيل...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500
    )

    async def on_submit(self, interaction: discord.Interaction):

        await create_ticket(
            interaction,
            "دعم فني",
            self.problem.value
        )


# ============================================================
# COMPLAINT MODAL
# ============================================================

class ComplaintModal(discord.ui.Modal):

    def __init__(self, complaint_type):

        self.complaint_type = complaint_type

        super().__init__(
            title=f"⚠️ شكوى على {complaint_type}"
        )

        self.target = discord.ui.TextInput(
            label=f"يوزر {complaint_type}",
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

    async def on_submit(self, interaction: discord.Interaction):

        reason = (
            f"👤 **{self.complaint_type}:** "
            f"{self.target.value}\n\n"
            f"📝 **سبب الشكوى:**\n"
            f"{self.reason.value}\n\n"
            "📎 **الدليل:**\n"
            "يرجى إرسال الدليل داخل التكت."
        )

        await create_ticket(
            interaction,
            f"شكوى على {self.complaint_type}",
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
        label="سبب إغلاق التكت",
        placeholder="اكتب سبب الإغلاق...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):

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
            "🔒 **تم بدء إغلاق التكت.**\n"
            "سيتم إغلاقه خلال **15 ثانية**.",
            ephemeral=True
        )

        # إظهار عد تنازلي بسيط
        for remaining in (10, 5, 3, 2, 1):

            try:

                await interaction.channel.send(
                    f"🔒 إغلاق التكت بعد **{remaining}**..."
                )

            except discord.HTTPException:
                pass

            await asyncio.sleep(
                1 if remaining <= 5 else 5
            )

        # ====================================================
        # تحديث قاعدة البيانات
        # ====================================================

        cursor.execute("""
            UPDATE tickets
            SET closed_by = ?,
                closed_at = ?,
                close_reason = ?,
                status = ?
            WHERE channel_id = ?
        """, (
            interaction.user.id,
            current_time(),
            (
                f"{self.solved.value}\n"
                f"{self.reason.value}"
            ),
            "مغلق",
            interaction.channel.id
        ))

        db.commit()

        # ====================================================
        # Transcript
        # ====================================================

        await send_transcript(
            interaction.channel
        )

        # ====================================================
        # التقييم
        # ====================================================

        ticket = get_ticket(
            interaction.channel.id
        )

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
                                "نرجو تقييم الإداري الذي خدمك.\n"
                                "اختر من ⭐ إلى ⭐⭐⭐⭐⭐⭐."
                            ),
                            color=BURGUNDY
                        ),
                        view=RatingView(
                            guild_id=interaction.guild.id,
                            staff_id=ticket["claimed_by"],
                            ticket_number=ticket["ticket_number"],
                            ticket_channel_id=interaction.channel.id
                        )
                    )

                except discord.Forbidden:
                    pass

        await asyncio.sleep(2)

        try:

            await interaction.channel.delete(
                reason="N9V Ticket Closed"
            )

        except discord.HTTPException:
            pass


# ============================================================
# ADD MEMBER MODAL
# ============================================================

class AddMemberModal(discord.ui.Modal, title="➕ إضافة عضو"):

    member_input = discord.ui.TextInput(
        label="ID أو يوزر العضو",
        placeholder="ضع ID أو اليوزر هنا",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ مانت أدمن، روح نام 😴",
                ephemeral=True
            )

            return

        member = find_member(
            interaction.guild,
            self.member_input.value
        )

        if not member:

            await interaction.response.send_message(
                "❌ ما لقيت العضو.",
                ephemeral=True
            )

            return

        try:

            await interaction.channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            )

            await interaction.response.send_message(
                f"✅ تم إضافة {member.mention} للتكت."
            )

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ حصل خطأ أثناء إضافة العضو.",
                ephemeral=True
            )


# ============================================================
# REMOVE MEMBER MODAL
# ============================================================

class RemoveMemberModal(discord.ui.Modal, title="🚫 طرد عضو"):

    member_input = discord.ui.TextInput(
        label="ID أو يوزر العضو",
        placeholder="ضع ID أو اليوزر هنا",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ مانت أدمن، روح نام 😴",
                ephemeral=True
            )

            return

        member = find_member(
            interaction.guild,
            self.member_input.value
        )

        if not member:

            await interaction.response.send_message(
                "❌ ما لقيت العضو.",
                ephemeral=True
            )

            return

        # لا نطرد صاحب التكت أو الإدارة بالخطأ
        ticket = get_ticket(
            interaction.channel.id
        )

        if ticket:

            if member.id == ticket["opener_id"]:

                await interaction.response.send_message(
                    "❌ ما تقدر تطرد صاحب التكت.",
                    ephemeral=True
                )

                return

        if is_staff(member):

            await interaction.response.send_message(
                "❌ ما تقدر تطرد إداري من التكت.",
                ephemeral=True
            )

            return

        try:

            await interaction.channel.set_permissions(
                member,
                overwrite=None
            )

            await interaction.response.send_message(
                f"🚫 تم طرد {member.mention} من التكت."
            )

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ حصل خطأ أثناء طرد العضو.",
                ephemeral=True
            )


# ============================================================
# RATING REASON MODAL
# ============================================================

class RatingReasonModal(discord.ui.Modal):

    def __init__(
        self,
        guild_id,
        staff_id,
        stars,
        ticket_number,
        ticket_channel_id
    ):

        super().__init__(
            title="⭐ سبب التقييم"
        )

        self.guild_id = guild_id
        self.staff_id = staff_id
        self.stars = stars
        self.ticket_number = ticket_number
        self.ticket_channel_id = ticket_channel_id

        self.reason = discord.ui.TextInput(
            label="سبب التقييم",
            placeholder="اكتب سبب تقييمك للإداري...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):

        guild = interaction.client.get_guild(
            self.guild_id
        )

        if not guild:

            await interaction.response.send_message(
                "❌ تعذر الوصول للسيرفر.",
                ephemeral=True
            )

            return

        staff = guild.get_member(
            self.staff_id
        )

        log_channel = guild.get_channel(
            LOG_CHANNEL_ID
        )

        embed = discord.Embed(
            title="⭐ N9V・TICKET RATING",
            color=BURGUNDY,
            timestamp=datetime.now()
        )

        embed.add_field(
            name="👤 العضو",
            value=(
                f"{interaction.user.mention}\n"
                f"`{interaction.user.id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ الإداري",
            value=(
                staff.mention
                if staff
                else f"`{self.staff_id}`"
            ),
            inline=False
        )

        embed.add_field(
            name="⭐ التقييم",
            value=f"{'⭐' * self.stars}",
            inline=False
        )

        embed.add_field(
            name="📝 سبب التقييم",
            value=self.reason.value,
            inline=False
        )

        embed.add_field(
            name="🎫 رقم التكت",
            value=f"`#{self.ticket_number:04d}`",
            inline=False
        )

        if log_channel:

            await log_channel.send(
                embed=embed
            )

            # إرسال نسخة التكت إذا كانت القناة ما زالت موجودة
            ticket_channel = guild.get_channel(
                self.ticket_channel_id
            )

            if ticket_channel:

                await send_transcript(
                    ticket_channel
                )

        await interaction.response.send_message(
            "✅ تم إرسال تقييمك بنجاح، شكرًا لك.",
            ephemeral=True
        )


# ============================================================
# RATING VIEW
# ============================================================

class RatingView(discord.ui.View):

    def __init__(
        self,
        guild_id,
        staff_id,
        ticket_number,
        ticket_channel_id
    ):

        super().__init__(
            timeout=86400
        )

        self.guild_id = guild_id
        self.staff_id = staff_id
        self.ticket_number = ticket_number
        self.ticket_channel_id = ticket_channel_id

        for stars in range(1, 7):

            button = discord.ui.Button(
                label=f"{stars} ⭐",
                style=discord.ButtonStyle.danger,
                custom_id=f"n9v_rating_{stars}"
            )

            button.callback = self.make_callback(
                stars
            )

            self.add_item(button)

    def make_callback(self, stars):

        async def callback(
            interaction: discord.Interaction
        ):

            await interaction.response.send_modal(
                RatingReasonModal(
                    guild_id=self.guild_id,
                    staff_id=self.staff_id,
                    stars=stars,
                    ticket_number=self.ticket_number,
                    ticket_channel_id=self.ticket_channel_id
                )
            )

        return callback


# ============================================================
# TICKET CONTROLS
# ============================================================

class TicketControls(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    # --------------------------------------------------------
    # CLAIM
    # --------------------------------------------------------

    @discord.ui.button(
        label="「 استلام التكت 」",
        emoji="🩸",
        style=discord.ButtonStyle.danger,
        custom_id="n9v_ticket_claim"
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ مانت أدمن، روح نام 😴",
                ephemeral=True
            )

            return

        ticket = get_ticket(
            interaction.channel.id
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ بيانات التكت غير موجودة.",
                ephemeral=True
            )

            return

        if ticket["claimed_by"]:

            await interaction.response.send_message(
                "❌ هذا التكت مستلم بالفعل.",
                ephemeral=True
            )

            # رسالة خاصة للإداري
            try:

                await interaction.user.send(
                    f"❌ التكت **{interaction.channel.name}** "
                    "مستلم بالفعل من إداري آخر."
                )

            except discord.Forbidden:
                pass

            return

        cursor.execute("""
            UPDATE tickets
            SET claimed_by = ?,
                claimed_at = ?
            WHERE channel_id = ?
        """, (
            interaction.user.id,
            current_time(),
            interaction.channel.id
        ))

        db.commit()

        await interaction.response.send_message(
            f"🛡️ تم استلام التكت بواسطة "
            f"{interaction.user.mention}."
        )

        # تحديث معلومات التكت
        try:

            await interaction.message.edit(
                embed=build_ticket_embed(
                    interaction.guild,
                    interaction.channel.id
                )
            )

        except discord.HTTPException:
            pass

    # --------------------------------------------------------
    # CLOSE
    # --------------------------------------------------------

    @discord.ui.button(
        label="「 إغلاق التكت 」",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="n9v_ticket_close"
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ مانت أدمن، روح نام 😴",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            CloseModal()
        )

    # --------------------------------------------------------
    # MENTION STAFF
    # --------------------------------------------------------

    @discord.ui.button(
        label="「 منشن الإدارة 」",
        emoji="📢",
        style=discord.ButtonStyle.danger,
        custom_id="n9v_ticket_mention"
    )
    async def mention(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        ticket = get_ticket(
            interaction.channel.id
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ بيانات التكت غير موجودة.",
                ephemeral=True
            )

            return

        if ticket["mention_count"] >= 3:

            await interaction.response.send_message(
                "❌ استنفدت **3 محاولات** لمنشن الإدارة.",
                ephemeral=True
            )

            return

        new_count = ticket["mention_count"] + 1

        cursor.execute("""
            UPDATE tickets
            SET mention_count = ?
            WHERE channel_id = ?
        """, (
            new_count,
            interaction.channel.id
        ))

        db.commit()

        mentions = []

        for role_id in (
            ADMIN_ROLE_ID,
            OWNER_ROLE_ID,
            COOWNER_ROLE_ID
        ):

            role = interaction.guild.get_role(
                role_id
            )

            if role:
                mentions.append(
                    role.mention
                )

        await interaction.response.send_message(
            (
                "📢 **تنبيه للإدارة**\n"
                + " ".join(mentions)
                + f"\n\n`المحاولة {new_count}/3`"
            ),
            allowed_mentions=discord.AllowedMentions(
                roles=True
            )
        )

    # --------------------------------------------------------
    # ADD MEMBER
    # --------------------------------------------------------

    @discord.ui.button(
        label="「 إضافة عضو 」",
        emoji="➕",
        style=discord.ButtonStyle.danger,
        custom_id="n9v_ticket_add"
    )
    async def add_member(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ مانت أدمن، روح نام 😴",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            AddMemberModal()
        )

    # --------------------------------------------------------
    # REMOVE MEMBER
    # --------------------------------------------------------

    @discord.ui.button(
        label="「 طرد من التكت 」",
        emoji="🚫",
        style=discord.ButtonStyle.danger,
        custom_id="n9v_ticket_remove"
    )
    async def remove_member(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ مانت أدمن، روح نام 😴",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            RemoveMemberModal()
        )


# ============================================================
# TICKET PANEL
# ============================================================

class TicketPanel(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    # --------------------------------------------------------
    # SUPPORT
    # --------------------------------------------------------

    @discord.ui.button(
        label="「 دعم فني 」",
        emoji="🛠️",
        style=discord.ButtonStyle.danger,
        custom_id="n9v_panel_support"
    )
    async def support(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            SupportModal()
        )

    # --------------------------------------------------------
    # QUESTION
    # --------------------------------------------------------

    @discord.ui.button(
        label="「 استفسار 」",
        emoji="❓",
        style=discord.ButtonStyle.danger,
        custom_id="n9v_panel_question"
    )
    async def question(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await create_ticket(
            interaction,
            "استفسار",
            "استفسار عام"
        )

    # --------------------------------------------------------
    # STAFF COMPLAINT
    # --------------------------------------------------------

    @discord.ui.button(
        label="「 شكوى على إداري 」",
        emoji="🛡️",
        style=discord.ButtonStyle.danger,
        custom_id="n9v_panel_staff_complaint"
    )
    async def staff_complaint(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            ComplaintModal("إداري")
        )

    # --------------------------------------------------------
    # MEMBER COMPLAINT
    # --------------------------------------------------------

    @discord.ui.button(
        label="「 شكوى على عضو 」",
        emoji="⚠️",
        style=discord.ButtonStyle.danger,
        custom_id="n9v_panel_member_complaint"
    )
    async def member_complaint(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            ComplaintModal("عضو")
        )


# ============================================================
# TRANSCRIPT
# ============================================================

async def send_transcript(channel: discord.TextChannel):

    log_channel = channel.guild.get_channel(
        LOG_CHANNEL_ID
    )

    if not log_channel:
        return

    ticket = get_ticket(
        channel.id
    )

    lines = []

    lines.append(
        "════════════════════════════════════════\n"
        "        N9V・TICKET TRANSCRIPT\n"
        "════════════════════════════════════════\n"
    )

    lines.append(
        f"Ticket: {channel.name}\n"
        f"Channel ID: {channel.id}\n"
        f"════════════════════════════════════════\n"
    )

    try:

        async for message in channel.history(
            limit=None,
            oldest_first=True
        ):

            timestamp = message.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            lines.append(
                f"[{timestamp}] "
                f"{message.author} "
                f"({message.author.id})\n"
            )

            lines.append(
                f"{message.content or '[بدون نص]'}\n"
            )

            if message.attachments:

                for attachment in message.attachments:

                    lines.append(
                        f"📎 {attachment.url}\n"
                    )

            lines.append(
                "────────────────────────────────────────\n"
            )

    except discord.HTTPException as error:

        lines.append(
            f"\nTranscript Error: {error}\n"
        )

    data = "\n".join(lines).encode(
        "utf-8",
        errors="replace"
    )

    file = discord.File(
        io.BytesIO(data),
        filename=f"{channel.name}-transcript.txt"
    )

    embed = None

    if ticket:

        embed = build_ticket_embed(
            channel.guild,
            channel.id
        )

    await log_channel.send(
        content=f"📁 **نسخة التكت:** `{channel.name}`",
        embed=embed,
        file=file
    )


# ============================================================
# COG
# ============================================================

class Ticket(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # ========================================================
    # SETUP TICKET
    # ========================================================

    @app_commands.command(
        name="setup-ticket",
        description="إرسال لوحة تذاكر N9V"
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def setup_ticket(
        self,
        interaction: discord.Interaction
    ):

        channel = interaction.guild.get_channel(
            PANEL_CHANNEL_ID
        )

        if channel is None:

            await interaction.response.send_message(
                "❌ روم لوحة التكت غير موجود.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="🎫 N9V・TICKET",
            description=(
                "═══════════════════════════\n\n"
                "🩸 **دعم السيرفر**\n\n"
                "اختر نوع التكت المناسب لك من "
                "الأزرار بالأسفل.\n\n"
                "يرجى اختيار القسم الصحيح حتى يتم "
                "خدمتك بشكل أسرع.\n\n"
                "═══════════════════════════"
            ),
            color=BURGUNDY
        )

        embed.set_image(
            url=PANEL_IMAGE
        )

        embed.set_footer(
            text="N9V・SUPPORT SYSTEM"
        )

        await channel.send(
            embed=embed,
            view=TicketPanel()
        )

        await interaction.response.send_message(
            f"✅ تم إرسال لوحة التكت في {channel.mention}.",
            ephemeral=True
        )


# ============================================================
# IMPORTANT: MAIN.PY LOADS THIS
# ============================================================

async def setup(bot):
    await bot.add_cog(Ticket(bot))

    # تسجيل الأزرار الدائمة
    bot.add_view(TicketPanel())
    bot.add_view(TicketControls())
