import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import io
from datetime import datetime

PANEL_IMAGE = "https://j.top4top.io/p_3914zdc6h0.jpg"
STAFF_ROLE_ID = 1550169763853111427
CATEGORY_ID = 1550170033655910541
TRANSCRIPT_CHANNEL_ID = 1501909696766808155
DB_NAME = "tickets.db"
COLOR = discord.Color.from_rgb(100, 0, 20)


# ================= DATABASE =================

def db():
    c = sqlite3.connect(DB_NAME)
    c.execute("""CREATE TABLE IF NOT EXISTS tickets(
        channel INTEGER PRIMARY KEY,
        user INTEGER,
        number INTEGER,
        type TEXT,
        claimed INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS counter(
        id INTEGER PRIMARY KEY,
        number INTEGER DEFAULT 0
    )""")
    c.execute("INSERT OR IGNORE INTO counter VALUES(1,0)")
    c.commit()
    return c


def next_number():
    c = db()
    n = c.execute("SELECT number FROM counter WHERE id=1").fetchone()[0] + 1
    c.execute("UPDATE counter SET number=? WHERE id=1", (n,))
    c.commit()
    c.close()
    return n


def get_ticket(channel):
    c = db()
    x = c.execute(
        "SELECT * FROM tickets WHERE channel=?",
        (channel,)
    ).fetchone()
    c.close()
    return x


def user_ticket(user):
    c = db()
    x = c.execute(
        "SELECT channel FROM tickets WHERE user=?",
        (user,)
    ).fetchone()
    c.close()
    return x[0] if x else None


# ================= TRANSCRIPT =================

async def transcript(channel):
    text = []

    async for m in channel.history(
        limit=None,
        oldest_first=True
    ):
        content = m.content or "[بدون محتوى]"

        if m.attachments:
            content += "\n" + "\n".join(
                a.url for a in m.attachments
            )

        text.append(
            f"[{m.created_at:%Y-%m-%d %H:%M:%S}] "
            f"{m.author}: {content}"
        )

    return "\n".join(text) or "لا توجد رسائل."


# ================= MODALS =================

class ServerModal(discord.ui.Modal, title="🌿 تذكرة السيرفر"):

    reason = discord.ui.TextInput(
        label="ما سبب فتح التكت؟",
        style=discord.TextStyle.paragraph
    )

    details = discord.ui.TextInput(
        label="شرح المشكلة / الطلب",
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, i):
        await create_ticket(
            i,
            "تذكرة السيرفر",
            self.reason.value,
            self.details.value,
            None
        )


class MapModal(discord.ui.Modal, title="🎮 تذكرة الماب"):

    reason = discord.ui.TextInput(
        label="ما سبب فتح التكت؟",
        style=discord.TextStyle.paragraph
    )

    roblox = discord.ui.TextInput(
        label="يوزرك في روبلوكس"
    )

    details = discord.ui.TextInput(
        label="التفاصيل",
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, i):
        await create_ticket(
            i,
            "تذكرة الماب",
            self.reason.value,
            self.details.value,
            self.roblox.value
        )


# ================= SELECT =================

class TicketSelect(discord.ui.Select):

    def __init__(self):
        super().__init__(
            placeholder="🎫 اختر نوع التذكرة",
            custom_id="rawabi_ticket_select",
            options=[
                discord.SelectOption(
                    label="تذكرة السيرفر",
                    emoji="🌿",
                    value="server"
                ),
                discord.SelectOption(
                    label="تذكرة الماب",
                    emoji="🎮",
                    value="map"
                )
            ]
        )

    async def callback(self, i):

        if user_ticket(i.user.id):
            ch = i.guild.get_channel(
                user_ticket(i.user.id)
            )

            if ch:
                return await i.response.send_message(
                    f"❌ لديك تكت مفتوحة: {ch.mention}",
                    ephemeral=True
                )

        await i.response.send_modal(
            ServerModal()
            if self.values[0] == "server"
            else MapModal()
        )


# ================= PANEL VIEW =================

class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# ================= TICKET BUTTONS =================

class TicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="استلام التذكرة",
        emoji="📥",
        style=discord.ButtonStyle.primary,
        custom_id="rawabi_ticket_claim"
    )
    async def claim(self, i, button):

        if not isinstance(i.user, discord.Member):
            return

        if (
            not i.user.guild_permissions.manage_channels
            and STAFF_ROLE_ID not in [r.id for r in i.user.roles]
        ):
            return await i.response.send_message(
                "❌ هذا الزر لفريق الدعم فقط.",
                ephemeral=True
            )

        t = get_ticket(i.channel.id)

        if not t:
            return await i.response.send_message(
                "❌ التكت غير موجودة.",
                ephemeral=True
            )

        if t[4]:
            return await i.response.send_message(
                "❌ التكت مستلمة بالفعل.",
                ephemeral=True
            )

        c = db()
        c.execute(
            "UPDATE tickets SET claimed=? WHERE channel=?",
            (i.user.id, i.channel.id)
        )
        c.commit()
        c.close()

        await i.response.send_message(
            embed=discord.Embed(
                title="📥 تم استلام التذكرة",
                description=f"تم استلام التذكرة بواسطة {i.user.mention}",
                color=COLOR
            )
        )

    @discord.ui.button(
        label="إغلاق التذكرة",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="rawabi_ticket_close"
    )
    async def close(self, i, button):

        if not isinstance(i.user, discord.Member):
            return

        if (
            not i.user.guild_permissions.manage_channels
            and STAFF_ROLE_ID not in [r.id for r in i.user.roles]
        ):
            return await i.response.send_message(
                "❌ لا تملك صلاحية إغلاق التكت.",
                ephemeral=True
            )

        t = get_ticket(i.channel.id)

        if not t:
            return await i.response.send_message(
                "❌ التكت غير موجودة.",
                ephemeral=True
            )

        await i.response.send_message(
            "🔒 جاري حفظ التكت وإغلاقها..."
        )

        data = await transcript(i.channel)

        file = discord.File(
            io.BytesIO(data.encode("utf-8")),
            filename=f"{i.channel.name}.txt"
        )

        log = i.guild.get_channel(
            TRANSCRIPT_CHANNEL_ID
        )

        if log:
            await log.send(
                embed=discord.Embed(
                    title="📁 تكت مغلقة",
                    description=(
                        f"👤 العضو: <@{t[1]}>\n"
                        f"🔢 الرقم: `{t[2]}`\n"
                        f"🎫 النوع: {t[3]}\n"
                        f"🔒 أغلقها: {i.user.mention}"
                    ),
                    color=COLOR
                ),
                file=file
            )

        try:
            user = await i.guild.fetch_member(t[1])

            dm_file = discord.File(
                io.BytesIO(data.encode("utf-8")),
                filename=f"{i.channel.name}.txt"
            )

            await user.send(
                "📁 تم إغلاق التكت وإرسال نسختها لك.\n\n"
                "⚠️ إذا حصلت إهانة أو إساءة داخل التكت، "
                "يمكنك مطالبة الإدارة العليا بمراجعة النسخة "
                "واتخاذ الإجراء المناسب.",
                file=dm_file
            )

        except:
            pass

        c = db()
        c.execute(
            "DELETE FROM tickets WHERE channel=?",
            (i.channel.id,)
        )
        c.commit()
        c.close()

        await i.channel.delete()


# ================= CREATE =================

async def create_ticket(
    i,
    ticket_type,
    reason,
    details,
    roblox
):

    old = user_ticket(i.user.id)

    if old:
        ch = i.guild.get_channel(old)

        if ch:
            return await i.response.send_message(
                f"❌ لديك تكت مفتوحة: {ch.mention}",
                ephemeral=True
            )

        c = db()
        c.execute(
            "DELETE FROM tickets WHERE channel=?",
            (old,)
        )
        c.commit()
        c.close()

    number = next_number()

    name = (
        f"تذكرة-السيرفر-{number:03d}"
        if ticket_type == "تذكرة السيرفر"
        else f"تذكرة-الماب-{number:03d}"
    )

    category = i.guild.get_channel(CATEGORY_ID)

    if not isinstance(category, discord.CategoryChannel):
        category = None

    staff = i.guild.get_role(STAFF_ROLE_ID)

    overwrites = {
        i.guild.default_role:
            discord.PermissionOverwrite(
                view_channel=False
            ),

        i.user:
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            )
    }

    if staff:
        overwrites[staff] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True
        )

    ch = await i.guild.create_text_channel(
        name=name,
        category=category,
        overwrites=overwrites
    )

    c = db()
    c.execute(
        "INSERT INTO tickets VALUES(?,?,?,?,0)",
        (
            ch.id,
            i.user.id,
            number,
            ticket_type
        )
    )
    c.commit()
    c.close()

    await i.response.send_message(
        f"✅ تم فتح التكت: {ch.mention}",
        ephemeral=True
    )

    embed = discord.Embed(
        color=COLOR
    )

    embed.add_field(
        name="👤 مالك التذكرة:",
        value=i.user.mention,
        inline=False
    )

    embed.add_field(
        name="🛡️ مشرفي التذاكر:",
        value=staff.mention if staff else "غير موجود",
        inline=False
    )

    embed.add_field(
        name="📅 تاريخ التذكرة:",
        value=f"<t:{int(datetime.now().timestamp())}:F>",
        inline=False
    )

    embed.add_field(
        name="🔢 رقم التذكرة:",
        value=f"`{number}`",
        inline=False
    )

    embed.add_field(
        name="🎫 قسم التذكرة:",
        value=ticket_type,
        inline=False
    )

    embed.set_image(url=PANEL_IMAGE)

    await ch.send(
        content=f"{i.user.mention} {staff.mention if staff else ''}",
        embed=embed,
        view=TicketView()
    )

    info = discord.Embed(
        title="📝 تفاصيل التذكرة",
        color=COLOR
    )

    info.add_field(
        name="سبب فتح التكت",
        value=reason,
        inline=False
    )

    info.add_field(
        name="شرح المشكلة / الطلب",
        value=details,
        inline=False
    )

    if roblox:
        info.add_field(
            name="🎮 يوزر روبلوكس",
            value=roblox,
            inline=False
        )

    info.add_field(
        name="📎 الدليل",
        value="يرجى إرسال الدليل داخل التكت.",
        inline=False
    )

    await ch.send(embed=info)


# ================= COG =================

class Tickets(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        db()

    @app_commands.command(
        name="ticket-panel",
        description="إرسال لوحة فتح التذاكر"
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def ticket_panel(self, i):

        embed = discord.Embed(
            title="🌿 مرحبًا بكم في الدعم الفني لشاليه روابي 🌿",
            description=(
                "نسعد بخدمتكم ومساعدتكم، ونسعى دائمًا "
                "لتقديم أفضل تجربة ممكنة لكم 🤍\n\n"
                "📌 **قبل فتح التكت:**\n"
                "• اكتب سبب التكت بوضوح.\n"
                "• اشرح المشكلة أو الطلب بالتفصيل.\n"
                "• أرفق الدليل إن وجد.\n"
                "• يمنع فتح أكثر من تكت لنفس المشكلة.\n"
                "• يرجى احترام فريق الدعم.\n\n"
                "⚠️ **تنبيه:**\n"
                "يرجى الانتظار حتى يرد عليك أحد أعضاء الدعم.\n\n"
                "**فريق دعم شاليه روابي**"
            ),
            color=COLOR
        )

        embed.set_image(url=PANEL_IMAGE)

        await i.channel.send(
            embed=embed,
            view=TicketPanelView()
        )

        await i.response.send_message(
            "✅ تم إرسال لوحة التكت.",
            ephemeral=True
        )


async def setup(bot):

    await bot.add_cog(Tickets(bot))

    # Persistent Views
    bot.add_view(TicketPanelView())
    bot.add_view(TicketView())
