# cogs/ticket.py
# N9V Ticket System
# discord.py 2.x

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import asyncio
from datetime import datetime
import io
import re


# ═════════════════════════════════════════════════════════════
# CONFIG
# ═════════════════════════════════════════════════════════════

TICKET_CATEGORY_ID = 1548014683695620116
PANEL_CHANNEL_ID = 1548014911932858398
LOG_CHANNEL_ID = 1495450684731162664

ADMIN_ROLE_ID = 1498008105819177240
OWNER_ROLE_ID = 1497718287956443249
COOWNER_ROLE_ID = 1497608751551746179

PANEL_IMAGE = "https://a.top4top.io/p_3910nb9nm0.png"

DB_FILE = "tickets.db"

BURGUNDY = discord.Color.from_rgb(105, 0, 20)
DARK_RED = discord.Color.from_rgb(75, 0, 15)


# ═════════════════════════════════════════════════════════════
# DATABASE
# ═════════════════════════════════════════════════════════════

db = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    channel_id INTEGER PRIMARY KEY,
    ticket_number INTEGER,
    ticket_type TEXT,
    reason TEXT,
    opener_id INTEGER,
    opened_at TEXT,
    claimed_by INTEGER DEFAULT 0,
    claimed_at TEXT DEFAULT '',
    closed_by INTEGER DEFAULT 0,
    closed_at TEXT DEFAULT '',
    close_reason TEXT DEFAULT '',
    status TEXT DEFAULT 'مفتوح'
)
""")

db.commit()


def next_ticket_number():
    cursor.execute("SELECT MAX(ticket_number) FROM tickets")
    result = cursor.fetchone()[0]
    return (result or 0) + 1


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_staff(member: discord.Member):
    staff_roles = {
        ADMIN_ROLE_ID,
        OWNER_ROLE_ID,
        COOWNER_ROLE_ID
    }

    return any(role.id in staff_roles for role in member.roles)


def get_ticket(channel_id):
    cursor.execute(
        "SELECT * FROM tickets WHERE channel_id = ?",
        (channel_id,)
    )
    return cursor.fetchone()


# ═════════════════════════════════════════════════════════════
# MODALS
# ═════════════════════════════════════════════════════════════

class ComplaintModal(discord.ui.Modal):
    def __init__(self, bot, complaint_type):
        super().__init__(
            title=f"شكوى على {complaint_type}"
        )

        self.bot = bot
        self.complaint_type = complaint_type

        self.target = discord.ui.TextInput(
            label=f"يوزر {complaint_type}",
            placeholder="اكتب اليوزر أو الـ ID",
            required=True,
            max_length=100
        )

        self.reason = discord.ui.TextInput(
            label="سبب الشكوى",
            placeholder="اكتب سبب الشكوى بالتفصيل",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.add_item(self.target)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):

        await create_ticket(
            interaction,
            self.complaint_type,
            f"الشكوى على: {self.target.value}\nسبب الشكوى: {self.reason.value}"
        )


class SupportModal(discord.ui.Modal):
    def __init__(self, bot):
        super().__init__(title="دعم فني")
        self.bot = bot

        self.problem = discord.ui.TextInput(
            label="ما هي مشكلتك؟",
            placeholder="اكتب مشكلتك هنا...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500
        )

        self.add_item(self.problem)

    async def on_submit(self, interaction: discord.Interaction):

        await create_ticket(
            interaction,
            "دعم فني",
            self.problem.value
        )


class CloseModal(discord.ui.Modal):
    def __init__(self, ticket_channel):
        super().__init__(title="إغلاق التكت")
        self.ticket_channel = ticket_channel

        self.solved = discord.ui.TextInput(
            label="هل تم حل المشكلة؟",
            placeholder="نعم / لا",
            required=True,
            max_length=20
        )

        self.reason = discord.ui.TextInput(
            label="سبب إغلاق التكت",
            placeholder="اكتب سبب الإغلاق...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )

        self.add_item(self.solved)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):

        if not is_staff(interaction.user):
            await interaction.response.send_message(
                "❌ مانت أدمن، روح نام 😴",
                ephemeral=True
            )
            return

        ticket = get_ticket(self.ticket_channel.id)

        if not ticket:
            await interaction.response.send_message(
                "❌ بيانات التكت غير موجودة.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 تم تسجيل طلب الإغلاق.\nسيتم إغلاق التكت خلال **15 ثانية**.",
            ephemeral=True
        )

        await asyncio.sleep(15)

        cursor.execute("""
            UPDATE tickets
            SET closed_by = ?,
                closed_at = ?,
                close_reason = ?,
                status = ?
            WHERE channel_id = ?
        """, (
            interaction.user.id,
            now(),
            self.reason.value,
            "مغلق",
            self.ticket_channel.id
        ))

        db.commit()

        # تحديث لوحة البيانات
        try:
            messages = [
                message async for message in self.ticket_channel.history(
                    limit=100
                )
            ]

            for message in messages:
                if message.author == self.ticket_channel.guild.me:
                    if message.embeds:
                        if message.embeds[0].title == "🎫 N9V・TICKET DATA":
                            await message.edit(
                                embed=build_ticket_embed(
                                    self.ticket_channel.id
                                )
                            )
                            break
        except Exception:
            pass

        # إرسال التقييم للعضو
        opener_id = ticket[4]
        claimed_by = ticket[6]

        opener = self.ticket_channel.guild.get_member(opener_id)

        if opener and claimed_by:
            staff = self.ticket_channel.guild.get_member(claimed_by)

            try:
                await opener.send(
                    embed=discord.Embed(
                        title="⭐ تقييم الدعم",
                        description=(
                            f"تم إغلاق تذكرتك **#{ticket[1]:04d}**.\n\n"
                            f"الإداري: {staff.mention if staff else 'غير معروف'}\n\n"
                            "اضغط على عدد النجوم لتقييم الإداري."
                        ),
                        color=BURGUNDY
                    ),
                    view=RatingView(
                        claimed_by,
                        self.ticket_channel.id
                    )
                )
            except discord.Forbidden:
                pass

        # إرسال نسخة التكت
        await send_transcript(self.ticket_channel)

        await asyncio.sleep(2)

        try:
            await self.ticket_channel.delete(
                reason="Ticket closed"
            )
        except discord.HTTPException:
            pass


class AddMemberModal(discord.ui.Modal):
    def __init__(self, ticket_channel):
        super().__init__(title="إضافة عضو للتكت")
        self.ticket_channel = ticket_channel

        self.member_input = discord.ui.TextInput(
            label="ID أو يوزر العضو",
            placeholder="ضع الـ ID أو اليوزر هنا",
            required=True,
            max_length=100
        )

        self.add_item(self.member_input)

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
            await self.ticket_channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            )

            await interaction.response.send_message(
                f"✅ تم إضافة {member.mention} للتكت.",
                ephemeral=True
            )

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ ما قدرت أضيف العضو.",
                ephemeral=True
            )


class RemoveMemberModal(discord.ui.Modal):
    def __init__(self, ticket_channel):
        super().__init__(title="طرد عضو من التكت")
        self.ticket_channel = ticket_channel

        self.member_input = discord.ui.TextInput(
            label="ID أو يوزر العضو",
            placeholder="ضع الـ ID أو اليوزر هنا",
            required=True,
            max_length=100
        )

        self.add_item(self.member_input)

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
            await self.ticket_channel.set_permissions(
                member,
                overwrite=None
            )

            await interaction.response.send_message(
                f"✅ تم طرد {member.mention} من التكت.",
                ephemeral=True
            )

        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ ما قدرت أطرد العضو.",
                ephemeral=True
            )


class RatingReasonModal(discord.ui.Modal):
    def __init__(self, stars, staff_id, ticket_channel_id):
        super().__init__(title="سبب التقييم")

        self.stars = stars
        self.staff_id = staff_id
        self.ticket_channel_id = ticket_channel_id

        self.reason = discord.ui.TextInput(
            label="سبب التقييم",
            placeholder="اكتب سبب تقييمك...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):

        guild = interaction.guild

        staff = guild.get_member(self.staff_id) if guild else None

        log
