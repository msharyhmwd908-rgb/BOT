import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

# الأيدي المطلوب
OWNER_ID = 1497718287956443249
ADMIN_ROLE_ID = 1498008105819177240
LOG_CHANNEL_ID = 1495450684731162664
TICKET_CATEGORY_ID = 1548014683695620116

COUNTER_FILE = "ticket_counter.txt"

def get_next_ticket_number():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w") as f:
            f.write("1")
        return 1
    with open(COUNTER_FILE, "r") as f:
        try:
            num = int(f.read().strip())
        except:
            num = 1
    with open(COUNTER_FILE, "w") as f:
        f.write(str(num + 1))
    return num

tickets_db = {}

class TicketModal(discord.ui.Modal):
    def __init__(self, ticket_type: str):
        super().__init__(title=f"تكت: {ticket_type}")
        self.ticket_type = ticket_type

        if ticket_type in ["شكوى على عضو", "شكوى على إداري"]:
            self.target_user = discord.ui.TextInput(
                label="يوزر الشخص (بالاسم تماماً وليس الآيدي)",
                placeholder="مثلا: username",
                required=True,
                max_length=100
            )
            self.reason = discord.ui.TextInput(
                label="سبب الشكوى",
                style=discord.TextStyle.paragraph,
                placeholder="اشرح سبب الشكوى بالتفصيل...",
                required=True,
                max_length=1000
            )
            self.add_item(self.target_user)
            self.add_item(self.reason)
        else:
            self.reason = discord.ui.TextInput(
                label="ما هي مشكلتك؟",
                style=discord.TextStyle.paragraph,
                placeholder="اشرح مشكلتك هنا...",
                required=True,
                max_length=1000
            )
            self.target_user = None
            self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild = interaction.guild
        category = guild.get_channel(TICKET_CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)

        # ضبط الصلاحيات: الأعضاء العاديين لا يرون القناة، فاتح التكت ورتبة الإدارة يرونها
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_channels=True)
        }

        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True)

        ticket_number = get_next_ticket_number()
        channel_name = f"ticket-{ticket_number:04d}"
        
        try:
            ticket_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        except Exception as e:
            await interaction.followup.send(f"❌ حدث خطأ أثناء إنشاء القناة (تأكد من صلاحيات البوت وأيدي الفئة): {e}", ephemeral=True)
            return

        target_txt = self.target_user.value if self.target_user else "لا يوجد"
        reason_txt = self.reason.value

        tickets_db[ticket_channel.id] = {
            "opener": interaction.user.id,
            "opener_mention": interaction.user.mention,
            "type": self.ticket_type,
            "reason": reason_txt,
            "target": target_txt,
            "open_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "claimed_by": "—",
            "claimed_time": "—",
            "closed_by": "—",
            "close_time": "—",
            "status": "مفتوح",
            "close_reason": "—",
            "allowed_users": [interaction.user.id]
        }

        embed = discord.Embed(
            title="╔════════════════════════════╗\n    🎫 N9V・TICKET DATA\n╚════════════════════════════╝",
            color=0x9B59B6
        )
        embed.description = (
            f"🆔 **رقم التكت:** `{ticket_number:04d}`\n"
            f"—\n"
            f"📂 **نوع التكت:** {self.ticket_type}\n"
            f"—\n"
            f"📝 **سبب فتح التكت:** {reason_txt}\n"
            f"—\n"
            f"👤 **فاتح التكت:** {interaction.user.mention}\n"
            f"—\n"
            f"🕐 **وقت الفتح:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"—\n"
            f"🛡️ **الإداري المستلم:** —\n"
            f"—\n"
            f"⏱️ **وقت الاستلام:** —\n"
            f"—\n"
            f"🔒 **الإداري المُغلق:** —\n"
            f"—\n"
            f"🕰️ **وقت الإغلاق:** —\n"
            f"—\n"
            f"📊 **حالة التكت:** مفتوح\n"
            f"—\n"
            f"📌 **سبب الإغلاق:** —\n\n"
            f"╔════════════════════════════╗\n"
            f"    🩸 N9V・SUPPORT\n"
            f"╚════════════════════════════╝"
        )

        if self.ticket_type in ["شكوى على عضو", "شكوى على إداري"]:
            embed.add_field(name="🎯 المشكو في حقه", value=target_txt, inline=False)
            embed.add_footer(text="أرسل الدليل (صور/روابط) داخل التكت الآن.")

        await ticket_channel.send(content=f"{interaction.user.mention}", embed=embed, view=TicketControlView())
        await interaction.followup.send(f"✅ تم فتح تكت الخاص بك بنجاح: {ticket_channel.mention}", ephemeral=True)

class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إستفسار", style=discord.ButtonStyle.primary, custom_id="ticket_query_v2", emoji="❓")
    async def query_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal("إستفسار"))

    @discord.ui.button(label="شكوى على عضو", style=discord.ButtonStyle.danger, custom_id="ticket_member_comp_v2", emoji="⚠️")
    async def member_comp(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal("شكوى على عضو"))

    @discord.ui.button(label="شكوى على إداري", style=discord.ButtonStyle.danger, custom_id="ticket_admin_comp_v2", emoji="🛡️")
    async def admin_comp(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal("شكوى على إداري"))

    @discord.ui.button(label="دعم فني", style=discord.ButtonStyle.success, custom_id="ticket_support_v2", emoji="🛠️")
    async def support_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal("دعم فني"))

class CloseReasonModal(discord.ui.Modal, title="سبب إغلاق التكت"):
    reason_input = discord.ui.TextInput(
        label="هل تم حل المشكلة؟ (اكتب السبب)",
        style=discord.TextStyle.paragraph,
        placeholder="اكتب هنا...",
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        data = tickets_db.get(channel.id, {})
        data["closed_by"] = interaction.user.mention
        data["close_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["status"] = "مغلق"
        data["close_reason"] = self.reason_input.value

        await interaction.followup.send("🔒 جاري إغلاق التكت وإرسال النسخة الاحتياطية...", ephemeral=True)

        opener_id = data.get("opener")
        opener_user = interaction.guild.get_member(opener_id) or await interaction.client.fetch_user(opener_id)
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)

        history_msgs = [f"[{m.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {m.author}: {m.content}" async for m in channel.history(limit=None, oldest_first=True)]
        log_text = f"نسخة احتياطية للتكت: {channel.name}\n" + "\n".join(history_msgs)
        
        file_path = f"transcript_{channel.id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(log_text)

        if opener_user:
            try:
                await opener_user.send(f"📁 هذه نسختك الاحتياطية للتكت المغلق في سيرفر {interaction.guild.name}:", file=discord.File(file_path))
            except:
                pass
        
        if log_channel:
            await log_channel.send(f"📁 أرشيف التكت المغلق `{channel.name}`:", file=discord.File(file_path))

        if opener_user:
            try:
                await opener_user.send("⭐ نرجو تقييم تجربتك مع الإداري الذي خدمك في التكت:", view=RatingView())
            except:
                pass

        await channel.delete()

class RatingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⭐ 1", style=discord.ButtonStyle.secondary, custom_id="rate_1_v2")
    async def r1(self, interaction: discord.Interaction, b): await self.rate_cb(interaction, "1 نجمة")
    @discord.ui.button(label="⭐⭐ 2", style=discord.ButtonStyle.secondary, custom_id="rate_2_v2")
    async def r2(self, interaction: discord.Interaction, b): await self.rate_cb(interaction, "2 نجوم")
    @discord.ui.button(label="⭐⭐⭐ 3", style=discord.ButtonStyle.secondary, custom_id="rate_3_v2")
    async def r3(self, interaction: discord.Interaction, b): await self.rate_cb(interaction, "3 نجوم")
    @discord.ui.button(label="⭐⭐⭐⭐ 4", style=discord.ButtonStyle.primary, custom_id="rate_4_v2")
    async def r4(self, interaction: discord.Interaction, b): await self.rate_cb(interaction, "4 نجوم")
    @discord.ui.button(label="⭐⭐⭐⭐⭐ 5", style=discord.ButtonStyle.success, custom_id="rate_5_v2")
    async def r5(self, interaction: discord.Interaction, b): await self.rate_cb(interaction, "5 نجوم")
    @discord.ui.button(label="⭐⭐⭐⭐⭐⭐ 6", style=discord.ButtonStyle.success, custom_id="rate_6_v2")
    async def r6(self, interaction: discord.Interaction, b): await self.rate_cb(interaction, "6 نجوم (ممتاز جداً)")

    async def rate_cb(self, interaction: discord.Interaction, rating: str):
        await interaction.response.send_modal(RatingReasonModal(rating))

class RatingReasonModal(discord.ui.Modal, title="سبب التقييم"):
    def __init__(self, rating: str):
        super().__init__()
        self.rating = rating
    reason = discord.ui.TextInput(label="اكتب سبب هذا التقييم بالتفصيل", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ شكراً لك! تم تسجيل تقييمك ({self.rating}) بنجاح.", ephemeral=True)
        log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"📊 تقييم جديد من {interaction.user.mention}:\nالتقييم: {self.rating}\nالسبب: {self.reason.value}")

class PunishmentModal(discord.ui.Modal, title="إعطاء عقوبة لعضو في التكت"):
    def __init__(self, target_member: discord.Member):
        super().__init__()
        self.target_member = target_member
    
    punish_reason = discord.ui.TextInput(label="سبب العقوبة", required=True)
    duration = discord.ui.TextInput(label="مدة العقوبة (مثال: 1 ساعة، 30 دقيقة)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ تم تسجيل العقوبة على العضو `{self.target_member.name}` بنجاح.\nالسبب: {self.punish_reason.value}\nالمدة: {self.duration.value}", ephemeral=True)

class SelectPunishUserView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=m.name[:25], value=str(m.id)) for m in guild.members if not m.bot][:25]
        if options:
            self.add_item(PunishSelect(options))

class PunishSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="اختر العضو لمعاقبته...", options=options)
    async def callback(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(int(self.values[0]))
        await interaction.response.send_modal(PunishmentModal(member))

class AddUserSelectView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=m.name[:25], value=str(m.id)) for m in guild.members if not m.bot][:25]
        if options:
            self.add_item(UserSelect(options))

class UserSelect(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder="اختر الشخص لإدخاله للتكت...", options=options)
    async def callback(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(int(self.values[0]))
        channel = interaction.channel
        await channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
        if channel.id in tickets_db:
            tickets_db[channel.id]["allowed_users"].append(member.id)
        await interaction.response.send_message(f"✅ تم إدخال العضو {member.mention} إلى التكت بنجاح.", ephemeral=True)

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def is_admin(self, interaction: discord.Interaction) -> bool:
        role = interaction.guild.get_role(ADMIN_ROLE_ID)
        return (role in interaction.user.roles) or (interaction.user.id == OWNER_ID) or interaction.user.guild_permissions.administrator

    @discord.ui.button(label="استلام التكت", style=discord.ButtonStyle.success, custom_id="claim_ticket_v2", emoji="🙋‍♂️")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ مانت إداري يا عيون بابا!", ephemeral=True)
            return

        channel = interaction.channel
        data = tickets_db.get(channel.id, {})
        if data.get("claimed_by") != "—":
            await interaction.response.send_message(f"❌ مافيه، التكت ذا مستلمه إداري ثاني مسبقاً!", ephemeral=True)
            return

        data["claimed_by"] = interaction.user.mention
        data["claimed_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
        if admin_role:
            await channel.set_permissions(admin_role, send_messages=True)

        await interaction.response.send_message(f"✅ قام الإداري {interaction.user.mention} باستلام التكت بنجاح!", ephemeral=False)

    @discord.ui.button(label="إغلاق التكت", style=discord.ButtonStyle.danger, custom_id="close_ticket_v2", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ مانت إداري يا عيون بابا!", ephemeral=True)
            return
        await interaction.response.send_modal(CloseReasonModal())

    @discord.ui.button(label="استدعاء الإدارة", style=discord.ButtonStyle.secondary, custom_id="call_admin_v2", emoji="🚨")
    async def call_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ مانت إداري يا عيون بابا!", ephemeral=True)
            return
        await interaction.response.send_message(f"🚨 تم استدعاء الإدارة العامة بنجاح بواسطة {interaction.user.mention} <@&{ADMIN_ROLE_ID}>", ephemeral=False)

    @discord.ui.button(label="خيارات اخرى", style=discord.ButtonStyle.blurple, custom_id="other_options_v2", emoji="⚙️")
    async def other_options(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_admin(interaction):
            await interaction.response.send_message("❌ مانت إداري يا عيون بابا!", ephemeral=True)
            return
        await interaction.response.send_message("اختر الإجراء المطلوب:", view=OtherOptionsSubView(interaction.guild), ephemeral=True)

class OtherOptionsSubView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild

    @discord.ui.button(label="ادخال شخص", style=discord.ButtonStyle.primary, emoji="➕")
    async def add_person(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("اختر الشخص الذي تريد إدخاله:", view=AddUserSelectView(self.guild), ephemeral=True)

    @discord.ui.button(label="معاقبة", style=discord.ButtonStyle.danger, emoji="⚖️")
    async def punish_person(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("اختر العضو المراد معاقبته:", view=SelectPunishUserView(self.guild), ephemeral=True)

    @discord.ui.button(label="منشن الاونر", style=discord.ButtonStyle.secondary, emoji="👑")
    async def mention_owner(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"👑 تنبيه للـ Owner: <@{OWNER_ID}> تم استدعاؤك بواسطة {interaction.user.mention}", ephemeral=False)

    @discord.ui.button(label="ارسل نسخ احتياطيه", style=discord.ButtonStyle.success, emoji="📁")
    async def send_transcript_manual(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        history_msgs = [f"[{m.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {m.author}: {m.content}" async for m in channel.history(limit=None, oldest_first=True)]
        log_text = f"نسخة احتياطية يدوية للتكت: {channel.name}\n" + "\n".join(history_msgs)
        
        file_path = f"transcript_manual_{channel.id}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(log_text)

        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"📁 نسخة احتياطية يدوية طلبها {interaction.user.mention}:", file=discord.File(file_path))
            await interaction.response.send_message("✅ تم إرسال النسخة الاحتياطية إلى قناة السجلات بنجاح.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ لم يتم العثور على قناة السجلات المحددة.", ephemeral=True)

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_ticket", description="إرسال لوحة فتح التكتات الرئيسية")
    async def setup_ticket(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ هذا الأمر خاص بإدارة السيرفر.", ephemeral=True)
            return

        await interaction.response.send_message("✅ جاري إرسال لوحة التكتات...", ephemeral=True)
        
        embed = discord.Embed(
            title="N9V・SUPPORT SYSTEM",
            description="معليك لا تشيل هم انت بس افتح تكت وإنشاء لله تنحل مشكلتك",
            color=0x9B59B6
        )
        embed.set_image(url="https://c.top4top.io/p_3909gh1t30.png")
        
        await interaction.channel.send(embed=embed, view=TicketSelectView())

async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
