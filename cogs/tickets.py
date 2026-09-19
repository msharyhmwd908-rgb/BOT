import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import io
from datetime import datetime


# =========================================================
# الإعدادات
# =========================================================

PANEL_IMAGE = "https://j.top4top.io/p_3914zdc6h0.jpg"

# رتبة الدعم
STAFF_ROLE_ID = 1550169763853111427

# كاتجوري التكت
# إذا لم توجد، سيتم فتح التكت بدون كاتجوري
CATEGORY_ID = 1550170033655910541

# روم إرسال نسخ التكتات
TRANSCRIPT_CHANNEL_ID = 1501909696766808155

# لون التكت
TICKET_COLOR = discord.Color.from_rgb(100, 0, 20)

# قاعدة البيانات
DB_NAME = "tickets.db"


# =========================================================
# DATABASE
# =========================================================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_counter (
            id INTEGER PRIMARY KEY,
            number INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS open_tickets (
            channel_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            ticket_number INTEGER NOT NULL,
            ticket_type TEXT NOT NULL,
            opened_at TEXT NOT NULL,
            claimed_by INTEGER DEFAULT NULL
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO ticket_counter (id, number)
        VALUES (1, 0)
    """)

    conn.commit()
    conn.close()


def get_next_ticket_number():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT number FROM ticket_counter WHERE id = 1"
    )

    row = cursor.fetchone()
    number = (row[0] if row else 0) + 1

    cursor.execute(
        "UPDATE ticket_counter SET number = ? WHERE id = 1",
        (number,)
    )

    conn.commit()
    conn.close()

    return number


def save_ticket(
    channel_id: int,
    user_id: int,
    ticket_number: int,
    ticket_type: str
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO open_tickets
        (channel_id, user_id, ticket_number, ticket_type, opened_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        channel_id,
        user_id,
        ticket_number,
        ticket_type,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def get_ticket(channel_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            channel_id,
            user_id,
            ticket_number,
            ticket_type,
            opened_at,
            claimed_by
        FROM open_tickets
        WHERE channel_id = ?
    """, (channel_id,))

    row = cursor.fetchone()
    conn.close()

    return row


def get_user_open_ticket(guild: discord.Guild, user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT channel_id
        FROM open_tickets
        WHERE user_id = ?
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        channel = guild.get_channel(row[0])

        if channel:
            return channel

        # الروم انحذف، نحذف السجل القديم
        delete_ticket(row[0])

    return None


def set_claimed(channel_id: int, user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE open_tickets
        SET claimed_by = ?
        WHERE channel_id = ?
    """, (user_id, channel_id))

    conn.commit()
    conn.close()


def delete_ticket(channel_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM open_tickets WHERE channel_id = ?",
        (channel_id,)
    )

    conn.commit()
    conn.close()


# =========================================================
# صلاحيات الدعم
# =========================================================

def is_staff(member: discord.Member):
    return (
        member.guild_permissions.manage_channels
        or any(role.id == STAFF_ROLE_ID for role in member.roles)
    )


# =========================================================
# Transcript
# =========================================================

async def create_transcript(channel: discord.TextChannel):

    lines = []

    async for message in channel.history(
        limit=None,
        oldest_first=True
    ):

        timestamp = message.created_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        content = message.content or ""

        if message.attachments:

            attachment_urls = []

            for attachment in message.attachments:
                attachment_urls.append(attachment.url)

            content += (
                "\nالمرفقات:\n"
                + "\n".join(attachment_urls)
            )

        if not content:
            content = "[بدون محتوى]"

        lines.append(
            f"[{timestamp}] "
            f"{message.author} ({message.author.id}): "
            f"{content}"
        )

    if not lines:
        lines.append("لا توجد رسائل.")

    return "\n".join(lines)


# =========================================================
# إرسال النسخة للعضو
# =========================================================

async def send_transcript_to_user(
    user: discord.User,
    channel: discord.TextChannel,
    transcript: str
):

    try:

        file = discord.File(
            io.BytesIO(transcript.encode("utf-8")),
            filename=f"{channel.name}-transcript.txt"
        )

        embed = discord.Embed(
            title="📁 نسخة التذكرة",
            description=(
                "تم إغلاق التذكرة وإرسال نسخة منها لك.\n\n"
                "⚠️ **في حال حصل أي شيء من إهانة أو إساءة "
                "داخل التكت، يمكنك مطالبة الإدارة العليا "
                "بمراجعة نسخة التكت واتخاذ الإجراء المناسب.**"
            ),
            color=TICKET_COLOR,
            timestamp=datetime.now()
        )

        embed.set_image(url=PANEL_IMAGE)

        await user.send(
            embed=embed,
            file=file
        )

    except discord.Forbidden:
        pass


# =========================================================
# إرسال النسخة للإدارة العليا
# =========================================================

async def send_transcript_to_log(
    guild: discord.Guild,
    channel: discord.TextChannel,
    opener: discord.User,
    transcript: str
):

    log_channel = guild.get_channel(
        TRANSCRIPT_CHANNEL_ID
    )

    if not isinstance(
        log_channel,
        discord.TextChannel
    ):
        return

    ticket = get_ticket(channel.id)

    ticket_number = (
        ticket[2]
        if ticket
        else "غير معروف"
    )

    file = discord.File(
        io.BytesIO(transcript.encode("utf-8")),
        filename=f"{channel.name}-transcript.txt"
    )

    embed = discord.Embed(
        title="📁 نسخة تذكرة مغلقة",
        color=TICKET_COLOR,
        timestamp=datetime.now()
    )

    embed.add_field(
        name="👤 صاحب التذكرة",
        value=opener.mention,
        inline=False
    )

    embed.add_field(
        name="🔢 رقم التذكرة",
        value=str(ticket_number),
        inline=True
    )

    embed.add_field(
        name="📁 اسم التذكرة",
        value=channel.name,
        inline=True
    )

    embed.add_field(
        name="🔒 أغلق التذكرة",
        value="سيتم تحديده من سجل الإغلاق",
        inline=False
    )

    embed.set_image(url=PANEL_IMAGE)

    await log_channel.send(
        embed=embed,
        file=file
    )


# =========================================================
# Modal تذكرة السيرفر
# =========================================================

class ServerTicketModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="🎫 تذكرة السيرفر"
        )

    reason = discord.ui.TextInput(
        label="ما سبب فتح التكت؟",
        placeholder="اكتب سبب فتح التكت...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    details = discord.ui.TextInput(
        label="شرح المشكلة / الطلب",
        placeholder="اشرح المشكلة أو الطلب بالتفصيل...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        await create_ticket(
            interaction=interaction,
            ticket_type="تذكرة السيرفر",
            reason=self.reason.value,
            details=self.details.value,
            roblox_user=None
        )


# =========================================================
# Modal تذكرة الماب
# =========================================================

class MapTicketModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(
            title="🎮 تذكرة الماب"
        )

    reason = discord.ui.TextInput(
        label="ما سبب فتح التكت؟",
        placeholder="اكتب سبب فتح التكت...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    roblox_user = discord.ui.TextInput(
        label="يوزرك في روبلوكس",
        placeholder="اكتب يوزرك في Roblox...",
        required=True,
        max_length=100
    )

    details = discord.ui.TextInput(
        label="التفاصيل",
        placeholder="اكتب تفاصيل المشكلة أو الطلب...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        await create_ticket(
            interaction=interaction,
            ticket_type="تذكرة الماب",
            reason=self.reason.value,
            details=self.details.value,
            roblox_user=self.roblox_user.value
        )


# =========================================================
# Select Menu
# =========================================================

class TicketSelect(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="تذكرة السيرفر",
                description="فتح تذكرة خاصة بالسيرفر",
                emoji="🌿",
                value="server"
            ),

            discord.SelectOption(
                label="تذكرة الماب",
                description="فتح تذكرة خاصة بالماب",
                emoji="🎮",
                value="map"
            )

        ]

        super().__init__(
            placeholder="🎫 اختر نوع التذكرة",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="rawabi_ticket_select"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        if not interaction.guild:
            return

        existing = get_user_open_ticket(
            interaction.guild,
            interaction.user.id
        )

        if existing:

            await interaction.response.send_message(
                f"❌ لديك تذكرة مفتوحة بالفعل:\n{existing.mention}",
                ephemeral=True
            )

            return

        if self.values[0] == "server":

            await interaction.response.send_modal(
                ServerTicketModal()
            )

        elif self.values[0] == "map":

            await interaction.response.send_modal(
                MapTicketModal()
            )


# =========================================================
# لوحة فتح التكت
# =========================================================

class TicketPanelView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

        self.add_item(
            TicketSelect()
        )


# =========================================================
# أزرار داخل التكت
# =========================================================

class TicketControlView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    # -----------------------------------------------------
    # استلام التكت
    # -----------------------------------------------------

    @discord.ui.button(
        label="استلام التذكرة",
        emoji="📥",
        style=discord.ButtonStyle.primary,
        custom_id="rawabi_ticket_claim"
    )
    async def claim_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ هذا الزر مخصص لفريق الدعم.",
                ephemeral=True
            )

            return

        ticket = get_ticket(
            interaction.channel.id
        )

        if not ticket:

            await interaction.response.send_message(
                "❌ لم يتم العثور على بيانات التكت.",
                ephemeral=True
            )

            return

        if ticket[5]:

            claimer = interaction.guild.get_member(
                ticket[5]
            )

            mention = (
                claimer.mention
                if claimer
                else f"<@{ticket[5]}>"
            )

            await interaction.response.send_message(
                f"❌ التكت مستلمة بالفعل من {mention}.",
                ephemeral=True
            )

            return

        set_claimed(
            interaction.channel.id,
            interaction.user.id
        )

        embed = discord.Embed(
            title="📥 تم استلام التذكرة",
            description=(
                f"تم استلام التذكرة بواسطة "
                f"{interaction.user.mention}\n\n"
                f"🛡️ **مشرف التذكرة:** "
                f"{interaction.user.mention}"
            ),
            color=TICKET_COLOR,
            timestamp=datetime.now()
        )

        await interaction.response.send_message(
            embed=embed
        )

    # -----------------------------------------------------
    # إغلاق التكت
    # -----------------------------------------------------

    @discord.ui.button(
        label="إغلاق التذكرة",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="rawabi_ticket_close"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return

        if not is_staff(interaction.user):

            await interaction.response.send_message(
                "❌ لا تملك صلاحية إغلاق التذكرة.",
                ephemeral=True
            )

            return

        channel = interaction.channel

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            return

        ticket = get_ticket(channel.id)

        if not ticket:

            await interaction.response.send_message(
                "❌ لم يتم العثور على بيانات التكت.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🔒 جاري حفظ نسخة التذكرة وإغلاقها..."
        )

        # صاحب التكت
        opener = interaction.guild.get_member(
            ticket[1]
        )

        if opener is None:
            opener = await interaction.guild.fetch_member(
                ticket[1]
            )

        # إنشاء النسخة
        transcript = await create_transcript(
            channel
        )

        # إرسال النسخة للإدارة
        await send_transcript_to_log(
            guild=interaction.guild,
            channel=channel,
            opener=opener,
            transcript=transcript
        )

        # إرسال النسخة للعضو
        await send_transcript_to_user(
            user=opener,
            channel=channel,
            transcript=transcript
        )

        # حذف من قاعدة البيانات
        delete_ticket(channel.id)

        # حذف الروم
        await channel.delete(
            reason=(
                f"Ticket closed by "
                f"{interaction.user} ({interaction.user.id})"
            )
        )


# =========================================================
# إنشاء التكت
# =========================================================

async def create_ticket(
    interaction: discord.Interaction,
    ticket_type: str,
    reason: str,
    details: str,
    roblox_user: str | None
):

    guild = interaction.guild

    if guild is None:
        return

    # التأكد من عدم وجود تكت
    existing = get_user_open_ticket(
        guild,
        interaction.user.id
    )

    if existing:

        await interaction.response.send_message(
            f"❌ لديك تذكرة مفتوحة بالفعل:\n{existing.mention}",
            ephemeral=True
        )

        return

    # رقم التكت
    ticket_number = get_next_ticket_number()

    # اسم الروم
    if ticket_type == "تذكرة السيرفر":
        prefix = "تذكرة-السيرفر"
    else:
        prefix = "تذكرة-الماب"

    channel_name = (
        f"{prefix}-{ticket_number:03d}"
    )

    # الكاتجوري
    category = guild.get_channel(
        CATEGORY_ID
    )

    if not isinstance(
        category,
        discord.CategoryChannel
    ):
        category = None

    # رتبة الدعم
    staff_role = guild.get_role(
        STAFF_ROLE_ID
    )

    # صلاحيات الروم
    overwrites = {

        guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        interaction.user:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )
    }

    if staff_role:

        overwrites[staff_role] = (
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            )
        )

    # إنشاء الروم
    channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        reason=f"Ticket opened by {interaction.user}"
    )

    # حفظ التكت
    save_ticket(
        channel_id=channel.id,
        user_id=interaction.user.id,
        ticket_number=ticket_number,
        ticket_type=ticket_type
    )

    # إظهار رسالة التكت للشخص
    await interaction.response.send_message(
        f"✅ تم فتح التذكرة الخاصة بك:\n{channel.mention}",
        ephemeral=True
    )

    # =====================================================
    # المنشنات
    # =====================================================

    staff_mention = (
        staff_role.mention
        if staff_role
        else f"<@&{STAFF_ROLE_ID}>"
    )

    content = (
        f"{interaction.user.mention} "
        f"{staff_mention}"
    )

    # =====================================================
    # Embed معلومات التكت
    # =====================================================

    now = datetime.now()

    embed = discord.Embed(
        color=TICKET_COLOR
    )

    # مالك التذكرة
    embed.add_field(
        name="👤 مالك التذكرة:",
        value=interaction.user.mention,
        inline
